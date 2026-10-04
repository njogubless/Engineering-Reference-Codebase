"""Email rule shared with the FastAPI API (Pydantic's EmailStr uses the same
`email-validator` library): syntactically valid AND not at a special-use
domain (RFC 6761: .test, .local, .invalid, localhost, ...), because such
addresses can never receive the verification or reset emails. No DNS lookups.
Found by Schemathesis: the two backends disagreed on `a@x.test`.
"""

from django.core.exceptions import ValidationError
from email_validator import EmailNotValidError, validate_email


def validate_deliverable_domain(value: str) -> None:
    try:
        validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValidationError(str(exc), code="invalid") from None
