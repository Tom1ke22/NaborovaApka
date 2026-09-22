"""Vyhodnotenie uchádzača po odoslaní prihlášky.

Toto je jediné miesto, ktoré spája všetky časti dokopy:

    CV (PDF/DOCX) ─┐
                   ├─► extraction (Gemini) ─► ExtractedProfile ─► scoring ─► ai_score
    prepis chatu ──┘

Spúšťa sa na pozadí cez `BackgroundTasks`, takže uchádzač nečaká na model.
Beží s vlastnou databázovou reláciou, lebo tá z requestu je v tom čase už
zatvorená.

Funkcia nikdy nevyhodí výnimku. Keď čokoľvek zlyhá, uchádzač ostane bez
skóre a do logu sa zapíše dôvod. Prihláška sa nikdy nestratí.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.ai import cv_text as cv_text_module
from app.core.ai.extraction import extract_profile
from app.core.ai.prompts import format_chat_transcript
from app.core.ai.scoring import Requirements, compute_score
from app.core.config import settings
from app.core.storage import get_storage
from app.db.base import AsyncSessionLocal
from app.models.applicant import Applicant
from app.models.chat import ChatMessage
from app.models.position import Position

logger = logging.getLogger(__name__)


async def _read_cv_text(cv_storage_path: str | None) -> str:
    """Stiahni CV z úložiska a vytiahni z neho text. Prázdny reťazec pri akomkoľvek probléme."""
    if not cv_storage_path:
        return ""

    try:
        data = await get_storage().load(cv_storage_path)
    except Exception:  # noqa: BLE001
        logger.warning("CV sa nepodarilo načítať: %s", cv_storage_path, exc_info=True)
        return ""

    if not data:
        return ""

    try:
        return cv_text_module.extract_text(data, cv_storage_path)
    except cv_text_module.UnsupportedCvFormat:
        logger.warning("Nepodporovaný formát CV: %s", cv_storage_path)
    except Exception:  # noqa: BLE001
        logger.warning("Text z CV sa nepodarilo získať: %s", cv_storage_path, exc_info=True)

    return ""


async def evaluate_applicant(applicant_id: uuid.UUID) -> None:
    """Vyhodnoť uchádzača a ulož skóre. Chyby sa iba zalogujú."""
    if not settings.ai_available:
        logger.info("AI je vypnutá, uchádzač %s ostáva bez skóre", applicant_id)
        return

    try:
        async with AsyncSessionLocal() as db:
            applicant = await db.scalar(
                select(Applicant).where(Applicant.id == applicant_id)
            )
            if applicant is None:
                logger.warning("Uchádzač %s sa nenašiel, hodnotenie sa preskakuje", applicant_id)
                return

            position = await db.scalar(
                select(Position)
                .where(Position.id == applicant.position_id)
                .options(selectinload(Position.requirements))
            )
            if position is None:
                logger.warning("Pozícia uchádzača %s sa nenašla", applicant_id)
                return

            messages = (
                await db.scalars(
                    select(ChatMessage)
                    .where(ChatMessage.applicant_id == applicant_id)
                    .order_by(ChatMessage.created_at)
                )
            ).all()

            history = [{"role": m.role.value, "content": m.content} for m in messages]
            transcript = format_chat_transcript(history)
            cv_text = await _read_cv_text(applicant.cv_storage_path)

            profile = await extract_profile(
                position=position,
                requirements=position.requirements,
                cv_text=cv_text,
                chat_transcript=transcript,
            )
            if profile is None:
                logger.warning(
                    "Fakty o uchádzačovi %s sa nepodarilo získať, ostáva bez skóre",
                    applicant_id,
                )
                return

            result = compute_score(
                Requirements.from_orm(position.requirements), profile
            )

            applicant.ai_score = result.score
            applicant.ai_score_reasoning = result.reasoning
            applicant.qualification_answers = {
                "profile": profile.model_dump(mode="json"),
                "score": result.to_dict(),
                "sources": {
                    "cv_text_chars": len(cv_text),
                    "chat_messages": len(history),
                    "model": settings.gemini_extraction_model,
                },
            }

            await db.commit()
            logger.info("Uchádzač %s vyhodnotený, skóre %s/10", applicant_id, result.score)

    except Exception:  # noqa: BLE001
        logger.exception("Hodnotenie uchádzača %s zlyhalo", applicant_id)
