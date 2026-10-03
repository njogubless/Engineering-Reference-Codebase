/**
 * Time handling rule: the API speaks UTC instants (RFC 3339, `...Z`); the UI
 * converts to the viewer's time zone and locale only when displaying. Never
 * parse or format dates with string manipulation, and never store local times.
 */
export function formatDateTime(
  iso: string,
  { locale, timeZone }: { locale?: string; timeZone?: string } = {},
): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short', timeZone }).format(
    new Date(iso),
  );
}
