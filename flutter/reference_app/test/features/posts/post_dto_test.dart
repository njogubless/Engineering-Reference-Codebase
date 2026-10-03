import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/features/posts/data/post_dto.dart';
import 'package:reference_app/features/posts/domain/post.dart';

Map<String, Object?> postJson({
  Object? createdAt = '2026-07-01T16:00:00.123456Z',
  Object? status = 'published',
}) => {
  'id': 'p1',
  'title': 'T',
  'body': 'B',
  'status': status,
  'author': {'id': 'u1', 'display_name': 'Ada'},
  'comment_count': 2,
  'created_at': createdAt,
  'updated_at': '2026-07-01T16:00:00Z',
  'published_at': null,
};

void main() {
  test('maps the wire format to the domain entity, keeping instants in UTC', () {
    final post = postFromJson(postJson());
    expect(post.status, PostStatus.published);
    expect(post.authorName, 'Ada');
    expect(post.createdAt.isUtc, isTrue);
    expect(post.createdAt.microsecond, 456);
  });

  test('rejects timestamps without a UTC designator', () {
    expect(() => postFromJson(postJson(createdAt: '2026-07-01T16:00:00')), throwsA(isA<ParseError>()));
  });

  test('rejects unknown statuses and malformed shapes', () {
    expect(() => postFromJson(postJson(status: 'archived')), throwsA(isA<ParseError>()));
    expect(() => postFromJson({'id': 1}), throwsA(isA<ParseError>()));
    expect(() => postsPageFromJson({'items': 'nope'}), throwsA(isA<ParseError>()));
  });
}
