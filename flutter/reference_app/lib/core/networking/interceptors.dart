import 'dart:math';

import 'package:dio/dio.dart';

import '../logging/app_logger.dart';
import 'dio_error_mapper.dart';

/// Keys this app stores in [RequestOptions.extra].
abstract final class RequestExtras {
  /// Per-request override of the retry count (`0` for probes and polling).
  static const retries = 'retries';
  static const _attempt = 'attempt';
  static const _startedAt = 'startedAt';
}

/// Adds one `X-Request-ID` per logical request. Retries re-send the same
/// [RequestOptions], so every attempt carries the same ID and server logs can
/// show "same request, attempt 2".
class RequestIdInterceptor extends Interceptor {
  RequestIdInterceptor({Random? random}) : _random = random ?? Random.secure();

  final Random _random;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.headers.putIfAbsent(requestIdHeader, _newId);
    handler.next(options);
  }

  String _newId() => List.generate(16, (_) => _random.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
}

/// Logs method, path, status and duration — never headers or bodies.
class LoggingInterceptor extends Interceptor {
  LoggingInterceptor(this._logger);

  final AppLogger _logger;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.extra[RequestExtras._startedAt] = DateTime.now();
    handler.next(options);
  }

  @override
  void onResponse(Response<Object?> response, ResponseInterceptorHandler handler) {
    _logger.debug('http_response', _context(response.requestOptions, status: response.statusCode));
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    _logger.info(
      'http_error',
      _context(err.requestOptions, status: err.response?.statusCode)..['type'] = err.type.name,
    );
    handler.next(err);
  }

  Map<String, Object?> _context(RequestOptions options, {int? status}) {
    final startedAt = options.extra[RequestExtras._startedAt];
    return {
      'method': options.method,
      'path': options.uri.path, // no query string: it may carry tokens
      'status': status,
      'attempt': options.extra[RequestExtras._attempt] ?? 1,
      'requestId': options.headers[requestIdHeader],
      if (startedAt is DateTime) 'durationMs': DateTime.now().difference(startedAt).inMilliseconds,
    };
  }
}

/// Retries transient failures of requests that are safe to repeat.
///
/// Safe means idempotent: GET/HEAD/PUT/DELETE/OPTIONS, or any request
/// carrying an `Idempotency-Key`. Retrying a plain POST could create a second
/// order or charge a card twice. Backoff is exponential with full jitter so
/// clients do not retry in lock-step; `Retry-After` wins when present.
class RetryInterceptor extends Interceptor {
  RetryInterceptor({
    required this.dio,
    this.retries = 2,
    this.baseDelay = const Duration(milliseconds: 300),
    this.maxDelay = const Duration(seconds: 5),
    Future<void> Function(Duration)? sleep,
    double Function()? random,
  }) : _sleep = sleep ?? Future<void>.delayed,
       _random = random ?? Random().nextDouble;

  final Dio dio;
  final int retries;
  final Duration baseDelay;
  final Duration maxDelay;
  final Future<void> Function(Duration) _sleep;
  final double Function() _random;

  static const _idempotentMethods = {'GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS'};
  static const _retryableStatuses = {429, 502, 503, 504};

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final options = err.requestOptions;
    final attempt = (options.extra[RequestExtras._attempt] as int?) ?? 1;
    final maxRetries = (options.extra[RequestExtras.retries] as int?) ?? retries;

    if (attempt > maxRetries || !_isSafeToRetry(options) || !_isTransient(err)) {
      handler.next(err);
      return;
    }

    await _sleep(delayFor(attempt, retryAfter: _retryAfter(err.response)));
    if (options.cancelToken?.isCancelled ?? false) {
      handler.next(err);
      return;
    }

    try {
      options.extra[RequestExtras._attempt] = attempt + 1;
      handler.resolve(await dio.fetch<Object?>(options));
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }

  /// Exponential backoff with full jitter, capped at [maxDelay].
  Duration delayFor(int attempt, {Duration? retryAfter}) {
    if (retryAfter != null) return retryAfter > maxDelay ? maxDelay : retryAfter;
    final ceiling = min(maxDelay.inMilliseconds, baseDelay.inMilliseconds * pow(2, attempt - 1));
    return Duration(milliseconds: (_random() * ceiling).round());
  }

  bool _isSafeToRetry(RequestOptions options) =>
      _idempotentMethods.contains(options.method.toUpperCase()) ||
      options.headers.containsKey('Idempotency-Key');

  bool _isTransient(DioException err) => switch (err.type) {
    DioExceptionType.connectionError ||
    DioExceptionType.connectionTimeout ||
    DioExceptionType.receiveTimeout => true,
    DioExceptionType.badResponse => _retryableStatuses.contains(err.response?.statusCode),
    _ => false,
  };

  Duration? _retryAfter(Response<Object?>? response) {
    final seconds = int.tryParse(response?.headers.value('retry-after') ?? '');
    return seconds == null || seconds < 0 ? null : Duration(seconds: seconds);
  }
}
