import 'package:flutter/material.dart';

/// UTC instant -> the device's local time, in the user's locale. Uses the
/// app's MaterialLocalizations, so no extra formatting package is needed.
String formatLocalDateTime(BuildContext context, DateTime instant) {
  final local = instant.toLocal();
  final localizations = MaterialLocalizations.of(context);
  return '${localizations.formatMediumDate(local)} ${localizations.formatTimeOfDay(TimeOfDay.fromDateTime(local))}';
}
