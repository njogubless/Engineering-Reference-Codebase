import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/application/session_controller.dart';
import '../auth/presentation/sign_in_screen.dart';
import '../diagnostics/presentation/diagnostics_screen.dart';
import '../posts/presentation/posts_screen.dart';

/// The patterns catalogue: one entry per demo. Phase 4 replaces these
/// Navigator pushes with go_router (named routes, guards, deep links).
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    void open(Widget screen) => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => screen));
    return Scaffold(
      appBar: AppBar(title: const Text('Reference App')),
      body: ListView(
        children: [
          ListTile(
            title: const Text('Posts'),
            subtitle: const Text('Pagination, pull-to-refresh, optimistic updates'),
            onTap: () => open(const PostsScreen()),
          ),
          ListTile(
            title: const Text('Diagnostics'),
            subtitle: const Text('Configuration, health, error handling'),
            onTap: () => open(const DiagnosticsScreen()),
          ),
          const Divider(),
          if (session == null)
            ListTile(title: const Text('Sign in'), onTap: () => open(const SignInScreen()))
          else
            ListTile(
              title: Text('Signed in as ${session.user.displayName}'),
              trailing: TextButton(
                onPressed: () => ref.read(sessionProvider.notifier).signOut(),
                child: const Text('Sign out'),
              ),
            ),
        ],
      ),
    );
  }
}
