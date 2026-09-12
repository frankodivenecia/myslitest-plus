"""Odesílání e-mailů přes SMTP (z .env: SMTP_HOST/PORT/USER/PASS, MAIL_FROM).
Port 587 = STARTTLS. Převzato z Dominia. Vyhazuje výjimku při chybě —
volající ji ošetří."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def send_email(to_addr: str, subject: str, body: str, html: str | None = None,
               reply_to: str | None = None, from_addr: str | None = None) -> None:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "")
    default_sender = os.getenv("MAIL_FROM", "").strip() or user
    sender = (from_addr or default_sender).strip()
    envelope = user or sender

    if not host or not user:
        raise RuntimeError("SMTP není nakonfigurováno (SMTP_HOST / SMTP_USER).")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_addr
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls(context=context)
        server.login(user, password)
        server.send_message(msg, from_addr=envelope)
