"""Volanie modelu, ktoré z CV a chatu vytiahne fakty o uchádzačovi.

Model tu nerozhoduje o skóre. Jeho úlohou je iba prečítať životopis a
prepis chatu a vyplniť `ExtractedProfile`. Výsledné číslo počíta
deterministicky `scoring.py`.

Používa sa štruktúrovaný výstup (`response_schema`), takže odpoveď je
vždy JSON v tvare `ExtractedProfile`. Ak volanie zlyhá alebo sa odpoveď
nedá overiť, vráti sa None a uchádzač ostane bez skóre. Nikdy sa odtiaľto
nevyhadzuje výnimka.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import ValidationError

from app.core.ai.client import EXTRACTION_TIMEOUT_SECONDS, get_client
from app.core.ai.prompts import (
    CHAT_CLOSE,
    CHAT_OPEN,
    CV_CLOSE,
    CV_OPEN,
    UNTRUSTED_NOTE,
    describe_position,
    wrap_untrusted,
)
from app.core.ai.schemas import ExtractedProfile
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_RULES = """\
Si personalista a hodnotíš uchádzača o konkrétnu pracovnú pozíciu.

Dostaneš údaje o pozícii, životopis uchádzača a prepis jeho chatu s asistentom.
Tvojou úlohou je vyplniť štruktúrované fakty o uchádzačovi. Nepočítaj žiadne
výsledné skóre okrem poľa overall_fit.

Pravidlá:
- Vychádzaj iba z toho, čo je v životopise alebo v chate. Nič si nedomýšľaj.
- Keď sa fakt nedá zistiť, nastav unknown a source na none. Unknown znamená
  „nedoložené", nie „nemá". Toto je dôležité, nehádaj.
- Do poľa evidence daj krátku doslovnú citáciu, ktorá fakt dokladá.
- Pole source hovorí, odkiaľ fakt pochádza: cv, chat, both alebo none.
- Pri rokoch praxe počítaj len prax relevantnú pre túto pozíciu.
- Pri vzdelaní a jazykoch posúď, či úroveň spĺňa požiadavku pozície. Rozhoduj
  vecne: napríklad výučný list v odbore spĺňa požiadavku stredoškolského
  vzdelania bez maturity.
- Ak pozícia danú požiadavku vôbec nemá, nastav meets_requirement na unknown.
- overall_fit je celkový odhad vhodnosti od 1 do 10. Zohľadni kvalitu praxe
  a doplňujúce pokyny firmy, nie iba splnené papiere.
- summary napíš po slovensky, jedna až dve vety.

{untrusted}
"""


def build_prompt(
    position: Any,
    requirements: Any,
    cv_text: str,
    chat_transcript: str,
) -> str:
    """Zlož používateľskú časť promptu z pozície, životopisu a prepisu chatu."""
    parts = ["Údaje o pozícii:\n" + describe_position(position, requirements)]

    custom = (getattr(position, "ai_bot_instructions", None) or "").strip()
    if custom:
        parts.append(
            "Doplňujúce pokyny od firmy, na čo si dať pri uchádzačovi pozor:\n" + custom
        )

    if cv_text.strip():
        parts.append("Životopis uchádzača:\n" + wrap_untrusted(cv_text, CV_OPEN, CV_CLOSE))
    else:
        parts.append(
            "Životopis: uchádzač ho nepriložil alebo sa z neho nedal prečítať text. "
            "Hodnoť len z chatu."
        )

    if chat_transcript.strip():
        parts.append(
            "Prepis chatu s asistentom:\n"
            + wrap_untrusted(chat_transcript, CHAT_OPEN, CHAT_CLOSE)
        )
    else:
        parts.append("Chat: uchádzač si nepísal s asistentom.")

    return "\n\n".join(parts)


def _to_profile(response: Any) -> ExtractedProfile | None:
    """Vytiahni `ExtractedProfile` z odpovede modelu, nech príde v akomkoľvek tvare."""
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, ExtractedProfile):
        return parsed
    if isinstance(parsed, dict):
        return ExtractedProfile.model_validate(parsed)

    text = getattr(response, "text", None)
    if text:
        return ExtractedProfile.model_validate_json(text)

    return None


async def extract_profile(
    position: Any,
    requirements: Any,
    cv_text: str,
    chat_transcript: str,
) -> ExtractedProfile | None:
    """Vráť fakty o uchádzačovi, alebo None ak sa ich nepodarilo získať."""
    client = get_client()
    if client is None:
        return None

    if not cv_text.strip() and not chat_transcript.strip():
        logger.info("Uchádzač nemá ani životopis, ani chat. Extrakcia sa preskakuje.")
        return None

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_RULES.format(untrusted=UNTRUSTED_NOTE),
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=ExtractedProfile,
        )

        async with asyncio.timeout(EXTRACTION_TIMEOUT_SECONDS):
            response = await client.aio.models.generate_content(
                model=settings.gemini_extraction_model,
                contents=build_prompt(position, requirements, cv_text, chat_transcript),
                config=config,
            )

        return _to_profile(response)

    except asyncio.TimeoutError:
        logger.warning("Extrakcia trvala dlhšie ako %s s", EXTRACTION_TIMEOUT_SECONDS)
    except (ValidationError, ValueError):
        logger.exception("Odpoveď modelu sa nedala prečítať ako ExtractedProfile")
    except Exception:  # noqa: BLE001
        logger.exception("Volanie Gemini pre extrakciu zlyhalo")

    return None
