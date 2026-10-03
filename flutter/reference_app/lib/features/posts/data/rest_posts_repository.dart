import '../../../core/networking/api_client.dart';
import '../domain/post.dart';
import '../domain/posts_repository.dart';
import 'post_dto.dart';

class RestPostsRepository implements PostsRepository {
  RestPostsRepository(this._api);

  final ApiClient _api;

  @override
  Future<PostsPage> fetchPage({String? cursor, int limit = 10}) async =>
      postsPageFromJson(await _api.get('/api/v1/posts', query: {'cursor': cursor, 'limit': limit}));

  @override
  Future<Post> fetchPost(String id) async => postFromJson(await _api.get('/api/v1/posts/$id'));

  @override
  Future<Post> create({
    required String title,
    String body = '',
    PostStatus status = PostStatus.draft,
  }) async => postFromJson(
    await _api.post('/api/v1/posts', body: {'title': title, 'body': body, 'status': status.name}),
  );

  @override
  Future<Post> update(String id, {String? title, String? body, PostStatus? status}) async => postFromJson(
    await _api.patch(
      '/api/v1/posts/$id',
      // Only the fields being changed: PATCH semantics, and no accidental nulls.
      body: {'title': ?title, 'body': ?body, 'status': ?status?.name},
    ),
  );

  @override
  Future<void> delete(String id) => _api.delete('/api/v1/posts/$id');
}
