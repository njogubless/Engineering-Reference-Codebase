import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_error.dart';
import '../../../core/providers.dart';
import '../data/rest_posts_repository.dart';
import '../domain/post.dart';
import '../domain/posts_repository.dart';

/// `Provider`: a long-lived object. Defaults to the REST API; a
/// `ProviderScope` override swaps in Firestore (or a fake in tests) without
/// touching any screen.
final postsRepositoryProvider = Provider<PostsRepository>(
  (ref) => RestPostsRepository(ref.watch(apiClientProvider)),
);

/// `FutureProvider.autoDispose.family`: one read-only fetch per post id,
/// freed when no screen shows that post any more.
final postDetailProvider = FutureProvider.autoDispose.family<Post, String>(
  (ref, id) => ref.watch(postsRepositoryProvider).fetchPost(id),
);

/// State of an infinite list. Loading *more* is separate from the list's own
/// AsyncValue: a failed page 3 must not replace pages 1-2 with an error screen.
final class PostsListState {
  const PostsListState({
    required this.items,
    required this.nextCursor,
    this.isLoadingMore = false,
    this.loadMoreError,
  });

  final List<Post> items;
  final String? nextCursor;
  final bool isLoadingMore;
  final AppError? loadMoreError;

  bool get hasMore => nextCursor != null;

  PostsListState copyWith({
    List<Post>? items,
    String? Function()? nextCursor,
    bool? isLoadingMore,
    AppError? Function()? loadMoreError,
  }) => PostsListState(
    items: items ?? this.items,
    nextCursor: nextCursor != null ? nextCursor() : this.nextCursor,
    isLoadingMore: isLoadingMore ?? this.isLoadingMore,
    loadMoreError: loadMoreError != null ? loadMoreError() : this.loadMoreError,
  );
}

/// `AsyncNotifier`: async initial load (`build`) plus methods that change the
/// state afterwards (load more, refresh, optimistic edits). A FutureProvider
/// cannot do the latter.
class PostsListController extends AsyncNotifier<PostsListState> {
  static const pageSize = 10;

  @override
  Future<PostsListState> build() async {
    final page = await ref.watch(postsRepositoryProvider).fetchPage(limit: pageSize);
    return PostsListState(items: page.items, nextCursor: page.nextCursor);
  }

  /// Safe to call repeatedly (scroll events fire many times): only one page
  /// request is ever in flight, and duplicates are dropped.
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || !current.hasMore || current.isLoadingMore) return;
    // Both outcomes build on `loading` (error already cleared), never on
    // `current`: rebuilding from the older snapshot would bring back the
    // previous page's error after a successful retry.
    final loading = current.copyWith(isLoadingMore: true, loadMoreError: () => null);
    state = AsyncData(loading);
    try {
      final page = await ref
          .read(postsRepositoryProvider)
          .fetchPage(cursor: loading.nextCursor, limit: pageSize);
      final seen = {for (final post in loading.items) post.id};
      state = AsyncData(
        loading.copyWith(
          items: [...loading.items, ...page.items.where((post) => !seen.contains(post.id))],
          nextCursor: () => page.nextCursor,
          isLoadingMore: false,
        ),
      );
    } on AppError catch (error) {
      state = AsyncData(loading.copyWith(isLoadingMore: false, loadMoreError: () => error));
    }
  }

  /// Pull-to-refresh: reload from the first page, keeping the old list on
  /// screen until the new one arrives.
  Future<void> refresh() async {
    ref.invalidateSelf();
    await future;
  }

  /// Optimistic: the list changes immediately; if the server refuses, the
  /// previous state comes back and the error is rethrown for the UI to show.
  Future<void> setStatus(Post post, PostStatus status) async {
    final before = state.value;
    if (before == null) return;
    _replace(post.copyWith(status: status));
    try {
      _replace(await ref.read(postsRepositoryProvider).update(post.id, status: status));
    } on AppError {
      state = AsyncData(before);
      rethrow;
    }
  }

  void _replace(Post updated) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData(
      current.copyWith(items: [for (final post in current.items) post.id == updated.id ? updated : post]),
    );
  }
}

final postsListProvider = AsyncNotifierProvider<PostsListController, PostsListState>(PostsListController.new);
