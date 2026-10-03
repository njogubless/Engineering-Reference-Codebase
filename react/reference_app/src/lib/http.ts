/**
 * A small typed HTTP client over `fetch`.
 *
 * Why not call `fetch` in components: every call site would have to repeat
 * timeouts, cancellation, retries, request IDs and error mapping — and most
 * would forget at least one. Why not axios: modern `fetch` + AbortController
 * cover everything below without a dependency.
 *
 * Guarantees:
 * - Every failure is thrown as `AppError` (see ./errors.ts).
 * - Every request has a timeout and can be cancelled by the caller's signal.
 * - Only idempotent requests are retried automatically (GET/HEAD/PUT/DELETE/OPTIONS,
 *   or any request carrying an `Idempotency-Key`). Retrying a plain POST could
 *   create a second order or charge a card twice.
 * - Retries use exponential backoff with full jitter and honour `Retry-After`.
 *
 * See docs/patterns/07-networking/README.md.
 */
import { AppError, codeForStatus, isProblem } from './errors';
import { logger } from './logger';

export type HttpMethod = 'GET' | 'HEAD' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'OPTIONS';

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  query?: Record<string, QueryValue>;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
  /** Makes a non-idempotent request safe to retry (the server must honour the key). */
  idempotencyKey?: string;
  /** Overrides the client's retry count for this request (e.g. 0 for probes and polling). */
  retries?: number;
}

export interface RetryPolicy {
  /** Retries after the first attempt (0 disables retrying). */
  retries: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

export interface HttpClientConfig {
  baseUrl: string;
  timeoutMs?: number;
  retry?: Partial<RetryPolicy>;
  /** Injected for tests; default `globalThis.fetch`. */
  fetch?: typeof fetch;
  /** Injected for tests; default real timers / Math.random. */
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
  random?: () => number;
  /**
   * Current access token, read at request time (never captured once), so a
   * sign-in or sign-out takes effect for the very next request.
   */
  getAccessToken?: () => string | null;
  /**
   * Called when a request that carried a token is rejected with 401: the
   * session is no longer valid. Phase 3 replaces "sign out" with a
   * single-flight token refresh.
   */
  onUnauthorized?: () => void;
}

export interface HttpClient {
  request<T>(method: HttpMethod, path: string, options?: RequestOptions): Promise<T>;
  get<T>(path: string, options?: RequestOptions): Promise<T>;
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>;
  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>;
  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>;
  delete<T>(path: string, options?: RequestOptions): Promise<T>;
}

const IDEMPOTENT_METHODS: ReadonlySet<HttpMethod> = new Set(['GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS']);
const RETRYABLE_STATUSES: ReadonlySet<number> = new Set([429, 502, 503, 504]);
const TIMEOUT = Symbol('timeout');
const CANCELLED = Symbol('cancelled');
const DEFAULT_RETRY: RetryPolicy = { retries: 2, baseDelayMs: 300, maxDelayMs: 5_000 };

export function createHttpClient(config: HttpClientConfig): HttpClient {
  const fetchImpl = config.fetch ?? globalThis.fetch.bind(globalThis);
  const sleep = config.sleep ?? abortableSleep;
  const random = config.random ?? Math.random;
  const retry: RetryPolicy = { ...DEFAULT_RETRY, ...config.retry };
  const defaultTimeoutMs = config.timeoutMs ?? 10_000;

  async function request<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
    const url = buildUrl(config.baseUrl, path, options.query);
    // One ID per logical request, shared by its retries, so server logs can
    // show "same request, attempt 2".
    const requestId = crypto.randomUUID();
    const headers: Record<string, string> = {
      Accept: 'application/json, application/problem+json',
      'X-Request-ID': requestId,
      ...options.headers,
    };
    if (options.body !== undefined) headers['Content-Type'] = 'application/json';
    if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey;
    const token = config.getAccessToken?.() ?? null;
    if (token !== null && headers.Authorization === undefined) headers.Authorization = `Bearer ${token}`;

    const canRetry = IDEMPOTENT_METHODS.has(method) || Boolean(options.idempotencyKey);
    const maxAttempts = canRetry ? (options.retries ?? retry.retries) + 1 : 1;

    for (let attempt = 1; ; attempt++) {
      const started = performance.now();
      try {
        const response = await fetchWithTimeout(
          fetchImpl,
          url,
          {
            method,
            headers,
            body: options.body === undefined ? undefined : JSON.stringify(options.body),
          },
          options.timeoutMs ?? defaultTimeoutMs,
          options.signal,
        );
        logger.debug('http_response', {
          method,
          path,
          status: response.status,
          attempt,
          durationMs: Math.round(performance.now() - started),
          requestId,
        });
        return await parseResponse<T>(response);
      } catch (error) {
        const appError = error instanceof AppError ? error : unexpected(error);
        if (appError.status === 401 && token !== null) config.onUnauthorized?.();
        if (attempt >= maxAttempts || !isRetryableError(appError)) throw appError;
        const delay = backoffDelay(attempt, retry, random, appError.retryAfterSeconds);
        logger.info('http_retry', { method, path, attempt, delayMs: delay, code: appError.code, requestId });
        try {
          await sleep(delay, options.signal);
        } catch {
          throw new AppError('cancelled', 'The request was cancelled.');
        }
      }
    }
  }

  return {
    request,
    get: (path, options) => request('GET', path, options),
    post: (path, body, options) => request('POST', path, { ...options, body }),
    put: (path, body, options) => request('PUT', path, { ...options, body }),
    patch: (path, body, options) => request('PATCH', path, { ...options, body }),
    delete: (path, options) => request('DELETE', path, options),
  };
}

function buildUrl(baseUrl: string, path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(path.replace(/^\//, ''), baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`);
  for (const [key, value] of Object.entries(query ?? {})) {
    // null/undefined mean "not set" — never send the string "undefined".
    if (value !== null && value !== undefined) url.searchParams.set(key, String(value));
  }
  return url.toString();
}

/**
 * Runs one attempt with its own timeout, while also honouring the caller's
 * signal. The two are distinguished so a timeout can be retried and a
 * user cancellation never is.
 */
async function fetchWithTimeout(
  fetchImpl: typeof fetch,
  url: string,
  init: RequestInit,
  timeoutMs: number,
  callerSignal?: AbortSignal,
): Promise<Response> {
  if (callerSignal?.aborted) throw new AppError('cancelled', 'The request was cancelled.');

  const controller = new AbortController();
  // The abort *reason* records why the attempt stopped.
  const timer = setTimeout(() => {
    controller.abort(TIMEOUT);
  }, timeoutMs);
  const onCallerAbort = () => {
    controller.abort(CANCELLED);
  };
  callerSignal?.addEventListener('abort', onCallerAbort, { once: true });

  try {
    return await fetchImpl(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (controller.signal.reason === TIMEOUT) {
      throw new AppError('timeout', 'The request timed out.', { cause: error });
    }
    if (controller.signal.reason === CANCELLED) {
      throw new AppError('cancelled', 'The request was cancelled.', { cause: error });
    }
    // fetch rejects (TypeError) only when no HTTP response was received.
    throw new AppError('network_error', 'Network request failed.', { cause: error });
  } finally {
    clearTimeout(timer);
    callerSignal?.removeEventListener('abort', onCallerAbort);
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const requestId = response.headers.get('X-Request-ID') ?? undefined;
  const text = await response.text();

  let data: unknown = undefined;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      if (response.ok) {
        throw new AppError('parse_error', 'The response was not valid JSON.', {
          status: response.status,
          requestId,
          cause: error,
        });
      }
      // A non-JSON error body (e.g. a proxy's HTML page) still has a meaningful status.
    }
  }

  if (response.ok) return data as T;

  if (isProblem(data)) throw AppError.fromProblem(data);
  throw new AppError(
    codeForStatus(response.status),
    `Request failed with status ${String(response.status)}.`,
    {
      status: response.status,
      requestId,
      retryAfterSeconds: parseRetryAfter(response.headers.get('Retry-After')),
    },
  );
}

function parseRetryAfter(header: string | null): number | undefined {
  if (header === null) return undefined;
  const seconds = Number(header);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : undefined;
}

function isRetryableError(error: AppError): boolean {
  if (error.code === 'network_error' || error.code === 'timeout') return true;
  return error.status !== undefined && RETRYABLE_STATUSES.has(error.status);
}

/** Exponential backoff with "full jitter": spreads retries so clients don't stampede a recovering server. */
export function backoffDelay(
  attempt: number,
  policy: RetryPolicy,
  random: () => number,
  retryAfterSeconds?: number,
): number {
  if (retryAfterSeconds !== undefined) return Math.min(retryAfterSeconds * 1000, policy.maxDelayMs);
  const ceiling = Math.min(policy.maxDelayMs, policy.baseDelayMs * 2 ** (attempt - 1));
  return Math.round(random() * ceiling);
}

function unexpected(error: unknown): AppError {
  return new AppError('internal_error', 'An unexpected client error occurred.', { cause: error });
}

function abortableSleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}
