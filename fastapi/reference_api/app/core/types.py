"""Input string types shared by every request schema."""

from pydantic import AfterValidator, BeforeValidator
from pydantic_core import PydanticCustomError


def _reject_unstorable_characters(value: str) -> str:
    """Reject characters PostgreSQL text columns cannot store.

    A NUL byte or an unpaired UTF-16 surrogate in user input otherwise
    travels all the way to the database driver and becomes a 500. DRF's
    CharField rejects both by default; Pydantic does not, so FastAPI apps
    must. Error codes match DRF's. (Found by Schemathesis, see tests/contract.)
    """
    if "\x00" in value:
        raise PydanticCustomError("null_characters_not_allowed", "Null characters are not allowed.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise PydanticCustomError(
            "surrogate_characters_not_allowed", "Surrogate characters are not allowed."
        ) from None
    return value


SafeChars = AfterValidator(_reject_unstorable_characters)
"""Put LAST in the metadata: `Annotated[str, StringConstraints(...), SafeChars]`.

Order matters. Wrapping a validated type in constraints, i.e.
`Annotated[Annotated[str, AfterValidator(f)], StringConstraints(...)]`
with `strip_whitespace=True, min_length=1`, builds a validator chain in
which the length check runs before stripping: "\f" passes as "" and the
database CHECK constraint turns it into a 500.
(Found by Schemathesis; regression test in tests/test_posts.py.)
"""


def _python_strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _reject_blank(value: str) -> str:
    if not value.strip():
        raise PydanticCustomError("blank", "This field may not be blank.")
    return value


PythonStrip = BeforeValidator(_python_strip)
"""Trim with Python's `str.strip()`, as DRF does. Use instead of
`StringConstraints(strip_whitespace=True)`, which trims in Rust with Unicode
`White_Space`: that excludes U+001C-U+001F, so "\x1d" would survive as a
title here and be rejected by the Django API. (Found by Schemathesis.)"""

NonBlank = AfterValidator(_reject_blank)
"""Reject whitespace-only values *without* changing the value (tokens, emails)."""
