"""Prihlásenie, odhlásenie a zmena hesla.

Token je JWT bez stavu na serveri, takže sám sa odvolať nedá. Riešime to
generáciou tokenov: `admin_users.token_version` ide do tokenu ako claim „tv"
a `require_admin` ho pri každom requeste porovnáva s DB. Odhlásenie aj zmena
hesla toto číslo zvýšia, čím okamžite padnú všetky vydané tokeny na všetkých
zariadeniach.

Prihlasovanie je chránené dvakrát: rate limitom na IP (brzdí hádanie z jednej
adresy) a lockoutom na účet v DB (brzdí hádanie z mnohých adries).
"""

import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.models.admin import AdminUser
from app.models.company import Company
from app.schemas.auth import LoginRequest, PasswordChangeRequest, TokenResponse

router = APIRouter()

# Po koľkých neúspešných pokusoch sa účet zamkne a na ako dlho.
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

def _bad_credentials() -> HTTPException:
    """Jediná odpoveď pre neexistujúci email aj pre zlé heslo.

    Status aj telo musia byť rovnaké, inak sa cez endpoint dá zisťovať, ktoré
    emaily v systéme sú. Vraciame novú instanciu, nie zdieľanú konštantu —
    vyhodená výnimka si na seba viaže traceback a kontext, a zdieľaný objekt by
    tie reťazce hromadil medzi requestami.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nesprávny email alebo heslo",
    )


@lru_cache(maxsize=1)
def _throwaway_hash() -> str:
    """Hash náhodného hesla, proti ktorému overujeme neexistujúci účet.

    Samotná rovnaká odpoveď nestačí: bcrypt trvá okolo 150 ms, takže keby sme
    pri neznámom emaile preskočili overenie hesla, odpoveď by prišla
    niekoľkonásobne rýchlejšie a účty by sa dali enumerovať meraním času.
    Heslo nikto nepozná, takže overenie proti nemu vždy zlyhá.
    """
    return hash_password(secrets.token_urlsafe(32))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(
        select(AdminUser)
        .join(Company, Company.id == AdminUser.company_id)
        .where(AdminUser.email == body.email, Company.is_active.is_(True))
    )

    now = datetime.now(timezone.utc)

    if user is None:
        # Lockoutu sa tu nedotýkame — neexistujúci email nemá riadok, ktorý by
        # sa dal zamknúť, a nič sa pre neho nikde neeviduje. Overenie proti
        # zahodenému hashu je tu len preto, aby odpoveď trvala približne
        # rovnako dlho ako pri existujúcom účte so zlým heslom.
        verify_password(body.password, _throwaway_hash())
        raise _bad_credentials()

    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Účet je po viacerých neúspešných prihláseniach dočasne zamknutý. "
                f"Skúste to znova o {LOCKOUT_MINUTES} minút."
            ),
        )

    if not verify_password(body.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        await db.commit()
        raise _bad_credentials()

    # Úspešné prihlásenie maže históriu neúspešných pokusov aj zámok.
    if user.failed_login_count or user.locked_until:
        user.failed_login_count = 0
        user.locked_until = None
        await db.commit()

    token = create_access_token(
        user_id=str(user.id),
        company_id=str(user.company_id),
        role=user.role,
        token_version=user.token_version,
    )
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Odhlás admina na serveri — na všetkých zariadeniach.

    Zvýšenie `token_version` zneplatní aj token, ktorým sa tento request
    autentifikoval. Zmazanie tokenu v prehliadači je už len kozmetika.
    """
    user.token_version += 1
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password", response_model=TokenResponse)
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    body: PasswordChangeRequest,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Zmeň heslo a odrež všetky existujúce session.

    Vraciame nový token, aby admin na tomto zariadení ostal prihlásený. Všetky
    staré tokeny — vrátane toho, ktorým prišiel tento request — padnú.
    """
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Súčasné heslo nie je správne"
        )

    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    user.failed_login_count = 0
    user.locked_until = None
    await db.commit()

    token = create_access_token(
        user_id=str(user.id),
        company_id=str(user.company_id),
        role=user.role,
        token_version=user.token_version,
    )
    return TokenResponse(access_token=token)
