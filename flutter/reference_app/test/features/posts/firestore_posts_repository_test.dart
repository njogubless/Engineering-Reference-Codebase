import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:fake_cloud_firestore/fake_cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/features/posts/data/firestore_posts_repository.dart';
import 'package:reference_app/features/posts/domain/post.dart';

/// Verified against fake_cloud_firestore (an in-memory Firestore). The
/// emulator run comes with Firebase Auth in Phase 3; see the matrix (🧪).
void main() {
  late FakeFirebaseFirestore db;
  late FirestorePostsRepository repository;

  setUp(() {
    db = FakeFirebaseFirestore();
    repository = FirestorePostsRepository(db, currentAuthor: () => (id: 'ada', name: 'Ada'));
  });

  Future<void> seed(int count, {DateTime? sameTime}) async {
    for (var n = 0; n < count; n++) {
      await db.collection('posts').doc('p${n.toString().padLeft(2, '0')}').set({
        'title': 'Post $n',
        'body': '',
        'status': 'published',
        'authorId': 'ada',
        'authorName': 'Ada',
        'commentCount': 0,
        'createdAt': Timestamp.fromDate(sameTime ?? DateTime.utc(2026, 7, 1).add(Duration(minutes: n))),
        'publishedAt': Timestamp.fromDate(DateTime.utc(2026, 7, 1)),
      });
    }
  }

  test('creates with server timestamps and reads back as a domain entity', () async {
    final post = await repository.create(title: '  Hello  ', status: PostStatus.published);
    expect(post.title, 'Hello');
    expect(post.authorName, 'Ada');
    expect(post.createdAt.isUtc, isTrue);
    expect(post.publishedAt, isNotNull);
  });

  Future<List<String>> walkAllPages() async {
    final ids = <String>[];
    String? cursor;
    do {
      final page = await repository.fetchPage(cursor: cursor, limit: 3);
      ids.addAll(page.items.map((p) => p.id));
      cursor = page.nextCursor;
    } while (cursor != null);
    return ids;
  }

  test('pages newest first', () async {
    await seed(7);
    expect(await walkAllPages(), ['p06', 'p05', 'p04', 'p03', 'p02', 'p01', 'p00']);
  });

  test('ties on createdAt still give every post exactly once', () async {
    // Document cursors add the document id as a tiebreaker. Its direction is
    // backend-defined (Firestore: same as the last orderBy; the fake differs),
    // so assert the property that matters: complete and duplicate-free.
    await seed(7, sameTime: DateTime.utc(2026, 7, 1));
    final ids = await walkAllPages();
    expect(ids, hasLength(7));
    expect(ids.toSet(), hasLength(7));
  });

  test('drafts are not listed', () async {
    await repository.create(title: 'Draft');
    expect((await repository.fetchPage()).items, isEmpty);
  });

  test('a comment and its counter change atomically in a transaction', () async {
    final post = await repository.create(title: 'P', status: PostStatus.published);
    await repository.addComment(post.id, 'First');
    await repository.addComment(post.id, 'Second');
    expect((await repository.fetchPost(post.id)).commentCount, 2);
    expect((await db.collection('posts').doc(post.id).collection('comments').get()).docs, hasLength(2));
  });

  test('commenting on a draft fails inside the transaction and writes nothing', () async {
    final draft = await repository.create(title: 'D');
    await expectLater(repository.addComment(draft.id, 'x'), throwsA(isA<ServerError>()));
    expect((await db.collection('posts').doc(draft.id).collection('comments').get()).docs, isEmpty);
    expect((await repository.fetchPost(draft.id)).commentCount, 0);
  });

  test('publishAll publishes several posts in one batch', () async {
    final a = await repository.create(title: 'A');
    final b = await repository.create(title: 'B');
    await repository.publishAll([a.id, b.id]);
    expect((await repository.fetchPage()).items, hasLength(2));
  });

  test('deleting a post also deletes its comments (Firestore does not cascade)', () async {
    final post = await repository.create(title: 'P', status: PostStatus.published);
    await repository.addComment(post.id, 'orphan?');
    await repository.delete(post.id);
    expect((await db.collection('posts').doc(post.id).collection('comments').get()).docs, isEmpty);
    await expectLater(repository.fetchPost(post.id), throwsA(isA<ServerError>()));
  });

  test('watchPost streams every change', () async {
    final post = await repository.create(title: 'Before');
    final titles = repository.watchPost(post.id).map((p) => p?.title);
    final expectation = expectLater(titles, emitsInOrder(['Before', 'After', null]));
    await repository.update(post.id, title: 'After');
    await repository.delete(post.id);
    await expectation;
  });

  test('a tampered cursor is a validation error', () async {
    await expectLater(repository.fetchPage(cursor: 'garbage'), throwsA(isA<ServerError>()));
  });
}
