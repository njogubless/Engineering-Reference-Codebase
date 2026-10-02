import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/core/errors/user_message.dart';

void main() {
  group('ServerError.fromProblem', () {
    test('parses a full problem', () {
      final error = ServerError.fromProblem({
        'type': 't',
        'title': 'Too many requests',
        'status': 429,
        'code': 'rate_limited',
        'request_id': 'r-1',
        'retry_after': 30,
      })!;
      expect(error.code, ServerErrorCode.rateLimited);
      expect(error.retryAfter, const Duration(seconds: 30));
      expect(error.message, 'Too many requests');
    });

    test('rejects values that are not problems', () {
      expect(ServerError.fromProblem('text'), isNull);
      expect(ServerError.fromProblem({'status': 500}), isNull);
      expect(ServerError.fromProblem({'status': 500, 'title': 'x', 'code': 'made_up'}), isNull);
    });
  });

  test('every wire code round-trips', () {
    for (final code in ServerErrorCode.values) {
      expect(ServerErrorCode.fromWire(code.wire), code);
    }
  });

  test('fromStatus classifies unknown statuses sensibly', () {
    expect(ServerErrorCode.fromStatus(418), ServerErrorCode.badRequest);
    expect(ServerErrorCode.fromStatus(503), ServerErrorCode.externalServiceError);
    expect(ServerErrorCode.fromStatus(500), ServerErrorCode.internalError);
  });

  group('userMessage', () {
    final errors = <AppError>[
      for (final code in ServerErrorCode.values) ServerError(code: code, status: 400, message: 'technical'),
      const NetworkError('technical'),
      const TimeoutError('technical'),
      const CancelledError('technical'),
      const ParseError('technical'),
      const UnexpectedError('technical'),
    ];

    test('never shows technical messages', () {
      for (final error in errors) {
        expect(userMessage(error), isNot(contains('technical')), reason: '$error');
        expect(userMessage(error), isNotEmpty);
      }
    });

    test('includes the wait for rate limiting', () {
      const error = ServerError(
        code: ServerErrorCode.rateLimited,
        status: 429,
        message: '',
        retryAfter: Duration(seconds: 30),
      );
      expect(userMessage(error), contains('30 seconds'));
    });
  });

  test('toAppError wraps unknown errors', () {
    final error = toAppError(StateError('boom'));
    expect(error, isA<UnexpectedError>());
    expect((error as UnexpectedError).cause, isA<StateError>());
  });

  test('only transient errors are retryable', () {
    expect(isRetryable(const TimeoutError()), isTrue);
    expect(
      isRetryable(const ServerError(code: ServerErrorCode.validationError, status: 422, message: '')),
      isFalse,
    );
  });
}
