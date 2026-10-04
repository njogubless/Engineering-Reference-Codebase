import 'package:flutter_test/flutter_test.dart';
import 'package:reference_app/core/errors/app_error.dart';
import 'package:reference_app/features/auth/data/auth_repository.dart';

void main() {
  test('parses a user, including phone-only users without email', () {
    final user = User.fromJson({
      'id': 'u1',
      'email': null,
      'email_verified': false,
      'display_name': 'Phone user',
      'date_joined': '2026-10-01T00:00:00Z',
    });
    expect(user.email, isNull);
    expect(user.emailVerified, isFalse);
  });

  test('rejects a user without the verification flag', () {
    expect(
      () => User.fromJson({'id': 'u1', 'email': 'a@b.c', 'display_name': 'A'}),
      throwsA(isA<ParseError>()),
    );
  });
}
