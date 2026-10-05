import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def new_claim_token() -> str:
    """Tajný token, ktorým uchádzač preukazuje, že chat je jeho.

    256 bitov náhody, takže stačí obyčajný SHA-256 hash, bcrypt by tu len
    zdržiaval každú správu v chate.
    """
    return secrets.token_urlsafe(32)


def hash_claim_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_claim_token(token: str, token_hash: str) -> bool:
    return bool(token) and hmac.compare_digest(hash_claim_token(token), token_hash)


def create_access_token(user_id: str, company_id: str, role: str, token_version: int) -> str:
    """Vydaj token pre admina.

    Claim „tv" je generácia tokenov (`admin_users.token_version`). Pri každom
    requeste sa porovnáva s hodnotou v DB, takže zvýšením čísla v DB sa všetky
    staré tokeny okamžite zneplatnia (odhlásenie, zmena hesla).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "role": role,
        "tv": token_version,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return {}
