import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/features/auth/application/session_controller.dart';
import 'package:reference_app/features/auth/data/auth_repository.dart';
import 'package:reference_app/features/posts/application/posts_providers.dart';
import 'package:reference_app/features/posts/presentation/posts_screen.dart';

import '../../support/fake_posts_repository.dart';

const ada = Session(
  user: User(id: 'ada', email: 'ada@example.com', displayName: 'Ada'),
  access: 'tok',
  refresh: 'ref',
);

class _SignedIn extends SessionController {
  @override
  Session? build() => ada;
}

Widget app(FakePostsRepository repository, {bool signedIn = false}) => ProviderScope(
  overrides: [
    postsRepositoryProvider.overrideWithValue(repository),
    if (signedIn) sessionProvider.overrideWith(_SignedIn.new),
  ],
  retry: (_, _) => null,
  child: const MaterialApp(home: PostsScreen()),
);

void main() {
  testWidgets('scrolling near the end loads the next page', (tester) async {
    final repository = FakePostsRepository([for (var n = 1; n <= 25; n++) makePost(n)]);
    await tester.pumpWidget(app(repository));
    await tester.pumpAndSettle();
    expect(find.text('Post 1'), findsOneWidget);
    expect(repository.pageRequests, 1);

    await tester.scrollUntilVisible(find.text('Post 25'), 400);
    await tester.pumpAndSettle();
    expect(repository.pageRequests, 3);
    await tester.scrollUntilVisible(find.text('You have reached the end.'), 200);
  });

  testWidgets('shows an empty state', (tester) async {
    await tester.pumpWidget(app(FakePostsRepository([])));
    await tester.pumpAndSettle();
    expect(find.text('No posts yet.'), findsOneWidget);
  });

  testWidgets('authors toggle publishing optimistically; a refusal rolls back with a message', (
    tester,
  ) async {
    final repository = FakePostsRepository([makePost(1), makePost(2, authorId: 'grace')])
      ..failNextUpdate = const ServerError(
        code: ServerErrorCode.authorizationError,
        status: 403,
        message: 'no',
      );
    await tester.pumpWidget(app(repository, signedIn: true));
    await tester.pumpAndSettle();

    // Only the author's own post has a switch.
    expect(find.byType(Switch), findsOneWidget);
    await tester.tap(find.byType(Switch));
    await tester.pump(); // optimistic frame, before the (failing) server call returns
    expect(tester.widget<Switch>(find.byType(Switch)).value, isFalse);

    await tester.pumpAndSettle();
    expect(tester.widget<Switch>(find.byType(Switch)).value, isTrue); // rolled back
    expect(find.text('You do not have permission to do this.'), findsOneWidget);
  });
}
