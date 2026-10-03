import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/config/app_config.dart';
import 'package:reference_app/core/logging/app_logger.dart';
import 'package:reference_app/core/networking/api_client.dart';
import 'package:reference_app/core/providers.dart';
import 'package:reference_app/features/auth/application/session_controller.dart';
import 'package:reference_app/features/posts/application/posts_providers.dart';
import 'package:reference_app/features/posts/domain/post.dart';

import '../../support/fake_adapter.dart';

const config = AppConfig(apiBaseUrl: 'http://api.test', environment: Environment.test);

Map<String, Object?> post(String id, {String status = 'published'}) => {
  'id': id,
  'title': 'T',
  'body': '',
  'status': status,
  'author': {'id': 'u1', 'display_name': 'Ada'},
  'comment_count': 0,
  'created_at': '2026-07-01T16:00:00Z',
  'updated_at': '2026-07-01T16:00:00Z',
  'published_at': status == 'published' ? '2026-07-01T16:00:00Z' : null,
};

void main() {
  late FakeAdapter adapter;
  late ProviderContainer container;

  setUp(() {
    adapter = FakeAdapter();
    container = ProviderContainer(
      overrides: [
        appConfigProvider.overrideWithValue(config),
        loggerProvider.overrideWithValue(AppLogger(minimumLevel: LogLevel.error, sink: (_, _, _) {})),
        // The real wiring from core/providers.dart, with only the network faked.
        dioProvider.overrideWith(
          (ref) => createDio(
            config,
            ref.watch(loggerProvider),
            adapter: adapter,
            sleep: (_) async {},
            accessToken: () => ref.read(sessionProvider)?.access,
            onUnauthorized: () => ref.read(sessionProvider.notifier).expire(),
          ),
        ),
      ],
      retry: (_, _) => null,
    );
    addTearDown(container.dispose);
  });

  Future<void> signIn() async {
    adapter
      ..enqueueJson({'access': 'tok', 'refresh': 'ref'})
      ..enqueueJson({'id': 'u1', 'email': 'ada@example.com', 'display_name': 'Ada'});
    await container.read(sessionProvider.notifier).signIn('ada@example.com', 'pw');
  }

  test('fetches a page with cursor and limit, and maps it', () async {
    adapter.enqueueJson({
      'items': [post('a')],
      'next_cursor': 'c2',
    });
    final page = await container.read(postsRepositoryProvider).fetchPage(cursor: 'c1', limit: 5);
    expect(adapter.requests.single.uri.query, 'cursor=c1&limit=5');
    expect(page.items.single.id, 'a');
    expect(page.nextCursor, 'c2');
  });

  test('PATCH sends only the fields being changed, with the session token', () async {
    await signIn();
    adapter.enqueueJson(post('a', status: 'draft'));
    await container.read(postsRepositoryProvider).update('a', status: PostStatus.draft);
    final request = adapter.requests.last;
    expect(request.method, 'PATCH');
    expect(request.data, {'status': 'draft'});
    expect(request.headers['Authorization'], 'Bearer tok');
  });

  test('anonymous requests carry no Authorization header', () async {
    adapter.enqueueJson({'items': <Object?>[], 'next_cursor': null});
    await container.read(postsRepositoryProvider).fetchPage();
    expect(adapter.requests.single.headers.containsKey('Authorization'), isFalse);
  });

  test('a 401 on an authenticated request ends the session', () async {
    await signIn();
    adapter.enqueue((_) async => problemResponse(401, 'authentication_error'));
    await expectLater(container.read(postsRepositoryProvider).fetchPost('a'), throwsA(anything));
    expect(container.read(sessionProvider), isNull);
  });

  test('sign-out ends the session even if the logout request fails', () async {
    await signIn();
    adapter.enqueue((_) async => problemResponse(500, 'internal_error'));
    await container.read(sessionProvider.notifier).signOut();
    expect(container.read(sessionProvider), isNull);
    expect(adapter.requests.last.data, {'refresh': 'ref'});
  });
}
