import '../../../core/errors/app_error.dart';
import '../../../core/networking/api_client.dart';

final class User {
  const User({required this.id, required this.email, required this.displayName, this.emailVerified = false});

  factory User.fromJson(Object? json) {
    if (json case {
      'id': final String id,
      'email': final String? email,
      'email_verified': final bool emailVerified,
      'display_name': final String name,
    }) {
      return User(id: id, email: email, displayName: name, emailVerified: emailVerified);
    }
    throw const ParseError('Unexpected user shape.');
  }

  final String id;

  /// Null for accounts created through phone sign-in.
  final String? email;
  final bool emailVerified;
  final String displayName;
}

/// Tokens + user. Held in memory only in Phase 2b: an app restart means
/// signing in again. Phase 3 adds secure storage and session restoration.
final class Session {
  const Session({required this.user, required this.access, required this.refresh});

  final User user;
  final String access;
  final String refresh;
}

class AuthRepository {
  AuthRepository(this._api);

  final ApiClient _api;

  Future<Session> signIn(String email, String password) async {
    final tokens = await _api.post('/api/v1/auth/token', body: {'email': email, 'password': password});
    if (tokens case {'access': final String access, 'refresh': final String refresh}) {
      final me = await _api.get('/api/v1/auth/me', headers: {'Authorization': 'Bearer $access'});
      return Session(user: User.fromJson(me), access: access, refresh: refresh);
    }
    throw const ParseError('Unexpected token response.');
  }

  /// Best effort: the refresh token also expires on its own.
  Future<void> signOut(String refresh) => _api.post('/api/v1/auth/logout', body: {'refresh': refresh});
}
