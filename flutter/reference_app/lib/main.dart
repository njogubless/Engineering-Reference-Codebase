import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/config/app_config.dart';
import 'core/logging/app_logger.dart';
import 'core/providers.dart';

void main() {
  final logger = AppLogger();

  // Global error capture: framework errors (build/layout/paint) and errors
  // from async code nobody awaited. Phase 15 forwards both to Crashlytics.
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    logger.error('flutter_error', {'exception': '${details.exception}'});
  };
  PlatformDispatcher.instance.onError = (error, stack) {
    logger.error('uncaught_error', {'error': '$error'});
    return true;
  };

  final AppConfig config;
  try {
    config = AppConfig.fromEnvironment();
  } on ConfigException catch (exception) {
    logger.error('invalid_config', {'problems': exception.problems});
    runApp(ConfigErrorApp(exception));
    return;
  }

  runApp(
    ProviderScope(
      overrides: [appConfigProvider.overrideWithValue(config), loggerProvider.overrideWithValue(logger)],
      // Retry in exactly one layer. Dio's RetryInterceptor already retries
      // transient failures of idempotent requests; Riverpod 3 would otherwise
      // retry failed providers too, multiplying attempts (a retry storm).
      retry: (retryCount, error) => null,
      child: const ReferenceApp(),
    ),
  );
}
