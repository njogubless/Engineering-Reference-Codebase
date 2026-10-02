import 'app_error.dart';

/// What the user sees for an error. Chosen by error *type and code*, never by
/// parsing [AppError.message]. Both switches are exhaustive: adding a code to
/// the contract or a new AppError subtype fails compilation here until the UI
/// decides how to present it.
String userMessage(AppError error) => switch (error) {
  ServerError(:final code, :final retryAfter) => switch (code) {
    ServerErrorCode.validationError => 'Please correct the highlighted fields.',
    ServerErrorCode.badRequest ||
    ServerErrorCode.methodNotAllowed ||
    ServerErrorCode.notAcceptable ||
    ServerErrorCode.unsupportedMediaType =>
      'The request could not be processed. Please try again or contact support.',
    ServerErrorCode.authenticationError => 'Please sign in to continue.',
    ServerErrorCode.authorizationError => 'You do not have permission to do this.',
    ServerErrorCode.notFound => 'We could not find what you were looking for.',
    ServerErrorCode.conflict ||
    ServerErrorCode.idempotencyKeyReused => 'This conflicts with a recent change. Refresh and try again.',
    ServerErrorCode.rateLimited =>
      retryAfter == null
          ? 'Too many attempts. Please wait a moment.'
          : 'Too many attempts. Try again in ${retryAfter.inSeconds} seconds.',
    ServerErrorCode.externalServiceError =>
      'A service we depend on is unavailable. Please try again shortly.',
    ServerErrorCode.internalError => 'Something went wrong on our side. Please try again.',
  },
  NetworkError() => 'You appear to be offline. Check your connection and try again.',
  TimeoutError() => 'The server took too long to respond. Please try again.',
  CancelledError() => 'The request was cancelled.',
  ParseError() => 'We received an unexpected response. Please try again.',
  UnexpectedError() => 'Something went wrong. Please try again.',
};

/// Errors where an immediate "Try again" action makes sense.
bool isRetryable(AppError error) => switch (error) {
  NetworkError() || TimeoutError() || UnexpectedError() => true,
  ServerError(:final code) => const {
    ServerErrorCode.externalServiceError,
    ServerErrorCode.internalError,
    ServerErrorCode.rateLimited,
  }.contains(code),
  CancelledError() || ParseError() => false,
};
