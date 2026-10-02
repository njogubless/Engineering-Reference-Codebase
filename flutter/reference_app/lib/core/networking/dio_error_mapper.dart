import 'package:dio/dio.dart';

import '../errors/app_error.dart';

const requestIdHeader = 'X-Request-ID';

/// Translates Dio's transport-level exceptions into the app's [AppError].
/// This is the only place in the app that knows about [DioException].
AppError mapDioException(DioException exception) {
  final error = exception.error;
  if (error is AppError) return error;

  return switch (exception.type) {
    DioExceptionType.cancel => const CancelledError(),
    DioExceptionType.connectionTimeout ||
    DioExceptionType.sendTimeout ||
    DioExceptionType.receiveTimeout ||
    DioExceptionType.transformTimeout => const TimeoutError(),
    DioExceptionType.connectionError => const NetworkError(),
    DioExceptionType.badCertificate => const NetworkError('The server certificate was rejected.'),
    DioExceptionType.badResponse => _fromResponse(exception.response),
    DioExceptionType.unknown =>
      error is FormatException
          ? ParseError(
              'The response was not valid JSON.',
              requestId: exception.response?.headers.value(requestIdHeader),
            )
          : UnexpectedError(error ?? exception, exception.stackTrace),
  };
}

ServerError _fromResponse(Response<Object?>? response) {
  final status = response?.statusCode ?? 500;
  final problem = ServerError.fromProblem(response?.data);
  if (problem != null) return problem;

  // Not Problem Details (e.g. a proxy's HTML error page): classify by status.
  final retryAfter = int.tryParse(response?.headers.value('retry-after') ?? '');
  return ServerError(
    code: ServerErrorCode.fromStatus(status),
    status: status,
    message: 'Request failed with status $status.',
    requestId: response?.headers.value(requestIdHeader),
    retryAfter: retryAfter == null ? null : Duration(seconds: retryAfter),
  );
}
