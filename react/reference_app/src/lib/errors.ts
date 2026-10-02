/**
 * One error type for everything the app can fail at.
 *
 * Server errors arrive as RFC 9457 Problem Details (contracts/openapi.yaml);
 * the client adds the failures that never reach a server. Components and
 * hooks only ever see `AppError`, never `Response`, `TypeError` or `DOMException`.
 * See docs/patterns/30-error-handling/README.md.
 */
import type { components } from './api/schema';

export type Problem = components['schemas']['Problem'];
export type FieldError = components['schemas']['FieldError'];
export type ServerErrorCode = components['schemas']['ErrorCode'];

/** Failures detected by the client itself (no usable server response). */
export type ClientErrorCode = 'network_error' | 'timeout' | 'cancelled' | 'parse_error';

export type AppErrorCode = ServerErrorCode | ClientErrorCode;

interface AppErrorOptions {
  status?: number;
  fieldErrors?: FieldError[];
  requestId?: string;
  retryAfterSeconds?: number;
  cause?: unknown;
}

export class AppError extends Error {
  override readonly name = 'AppError';
  readonly code: AppErrorCode;
  readonly status: number | undefined;
  readonly fieldErrors: readonly FieldError[];
  readonly requestId: string | undefined;
  readonly retryAfterSeconds: number | undefined;

  constructor(code: AppErrorCode, message: string, options: AppErrorOptions = {}) {
    super(message, { cause: options.cause });
    this.code = code;
    this.status = options.status;
    this.fieldErrors = options.fieldErrors ?? [];
    this.requestId = options.requestId;
    this.retryAfterSeconds = options.retryAfterSeconds;
  }

  static fromProblem(problem: Problem): AppError {
    return new AppError(problem.code, problem.detail ?? problem.title, {
      status: problem.status,
      fieldErrors: problem.errors ?? [],
      requestId: problem.request_id,
      retryAfterSeconds: problem.retry_after,
    });
  }
}

export function isAppError(value: unknown): value is AppError {
  return value instanceof AppError;
}

const SERVER_ERROR_CODES: ReadonlySet<string> = new Set<ServerErrorCode>([
  'bad_request',
  'validation_error',
  'authentication_error',
  'authorization_error',
  'not_found',
  'method_not_allowed',
  'not_acceptable',
  'conflict',
  'idempotency_key_reused',
  'unsupported_media_type',
  'rate_limited',
  'internal_error',
  'external_service_error',
]);

/** Type guard for untrusted JSON: only a well-formed Problem is treated as one. */
export function isProblem(value: unknown): value is Problem {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.status === 'number' &&
    typeof candidate.title === 'string' &&
    typeof candidate.code === 'string' &&
    SERVER_ERROR_CODES.has(candidate.code)
  );
}

/** Best-effort code for an error response that is not Problem Details (e.g. a proxy's HTML 502). */
export function codeForStatus(status: number): ServerErrorCode {
  switch (status) {
    case 400:
      return 'bad_request';
    case 401:
      return 'authentication_error';
    case 403:
      return 'authorization_error';
    case 404:
      return 'not_found';
    case 405:
      return 'method_not_allowed';
    case 409:
      return 'conflict';
    case 415:
      return 'unsupported_media_type';
    case 422:
      return 'validation_error';
    case 429:
      return 'rate_limited';
    case 502:
    case 503:
    case 504:
      return 'external_service_error';
    default:
      return status >= 500 ? 'internal_error' : 'bad_request';
  }
}

/** Normalise anything thrown into an AppError (for boundaries and catch blocks). */
export function toAppError(error: unknown): AppError {
  if (isAppError(error)) return error;
  return new AppError('internal_error', 'An unexpected error occurred.', { cause: error });
}

function assertNever(value: never): never {
  throw new Error(`Unhandled error code: ${String(value)}`);
}

/**
 * What the user sees. Switches on `code`, never on `message`, and is
 * exhaustive: adding a code to the contract fails type checking here until
 * the UI decides how to present it.
 */
export function userMessage(error: AppError): string {
  switch (error.code) {
    case 'validation_error':
      return 'Please correct the highlighted fields.';
    case 'bad_request':
    case 'method_not_allowed':
    case 'not_acceptable':
    case 'unsupported_media_type':
      return 'The request could not be processed. Please try again or contact support.';
    case 'authentication_error':
      return 'Please sign in to continue.';
    case 'authorization_error':
      return 'You do not have permission to do this.';
    case 'not_found':
      return 'We could not find what you were looking for.';
    case 'conflict':
    case 'idempotency_key_reused':
      return 'This conflicts with a recent change. Refresh and try again.';
    case 'rate_limited':
      return error.retryAfterSeconds === undefined
        ? 'Too many attempts. Please wait a moment.'
        : `Too many attempts. Try again in ${String(error.retryAfterSeconds)} seconds.`;
    case 'external_service_error':
      return 'A service we depend on is unavailable. Please try again shortly.';
    case 'internal_error':
      return 'Something went wrong on our side. Please try again.';
    case 'network_error':
      return 'You appear to be offline. Check your connection and try again.';
    case 'timeout':
      return 'The server took too long to respond. Please try again.';
    case 'cancelled':
      return 'The request was cancelled.';
    case 'parse_error':
      return 'We received an unexpected response. Please try again.';
    default:
      return assertNever(error.code);
  }
}

/** Errors where an immediate "Try again" button makes sense. */
export function isRetryable(error: AppError): boolean {
  return ['network_error', 'timeout', 'external_service_error', 'internal_error', 'rate_limited'].includes(
    error.code,
  );
}
