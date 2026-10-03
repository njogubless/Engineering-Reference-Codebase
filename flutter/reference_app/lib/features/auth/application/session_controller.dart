import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_error.dart';
import '../../../core/providers.dart';
import '../data/auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(ref.watch(apiClientProvider)),
);

/// `Notifier`: synchronous state (the current session, or null) changed by
/// methods. Not an AsyncNotifier: "signing in" is the sign-in screen's state,
/// not the session's.
class SessionController extends Notifier<Session?> {
  @override
  Session? build() => null;

  Future<void> signIn(String email, String password) async {
    state = await ref.read(authRepositoryProvider).signIn(email, password);
  }

  Future<void> signOut() async {
    final refresh = state?.refresh;
    state = null; // the local session ends first, whatever the network does
    if (refresh == null) return;
    try {
      await ref.read(authRepositoryProvider).signOut(refresh);
    } on AppError catch (error) {
      ref.read(loggerProvider).warning('logout_request_failed', {'error': error.message});
    }
  }

  /// Called by the HTTP layer when the server rejects the access token.
  void expire() => state = null;
}

final sessionProvider = NotifierProvider<SessionController, Session?>(SessionController.new);
