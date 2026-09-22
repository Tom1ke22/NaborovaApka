"""Zdieľaný klient pre Gemini API.

Klient sa vytvára lenivo a len raz. Ak nie je nastavený kľúč alebo je
`AI_ENABLED=false`, vráti sa None a volajúci modul sa prepne na záložné
správanie. Nikdy sa odtiaľto nevyhadzuje výnimka, aby chýbajúca
konfigurácia nezhodila štart aplikácie.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Koľko sekúnd čakáme na odpoveď modelu, kým to vzdáme.
CHAT_TIMEOUT_SECONDS = 45
EXTRACTION_TIMEOUT_SECONDS = 90

_client: Any | None = None
_initialized = False


def get_client() -> Any | None:
    """Vráť Gemini klienta, alebo None ak AI nie je nakonfigurovaná alebo sa nedá vytvoriť."""
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True

    if not settings.ai_available:
        logger.info(
            "AI je vypnutá (AI_ENABLED=%s, kľúč nastavený=%s). "
            "Chatbot pobeží v záložnom režime a uchádzači ostanú bez skóre.",
            settings.ai_enabled,
            bool(settings.gemini_api_key),
        )
        _client = None
        return None

    try:
        from google import genai

        _client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Gemini klient pripravený (chat=%s)", settings.gemini_chat_model)
    except Exception:  # noqa: BLE001
        logger.exception("Gemini klienta sa nepodarilo vytvoriť, AI sa vypína")
        _client = None

    return _client


def reset_client() -> None:
    """Zahoď uloženého klienta. Slúži testom, ktoré menia nastavenia."""
    global _client, _initialized
    _client = None
    _initialized = False
