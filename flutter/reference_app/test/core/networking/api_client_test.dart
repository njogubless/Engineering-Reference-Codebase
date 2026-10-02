import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/config/app_config.dart';
import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/core/logging/app_logger.dart';
import 'package:reference_app/core/networking/api_client.dart';
import 'package:reference_app/core/networking/interceptors.dart';

import '../../support/fake_adapter.dart';

const config = AppConfig(apiBaseUrl: 'http://api.test', environment: Environment.test);

void main() {
  late FakeAdapter adapter;
  late List<Duration> sleeps;
  late ApiClient api;

  setUp(() {
    adapter = FakeAdapter();
    sleeps = [];
    final dio = createDio(
      config,
      AppLogger(minimumLevel: LogLevel.error, sink: (_, _, _) {}),
      adapter: adapter,
      sleep: (delay) async => sleeps.add(delay),
      random: () => 0.5,
    );
    api = ApiClient(dio);
  });

  Future<AppError> captureError(Future<Object?> future) async {
    try {
      await future;
    } on AppError catch (error) {
      return error;
    }
    fail('expected an AppError');
  }

  group('requests', () {
    test('decodes JSON, drops null query values and sends a request ID', () async {
      adapter.enqueueJson({'id': 1}, status: 201);
      final result = await api.post('/things', body: {'name': 'a'});
      expect(result, {'id': 1});

      adapter.enqueueJson([]);
      await api.get('/things', query: {'page': 2, 'skip': null});
      expect(adapter.requests.last.uri.query, 'page=2');
      expect(adapter.requests.last.headers['X-Request-ID'], matches(RegExp(r'^[0-9a-f]{32}$')));
    });
  });

  group('error mapping', () {
    test('Problem Details become ServerError with field errors and request id', () async {
      adapter.enqueue(
        (_) async => problemResponse(
          422,
          'validation_error',
          extra: {
            'errors': [
              {'field': 'title', 'code': 'required', 'message': 'Required.'},
            ],
          },
        ),
      );
      final error = await captureError(api.post('/x', body: {}));
      expect(error, isA<ServerError>());
      final serverError = error as ServerError;
      expect(serverError.code, ServerErrorCode.validationError);
      expect(serverError.requestId, 'srv-1');
      expect(serverError.fieldErrors, [
        const FieldError(field: 'title', code: 'required', message: 'Required.'),
      ]);
    });

    test('a non-Problem error body is classified by status', () async {
      adapter.enqueue(
        (_) async => ResponseBody.fromString(
          '<html>Bad gateway</html>',
          404,
          headers: {
            Headers.contentTypeHeader: ['text/html'],
          },
        ),
      );
      final error = await captureError(api.get('/x')) as ServerError;
      expect(error.code, ServerErrorCode.notFound);
    });

    test('invalid JSON in a success response is a ParseError', () async {
      adapter.enqueue(
        (_) async => ResponseBody.fromString(
          '{oops',
          200,
          headers: {
            Headers.contentTypeHeader: ['application/json'],
          },
        ),
      );
      expect(await captureError(api.get('/x')), isA<ParseError>());
    });

    test('connection failures are NetworkError', () async {
      adapter.enqueue(
        (options) async => throw DioException.connectionError(requestOptions: options, reason: 'refused'),
      );
      adapter.enqueue(
        (options) async => throw DioException.connectionError(requestOptions: options, reason: 'refused'),
      );
      adapter.enqueue(
        (options) async => throw DioException.connectionError(requestOptions: options, reason: 'refused'),
      );
      expect(await captureError(api.get('/x')), isA<NetworkError>());
    });

    test('timeouts are TimeoutError', () async {
      adapter.enqueue(
        (options) async => throw DioException.receiveTimeout(timeout: Duration.zero, requestOptions: options),
      );
      expect(await captureError(api.get('/x', retries: 0)), isA<TimeoutError>());
    });

    test('cancelling an in-flight request gives CancelledError and is never retried', () async {
      final token = CancelToken();
      final inFlight = Completer<void>();
      adapter.enqueue((_) async {
        inFlight.complete();
        await Future<void>.delayed(const Duration(milliseconds: 200));
        return jsonResponse({});
      });
      final pending = api.get('/slow', cancelToken: token);
      await inFlight.future;
      token.cancel();
      expect(await captureError(pending), isA<CancelledError>());
      expect(adapter.requests, hasLength(1));
    });

    test('a request cancelled before it is sent never reaches the network', () async {
      final token = CancelToken()..cancel();
      expect(await captureError(api.get('/never', cancelToken: token)), isA<CancelledError>());
      expect(adapter.requests, isEmpty);
    });
  });

  group('retries', () {
    test('idempotent requests retry on 503 with jittered backoff, then succeed', () async {
      adapter
        ..enqueue((_) async => problemResponse(503, 'external_service_error'))
        ..enqueue((_) async => problemResponse(503, 'external_service_error'))
        ..enqueueJson({'ok': true});
      expect(await api.get('/flaky'), {'ok': true});
      expect(adapter.requests, hasLength(3));
      expect(sleeps, [const Duration(milliseconds: 150), const Duration(milliseconds: 300)]);
    });

    test('every attempt carries the same request ID', () async {
      adapter
        ..enqueue((_) async => problemResponse(503, 'external_service_error'))
        ..enqueueJson({});
      await api.get('/flaky');
      expect(adapter.requests.map((r) => r.headers['X-Request-ID']).toSet(), hasLength(1));
    });

    test('a plain POST is never retried', () async {
      adapter.enqueue((_) async => problemResponse(503, 'external_service_error'));
      await captureError(api.post('/orders', body: {}));
      expect(adapter.requests, hasLength(1));
    });

    test('a POST with an Idempotency-Key is retried', () async {
      adapter
        ..enqueue((_) async => problemResponse(503, 'external_service_error'))
        ..enqueueJson({'id': 9});
      expect(await api.post('/orders', body: {}, idempotencyKey: 'key-1'), {'id': 9});
      expect(adapter.requests.last.headers['Idempotency-Key'], 'key-1');
    });

    test('client errors are not retried', () async {
      adapter.enqueue((_) async => problemResponse(404, 'not_found'));
      await captureError(api.get('/missing'));
      expect(adapter.requests, hasLength(1));
    });

    test('Retry-After is honoured', () async {
      adapter
        ..enqueue((_) async => jsonResponse({}, status: 429, headers: {'retry-after': '2'}))
        ..enqueueJson({});
      await api.get('/limited');
      expect(sleeps, [const Duration(seconds: 2)]);
    });

    test('a per-request retry override of 0 disables retries', () async {
      adapter.enqueue((_) async => problemResponse(503, 'external_service_error'));
      await captureError(api.get('/probe', retries: 0));
      expect(adapter.requests, hasLength(1));
    });

    test('acceptStatuses turns an error status into data', () async {
      adapter.enqueueJson({'status': 'unavailable'}, status: 503);
      expect(await api.get('/health/ready', retries: 0, acceptStatuses: {503}), {'status': 'unavailable'});
    });
  });

  group('RetryInterceptor.delayFor', () {
    final interceptor = RetryInterceptor(
      dio: Dio(),
      baseDelay: const Duration(milliseconds: 100),
      maxDelay: const Duration(seconds: 1),
      random: () => 1,
    );

    test('grows exponentially and is capped', () {
      expect([1, 2, 3, 4, 5].map((a) => interceptor.delayFor(a).inMilliseconds), [100, 200, 400, 800, 1000]);
    });

    test('caps Retry-After', () {
      expect(interceptor.delayFor(1, retryAfter: const Duration(minutes: 1)), const Duration(seconds: 1));
    });
  });
}
