/// One error type for everything the app can fail at.
///
/// Server errors arrive as RFC 9457 Problem Details (contracts/openapi.yaml);
/// the client adds failures that never reach a server. Repositories throw only
/// [AppError]; state and UI never see `DioException`, `SocketException` or
/// `FormatException`. See docs/patterns/30-error-handling/README.md.
///
/// Dart idiom: a `sealed` hierarchy, so a `switch` over an [AppError] must
/// handle every kind of failure or it does not compile.
library;

/// Stable codes from the contract's `ErrorCode` enum.
enum ServerErrorCode {
  badRequest('bad_request'),
  validationError('validation_error'),
  authenticationError('authentication_error'),
  authorizationError('authorization_error'),
  notFound('not_found'),
  methodNotAllowed('method_not_allowed'),
  notAcceptable('not_acceptable'),
  conflict('conflict'),
  idempotencyKeyReused('idempotency_key_reused'),
  unsupportedMediaType('unsupported_media_type'),
  rateLimited('rate_limited'),
  internalError('internal_error'),
  externalServiceError('external_service_error');

  const ServerErrorCode(this.wire);

  final String wire;

  static final Map<String, ServerErrorCode> _byWire = {for (final code in values) code.wire: code};

  static ServerErrorCode? fromWire(String? wire) => _byWire[wire];

  /// Best-effort code for an error response that is not Problem Details.
  static ServerErrorCode fromStatus(int status) => switch (status) {
    400 => badRequest,
    401 => authenticationError,
    403 => authorizationError,
    404 => notFound,
    405 => methodNotAllowed,
    409 => conflict,
    415 => unsupportedMediaType,
    422 => validationError,
    429 => rateLimited,
    502 || 503 || 504 => externalServiceError,
    _ when status >= 500 => internalError,
    _ => badRequest,
  };
}

final class FieldError {
  const FieldError({required this.field, required this.code, required this.message});

  final String? field;
  final String code;
  final String message;

  @override
  bool operator ==(Object other) =>
      other is FieldError && other.field == field && other.code == code && other.message == message;

  @override
  int get hashCode => Object.hash(field, code, message);

  @override
  String toString() => 'FieldError($field, $code, $message)';
}

sealed class AppError implements Exception {
  const AppError(this.message);

  /// Technical description for logs. Never shown to users — see `userMessage`.
  final String message;

  /// Server request ID, when the failure has one (for support references).
  String? get requestId => null;

  @override
  String toString() => '$runtimeType: $message';
}

/// The server answered with an error status.
final class ServerError extends AppError {
  const ServerError({
    required this.code,
    required this.status,
    required String message,
    this.fieldErrors = const [],
    this.requestId,
    this.retryAfter,
  }) : super(message);

  /// Parses a Problem Details body; returns null if [json] is not one.
  static ServerError? fromProblem(Object? json) {
    if (json is! Map<String, Object?>) return null;
    final code = ServerErrorCode.fromWire(json['code'] as String?);
    final status = json['status'];
    final title = json['title'];
    if (code == null || status is! int || title is! String) return null;

    final errors = json['errors'];
    final retryAfter = json['retry_after'];
    return ServerError(
      code: code,
      status: status,
      message: (json['detail'] as String?) ?? title,
      requestId: json['request_id'] as String?,
      retryAfter: retryAfter is int ? Duration(seconds: retryAfter) : null,
      fieldErrors: [
        if (errors is List)
          for (final error in errors.whereType<Map<String, Object?>>())
            FieldError(
              field: error['field'] as String?,
              code: error['code'] as String? ?? 'invalid',
              message: error['message'] as String? ?? '',
            ),
      ],
    );
  }

  final ServerErrorCode code;
  final int status;
  final List<FieldError> fieldErrors;
  @override
  final String? requestId;
  final Duration? retryAfter;
}

/// No HTTP response was received (offline, DNS failure, connection refused).
final class NetworkError extends AppError {
  const NetworkError([super.message = 'Network request failed.']);
}

/// The request did not complete in time.
final class TimeoutError extends AppError {
  const TimeoutError([super.message = 'The request timed out.']);
}

/// The caller cancelled the request (e.g. the screen was closed).
final class CancelledError extends AppError {
  const CancelledError([super.message = 'The request was cancelled.']);
}

/// The response could not be understood (bad JSON or unexpected shape).
final class ParseError extends AppError {
  const ParseError(super.message, {this.requestId});

  @override
  final String? requestId;
}

/// A bug or an exception nobody anticipated. Wraps it instead of leaking it.
final class UnexpectedError extends AppError {
  const UnexpectedError(this.cause, [this.stackTrace]) : super('An unexpected error occurred.');

  final Object cause;
  final StackTrace? stackTrace;
}

/// Normalises anything caught into an [AppError] (for providers and catch-alls).
AppError toAppError(Object error, [StackTrace? stackTrace]) =>
    error is AppError ? error : UnexpectedError(error, stackTrace);
