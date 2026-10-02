import { isRetryable, toAppError, userMessage } from '../../lib/errors';

/**
 * The one way the UI presents an error: a user-facing message chosen by
 * error code, the request ID for support, and a retry action when useful.
 */
export function ErrorAlert({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const appError = toAppError(error);
  return (
    <div role="alert" className="error-alert">
      <p>{userMessage(appError)}</p>
      {appError.requestId !== undefined && (
        <p className="error-alert__reference">
          Reference: <code>{appError.requestId}</code>
        </p>
      )}
      {onRetry !== undefined && isRetryable(appError) && (
        <button type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
