import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../errors/app_error.dart';
import '../logging/app_logger.dart';
import 'dio_error_mapper.dart';
import 'interceptors.dart';

/// Builds the app's single [Dio] instance: base URL, timeouts and interceptors.
///
/// Interceptor order matters: the request ID is set before logging, and
/// retries happen last so each retried attempt is logged.
Dio createDio(
  AppConfig config,
  AppLogger logger, {
  HttpClientAdapter? adapter,
  Future<void> Function(Duration)? sleep,
  double Function()? random,
}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: config.apiBaseUrl,
      connectTimeout: const Duration(seconds: 5),
      sendTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {Headers.acceptHeader: 'application/json, application/problem+json'},
    ),
  );
  if (adapter != null) dio.httpClientAdapter = adapter;
  dio.interceptors.addAll([
    RequestIdInterceptor(),
    LoggingInterceptor(logger),
    RetryInterceptor(dio: dio, sleep: sleep, random: random),
  ]);
  return dio;
}

/// The API surface repositories use. Returns decoded JSON and throws only
/// [AppError]; repositories turn the JSON into typed models.
///
/// Thin on purpose: Dio already provides the HTTP machinery. This class exists
/// to fix the *error contract* in one place.
class ApiClient {
  ApiClient(this._dio);

  final Dio _dio;

  Future<Object?> get(
    String path, {
    Map<String, Object?>? query,
    CancelToken? cancelToken,
    int? retries,
    Set<int>? acceptStatuses,
  }) => _send(
    'GET',
    path,
    query: query,
    cancelToken: cancelToken,
    retries: retries,
    acceptStatuses: acceptStatuses,
  );

  Future<Object?> post(String path, {Object? body, String? idempotencyKey, CancelToken? cancelToken}) =>
      _send('POST', path, body: body, idempotencyKey: idempotencyKey, cancelToken: cancelToken);

  Future<Object?> put(String path, {Object? body, CancelToken? cancelToken}) =>
      _send('PUT', path, body: body, cancelToken: cancelToken);

  Future<Object?> patch(String path, {Object? body, String? idempotencyKey, CancelToken? cancelToken}) =>
      _send('PATCH', path, body: body, idempotencyKey: idempotencyKey, cancelToken: cancelToken);

  Future<Object?> delete(String path, {CancelToken? cancelToken}) =>
      _send('DELETE', path, cancelToken: cancelToken);

  Future<Object?> _send(
    String method,
    String path, {
    Map<String, Object?>? query,
    Object? body,
    String? idempotencyKey,
    CancelToken? cancelToken,
    int? retries,
    Set<int>? acceptStatuses,
  }) async {
    try {
      final response = await _dio.request<Object?>(
        path,
        data: body,
        // null means "not set" — never send the string "null".
        queryParameters: query == null
            ? null
            : {for (final MapEntry(:key, :value) in query.entries) key: ?value},
        cancelToken: cancelToken,
        options: Options(
          method: method,
          headers: {'Idempotency-Key': ?idempotencyKey},
          extra: {RequestExtras.retries: ?retries},
          validateStatus: acceptStatuses == null
              ? null
              : (status) =>
                    status != null && ((status >= 200 && status < 300) || acceptStatuses.contains(status)),
        ),
      );
      return response.data;
    } on DioException catch (exception) {
      throw mapDioException(exception);
    }
  }
}
