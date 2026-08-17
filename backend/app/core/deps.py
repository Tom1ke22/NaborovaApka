import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

bearer_scheme = HTTPBearer()


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    payload = decode_token(credentials.credentials)
    if not payload or "company_id" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


def get_company_id(payload: dict = Depends(require_admin)) -> uuid.UUID:
    return uuid.UUID(payload["company_id"])
