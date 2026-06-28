"""Brevo email helpers for CodeMentor AI."""

from __future__ import annotations

import logging
from email.utils import parseaddr

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _parse_sender(from_address: str | None) -> dict[str, str]:
    """Split a Brevo sender string into the API shape Brevo expects."""
    name, email = parseaddr(from_address or "")
    if not email:
        return {}
    payload = {"email": email.strip()}
    if name.strip():
        payload["name"] = name.strip()
    return payload


def is_email_configured() -> bool:
    settings = get_settings()
    return bool((settings.brevo_api_key or "").strip() and (settings.brevo_from or "").strip())


async def send_email(*, to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Send a Brevo email if configured, returning False when unavailable.

    The helper is intentionally non-fatal so login can still succeed if the
    email service is missing or temporarily unavailable.
    """
    settings = get_settings()
    api_key = (settings.brevo_api_key or "").strip()
    from_address = (settings.brevo_from or "").strip()

    if not api_key or not from_address:
        logger.warning("Brevo email service is not configured.")
        return False

    payload = {
        "sender": _parse_sender(from_address),
        "to": [{"email": to.strip()}],
        "subject": subject,
        "textContent": text,
        "htmlContent": html or f"<p>{text}</p>",
    }

    timeout = httpx.Timeout(settings.email_send_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                BREVO_API_URL,
                headers={
                    "accept": "application/json",
                    "api-key": api_key,
                    "content-type": "application/json",
                },
                json=payload,
            )

        if not response.is_success:
            provider_message = None
            try:
                provider_message = response.json()
            except ValueError:
                provider_message = response.text

            logger.warning(
                "Brevo email delivery failed.",
                extra={
                    "status_code": response.status_code,
                    "provider_message": provider_message,
                },
            )
            return False

        return True
    except httpx.TimeoutException:
        logger.warning("Brevo email delivery timed out.")
        return False
    except httpx.RequestError as exc:
        logger.warning("Brevo email delivery error: %s", exc.__class__.__name__)
        return False
    except Exception as exc:  # noqa: BLE001 - keep login flow resilient
        logger.exception("Unexpected Brevo email failure: %s", exc.__class__.__name__)
        return False


async def send_login_otp(*, name: str, email: str, otp: str, expires_in_minutes: int) -> bool:
    """Send a login OTP email."""
    subject = "Your CodeMentor AI login code"
    text = (
        f"Hello {name},\n\n"
        f"Your CodeMentor AI login code is {otp}.\n"
        f"It expires in {expires_in_minutes} minutes.\n"
    )
    html = (
        f"<p>Hello {name},</p>"
        f"<p>Your CodeMentor AI login code is <strong>{otp}</strong>.</p>"
        f"<p>It expires in {expires_in_minutes} minutes.</p>"
    )
    return await send_email(to=email, subject=subject, text=text, html=html)
