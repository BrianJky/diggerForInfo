import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def send_email(subject: str, body: str, config: dict) -> None:
    notify = config.get("notify", {})
    host = notify.get("smtp_host")
    to_emails = notify.get("to_emails", [])
    if not host or not to_emails:
        LOGGER.info("SMTP not configured, skip email")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = notify.get("smtp_user", "")
    msg["To"] = ", ".join(to_emails)
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, notify.get("smtp_port", 587)) as server:
            server.starttls()
            if notify.get("smtp_user"):
                server.login(notify.get("smtp_user"), notify.get("smtp_password"))
            server.send_message(msg)
        LOGGER.info("Email sent")
    except smtplib.SMTPException as exc:
        LOGGER.warning("Failed to send email: %s", exc)


def write_to_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
