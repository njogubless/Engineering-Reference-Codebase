import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_error.dart';
import '../../../shared/widgets/error_view.dart';
import '../application/session_controller.dart';

class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _submitting = false;
  AppError? _error;

  @override
  void dispose() {
    // Controllers own native resources: always dispose them.
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return; // no double submits
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref.read(sessionProvider.notifier).signIn(_email.text, _password.text);
      if (mounted) Navigator.of(context).pop();
    } on AppError catch (error) {
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Sign in')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          controller: _email,
          decoration: const InputDecoration(labelText: 'Email'),
          keyboardType: TextInputType.emailAddress,
          autofillHints: const [AutofillHints.username],
        ),
        TextField(
          controller: _password,
          decoration: const InputDecoration(labelText: 'Password'),
          obscureText: true,
          autofillHints: const [AutofillHints.password],
          onSubmitted: (_) => _submit(),
        ),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: _submitting ? null : _submit,
          child: Text(_submitting ? 'Signing in…' : 'Sign in'),
        ),
        if (_error case final ServerError error when error.code == ServerErrorCode.authenticationError)
          const Padding(padding: EdgeInsets.only(top: 12), child: Text('Email or password is incorrect.'))
        else if (_error case final error?)
          ErrorView(error: error),
        const SizedBox(height: 24),
        const Text('Demo account (after `make seed`): ada@example.com / demo-password-123'),
      ],
    ),
  );
}
