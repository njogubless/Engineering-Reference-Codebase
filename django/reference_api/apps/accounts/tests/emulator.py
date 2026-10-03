"""Helpers for the Firebase Auth emulator (REST API; stdlib only).

They do what a client SDK would: sign up, sign in, phone OTP. The tokens are
real emulator ID tokens, verified by the same firebase-admin code as production.
"""

import base64
import json
import os
import urllib.request
from typing import Any

HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
PROJECT = "demo-reference"
IDENTITY = f"http://{HOST}/identitytoolkit.googleapis.com/v1"
ADMIN = f"http://{HOST}/emulator/v1/projects/{PROJECT}"


def _call(method: str, url: str, body: dict[str, Any] | None = None) -> Any:
    request = urllib.request.Request(  # noqa: S310 - fixed local emulator URL
        url,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        raw = response.read()
    return json.loads(raw) if raw else None


def reset() -> None:
    _call("DELETE", f"{ADMIN}/accounts")


def sign_up(email: str, password: str) -> dict[str, Any]:
    return _call(
        "POST",
        f"{IDENTITY}/accounts:signUp?key=fake-key",
        {"email": email, "password": password, "returnSecureToken": True},
    )


def sign_in(email: str, password: str) -> dict[str, Any]:
    return _call(
        "POST",
        f"{IDENTITY}/accounts:signInWithPassword?key=fake-key",
        {"email": email, "password": password, "returnSecureToken": True},
    )


def phone_sign_in(number: str) -> dict[str, Any]:
    session = _call(
        "POST",
        f"{IDENTITY}/accounts:sendVerificationCode?key=fake-key",
        {"phoneNumber": number, "recaptchaToken": "x"},
    )["sessionInfo"]
    codes = _call("GET", f"{ADMIN}/verificationCodes")["verificationCodes"]
    code = next(c["code"] for c in reversed(codes) if c["phoneNumber"] == number)
    return _call(
        "POST",
        f"{IDENTITY}/accounts:signInWithPhoneNumber?key=fake-key",
        {"sessionInfo": session, "code": code},
    )


def with_claim(id_token: str, **claims: Any) -> str:
    """Rewrite claims of an (unsigned) emulator token, e.g. a foreign audience."""
    header, payload, signature = id_token.split(".")
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    data.update(claims)
    encoded = base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()
    return f"{header}.{encoded}.{signature}"
