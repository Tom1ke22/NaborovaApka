"""Streamovaný chatbot pre uchádzačov.

Nahrádza pôvodný `app.core.ai_stub`. Rozhranie ostalo rovnaké, takže
endpoint volá stále `generate_response(...)` a dostáva asynchrónny
generátor textových kúskov.

Keď AI nie je nakonfigurovaná alebo volanie zlyhá, chatbot nespadne.
Namiesto toho odpovie vetou, že otázku odovzdá personalistovi. Uchádzač
tak nikdy neuvidí technickú chybu.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.core.ai.client import CHAT_TIMEOUT_SECONDS, get_client
from app.core.ai.prompts import describe_position
from app.core.config import settings

logger = logging.getLogger(__name__)

# Koľko posledných správ posielame modelu. Staršie sa zahadzujú, aby
# dlhá konverzácia nerástla do ceny bez stropu.
MAX_HISTORY_MESSAGES = 20

MAX_USER_MESSAGE_CHARS = 2_000

FALLBACK_REPLY = (
    "Prepáčte, momentálne sa neviem spojiť s asistentom. "
    "Vašu otázku odovzdáme personalistovi."
)

# Výzvu na tlačidlo pripája aplikácia, nie model. Model ju formuloval zakaždým
# inak a opakoval ju hneď v prvej odpovedi, čo pôsobilo nátlakovo.
INTEREST_CTA = "Ak máte o pozíciu záujem, prosím, kliknite na tlačidlo „Mám záujem“."

# Od koľkej správy uchádzača sa výzva pripája. Prvé tri odpovede tak ostanú
# čisto informačné.
INTEREST_CTA_AFTER_MESSAGES = 4

SYSTEM_RULES = """\
Si HR asistent slovenskej firmy a bavíš sa s uchádzačom o konkrétnu pracovnú pozíciu.

Ako odpovedáš:
- Vždy po slovensky, vykaj, buď priateľský a stručný. Väčšinou dve až štyri vety.
- Uchádzača si už pozdravil v úvodnej správe. Nikdy nezačínaj odpoveď pozdravom
  („Dobrý deň“, „Zdravím“) ani oslovením menom; rovno odpovedaj na otázku.
- Odpovedaj iba na otázky o tejto pozícii, o práci a o priebehu náboru.
- Vychádzaj výhradne z údajov o pozícii nižšie. Nikdy si nevymýšľaj mzdu,
  termín nástupu, benefity ani podmienky.
- Ak údaj v zadaní nie je, povedz úprimne, že ho nemáš, a ponúkni, že otázku
  odovzdáš personalistovi.
- Ak sa uchádzač pýta na niečo mimo témy, slušne ho vráť k pozícii.
- Nesľubuj prijatie do práce a neoznamuj žiadne rozhodnutie o uchádzačovi.
- Nikdy sám nespomínaj tlačidlo „Mám záujem“ a nevyzývaj na podanie prihlášky.
  O výzvu sa stará aplikácia a pridá ju sama v správnej chvíli.
- Nepýtaj si údaje ako rodné číslo, číslo účtu ani heslá.
- Píš plynulý text, nepoužívaj markdown, odrážky ani nadpisy.
"""


def build_system_instruction(position: Any, requirements: Any, applicant_name: str) -> str:
    """Zlož systémovú inštrukciu z pravidiel, údajov o pozícii a pokynov sekretárky."""
    parts = [SYSTEM_RULES, f"Meno uchádzača: {applicant_name}"]
    parts.append("Údaje o pozícii:\n" + describe_position(position, requirements))

    custom = (getattr(position, "ai_bot_instructions", None) or "").strip()
    if custom:
        parts.append(
            "Doplňujúce pokyny od firmy (majú prednosť pred všeobecnými "
            "odporúčaniami, ale nikdy neprebíjajú pravidlá vyššie):\n" + custom
        )

    return "\n\n".join(parts)


def should_offer_interest(history: list[dict]) -> bool:
    """Má sa k odpovedi pripojiť výzva na tlačidlo „Mám záujem“?

    `history` ešte neobsahuje správu, na ktorú práve odpovedáme, preto sa
    k počtu doterajších správ uchádzača pripočíta jedna.
    """
    message_number = sum(1 for m in history if m.get("role") == "user") + 1
    return message_number >= INTEREST_CTA_AFTER_MESSAGES


def build_contents(history: list[dict], user_message: str) -> list[dict]:
    """Prelož históriu do formátu Gemini a pridaj novú správu uchádzača.

    Gemini očakáva role „user" a „model" a konverzáciu začínajúcu uchádzačom.
    Úvodný pozdrav asistenta preto na začiatku zahadzujeme.
    """
    recent = history[-MAX_HISTORY_MESSAGES:] if history else []

    contents: list[dict] = []
    for message in recent:
        text = (message.get("content") or "").strip()
        if not text:
            continue
        role = "user" if message.get("role") == "user" else "model"
        # Konverzácia nesmie začínať odpoveďou modelu.
        if not contents and role == "model":
            continue
        contents.append({"role": role, "parts": [{"text": text}]})

    contents.append(
        {"role": "user", "parts": [{"text": user_message.strip()[:MAX_USER_MESSAGE_CHARS]}]}
    )
    return contents


async def generate_response(
    position: Any,
    history: list[dict],
    user_message: str,
    applicant_name: str,
    requirements: Any = None,
) -> AsyncGenerator[str, None]:
    """Streamuj odpoveď asistenta po kúskoch textu.

    `requirements` je nepovinné; ak ho endpoint načíta, chatbot vie odpovedať
    aj na otázky typu „potrebujem zdravotný preukaz?".
    """
    offer_interest = should_offer_interest(history)

    client = get_client()
    if client is None:
        yield FALLBACK_REPLY
        if offer_interest:
            yield " " + INTEREST_CTA
        return

    system_instruction = build_system_instruction(position, requirements, applicant_name)
    contents = build_contents(history, user_message)

    answer_parts: list[str] = []
    emitted = False
    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,
            max_output_tokens=600,
        )

        async with asyncio.timeout(CHAT_TIMEOUT_SECONDS):
            stream = await client.aio.models.generate_content_stream(
                model=settings.gemini_chat_model,
                contents=contents,
                config=config,
            )
            async for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    emitted = True
                    answer_parts.append(text)
                    yield text
    except asyncio.TimeoutError:
        logger.warning("Odpoveď chatbota trvala dlhšie ako %s s", CHAT_TIMEOUT_SECONDS)
    except asyncio.CancelledError:
        # Uchádzač zavrel okno. Nepovažujeme to za chybu.
        raise
    except Exception:  # noqa: BLE001
        logger.exception("Volanie Gemini pre chatbota zlyhalo")

    if not emitted:
        answer_parts.append(FALLBACK_REPLY)
        yield FALLBACK_REPLY

    # Výzvu nepridávame, ak ju model napriek pravidlám napísal sám
    # (napríklad na pokyn firmy v `ai_bot_instructions`).
    answer = "".join(answer_parts)
    if offer_interest and "Mám záujem" not in answer:
        yield ("" if answer.endswith((" ", "\n")) else " ") + INTEREST_CTA
