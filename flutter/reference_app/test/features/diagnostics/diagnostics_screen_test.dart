import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/config/app_config.dart';
import 'package:reference_app/core/logging/app_logger.dart';
import 'package:reference_app/core/networking/api_client.dart';
import 'package:reference_app/core/providers.dart';
import 'package:reference_app/features/diagnostics/presentation/diagnostics_screen.dart';

import '../../support/fake_adapter.dart';

const config = AppConfig(apiBaseUrl: 'http://api.test', environment: Environment.test);

/// Widget tests run the real providers, repository and Dio pipeline; only the
/// HTTP adapter is fake. Requests are matched by path, not order, because the
/// screen loads several providers concurrently.
Widget buildApp(Map<String, FakeHandler> routes) {
  final adapter = FakeAdapter(routes: routes);
  return ProviderScope(
    overrides: [
      appConfigProvider.overrideWithValue(config),
      dioProvider.overrideWith(
        (ref) => createDio(
          config,
          AppLogger(minimumLevel: LogLevel.error, sink: (_, _, _) {}),
          adapter: adapter,
          sleep: (_) async {},
        ),
      ),
    ],
    retry: (_, _) => null,
    child: const MaterialApp(home: DiagnosticsScreen()),
  );
}

void main() {
  final healthy = <String, FakeHandler>{
    '/api/v1/meta': (_) async => jsonResponse({
      'api_version': '1',
      'environment': 'test',
      'features': {'maintenance_banner': true},
    }),
    '/health/ready': (_) async => jsonResponse({
      'status': 'ok',
      'checks': {'database': 'ok'},
    }),
  };

  testWidgets('shows server configuration and readiness', (tester) async {
    await tester.pumpWidget(buildApp(healthy));
    await tester.pumpAndSettle();
    expect(find.text('maintenance_banner: on'), findsOneWidget);
    expect(find.text('database: ok'), findsOneWidget);
  });

  testWidgets('a 503 readiness is shown as data, not as an error', (tester) async {
    await tester.pumpWidget(
      buildApp({
        ...healthy,
        '/health/ready': (_) async => jsonResponse({
          'status': 'unavailable',
          'checks': {'database': 'fail'},
        }, status: 503),
      }),
    );
    await tester.pumpAndSettle();
    expect(find.text('database: fail'), findsOneWidget);
  });

  testWidgets('shows a user-facing error with reference, then recovers on retry', (tester) async {
    var fail = true;
    await tester.pumpWidget(
      buildApp({
        ...healthy,
        '/api/v1/meta': (_) async => fail
            ? problemResponse(500, 'internal_error')
            : jsonResponse({'api_version': '1', 'environment': 'test', 'features': <String, bool>{}}),
      }),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('Something went wrong on our side'), findsOneWidget);
    expect(find.text('Reference: srv-1'), findsOneWidget);

    fail = false;
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();
    expect(find.text('Feature flags: none'), findsOneWidget);
  });

  testWidgets('demonstrates a 404 Problem end to end', (tester) async {
    await tester.pumpWidget(
      buildApp({...healthy, '/api/v1/does-not-exist': (_) async => problemResponse(404, 'not_found')}),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Request a missing resource'));
    await tester.pumpAndSettle();
    expect(find.text('We could not find what you were looking for.'), findsOneWidget);
  });
}
