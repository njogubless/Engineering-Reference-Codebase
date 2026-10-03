"""Transactional email as a dependency.

`EmailSender` is a small protocol with two real implementations: SMTP
(Mailpit in development, a provider in production) and an in-memory outbox
for tests, swapped through `app.dependency_overrides`.

Sending runs in FastAPI `BackgroundTasks`: after the response is sent, in
the same process. That keeps the response time independent of SMTP (and of
whether an account exists), but a crash or restart loses the email. Phase 10
compares this with a durable queue (Celery) and explains when each fits.
"""

import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from typing import Annotated, Protocol

from fastapi import Depends, Request

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self._settings.default_from_email
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        try:
            with smtplib.SMTP(
                self._settings.email_host, self._settings.email_port, timeout=10
            ) as smtp:
                if self._settings.email_use_tls:
                    smtp.starttls()
                if self._settings.email_username:
                    smtp.login(self._settings.email_username, self._settings.email_password)
                smtp.send_message(mime)
        except OSError:
            # Runs after the response: nobody to report to but the logs.
            # Never log the body: it contains a single-use credential.
            logger.exception("email_send_failed", extra={"subject": message.subject})


@dataclass
class OutboxEmailSender:
    """Test double: records messages instead of sending them."""

    messages: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def get_email_sender(request: Request) -> EmailSender:
    sender: EmailSender = request.app.state.email_sender
    return sender


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
