import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/features/posts/application/posts_providers.dart';
import 'package:reference_app/features/posts/domain/post.dart';

import '../../support/fake_posts_repository.dart';

void main() {
  late FakePostsRepository repository;
  late ProviderContainer container;

  setUp(() {
    repository = FakePostsRepository([for (var n = 1; n <= 25; n++) makePost(n)]);
    // Provider override: the controller runs unchanged against a fake.
    container = ProviderContainer(
      overrides: [postsRepositoryProvider.overrideWithValue(repository)],
      retry: (_, _) => null,
    );
    addTearDown(container.dispose);
  });

  Future<PostsListState> load() => container.read(postsListProvider.future);
  PostsListController controller() => container.read(postsListProvider.notifier);
  PostsListState current() => container.read(postsListProvider).requireValue;

  test('loads the first page', () async {
    final state = await load();
    expect(state.items, hasLength(10));
    expect(state.hasMore, isTrue);
  });

  test('loads more pages until the end', () async {
    await load();
    await controller().loadMore();
    await controller().loadMore();
    expect(current().items, hasLength(25));
    expect(current().hasMore, isFalse);
    await controller().loadMore(); // at the end: no request
    expect(repository.pageRequests, 3);
  });

  test('concurrent loadMore calls (scroll events) send one request', () async {
    await load();
    repository.pageGate = Completer<void>();
    final calls = [controller().loadMore(), controller().loadMore(), controller().loadMore()];
    expect(current().isLoadingMore, isTrue);
    repository.pageGate!.complete();
    await Future.wait(calls);
    expect(repository.pageRequests, 2);
    expect(current().items.map((p) => p.id).toSet(), hasLength(20));
  });

  test('a failed next page keeps the loaded items and can be retried', () async {
    await load();
    repository.failNextPage = const NetworkError();
    await controller().loadMore();
    expect(current().items, hasLength(10));
    expect(current().loadMoreError, isA<NetworkError>());
    await controller().loadMore();
    expect(current().items, hasLength(20));
    expect(current().loadMoreError, isNull);
  });

  test('duplicates across pages are dropped (a row shifted between requests)', () async {
    await load();
    repository.posts.insert(0, makePost(99)); // new row shifts the "offset" fake by one
    await controller().loadMore();
    final ids = current().items.map((p) => p.id).toList();
    expect(ids.toSet().length, ids.length);
  });

  test('status changes are optimistic', () async {
    final post = (await load()).items.first;
    final pending = controller().setStatus(post, PostStatus.draft);
    expect(current().items.first.status, PostStatus.draft); // before the server answers
    await pending;
    expect(repository.posts.first.status, PostStatus.draft);
  });

  test('a refused change rolls back and rethrows for the UI', () async {
    final post = (await load()).items.first;
    repository.failNextUpdate = const ServerError(
      code: ServerErrorCode.authorizationError,
      status: 403,
      message: 'no',
    );
    await expectLater(controller().setStatus(post, PostStatus.draft), throwsA(isA<ServerError>()));
    expect(current().items.first.status, PostStatus.published);
  });

  test('refresh reloads from the first page', () async {
    await load();
    await controller().loadMore();
    await controller().refresh();
    expect(current().items, hasLength(10));
  });
}
