import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.evaluate import evaluate_applicant
from app.core.config import settings
from app.core.deps import get_company_id
from app.core.storage import get_storage
from app.db.base import get_db
from app.models.applicant import Applicant
from app.models.chat import ChatMessage
from app.schemas.applicant import ApplicantDetail, ApplicantRow
from app.schemas.chat import ChatMsgOut

router = APIRouter(prefix="/admin/applicants", tags=["admin-applicants"])


@router.get("", response_model=list[ApplicantRow])
async def list_applicants(
    position_id: uuid.UUID | None = None,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Záujemcovia firmy. S `position_id` len tí, ktorí sa hlásili na danú pozíciu."""
    query = select(Applicant).where(Applicant.company_id == company_id)
    if position_id is not None:
        query = query.where(Applicant.position_id == position_id)

    result = await db.execute(query.order_by(Applicant.submitted_at.desc()))
    return result.scalars().all()


@router.get("/{applicant_id}", response_model=ApplicantDetail)
async def get_applicant(
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
    if not applicant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Záujemca nenájdený")
    return applicant


@router.post("/{applicant_id}/evaluate", status_code=status.HTTP_202_ACCEPTED)
async def reevaluate_applicant(
    applicant_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    company_id: uuid.UUID = Depends(get_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Spusti AI hodnotenie uchádzača znova.

    Slúži na zotavenie, keď hodnotenie po odoslaní prihlášky zlyhalo
    (napr. Gemini bolo krátko nedostupné) a uchádzač ostal bez skóre.
    Prepíše doterajšie skóre novým.
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
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Záujemca nenájdený")

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

    storage = get_storage()
    signed_url = await storage.generate_signed_url(applicant.cv_storage_path)
    url = signed_url or f"/api/admin/applicants/{applicant_id}/cv/download"
    return {"url": url}


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
    if not os.path.exists(applicant.cv_storage_path):
        raise HTTPException(status_code=404, detail="Súbor nenájdený na disku")

    ext = os.path.splitext(applicant.cv_storage_path)[1]
    filename = f"cv_{applicant.last_name}_{applicant.first_name}{ext}"
    return FileResponse(applicant.cv_storage_path, filename=filename)


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
