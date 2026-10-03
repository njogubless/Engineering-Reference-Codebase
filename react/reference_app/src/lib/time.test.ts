import { formatDateTime } from './time';

const NEW_YORK = { locale: 'en-US', timeZone: 'America/New_York' };

it('converts UTC to the viewer time zone', () => {
  expect(formatDateTime('2026-07-01T16:00:00Z', NEW_YORK)).toBe('Jul 1, 2026, 12:00 PM');
});

it('handles the DST jump: 02:00-02:59 local does not exist on that day', () => {
  // 06:30Z is 01:30 EST; one hour later the clocks jump to 03:30 EDT.
  expect(formatDateTime('2026-03-08T06:30:00Z', NEW_YORK)).toBe('Mar 8, 2026, 1:30 AM');
  expect(formatDateTime('2026-03-08T07:30:00Z', NEW_YORK)).toBe('Mar 8, 2026, 3:30 AM');
});

it('formats per locale', () => {
  expect(formatDateTime('2026-07-01T16:00:00Z', { locale: 'en-GB', timeZone: 'Africa/Nairobi' })).toBe(
    '1 Jul 2026, 19:00',
  );
});
