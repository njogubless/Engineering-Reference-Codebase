import 'dart:convert';

import 'package:cloud_firestore/cloud_firestore.dart';

import '../../../core/errors/app_error.dart';
import '../domain/post.dart';
import '../domain/posts_repository.dart';

/// Who is acting. Firebase Auth supplies this in Phase 3; until then the
/// caller provides it (and Firestore security rules, Phase 4, enforce it).
typedef CurrentAuthor = ({String id, String name});

/// [PostsRepository] on Cloud Firestore.
///
/// Data model: `posts/{postId}` documents with a `comments` subcollection.
/// Firestore differs from the SQL backends in ways this class makes explicit:
/// - No joins: the author's name is copied into each post (denormalised).
/// - No cascading deletes: deleting a post must delete its comments.
/// - No server-computed counts on read: `commentCount` is maintained in a
///   transaction whenever a comment is added.
/// - Pagination uses the same keyset idea as the APIs, through Firestore's
///   document cursors (`startAfterDocument`).
class FirestorePostsRepository implements PostsRepository {
  FirestorePostsRepository(this._db, {required this.currentAuthor});

  final FirebaseFirestore _db;
  final CurrentAuthor Function() currentAuthor;

  CollectionReference<Map<String, Object?>> get _posts => _db.collection('posts');

  CollectionReference<Map<String, Object?>> _comments(String postId) =>
      _posts.doc(postId).collection('comments');

  /// Firestore's canonical cursor: `startAfterDocument`. A cursor taken from
  /// a document snapshot implicitly adds the document id as a tiebreaker, so
  /// posts with identical `createdAt` still page in a stable order. The client
  /// cursor carries only the last document's id (opaque, base64).
  @override
  Future<PostsPage> fetchPage({String? cursor, int limit = 10}) => _guard(() async {
    var query = _posts
        .where('status', isEqualTo: PostStatus.published.name)
        .orderBy('createdAt', descending: true);
    if (cursor != null) {
      final last = await _posts.doc(_decodeCursor(cursor)).get();
      if (!last.exists) throw _invalidCursor;
      query = query.startAfterDocument(last);
    }
    final docs = (await query.limit(limit + 1).get(_estimateTimestamps)).docs;
    final items = [for (final doc in docs.take(limit)) _fromDoc(doc)];
    final next = docs.length > limit ? base64Url.encode(utf8.encode(items.last.id)) : null;
    return PostsPage(items: items, nextCursor: next);
  });

  @override
  Future<Post> fetchPost(String id) => _guard(() async {
    final doc = await _posts.doc(id).get(_estimateTimestamps);
    if (!doc.exists) {
      throw const ServerError(code: ServerErrorCode.notFound, status: 404, message: 'No such post.');
    }
    return _fromDoc(doc);
  });

  /// Live updates: Firestore pushes every change; no polling.
  Stream<Post?> watchPost(String id) =>
      _posts.doc(id).snapshots().map((doc) => doc.exists ? _fromDoc(doc) : null);

  @override
  Future<Post> create({required String title, String body = '', PostStatus status = PostStatus.draft}) =>
      _guard(() async {
        final author = currentAuthor();
        final ref = _posts.doc(); // client-generated id: no round trip needed
        await ref.set({
          'title': title.trim(),
          'body': body,
          'status': status.name,
          'authorId': author.id,
          'authorName': author.name, // denormalised: Firestore has no joins
          'commentCount': 0,
          // The server's clock, not the device's (which may be wrong).
          'createdAt': FieldValue.serverTimestamp(),
          'publishedAt': status == PostStatus.published ? FieldValue.serverTimestamp() : null,
        });
        return fetchPost(ref.id);
      });

  @override
  Future<Post> update(String id, {String? title, String? body, PostStatus? status}) => _guard(() async {
    await _posts.doc(id).update({
      'title': ?title?.trim(),
      'body': ?body,
      if (status != null) ...{
        'status': status.name,
        'publishedAt': status == PostStatus.published ? FieldValue.serverTimestamp() : null,
      },
    });
    return fetchPost(id);
  });

  /// Firestore does not cascade: comments must be deleted explicitly, or they
  /// live on as orphans under a deleted path. A batch makes it all-or-nothing.
  /// (A batch holds at most 500 writes; larger subcollections need chunking or
  /// a server-side recursive delete.)
  @override
  Future<void> delete(String id) => _guard(() async {
    final batch = _db.batch();
    for (final comment in (await _comments(id).get()).docs) {
      batch.delete(comment.reference);
    }
    batch.delete(_posts.doc(id));
    await batch.commit();
  });

  /// Adds a comment and increments the post's counter atomically.
  ///
  /// A transaction (not two separate writes): with concurrent commenters,
  /// read-modify-write of `commentCount` outside a transaction loses updates.
  /// Firestore retries the transaction function on contention, so it must
  /// have no side effects besides its reads and writes.
  Future<void> addComment(String postId, String body) => _guard(
    () => _db.runTransaction((transaction) async {
      final postRef = _posts.doc(postId);
      final post = await transaction.get(postRef);
      if (!post.exists || post.data()?['status'] != PostStatus.published.name) {
        throw const ServerError(
          code: ServerErrorCode.validationError,
          status: 422,
          message: 'Drafts cannot be commented on.',
        );
      }
      final author = currentAuthor();
      transaction
        ..set(_comments(postId).doc(), {
          'body': body.trim(),
          'authorId': author.id,
          'authorName': author.name,
          'createdAt': FieldValue.serverTimestamp(),
        })
        ..update(postRef, {'commentCount': FieldValue.increment(1)});
    }),
  );

  /// Publishes several posts in one atomic batch: all succeed or none do.
  Future<void> publishAll(Iterable<String> ids) => _guard(() async {
    final batch = _db.batch();
    for (final id in ids) {
      batch.update(_posts.doc(id), {
        'status': PostStatus.published.name,
        'publishedAt': FieldValue.serverTimestamp(),
      });
    }
    await batch.commit();
  });

  Post _fromDoc(DocumentSnapshot<Map<String, Object?>> doc) {
    // A just-written FieldValue.serverTimestamp() is null in local snapshots
    // until the server confirms it. One-off reads ask Firestore to estimate it
    // (_estimateTimestamps); streams cannot, so a pending value means "now".
    final data = doc.data();
    if (data case {
      'title': final String title,
      'body': final String body,
      'status': final String status,
      'authorId': final String authorId,
      'authorName': final String authorName,
      'commentCount': final int commentCount,
    }) {
      final publishedAt = _instant(data['publishedAt']);
      return Post(
        id: doc.id,
        title: title,
        body: body,
        status: PostStatus.values.byName(status),
        authorId: authorId,
        authorName: authorName,
        commentCount: commentCount,
        createdAt: _instant(data['createdAt']) ?? DateTime.now().toUtc(),
        publishedAt: publishedAt,
      );
    }
    throw ParseError('Unexpected post document ${doc.id}.');
  }

  static const _estimateTimestamps = GetOptions(serverTimestampBehavior: ServerTimestampBehavior.estimate);

  static DateTime? _instant(Object? value) => value is Timestamp ? value.toDate().toUtc() : null;

  static const _invalidCursor = ServerError(
    code: ServerErrorCode.validationError,
    status: 422,
    message: 'Invalid cursor.',
  );

  String _decodeCursor(String cursor) {
    try {
      return utf8.decode(base64Url.decode(cursor));
    } on FormatException {
      throw _invalidCursor;
    }
  }

  /// Firestore throws [FirebaseException]; the app only ever sees [AppError].
  Future<T> _guard<T>(Future<T> Function() action) async {
    try {
      return await action();
    } on AppError {
      rethrow;
    } on FirebaseException catch (error, stack) {
      throw switch (error.code) {
        'unavailable' || 'deadline-exceeded' => const NetworkError('Firestore is unreachable.'),
        'permission-denied' => const ServerError(
          code: ServerErrorCode.authorizationError,
          status: 403,
          message: 'Firestore denied access.',
        ),
        'not-found' => const ServerError(code: ServerErrorCode.notFound, status: 404, message: 'Not found.'),
        _ => UnexpectedError(error, stack),
      };
    }
  }
}
