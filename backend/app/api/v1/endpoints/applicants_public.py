import logging
import os
import re
import uuid

from email_validator import EmailNotValidError, validate_email

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.evaluate import evaluate_applicant
from app.core.config import settings
from app.core.cv_validation import detect_cv_type
from app.core.limiter import limiter
from app.core.security import hash_claim_token
from app.core.storage import get_storage
from app.db.base import get_db
from app.models.applicant import AiStatusEnum, Applicant
from app.models.chat import ChatMessage, ChatSession
from app.models.company import Company
from app.models.position import Position, PositionStatusEnum

logger = logging.getLogger(__name__)

router = APIRouter(tags=["apply"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_CV_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Stropy podľa stĺpcov v `applicants`. Bez nich dlhšia hodnota prejde až do DB
# a uchádzač dostane 500 namiesto zrozumiteľnej chyby.
MAX_NAME_CHARS = 100
MAX_PHONE_CHARS = 30
MAX_EMAIL_CHARS = 255

# Riadiace znaky (CR, LF, TAB, NUL…). V mene ani telefóne nemajú čo robiť a
# CRLF by sa dostal do exportov, e-mailových hlavičiek a logov.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_PHONE_CHARS = re.compile(r"^[0-9+\- ()/]+$")  # len medzera, nie \s — ten by pustil CR/LF


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _clean_name(value: str, label: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise _invalid(f"{label} je povinné")
    if len(value) > MAX_NAME_CHARS:
        raise _invalid(f"{label} môže mať najviac {MAX_NAME_CHARS} znakov")
    if _CONTROL_CHARS.search(value):
        raise _invalid(f"{label} obsahuje nepovolené znaky")
    return value


def _clean_phone(value: str) -> str:
    value = value.strip()
    digits = sum(ch.isdigit() for ch in value)
    if len(value) > MAX_PHONE_CHARS or not _PHONE_CHARS.match(value) or not 9 <= digits <= 15:
        raise _invalid("Zadajte platné telefónne číslo (napr. +421 912 345 678)")
    return value


def _clean_email(value: str) -> str:
    """Overený e-mail v malých písmenách.

    Malé písmená kvôli dohľadaniu opakovaných prihlášok (Jan@x.sk = jan@x.sk)
    a aby na to stačil obyčajný index na (company_id, email).
    """
    value = value.strip()
    if len(value) > MAX_EMAIL_CHARS:
        raise _invalid("E-mail je príliš dlhý")
    try:
        normalized = validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError:
        raise _invalid("Zadajte platný e-mail (napr. jan@gmail.com)") from None
    return normalized.lower()


async def _get_active_company(slug: str, db: AsyncSession) -> Company:
    result = await db.execute(
        select(Company).where(Company.slug == slug, Company.is_active == True)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firma nenájdená")
    return company


async def _claim_chat(
    db: AsyncSession,
    *,
    session_id: str,
    claim_token: str,
    company_id: uuid.UUID,
    position_id: uuid.UUID,
    applicant_id: uuid.UUID,
) -> None:
    """Pripoj chat k prihláške, ale len jeho vlastníkovi a len raz.

    `session_id` sám nestačí. Uniká (história prehliadača, logy, Referer) a kto
    ho pozná, nesmie si cudzí rozhovor pripojiť k vlastnej prihláške — admin by
    ho videl pod útočníkovým menom a AI by hodnotila cudzie odpovede. Vlastníka
    preukazuje claim token z `chat/start`.

    Väzba sa zapisuje jedným podmieneným UPDATE. Dve súbežné prihlášky s tým
    istým tokenom tak nemôžu chat získať obe, vyhrá prvá.
    Keď token nesedí, prihláška ostane bez chatu a chyba sa nevracia. Uchádzač
    nemá čo opraviť a útočník sa nedozvie, či session existuje.
    """
    claimed = await db.execute(
        update(ChatSession)
        .where(
            ChatSession.id == session_id,
            ChatSession.company_id == company_id,
            ChatSession.position_id == position_id,
            ChatSession.claim_token_hash == hash_claim_token(claim_token),
            ChatSession.applicant_id.is_(None),
        )
        .values(applicant_id=applicant_id)
    )
    if claimed.rowcount != 1:
        return

    await db.execute(
        update(ChatMessage)
        .where(
            ChatMessage.applicant_session_id == session_id,
            ChatMessage.company_id == company_id,
            ChatMessage.applicant_id.is_(None),
        )
        .values(applicant_id=applicant_id)
    )


async def _delete_quietly(cv_path: str) -> None:
    try:
        await get_storage().delete(cv_path)
    except Exception:  # noqa: BLE001 — úklid nesmie prekryť pôvodnú chybu
        logger.warning("CV po neúspešnej prihláške sa nepodarilo zmazať: %s", cv_path)


@router.post("/{slug}/applicants", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def submit_application(
    request: Request,
    slug: str,
    background_tasks: BackgroundTasks,
    position_id: uuid.UUID = Form(...),
    # Oba nepovinné: prihláška vznikne aj bez chatu. Chat sa k nej pripojí len
    # s platným claim tokenom (pozri `_claim_chat`).
    session_id: str = Form("", max_length=100),
    claim_token: str = Form("", max_length=200),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    cv: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    first_name = _clean_name(first_name, "Meno")
    last_name = _clean_name(last_name, "Priezvisko")
    phone = _clean_phone(phone)
    email = _clean_email(email)

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
        # Prípona sa dá premenovať, obsah nie. Súbor, ktorý nie je PDF/DOCX,
        # by si inak admin stiahol a otvoril.
        if detect_cv_type(content) != ext:
            raise HTTPException(
                status_code=400,
                detail="Súbor nie je platné PDF ani DOCX. Nahrajte prosím životopis znova.",
            )
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
        ai_status=(
            AiStatusEnum.pending.value if settings.ai_available else AiStatusEnum.skipped.value
        ),
    ))

    # Applicant musí byť v DB skôr, než naň ukáže cudzí kľúč z chat_sessions.
    await db.flush()

    if session_id and claim_token:
        await _claim_chat(
            db,
            session_id=session_id,
            claim_token=claim_token,
            company_id=company.id,
            position_id=position_id,
            applicant_id=applicant_id,
        )

    try:
        await db.commit()
    except Exception:
        # Prihláška sa neuložila, CV by ostalo na disku bez vlastníka.
        if cv_path:
            await _delete_quietly(cv_path)
        raise

    # AI hodnotenie beží až po odoslaní odpovede, aby uchádzač nečakal na model.
    # Keď zlyhá, prihláška ostane uložená, uchádzač dostane ai_status=failed
    # a admin ho môže dať vyhodnotiť znova.
    if settings.ai_available:
        background_tasks.add_task(evaluate_applicant, applicant_id)

    return {"id": str(applicant_id)}
