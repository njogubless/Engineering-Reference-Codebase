# Common problem: a case-insensitive lookup that scans the whole table

**Code:** [apps/accounts/models.py](../../django/reference_api/apps/accounts/models.py) (`get_by_natural_key`)
**Test:** `test_login_lookup_uses_the_email_index` in [test_auth.py](../../django/reference_api/apps/accounts/tests/test_auth.py)

## ❌ Problematic

```python
def get_by_natural_key(self, username):
    return self.get(email__iexact=username)       # every login
```

## Why it fails

On PostgreSQL, Django compiles `iexact` to:

```sql
WHERE UPPER("email"::text) = UPPER('ada@example.com')
```

Neither the unique index on `email` nor one on `lower(email)` can serve
`UPPER(email)`, so every login reads the entire users table. It's invisible
with 100 users and becomes the slowest query in the system at 1 million.

The test proves it. With the problematic version, `EXPLAIN` reports:

```text
Seq Scan on accounts_user  Filter: (upper((email)::text) = 'ADA@EXAMPLE.COM'::text)
```

## ✅ Improved

Normalise once on write and once on lookup, then match exactly:

```python
def normalize_email(email): return email.strip().lower()

def get_by_natural_key(self, username):
    return self.get(email=normalize_email(username))   # uses the unique index
```

A functional unique index on `lower(email)` still guards writes that bypass
normalisation (a shell, a data migration).

## Generalising

Whenever a query wraps an indexed column in a function (`UPPER(col)`,
`DATE(created_at)`, `col::text`), the plain index on `col` no longer applies.
Either index the expression or store data in the form you query by. Check
with `EXPLAIN`, and keep the check in a test when the query matters.
