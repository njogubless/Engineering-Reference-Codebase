/**
 * Client logging with levels and redaction.
 *
 * In production only warnings and errors are emitted; a real app would also
 * forward them to an error tracker (Phase 15). Never log tokens, passwords,
 * request/response bodies or personal data — redaction below is a safety net.
 */
type Level = 'debug' | 'info' | 'warn' | 'error';
type Context = Record<string, unknown>;

const LEVELS: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };
const SENSITIVE_KEY = /pass(word)?|secret|token|authorization|cookie|api[_-]?key|otp|card|cvv/i;

export function redact(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redact);
  if (value !== null && typeof value === 'object' && !(value instanceof Error)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        SENSITIVE_KEY.test(key) ? '[REDACTED]' : redact(item),
      ]),
    );
  }
  return value;
}

function minimumLevel(): number {
  return import.meta.env.PROD ? LEVELS.warn : LEVELS.debug;
}

function emit(level: Level, event: string, context?: Context): void {
  if (LEVELS[level] < minimumLevel()) return;
  const payload = context === undefined ? '' : redact(context);
  // eslint-disable-next-line no-console -- this module is the single console sink
  console[level](`[${level}] ${event}`, payload);
}

export const logger = {
  debug: (event: string, context?: Context) => {
    emit('debug', event, context);
  },
  info: (event: string, context?: Context) => {
    emit('info', event, context);
  },
  warn: (event: string, context?: Context) => {
    emit('warn', event, context);
  },
  error: (event: string, context?: Context) => {
    emit('error', event, context);
  },
};
