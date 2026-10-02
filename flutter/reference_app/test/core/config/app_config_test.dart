import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/config/app_config.dart';

void main() {
  test('parses valid configuration', () {
    final config = AppConfig.parse(apiBaseUrl: 'https://api.example.com', environment: 'production');
    expect(config.environment, Environment.production);
  });

  test('reports every problem at once', () {
    expect(
      () => AppConfig.parse(apiBaseUrl: '', environment: 'prod'),
      throwsA(
        isA<ConfigException>().having((e) => e.problems, 'problems', [
          'API_BASE_URL is required',
          'ENVIRONMENT must be one of development, test, staging, production',
        ]),
      ),
    );
  });

  test('rejects non-http URLs and plain http in production', () {
    expect(
      () => AppConfig.parse(apiBaseUrl: 'ftp://x', environment: 'test'),
      throwsA(isA<ConfigException>()),
    );
    expect(
      () => AppConfig.parse(apiBaseUrl: 'http://api.example.com', environment: 'production'),
      throwsA(isA<ConfigException>()),
    );
  });

  test('fromEnvironment fails fast when nothing was defined', () {
    // Tests run without --dart-define, so this must throw, not default.
    expect(AppConfig.fromEnvironment, throwsA(isA<ConfigException>()));
  });
}
