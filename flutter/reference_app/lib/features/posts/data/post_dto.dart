import '../../../core/errors/app_error.dart';
import '../domain/post.dart';

/// JSON (the wire format from contracts/openapi.yaml) -> domain entity.
/// Validates shape at the boundary: a malformed response is a ParseError
/// here, not a TypeError deep in a widget.
Post postFromJson(Object? json) {
  if (json case {
    'id': final String id,
    'title': final String title,
    'body': final String body,
    'status': final String status,
    'author': {'id': final String authorId, 'display_name': final String authorName},
    'comment_count': final int commentCount,
    'created_at': final String createdAt,
    'published_at': final String? publishedAt,
  }) {
    return Post(
      id: id,
      title: title,
      body: body,
      status: _status(status),
      authorId: authorId,
      authorName: authorName,
      commentCount: commentCount,
      createdAt: _instant(createdAt),
      publishedAt: publishedAt == null ? null : _instant(publishedAt),
    );
  }
  throw const ParseError('Unexpected post shape.');
}

PostsPage postsPageFromJson(Object? json) {
  if (json case {'items': final List<Object?> items, 'next_cursor': final String? nextCursor}) {
    return PostsPage(items: [for (final item in items) postFromJson(item)], nextCursor: nextCursor);
  }
  throw const ParseError('Unexpected page shape.');
}

PostStatus _status(String value) => switch (value) {
  'draft' => PostStatus.draft,
  'published' => PostStatus.published,
  _ => throw ParseError('Unknown post status "$value".'),
};

DateTime _instant(String value) {
  final parsed = DateTime.tryParse(value);
  // RFC 3339 with an offset: reject local "wall clock" times outright.
  if (parsed == null || !parsed.isUtc) throw ParseError('Expected a UTC timestamp, got "$value".');
  return parsed;
}
