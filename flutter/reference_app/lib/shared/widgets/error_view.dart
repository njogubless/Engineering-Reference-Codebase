import 'package:flutter/material.dart';

import '../../core/errors/app_error.dart';
import '../../core/errors/user_message.dart';

/// The one way the UI presents an error: a user-facing message chosen by error
/// type/code, the request ID for support, and a retry action when useful.
class ErrorView extends StatelessWidget {
  const ErrorView({required this.error, this.onRetry, super.key});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final appError = toAppError(error);
    final requestId = appError.requestId;
    final colors = Theme.of(context).colorScheme;
    return Semantics(
      liveRegion: true,
      child: Card(
        color: colors.errorContainer,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(userMessage(appError), style: TextStyle(color: colors.onErrorContainer)),
              if (requestId != null) SelectableText('Reference: $requestId'),
              if (onRetry != null && isRetryable(appError))
                TextButton(onPressed: onRetry, child: const Text('Try again')),
            ],
          ),
        ),
      ),
    );
  }
}
