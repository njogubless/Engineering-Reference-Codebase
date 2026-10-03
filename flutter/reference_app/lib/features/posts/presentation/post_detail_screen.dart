import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/format.dart';
import '../../../shared/widgets/error_view.dart';
import '../application/posts_providers.dart';

class PostDetailScreen extends ConsumerWidget {
  const PostDetailScreen({required this.postId, super.key});

  final String postId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final post = ref.watch(postDetailProvider(postId));
    return Scaffold(
      appBar: AppBar(title: const Text('Post')),
      body: switch (post) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(value.title, style: Theme.of(context).textTheme.headlineSmall),
            Text(
              '${value.authorName} · ${value.status.name} · ${formatLocalDateTime(context, value.createdAt)}',
            ),
            const SizedBox(height: 16),
            Text(value.body),
          ],
        ),
        AsyncError(:final error) => Center(
          child: ErrorView(error: error, onRetry: () => ref.invalidate(postDetailProvider(postId))),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}
