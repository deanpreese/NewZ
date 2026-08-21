"""The send (P4 E3A.3).

Gmail over SMTP_SSL, credentials from `.env` — `GMAIL_USER`, `GMAIL_PASS`,
`GMAIL_TO` — which have sat there unused since the repo was created. The
constitution already permits this and draws the line in the right place:
`read-only-web-001`, *"Email to the operator is not publishing; email to anyone
else is."*

**A send failure is never raised.** It is returned, recorded in `monitor_log`,
and retried on the next hourly run. The monitor going quiet because its mail
server did is the failure mode the whole phase exists to avoid.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

HOST = "smtp.gmail.com"
PORT = 465


class NotConfigured(RuntimeError):
    """No credentials. Not an error the monitor stops for."""


def send(subject: str, body: str, *, user: str | None, password: str | None,
         to: str | None, host: str = HOST, port: int = PORT,
         transport=None) -> str:
    """Send, and return "" on success or the reason it did not.

    `transport` is the seam the tests use: any callable taking the built
    message. Nothing about the message depends on the network, so the composed
    mail is assertable without one.
    """
    if not (user and password and to):
        missing = [n for n, v in (("GMAIL_USER", user), ("GMAIL_PASS", password),
                                  ("GMAIL_TO", to)) if not v]
        return f"not configured: {', '.join(missing)} unset"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)

    if transport is not None:
        transport(msg)
        return ""
    try:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as s:
            s.login(user, password)
            s.send_message(msg)
    except (smtplib.SMTPException, OSError, ssl.SSLError) as e:
        return f"{type(e).__name__}: {e}"
    return ""
