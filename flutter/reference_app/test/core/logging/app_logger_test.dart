import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/logging/app_logger.dart';

void main() {
  test('redacts sensitive keys recursively', () {
    expect(
      redact({
        'user': 'a',
        'accessToken': 't',
        'nested': [
          {'password': 'p'},
        ],
      }),
      {
        'user': 'a',
        'accessToken': '[REDACTED]',
        'nested': [
          {'password': '[REDACTED]'},
        ],
      },
    );
  });

  test('drops messages below the minimum level', () {
    final events = <String>[];
    AppLogger(minimumLevel: LogLevel.warning, sink: (_, event, _) => events.add(event))
      ..info('ignored')
      ..warning('kept');
    expect(events, ['kept']);
  });
}
