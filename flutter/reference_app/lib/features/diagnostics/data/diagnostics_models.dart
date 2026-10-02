import '../../../core/errors/app_error.dart';

/// Models validate JSON at the boundary: a malformed response becomes a
/// [ParseError] here, instead of a `TypeError` somewhere in the UI.
final class ServerMeta {
  const ServerMeta({required this.apiVersion, required this.environment, required this.features});

  factory ServerMeta.fromJson(Object? json) {
    if (json case {
      'api_version': final String apiVersion,
      'environment': final String environment,
      'features': final Map<String, Object?> features,
    } when features.values.every((value) => value is bool)) {
      return ServerMeta(
        apiVersion: apiVersion,
        environment: environment,
        features: features.cast<String, bool>(),
      );
    }
    throw const ParseError('Unexpected /api/v1/meta response shape.');
  }

  final String apiVersion;
  final String environment;
  final Map<String, bool> features;
}

final class Readiness {
  const Readiness({required this.ready, required this.checks});

  factory Readiness.fromJson(Object? json) {
    if (json case {
      'status': final String status,
      'checks': final Map<String, Object?> checks,
    } when checks.values.every((value) => value is String)) {
      return Readiness(ready: status == 'ok', checks: checks.cast<String, String>());
    }
    throw const ParseError('Unexpected /health/ready response shape.');
  }

  final bool ready;
  final Map<String, String> checks;
}
