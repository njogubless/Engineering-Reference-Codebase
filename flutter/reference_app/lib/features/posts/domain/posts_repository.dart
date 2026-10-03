import 'post.dart';

/// The contract feature code depends on.
///
/// An interface is justified here because two real implementations exist:
/// [RestPostsRepository] (the reference APIs) and [FirestorePostsRepository].
/// The same screens run against either by overriding one provider. Without a
/// second implementation, this file would be ceremony (see the diagnostics
/// feature, which has none).
abstract interface class PostsRepository {
  Future<PostsPage> fetchPage({String? cursor, int limit = 10});

  Future<Post> fetchPost(String id);

  Future<Post> create({required String title, String body = '', PostStatus status = PostStatus.draft});

  Future<Post> update(String id, {String? title, String? body, PostStatus? status});

  Future<void> delete(String id);
}
