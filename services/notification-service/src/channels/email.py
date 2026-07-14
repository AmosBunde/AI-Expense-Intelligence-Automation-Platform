"""SMTP email channel. No-op (delivered=false) when SMTP is unconfigured."""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("notification-service.email")


def send_email(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    host = os.getenv("SMTP_HOST", "")
    if not host:
        logger.info("SMTP not configured; would send to=%s subject=%r", recipient, subject)
        return False, "smtp-not-configured"
    if not recipient:
        return False, "no-recipient"

    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM", "expenses@localhost")
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            user = os.getenv("SMTP_USER", "")
            if user:
                smtp.login(user, os.getenv("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        return True, "sent"
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("SMTP send failed: %s", exc)
        return False, f"smtp-error: {exc}"
