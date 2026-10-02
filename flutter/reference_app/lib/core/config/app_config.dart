/// Typed, validated build-time configuration.
///
/// Values come from `--dart-define-from-file=config/<environment>.json`
/// (see config/README.md). Like Vite's `VITE_*` variables, they are compiled
/// into the app binary and can be extracted from it: they are PUBLIC.
/// API URLs and public keys belong here; secrets never do.
library;

enum Environment { development, test, staging, production }

class ConfigException implements Exception {
  const ConfigException(this.problems);

  final List<String> problems;

  @override
  String toString() => 'Invalid configuration: ${problems.join('; ')}';
}

final class AppConfig {
  const AppConfig({required this.apiBaseUrl, required this.environment});

  /// Reads compile-time defines. `String.fromEnvironment` must be called with
  /// constant keys, so the raw values are read here and validated in [parse].
  factory AppConfig.fromEnvironment() => AppConfig.parse(
    apiBaseUrl: const String.fromEnvironment('API_BASE_URL'),
    environment: const String.fromEnvironment('ENVIRONMENT'),
  );

  /// Validates raw values and reports every problem at once.
  factory AppConfig.parse({required String apiBaseUrl, required String environment}) {
    final problems = <String>[];

    final uri = Uri.tryParse(apiBaseUrl);
    if (apiBaseUrl.isEmpty) {
      problems.add('API_BASE_URL is required');
    } else if (uri == null || !uri.hasScheme || !(uri.isScheme('http') || uri.isScheme('https'))) {
      problems.add('API_BASE_URL must be an absolute http(s) URL');
    }

    final env = Environment.values.asNameMap()[environment];
    if (env == null) {
      problems.add('ENVIRONMENT must be one of ${Environment.values.map((e) => e.name).join(', ')}');
    }

    if (env == Environment.production && uri != null && uri.isScheme('http')) {
      problems.add('API_BASE_URL must use https in production');
    }

    if (problems.isNotEmpty) throw ConfigException(problems);
    return AppConfig(apiBaseUrl: apiBaseUrl, environment: env!);
  }

  final String apiBaseUrl;
  final Environment environment;
}
