# 41 · Money, Time and Units

> Phase 2 covers time. Money (integer minor units + currency) arrives with
> payments in Phase 11.

## Time: store instants, display local

| Where | Rule | Implementation |
|---|---|---|
| Database | instants as `timestamptz` | Django `USE_TZ = True`; SQLAlchemy `type_annotation_map = {datetime: DateTime(timezone=True)}`, because the default is *naive* |
| API | RFC 3339 in UTC (`...Z`) | both backends; tested (`created_at.endswith("Z")`) |
| Client parsing | reject timestamps without an offset | Flutter `post_dto.dart` (`!parsed.isUtc` → `ParseError`) |
| Client display | convert to the viewer's zone and locale only when rendering | React `formatDateTime` (`Intl.DateTimeFormat`); Flutter `formatLocalDateTime` (`MaterialLocalizations`, no extra package) |
| Ordering | never by a client clock | server timestamps (`FieldValue.serverTimestamp()` in Firestore) |

### DST is a real edge case

On 8 March 2026, New York clocks jump from 01:59 to 03:00. The React test
proves that 06:30Z displays as 1:30 AM and 07:30Z as 3:30 AM: the hour
between doesn't exist locally. Code that adds "24 hours" to a local
date-time, or stores local times, gets days like this wrong. Store instants;
do calendar arithmetic in a time-zone-aware library at the edge.

## Common mistakes

| ❌ | ✅ |
|---|---|
| `DateTime.now()` / `new Date()` from the device as the record time | server timestamps |
| Naive `TIMESTAMP` columns | `timestamptz` |
| Formatting dates with string concatenation | `Intl` / localizations |
| Parsing `"2026-07-01 12:00"` (no offset) as if it were UTC | reject it at the boundary |
| Converting to local time before storing | store UTC; convert on display |
