import 'package:flutter/material.dart';

import 'core/config/app_config.dart';
import 'features/diagnostics/presentation/diagnostics_screen.dart';

class ReferenceApp extends StatelessWidget {
  const ReferenceApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Reference App',
    theme: ThemeData(colorSchemeSeed: Colors.indigo),
    darkTheme: ThemeData(colorSchemeSeed: Colors.indigo, brightness: Brightness.dark),
    home: const DiagnosticsScreen(),
  );
}

/// Shown instead of the app when the build was configured incorrectly.
class ConfigErrorApp extends StatelessWidget {
  const ConfigErrorApp(this.exception, {super.key});

  final ConfigException exception;

  @override
  Widget build(BuildContext context) => MaterialApp(
    home: Scaffold(
      appBar: AppBar(title: const Text('Configuration error')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [for (final problem in exception.problems) Text('• $problem')],
      ),
    ),
  );
}
