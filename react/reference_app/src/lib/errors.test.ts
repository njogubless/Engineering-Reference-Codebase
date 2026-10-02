import {
  AppError,
  codeForStatus,
  isProblem,
  isRetryable,
  toAppError,
  userMessage,
  type AppErrorCode,
} from './errors';

describe('isProblem', () => {
  it('accepts a well-formed problem', () => {
    expect(isProblem({ type: 't', title: 'x', status: 404, code: 'not_found', request_id: 'r' })).toBe(true);
  });

  it.each([null, 'text', { status: 500 }, { status: 500, title: 'x', code: 'made_up_code' }])(
    'rejects %j',
    (value) => {
      expect(isProblem(value)).toBe(false);
    },
  );
});

describe('codeForStatus', () => {
  it.each([
    [401, 'authentication_error'],
    [403, 'authorization_error'],
    [418, 'bad_request'],
    [503, 'external_service_error'],
    [500, 'internal_error'],
  ] as const)('%i -> %s', (status, code) => {
    expect(codeForStatus(status)).toBe(code);
  });
});

describe('userMessage', () => {
  const codes: AppErrorCode[] = [
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
    'network_error',
    'timeout',
    'cancelled',
    'parse_error',
  ];

  it.each(codes)('has a non-technical message for %s', (code) => {
    const message = userMessage(new AppError(code, 'technical detail'));
    expect(message).not.toContain('technical detail');
    expect(message.length).toBeGreaterThan(0);
  });

  it('includes the wait time for rate limiting when known', () => {
    expect(userMessage(new AppError('rate_limited', '', { retryAfterSeconds: 30 }))).toContain('30 seconds');
  });
});

it('toAppError wraps unknown values without leaking them', () => {
  const error = toAppError(new TypeError('x is undefined'));
  expect(error.code).toBe('internal_error');
  expect(error.cause).toBeInstanceOf(TypeError);
});

it('only offers retry for transient errors', () => {
  expect(isRetryable(new AppError('timeout', ''))).toBe(true);
  expect(isRetryable(new AppError('validation_error', ''))).toBe(false);
});
