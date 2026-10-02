import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'config/app_config.dart';
import 'logging/app_logger.dart';
import 'networking/api_client.dart';

/// Values known only at startup are *overridden* in `main()`
/// (`ProviderScope(overrides: [...])`). Reading them without an override is a
/// wiring bug, so they fail loudly instead of returning a fake default.
final appConfigProvider = Provider<AppConfig>(
  (ref) => throw StateError('appConfigProvider must be overridden in ProviderScope'),
);

final loggerProvider = Provider<AppLogger>((ref) => AppLogger());

/// `Provider` (not Future/Notifier): a synchronously built, long-lived object.
/// Tests override it to inject a fake HTTP adapter.
final dioProvider = Provider<Dio>((ref) {
  final dio = createDio(ref.watch(appConfigProvider), ref.watch(loggerProvider));
  ref.onDispose(dio.close);
  return dio;
});

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient(ref.watch(dioProvider)));
