"""Závislosti pre admin API.

Token sám nestačí. Dekódovaný JWT hovorí len to, čo platilo pri prihlásení,
a platí osem hodín. Preto sa pri každom requeste pozrieme do databázy a
overíme, že:

- admin účet ešte existuje (zmazaný admin nesmie mať prístup do expirácie),
- jeho `token_version` sa zhoduje s claimom „tv" v tokene (odhlásenie a zmena
  hesla toto číslo zvýšia, takže staré tokeny okamžite padajú),
- firma je aktívna (deaktivovaná firma nesmie čítať osobné údaje uchádzačov).

`company_id` sa berie z načítaného riadku admina, nikdy z URL. Hodnota v tokene
sa navyše musí zhodovať s DB — keby sa tokeny niekedy vydávali s iným
company_id, request neprejde.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import get_db
from app.models.admin import AdminUser
from app.models.company import Company

bearer_scheme = HTTPBearer()


def _unauthorized() -> HTTPException:
    """Jediná odpoveď pre akýkoľvek neplatný token.

    Volajúci nemá vedieť, čo presne bolo zlé — či token expiroval, či admin
    zmizol, alebo či bola firma deaktivovaná. Nová instancia pri každom
    vyhodení, aby sa na zdieľanom objekte nehromadil traceback a kontext.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Vráť prihláseného admina z DB, alebo 401."""
    payload = decode_token(credentials.credentials)
    if not payload or "company_id" not in payload or "sub" not in payload:
        raise _unauthorized()

    try:
        user_id = uuid.UUID(str(payload["sub"]))
        company_id = uuid.UUID(str(payload["company_id"]))
    except (ValueError, AttributeError, TypeError):
        raise _unauthorized() from None

    # Token bez claimu „tv" (vydaný pred zavedením generácií) neprejde. Verzia
    # v DB začína na 0, takže akákoľvek náhrada by naopak mohla sadnúť.
    token_version = payload.get("tv")
    if not isinstance(token_version, int) or isinstance(token_version, bool):
        raise _unauthorized()

    user = await db.scalar(
        select(AdminUser)
        .join(Company, Company.id == AdminUser.company_id)
        .where(
            AdminUser.id == user_id,
            AdminUser.company_id == company_id,
            AdminUser.token_version == token_version,
            Company.is_active.is_(True),
        )
    )
    if user is None:
        raise _unauthorized()

    return user


def get_company_id(user: AdminUser = Depends(require_admin)) -> uuid.UUID:
    return user.company_id
