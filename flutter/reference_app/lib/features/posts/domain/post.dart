/// Domain entity: what the app works with, independent of where it came
/// from (REST JSON or a Firestore document). Immutable; change via [copyWith].
enum PostStatus { draft, published }

final class Post {
  const Post({
    required this.id,
    required this.title,
    required this.body,
    required this.status,
    required this.authorId,
    required this.authorName,
    required this.commentCount,
    required this.createdAt,
    this.publishedAt,
  });

  final String id;
  final String title;
  final String body;
  final PostStatus status;
  final String authorId;
  final String authorName;
  final int commentCount;

  /// Instants, always in UTC. Converted to local time only for display.
  final DateTime createdAt;
  final DateTime? publishedAt;

  bool get isPublished => status == PostStatus.published;

  Post copyWith({String? title, String? body, PostStatus? status, int? commentCount}) => Post(
    id: id,
    title: title ?? this.title,
    body: body ?? this.body,
    status: status ?? this.status,
    authorId: authorId,
    authorName: authorName,
    commentCount: commentCount ?? this.commentCount,
    createdAt: createdAt,
    publishedAt: publishedAt,
  );
}

final class PostsPage {
  const PostsPage({required this.items, required this.nextCursor});

  final List<Post> items;

  /// Opaque: pass it back unchanged; null at the end of the list.
  final String? nextCursor;
}
