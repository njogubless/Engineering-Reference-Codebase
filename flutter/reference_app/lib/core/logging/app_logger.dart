import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';

/// Client logging with levels and redaction.
///
/// Release builds keep warnings and errors only; Phase 15 forwards them to
/// Crashlytics. Never log tokens, passwords, request/response bodies or
/// personal data — redaction is a safety net, not a licence.
enum LogLevel { debug, info, warning, error }

final _sensitiveKey = RegExp(
  r'pass(word)?|secret|token|authorization|cookie|api[_-]?key|otp|card|cvv',
  caseSensitive: false,
);

Object? redact(Object? value) => switch (value) {
  Map<Object?, Object?>() => {
    for (final MapEntry(:key, value: item) in value.entries)
      key: _sensitiveKey.hasMatch('$key') ? '[REDACTED]' : redact(item),
  },
  List<Object?>() => [for (final item in value) redact(item)],
  _ => value,
};

class AppLogger {
  AppLogger({LogLevel? minimumLevel, this.sink = _developerLog})
    : minimumLevel = minimumLevel ?? (kReleaseMode ? LogLevel.warning : LogLevel.debug);

  final LogLevel minimumLevel;
  final void Function(LogLevel level, String event, Map<Object?, Object?> context) sink;

  void debug(String event, [Map<String, Object?> context = const {}]) => _log(LogLevel.debug, event, context);
  void info(String event, [Map<String, Object?> context = const {}]) => _log(LogLevel.info, event, context);
  void warning(String event, [Map<String, Object?> context = const {}]) =>
      _log(LogLevel.warning, event, context);
  void error(String event, [Map<String, Object?> context = const {}]) => _log(LogLevel.error, event, context);

  void _log(LogLevel level, String event, Map<String, Object?> context) {
    if (level.index < minimumLevel.index) return;
    sink(level, event, redact(context)! as Map<Object?, Object?>);
  }
}

void _developerLog(LogLevel level, String event, Map<Object?, Object?> context) {
  developer.log(
    context.isEmpty ? event : '$event $context',
    name: 'app',
    level: switch (level) {
      LogLevel.debug => 500,
      LogLevel.info => 800,
      LogLevel.warning => 900,
      LogLevel.error => 1000,
    },
  );
}
