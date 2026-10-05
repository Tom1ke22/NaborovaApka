import logging
import mimetypes
import os
import uuid
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ai.evaluate import effective_ai_status, evaluate_applicant
from app.core.config import settings
from app.core.deps import get_company_id
from app.core.storage import get_storage
from app.db.base import get_db, utcnow
from app.models.applicant import AiStatusEnum, Applicant
from app.models.chat import ChatMessage, ChatSession
from app.schemas.applicant import ApplicantDetail, ApplicantRow
from app.schemas.chat import ChatMsgOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/applicants", tags=["admin-applicants"])


async def _get_applicant(
    db: AsyncSession, applicant_id: uuid.UUID, company_id: uuid.UUID
) -> Applicant:
    applicant = await db.scalar(
        select(Applicant).where(
            Applicant.id == applicant_id,
            Applicant.company_id == company_id,
        )
    )
    if not applicant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Záujemca nenájdený")
    return applicant


async def _applications_per_email(
    db: AsyncSession, company_id: uuid.UUID, emails: set[str]
) -> dict[str, int]:
    """Koľko prihlášok má firma od každého e-mailu.

    Opakované prihlášky sa neodmietajú (človek sa môže hlásiť na viac pozícií
    alebo poslať opravené CV), len sa v admine označia. Odmietnutie by navyše
    prezradilo, či sa daný e-mail už niekde hlásil.
    """
    if not emails:
        return {}
    rows = await db.execute(
        select(Applicant.email, func.count(Applicant.id))
        .where(Applicant.company_id == company_id, Applicant.email.in_(emails))
        .group_by(Applicant.email)
    )
    return dict(rows.all())


CV_FILE_MISSING = (
    "Súbor životopisu sa v úložisku nenachádza (bol zmazaný alebo sa neuložil). "
    "Opakovanie nepomôže — požiadajte uchádzača o nové CV."
)


@router.get("", response_model=list[ApplicantRow])
async def list_applicants(
    position_id: uuid.UUID | None = None,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Záujemcovia firmy. S `position_id` len tí, ktorí sa hlásili na danú pozíciu."""
    query = select(Applicant).options(selectinload(Applicant.position)).where(
        Applicant.company_id == company_id
    )
    if position_id is not None:
        query = query.where(Applicant.position_id == position_id)

    result = await db.execute(query.order_by(Applicant.submitted_at.desc()))
    applicants = result.scalars().all()
    per_email = await _applications_per_email(db, company_id, {a.email for a in applicants})
    return [
        ApplicantRow(
            id=a.id,
            first_name=a.first_name,
            last_name=a.last_name,
            email=a.email,
            phone=a.phone,
            ai_score=a.ai_score,
            ai_status=effective_ai_status(a.ai_status, a.ai_status_changed_at),
            other_applications=per_email.get(a.email, 1) - 1,
            submitted_at=a.submitted_at,
            position_id=a.position_id,
            position_title=a.position.title,
        )
        for a in applicants
    ]


@router.get("/{applicant_id}", response_model=ApplicantDetail)
async def get_applicant(
    applicant_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Applicant).options(selectinload(Applicant.position)).where(
            Applicant.id == applicant_id,
            Applicant.company_id == company_id,
        )
    )
    applicant = result.scalar_one_or_none()
    if not applicant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Záujemca nenájdený")
    per_email = await _applications_per_email(db, company_id, {applicant.email})
    return ApplicantDetail(
        id=applicant.id,
        first_name=applicant.first_name,
        last_name=applicant.last_name,
        email=applicant.email,
        phone=applicant.phone,
        ai_score=applicant.ai_score,
        ai_status=effective_ai_status(applicant.ai_status, applicant.ai_status_changed_at),
        other_applications=per_email.get(applicant.email, 1) - 1,
        submitted_at=applicant.submitted_at,
        position_id=applicant.position_id,
        position_title=applicant.position.title,
        cv_storage_path=applicant.cv_storage_path,
        ai_score_reasoning=applicant.ai_score_reasoning,
        qualification_answers=applicant.qualification_answers,
    )


@router.post("/{applicant_id}/evaluate", status_code=status.HTTP_202_ACCEPTED)
async def reevaluate_applicant(
    applicant_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Spusti AI hodnotenie uchádzača znova (tlačidlo „Skúsiť znova").

    Slúži na zotavenie, keď hodnotenie po odoslaní prihlášky zlyhalo
    (napr. Gemini bolo krátko nedostupné) a uchádzač ostal bez skóre.
    Stav sa hneď prepne na pending, aby admin videl, že beží. Prepíše
    doterajšie skóre novým.
    """
    if not settings.ai_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI nie je nakonfigurovaná, hodnotenie sa nedá spustiť",
        )

    result = await db.execute(
        select(Applicant).where(
            Applicant.id == applicant_id,
            Applicant.company_id == company_id,
        )
    )
    applicant = result.scalar_one_or_none()
    if not applicant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Záujemca nenájdený")

    applicant.ai_status = AiStatusEnum.pending.value
    applicant.ai_status_changed_at = utcnow()
    await db.commit()

    background_tasks.add_task(evaluate_applicant, applicant_id)
    return {"status": "spustené"}


@router.get("/{applicant_id}/cv")
async def get_cv_url(
    applicant_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Applicant).where(
            Applicant.id == applicant_id,
            Applicant.company_id == company_id,
        )
    )
    applicant = result.scalar_one_or_none()
    if not applicant or not applicant.cv_storage_path:
        raise HTTPException(status_code=404, detail="CV nenájdené")
    # Overiť hneď tu: chýbajúci súbor sa opakovaním nikdy neopraví a admin
    # má dostať presnú hlášku, nie všeobecné „skúste to znova".
    if not await get_storage().exists(applicant.cv_storage_path):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=CV_FILE_MISSING)

    # Vždy náš autentifikovaný endpoint, nikdy podpísaný URL na úložisko.
    # Podpísaný URL je heslo samo o sebe: kto ho získa z logov, histórie
    # alebo preposlaného odkazu, stiahne CV bez prihlásenia.
    return {"url": f"/api/admin/applicants/{applicant_id}/cv/download"}


@router.get("/{applicant_id}/cv/download")
async def download_cv(
    applicant_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Applicant).where(
            Applicant.id == applicant_id,
            Applicant.company_id == company_id,
        )
    )
    applicant = result.scalar_one_or_none()
    if not applicant or not applicant.cv_storage_path:
        raise HTTPException(status_code=404, detail="CV nenájdené")

    # Funguje rovnako pre lokálny disk aj GCS: súbor ide cez backend, takže
    # o prístupe rozhoduje admin token, nie znalosť URL.
    data = await get_storage().load(applicant.cv_storage_path)
    if data is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=CV_FILE_MISSING)

    ext = os.path.splitext(applicant.cv_storage_path)[1]
    filename = f"cv_{applicant.last_name}_{applicant.first_name}{ext}"
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            # CV je osobný údaj: nesmie ostať v cache prehliadača ani proxy.
            "Cache-Control": "no-store",
        },
    )


@router.get("/{applicant_id}/chat", response_model=list[ChatMsgOut])
async def get_applicant_chat(
    applicant_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Applicant).where(
            Applicant.id == applicant_id,
            Applicant.company_id == company_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Záujemca nenájdený")

    msgs_result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.applicant_id == applicant_id,
            ChatMessage.company_id == company_id,
        )
        .order_by(ChatMessage.created_at)
    )
    return msgs_result.scalars().all()


@router.delete("/{applicant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_applicant(
    applicant_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Natrvalo zmaž uchádzača (GDPR — právo na výmaz).

    Maže prihlášku, prepis chatu aj súbor CV. Nedá sa vrátiť.

    Poradie: najprv DB, potom súbor. Keď zlyhá zmazanie súboru, osobné údaje
    v DB sú už preč a súbor bez vlastníka odprace `scripts/cleanup_orphan_cvs.py`.
    Opačné poradie by pri chybe DB nechalo uchádzača s CV, ktoré už neexistuje.
    """
    applicant = await _get_applicant(db, applicant_id, company_id)
    cv_path = applicant.cv_storage_path

    await db.execute(
        delete(ChatMessage).where(
            ChatMessage.applicant_id == applicant_id,
            ChatMessage.company_id == company_id,
        )
    )
    await db.execute(delete(ChatSession).where(ChatSession.applicant_id == applicant_id))
    await db.delete(applicant)
    await db.commit()

    if cv_path:
        try:
            await get_storage().delete(cv_path)
        except Exception:  # noqa: BLE001
            logger.warning(
                "CV zmazaného uchádzača %s sa nepodarilo odstrániť, odprace ho úklid",
                applicant_id, exc_info=True,
            )
