import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../data/diagnostics_models.dart';
import '../data/diagnostics_repository.dart';

final diagnosticsRepositoryProvider = Provider<DiagnosticsRepository>(
  (ref) => DiagnosticsRepository(ref.watch(apiClientProvider)),
);

/// Cancels the in-flight request when the provider is disposed (the screen
/// was closed), so a slow response cannot update state nobody is watching.
CancelToken _cancelOnDispose(Ref ref) {
  final token = CancelToken();
  ref.onDispose(token.cancel);
  return token;
}

/// `FutureProvider.autoDispose`: a read-only fetch with no mutations, so a
/// Notifier would add nothing. autoDispose frees it when the screen closes.
final serverMetaProvider = FutureProvider.autoDispose<ServerMeta>(
  (ref) => ref.watch(diagnosticsRepositoryProvider).fetchMeta(cancelToken: _cancelOnDispose(ref)),
);

final readinessProvider = FutureProvider.autoDispose<Readiness>(
  (ref) => ref.watch(diagnosticsRepositoryProvider).fetchReadiness(cancelToken: _cancelOnDispose(ref)),
);

final missingResourceProvider = FutureProvider.autoDispose<void>(
  (ref) => ref.watch(diagnosticsRepositoryProvider).fetchMissingResource(cancelToken: _cancelOnDispose(ref)),
);
