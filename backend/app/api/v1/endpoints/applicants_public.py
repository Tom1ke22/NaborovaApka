import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.storage import get_storage
from app.db.base import get_db
from app.models.applicant import Applicant
from app.models.chat import ChatMessage
from app.models.company import Company
from app.models.position import Position, PositionStatusEnum

router = APIRouter(tags=["apply"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_CV_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


async def _get_active_company(slug: str, db: AsyncSession) -> Company:
    result = await db.execute(
        select(Company).where(Company.slug == slug, Company.is_active == True)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firma nenájdená")
    return company


@router.post("/{slug}/applicants", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def submit_application(
    request: Request,
    slug: str,
    position_id: uuid.UUID = Form(...),
    session_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    cv: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_active_company(slug, db)

    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.company_id == company.id,
            Position.status == PositionStatusEnum.active,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pozícia nenájdená")

    applicant_id = uuid.uuid4()
    cv_path = None

    if cv and cv.filename:
        ext = os.path.splitext(cv.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Povolené sú iba PDF a DOCX súbory")
        content = await cv.read()
        if len(content) > MAX_CV_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="CV súbor je príliš veľký. Maximum je 10 MB.")
        storage = get_storage()
        cv_path = await storage.save(content, f"{applicant_id}{ext}")

    db.add(Applicant(
        id=applicant_id,
        company_id=company.id,
        position_id=position_id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        cv_storage_path=cv_path,
    ))

    if session_id:
        await db.execute(
            update(ChatMessage)
            .where(
                ChatMessage.applicant_session_id == session_id,
                ChatMessage.company_id == company.id,
            )
            .values(applicant_id=applicant_id)
        )

    await db.commit()
    return {"id": str(applicant_id)}
