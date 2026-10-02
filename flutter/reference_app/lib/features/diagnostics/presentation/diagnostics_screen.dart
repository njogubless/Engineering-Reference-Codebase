import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../../../shared/widgets/error_view.dart';
import '../application/diagnostics_providers.dart';

/// Phase 1 demo: configuration, health checks, feature flags and the error
/// model, end to end against the backend in `API_BASE_URL`.
///
/// The widget only reads providers and renders `AsyncValue` states; it never
/// touches Dio, JSON or exceptions directly.
class DiagnosticsScreen extends ConsumerStatefulWidget {
  const DiagnosticsScreen({super.key});

  @override
  ConsumerState<DiagnosticsScreen> createState() => _DiagnosticsScreenState();
}

class _DiagnosticsScreenState extends ConsumerState<DiagnosticsScreen> {
  bool _showErrorDemo = false;

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(appConfigProvider);
    final meta = ref.watch(serverMetaProvider);
    final readiness = ref.watch(readinessProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Diagnostics')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _Heading('Client configuration'),
          Text('Environment: ${config.environment.name}'),
          Text('API base URL: ${config.apiBaseUrl}'),
          const _Heading('Server'),
          switch (meta) {
            AsyncData(:final value) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Server environment: ${value.environment}'),
                Text('API version: ${value.apiVersion}'),
                if (value.features.isEmpty) const Text('Feature flags: none'),
                for (final MapEntry(:key, value: enabled) in value.features.entries)
                  Text('$key: ${enabled ? 'on' : 'off'}'),
              ],
            ),
            AsyncError(:final error) => ErrorView(
              error: error,
              onRetry: () => ref.invalidate(serverMetaProvider),
            ),
            _ => const LinearProgressIndicator(),
          },
          const _Heading('Readiness'),
          switch (readiness) {
            AsyncData(:final value) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final MapEntry(:key, value: result) in value.checks.entries) Text('$key: $result'),
              ],
            ),
            AsyncError(:final error) => ErrorView(error: error),
            _ => const LinearProgressIndicator(),
          },
          const _Heading('Error handling demo'),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => setState(() => _showErrorDemo = true),
              child: const Text('Request a missing resource'),
            ),
          ),
          if (_showErrorDemo) const _MissingResourceResult(),
        ],
      ),
    );
  }
}

/// Watches the demo provider only once the button was pressed.
class _MissingResourceResult extends ConsumerWidget {
  const _MissingResourceResult();

  @override
  Widget build(BuildContext context, WidgetRef ref) => switch (ref.watch(missingResourceProvider)) {
    AsyncError(:final error) => ErrorView(error: error),
    AsyncData() => const Text('Unexpectedly succeeded.'),
    _ => const LinearProgressIndicator(),
  };
}

class _Heading extends StatelessWidget {
  const _Heading(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 24, bottom: 8),
    child: Text(text, style: Theme.of(context).textTheme.titleMedium),
  );
}
