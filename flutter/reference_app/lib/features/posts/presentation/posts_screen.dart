import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_error.dart';
import '../../../core/errors/user_message.dart';
import '../../../shared/format.dart';
import '../../../shared/widgets/error_view.dart';
import '../../auth/application/session_controller.dart';
import '../application/posts_providers.dart';
import '../domain/post.dart';
import 'post_detail_screen.dart';

/// Infinite scroll + pull-to-refresh + every list state, in one screen.
class PostsScreen extends ConsumerStatefulWidget {
  const PostsScreen({super.key});

  @override
  ConsumerState<PostsScreen> createState() => _PostsScreenState();
}

class _PostsScreenState extends ConsumerState<PostsScreen> {
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scroll.dispose(); // controllers hold listeners: always dispose
    super.dispose();
  }

  void _onScroll() {
    // Start loading before the user hits the very bottom.
    if (_scroll.position.extentAfter < 400) {
      ref.read(postsListProvider.notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final posts = ref.watch(postsListProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Posts')),
      body: switch (posts) {
        AsyncData(:final value) when value.items.isEmpty => const Center(child: Text('No posts yet.')),
        AsyncData(:final value) => RefreshIndicator(
          onRefresh: () => ref.read(postsListProvider.notifier).refresh(),
          child: ListView.builder(
            controller: _scroll,
            // Builder: only visible rows are built, however long the list.
            itemCount: value.items.length + 1,
            itemBuilder: (context, index) =>
                index < value.items.length ? _PostTile(post: value.items[index]) : _ListFooter(state: value),
          ),
        ),
        AsyncError(:final error) => Center(
          child: ErrorView(error: error, onRetry: () => ref.invalidate(postsListProvider)),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _PostTile extends ConsumerWidget {
  const _PostTile({required this.post});

  final Post post;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // `select`: rebuild only when the signed-in user's id changes, not on
    // every session change (e.g. a token refresh).
    final userId = ref.watch(sessionProvider.select((session) => session?.user.id));
    final comments = post.commentCount == 1 ? '1 comment' : '${post.commentCount} comments';
    return ListTile(
      title: Text(post.title),
      subtitle: Text(
        '${post.authorName} · ${formatLocalDateTime(context, post.publishedAt ?? post.createdAt)} · $comments',
      ),
      trailing: userId == post.authorId
          ? Switch(
              value: post.isPublished,
              onChanged: (published) async {
                try {
                  await ref
                      .read(postsListProvider.notifier)
                      .setStatus(post, published ? PostStatus.published : PostStatus.draft);
                } on AppError catch (error) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(userMessage(error))));
                  }
                }
              },
            )
          : null,
      onTap: () => Navigator.of(
        context,
      ).push(MaterialPageRoute<void>(builder: (_) => PostDetailScreen(postId: post.id))),
    );
  }
}

class _ListFooter extends ConsumerWidget {
  const _ListFooter({required this.state});

  final PostsListState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
    padding: const EdgeInsets.all(16),
    child: Center(
      child: switch (state) {
        PostsListState(isLoadingMore: true) => const CircularProgressIndicator(),
        PostsListState(:final loadMoreError?) => ErrorView(
          error: loadMoreError,
          onRetry: () => ref.read(postsListProvider.notifier).loadMore(),
        ),
        PostsListState(hasMore: true) => TextButton(
          onPressed: () => ref.read(postsListProvider.notifier).loadMore(),
          child: const Text('Load more'),
        ),
        _ => const Text('You have reached the end.'),
      },
    ),
  );
}
