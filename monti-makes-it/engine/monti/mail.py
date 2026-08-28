"""Outbound email.

Two providers:
  log  — writes to the email_log table and stdout (default; safe for dev)
  smtp — real delivery through any SMTP host (Postmark, SES, Google Workspace…)

Every send is recorded in email_log either way, so the admin bay has a
complete audit trail of what left the building.
"""
import smtplib
import traceback
from email.message import EmailMessage

from flask import current_app, render_template

from .db import execute


def _send_smtp(to_addr, subject, html, text, cc=None):
    cfg = current_app.config
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to_addr
    if cc:
        msg["Cc"] = cc
    msg.set_content(text or "")
    msg.add_alternative(html, subtype="html")

    if cfg["SMTP_USE_TLS"]:
        server = smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20)
    try:
        if cfg["SMTP_USER"]:
            server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.send_message(msg)
    finally:
        server.quit()


def send(to_addr, subject, template=None, cc=None, html=None, text=None, **ctx):
    """Render `template` (an email/*.html file) and deliver it."""
    if template:
        html = render_template(f"email/{template}.html", subject=subject, **ctx)
    html = html or ""
    text = text or _strip(html)

    status, error = "SENT", None
    provider = current_app.config["MAIL_PROVIDER"]
    try:
        if provider == "smtp" and current_app.config["SMTP_HOST"]:
            _send_smtp(to_addr, subject, html, text, cc)
        else:
            status = "LOGGED"
            current_app.logger.info("[mail:%s] to=%s cc=%s subject=%s", provider, to_addr, cc, subject)
    except Exception as exc:  # noqa: BLE001 - never let email break a checkout
        status, error = "FAILED", f"{exc}\n{traceback.format_exc(limit=3)}"
        current_app.logger.error("Email send failed to %s: %s", to_addr, exc)

    try:
        execute(
            "INSERT INTO email_log (to_addr, cc_addr, subject, body, template, status, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (to_addr, cc, subject, html, template, status, error),
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("Could not write email_log row")
    return status == "SENT" or status == "LOGGED"


def _strip(html: str) -> str:
    out, keep = [], True
    for ch in html:
        if ch == "<":
            keep = False
        elif ch == ">":
            keep = True
        elif keep:
            out.append(ch)
    text = "".join(out)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
