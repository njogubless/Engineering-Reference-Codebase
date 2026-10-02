import 'package:dio/dio.dart';

import '../../../core/networking/api_client.dart';
import 'diagnostics_models.dart';

/// Talks to the API and returns typed models. No Flutter, no Riverpod: plain
/// Dart, so it is unit-testable and reusable.
///
/// No domain-layer interface: there is one implementation and no business
/// rule to protect, so an abstract repository would add a file and nothing else.
class DiagnosticsRepository {
  DiagnosticsRepository(this._api);

  final ApiClient _api;

  Future<ServerMeta> fetchMeta({CancelToken? cancelToken}) async =>
      ServerMeta.fromJson(await _api.get('/api/v1/meta', cancelToken: cancelToken));

  /// 503 is a valid answer ("not ready"), not an error; and a probe reports
  /// the current state, so it is never retried.
  Future<Readiness> fetchReadiness({CancelToken? cancelToken}) async => Readiness.fromJson(
    await _api.get('/health/ready', cancelToken: cancelToken, retries: 0, acceptStatuses: {503}),
  );

  /// Deliberately requests a path that does not exist (error-handling demo).
  Future<void> fetchMissingResource({CancelToken? cancelToken}) =>
      _api.get('/api/v1/does-not-exist', cancelToken: cancelToken);
}
