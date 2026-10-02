# 03 · Authentication

> Phase 2a covers the **backend** side: first-party email/password with
> short-lived access tokens and rotating refresh tokens. Client flows,
> Firebase (email, Google, phone) and backend Firebase token verification
> follow in Phase 3.

## The problem

"Log the user in and remember them" sounds simple. Most of the real
decisions are about failure and theft:
- How long is a stolen credential useful?
- Can the API reveal which emails have accounts?
- What happens when two tabs refresh at the same moment?
- What does a database leak expose?

## The pattern

```text
POST /auth/token  {email, password}        ──► {access (JWT, 15 min), refresh (7 days, single use)}
GET  /api/...     Authorization: Bearer <access>
POST /auth/token/refresh {refresh}          ──► {new access, NEW refresh}; the old refresh is dead
POST /auth/logout {refresh}                 ──► 204, revokes it (idempotent)
```

| Decision | Choice | Why |
|---|---|---|
| Access token | JWT, HS256, 15 minutes, `sub` = user id | Stateless check on every request; the short life limits damage if it leaks |
| Refresh token | single use, rotated on every refresh, 7 days | A leaked refresh token stops working after one use |
| Reuse of a rotated token | FastAPI: revoke the whole token *family* (theft detection) · Django/simplejwt: reject that token | Reuse means two parties hold the token, and the server can't tell which is legitimate |
| Refresh storage | FastAPI: SHA-256 hash only · simplejwt: stores the JWT (needed for its blacklist) | A database leak should not hand out live sessions |
| Passwords | Argon2id | Memory-hard: GPU cracking is expensive |
| Wrong email vs wrong password | identical 401 message **and** identical timing (FastAPI verifies a dummy hash for unknown emails) | No account enumeration through messages or response time |
| Missing credentials | 401 with `WWW-Authenticate: Bearer` | RFC 6750. With no authenticator configured, DRF returns 403 instead, so configuring one matters |
| Invalid token on a public endpoint | 401, never silently anonymous | A client with a broken token should find out |
| Logout | always 204 | Idempotent: a retried logout never shows an error |

## How it is implemented

| | Django | FastAPI |
|---|---|---|
| Tokens | `djangorestframework-simplejwt` (`ROTATE_REFRESH_TOKENS`, `BLACKLIST_AFTER_ROTATION`) | hand-written with `pyjwt` + a `refresh_tokens` table ([app/auth/](../../../fastapi/reference_api/app/auth/)) |
| Concurrent refresh with one token | blacklist check | `SELECT ... FOR UPDATE` on the token row; tested: exactly one of two concurrent refreshes succeeds |
| Current user | `JWTAuthentication` + `IsAuthenticated`; `require_user(request)` narrows the type | `CurrentUser` / `OptionalUser` dependencies |
| Password rules | Django's validators | the same codes; the similarity check ports Django's algorithm so both accept the same passwords |
| User model | custom `AbstractUser` with email login and UUIDv7 keys, **set before the first migration** | `users` table |
| Code | [apps/accounts/](../../../django/reference_api/apps/accounts/) | [app/auth/](../../../fastapi/reference_api/app/auth/) |

**Why two implementations differ on purpose:** Django has an established
library, and using it *is* the idiomatic answer. FastAPI shows the mechanism
those libraries hide, plus one thing simplejwt doesn't do out of the box:
family revocation on reuse.

### Emails

Emails are normalised (trimmed, lowercased) on write, and lookups normalise
the input and match exactly. A functional unique index on `lower(email)`
guards writes that skip normalisation. **Don't** use `email__iexact`
for lookups: it compiles to `UPPER(email) = UPPER(%s)`, which can't use
either index. A test runs `EXPLAIN` and fails on a sequential scan (see
[common problem](../../common-problems/case-insensitive-lookup-full-scan.md)).

## Common mistakes

| ❌ | ✅ |
|---|---|
| Long-lived access tokens (days) | 15 minutes + refresh |
| Refresh tokens that never rotate | single use, rotated |
| "User not found" vs "wrong password" | one message, same timing |
| Storing refresh tokens in plain text | store a hash |
| `jwt.decode(token, key)` without an algorithm allow-list | `algorithms=["HS256"]` (prevents `alg=none` / key-confusion attacks) |
| A short HMAC key | ≥ 32 bytes, checked at startup in both backends (PyJWT warns, and the test suite treats warnings as errors) |
| Treating an invalid token as anonymous | 401 |
| Trusting a user id sent by the client | identity only from the verified token |

## Edge cases covered by tests

Case-insensitive login and registration; weak, common, numeric and similar
passwords; inactive users; expired, malformed and wrong-type tokens; refresh
rotation; reuse of a rotated token (family revoked); concurrent refresh;
idempotent logout, including garbage tokens; refresh tokens stored hashed;
unknown fields such as `is_staff` rejected at registration.
