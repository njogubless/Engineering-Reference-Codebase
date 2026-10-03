import 'dart:async';

import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/features/posts/domain/post.dart';
import 'package:reference_app/features/posts/domain/posts_repository.dart';

Post makePost(int n, {PostStatus status = PostStatus.published, String authorId = 'ada'}) => Post(
  id: 'p$n',
  title: 'Post $n',
  body: 'Body $n',
  status: status,
  authorId: authorId,
  authorName: authorId == 'ada' ? 'Ada' : 'Grace',
  commentCount: n % 3,
  createdAt: DateTime.utc(2026, 7, 1, 12).subtract(Duration(hours: n)),
  publishedAt: status == PostStatus.published
      ? DateTime.utc(2026, 7, 1, 12).subtract(Duration(hours: n))
      : null,
);

/// In-memory repository. Cursor = index of the next item as a string.
/// [pageGate] lets a test hold a page request open; [failNextUpdate] /
/// [failNextPage] inject errors.
class FakePostsRepository implements PostsRepository {
  FakePostsRepository(this.posts);

  final List<Post> posts;
  int pageRequests = 0;
  Completer<void>? pageGate;
  AppError? failNextPage;
  AppError? failNextUpdate;

  @override
  Future<PostsPage> fetchPage({String? cursor, int limit = 10}) async {
    pageRequests++;
    await pageGate?.future;
    final error = failNextPage;
    if (error != null) {
      failNextPage = null;
      throw error;
    }
    final start = int.parse(cursor ?? '0');
    final items = posts.skip(start).take(limit).toList();
    final next = start + limit < posts.length ? '${start + limit}' : null;
    return PostsPage(items: items, nextCursor: next);
  }

  @override
  Future<Post> fetchPost(String id) async => posts.firstWhere(
    (post) => post.id == id,
    orElse: () => throw const ServerError(code: ServerErrorCode.notFound, status: 404, message: 'nope'),
  );

  @override
  Future<Post> create({required String title, String body = '', PostStatus status = PostStatus.draft}) =>
      throw UnsupportedError('not used in these tests');

  @override
  Future<Post> update(String id, {String? title, String? body, PostStatus? status}) async {
    await Future<void>.delayed(const Duration(milliseconds: 10));
    final error = failNextUpdate;
    if (error != null) {
      failNextUpdate = null;
      throw error;
    }
    final index = posts.indexWhere((post) => post.id == id);
    return posts[index] = posts[index].copyWith(title: title, body: body, status: status);
  }

  @override
  Future<void> delete(String id) async => posts.removeWhere((post) => post.id == id);
}
