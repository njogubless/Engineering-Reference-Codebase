import { delay, http as mock, HttpResponse } from 'msw';

import { AppError } from './errors';
import { backoffDelay, createHttpClient, type HttpClientConfig } from './http';
import { API, server } from '../test/server';

function client(overrides: Partial<HttpClientConfig> = {}) {
  const sleeps: number[] = [];
  const instance = createHttpClient({
    baseUrl: API,
    sleep: (ms) => {
      sleeps.push(ms);
      return Promise.resolve();
    },
    random: () => 0.5,
    ...overrides,
  });
  return { http: instance, sleeps };
}

async function captureError(promise: Promise<unknown>): Promise<AppError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof AppError) return error;
    throw error;
  }
  throw new Error('expected the request to fail');
}

const problem = (status: number, code: string, extra: Record<string, unknown> = {}) =>
  HttpResponse.json(
    { type: `https://errors.reference.dev/${code}`, title: 'T', status, code, request_id: 'srv-1', ...extra },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );

describe('requests', () => {
  it('sends JSON, query params and a request ID, and parses JSON', async () => {
    let seen: Request | undefined;
    server.use(
      mock.post(`${API}/api/v1/things`, async ({ request }) => {
        seen = request.clone();
        return HttpResponse.json({ id: 1 }, { status: 201 });
      }),
    );
    const { http } = client();
    const result = await http.post<{ id: number }>(
      '/api/v1/things',
      { name: 'a' },
      { query: { page: 2, skip: undefined } },
    );
    expect(result).toEqual({ id: 1 });
    expect(new URL(seen!.url).search).toBe('?page=2');
    expect(seen!.headers.get('content-type')).toBe('application/json');
    expect(seen!.headers.get('x-request-id')).toMatch(/^[0-9a-f-]{36}$/);
    expect(await seen!.json()).toEqual({ name: 'a' });
  });

  it('returns undefined for 204 No Content', async () => {
    server.use(mock.delete(`${API}/x`, () => new HttpResponse(null, { status: 204 })));
    await expect(client().http.delete('/x')).resolves.toBeUndefined();
  });
});

describe('error mapping', () => {
  it('maps Problem Details to AppError with field errors and request id', async () => {
    server.use(
      mock.post(`${API}/x`, () =>
        problem(422, 'validation_error', {
          errors: [{ field: 'title', code: 'required', message: 'Required.' }],
        }),
      ),
    );
    const error = await captureError(client().http.post('/x', {}));
    expect(error.code).toBe('validation_error');
    expect(error.status).toBe(422);
    expect(error.requestId).toBe('srv-1');
    expect(error.fieldErrors).toEqual([{ field: 'title', code: 'required', message: 'Required.' }]);
  });

  it('maps a non-Problem error body by status (e.g. a proxy HTML page)', async () => {
    server.use(mock.get(`${API}/x`, () => new HttpResponse('<html>Bad gateway</html>', { status: 404 })));
    const error = await captureError(client().http.get('/x'));
    expect(error.code).toBe('not_found');
    expect(error.status).toBe(404);
  });

  it('reports invalid JSON in a success response as parse_error', async () => {
    server.use(mock.get(`${API}/x`, () => new HttpResponse('{oops', { status: 200 })));
    expect((await captureError(client().http.get('/x'))).code).toBe('parse_error');
  });

  it('reports a failed connection as network_error', async () => {
    server.use(mock.get(`${API}/x`, () => HttpResponse.error()));
    const { http } = client({ retry: { retries: 0 } });
    expect((await captureError(http.get('/x'))).code).toBe('network_error');
  });
});

describe('timeouts and cancellation', () => {
  it('times out slow responses', async () => {
    server.use(
      mock.get(`${API}/slow`, async () => {
        await delay(200);
        return HttpResponse.json({});
      }),
    );
    const { http } = client({ timeoutMs: 20, retry: { retries: 0 } });
    expect((await captureError(http.get('/slow'))).code).toBe('timeout');
  });

  it('distinguishes caller cancellation from timeout and never retries it', async () => {
    let calls = 0;
    server.use(
      mock.get(`${API}/slow`, async () => {
        calls++;
        await delay(200);
        return HttpResponse.json({});
      }),
    );
    const controller = new AbortController();
    const { http } = client();
    const pending = http.get('/slow', { signal: controller.signal });
    setTimeout(() => {
      controller.abort();
    }, 10);
    expect((await captureError(pending)).code).toBe('cancelled');
    expect(calls).toBe(1);
  });

  it('fails immediately when the signal is already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    expect((await captureError(client().http.get('/never', { signal: controller.signal }))).code).toBe(
      'cancelled',
    );
  });
});

describe('retries', () => {
  it('retries idempotent requests on 503 with backoff, then succeeds', async () => {
    let calls = 0;
    server.use(
      mock.get(`${API}/flaky`, () => {
        calls++;
        return calls < 3 ? problem(503, 'external_service_error') : HttpResponse.json({ ok: true });
      }),
    );
    const { http, sleeps } = client();
    await expect(http.get('/flaky')).resolves.toEqual({ ok: true });
    expect(calls).toBe(3);
    expect(sleeps).toEqual([150, 300]); // full jitter with random() = 0.5
  });

  it('keeps the same request ID across retries', async () => {
    const ids: (string | null)[] = [];
    server.use(
      mock.get(`${API}/flaky`, ({ request }) => {
        ids.push(request.headers.get('x-request-id'));
        return ids.length < 2 ? problem(503, 'external_service_error') : HttpResponse.json({});
      }),
    );
    await client().http.get('/flaky');
    expect(new Set(ids).size).toBe(1);
  });

  it('never retries a plain POST (it might not be safe to repeat)', async () => {
    let calls = 0;
    server.use(
      mock.post(`${API}/orders`, () => {
        calls++;
        return problem(503, 'external_service_error');
      }),
    );
    await captureError(client().http.post('/orders', {}));
    expect(calls).toBe(1);
  });

  it('retries a POST that carries an Idempotency-Key', async () => {
    let calls = 0;
    server.use(
      mock.post(`${API}/orders`, ({ request }) => {
        calls++;
        expect(request.headers.get('idempotency-key')).toBe('key-1');
        return calls < 2 ? problem(503, 'external_service_error') : HttpResponse.json({ id: 9 });
      }),
    );
    await expect(client().http.post('/orders', {}, { idempotencyKey: 'key-1' })).resolves.toEqual({ id: 9 });
  });

  it('does not retry client errors', async () => {
    let calls = 0;
    server.use(
      mock.get(`${API}/missing`, () => {
        calls++;
        return problem(404, 'not_found');
      }),
    );
    await captureError(client().http.get('/missing'));
    expect(calls).toBe(1);
  });

  it('honours Retry-After on 429', async () => {
    let calls = 0;
    server.use(
      mock.get(`${API}/limited`, () => {
        calls++;
        return calls === 1 ? problem(429, 'rate_limited', { retry_after: 2 }) : HttpResponse.json({});
      }),
    );
    const { http, sleeps } = client();
    await http.get('/limited');
    expect(sleeps).toEqual([2000]);
  });

  it('respects a per-request retry override', async () => {
    let calls = 0;
    server.use(
      mock.get(`${API}/probe`, () => {
        calls++;
        return problem(503, 'external_service_error');
      }),
    );
    await captureError(client().http.get('/probe', { retries: 0 }));
    expect(calls).toBe(1);
  });
});

describe('backoffDelay', () => {
  const policy = { retries: 5, baseDelayMs: 100, maxDelayMs: 1000 };

  it('grows exponentially and is capped', () => {
    expect([1, 2, 3, 4, 5].map((attempt) => backoffDelay(attempt, policy, () => 1))).toEqual([
      100, 200, 400, 800, 1000,
    ]);
  });

  it('caps Retry-After at the maximum delay', () => {
    expect(backoffDelay(1, policy, () => 1, 60)).toBe(1000);
  });
});
