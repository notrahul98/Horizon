"""
Phase 5: alert delivery.

Telegram only for now — free, no payment info needed, just a bot token from
@BotFather. Email/SMS need paid or credentialed services and weren't asked
for yet. Follows the same pattern as agents/*_agent.py: if the credentials
aren't set, calls no-op (logging what *would* have been sent) instead of
failing loudly, so the scheduled job never crashes just because Telegram
isn't configured.
"""

import os
import logging

import requests

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_telegram(text: str) -> bool:
    """Send a Markdown-formatted message. Returns True on success."""
    if not telegram_enabled():
        logger.warning(
            "[telegram] not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) "
            "— message not sent:\n%s", text,
        )
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=15)
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("[telegram] send failed")
        return False
