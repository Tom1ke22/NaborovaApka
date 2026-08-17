from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_applicants,
    admin_positions,
    applicants_public,
    auth,
    chat,
    positions,
)

router = APIRouter()

# Admin routery musia byť registrované PRED /{slug}/ routami
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(admin_positions.router)   # prefix="/admin/positions"
router.include_router(admin_applicants.router)  # prefix="/admin/applicants"

# Verejné routery s /{slug}/ prefixom
router.include_router(positions.router)          # /{slug}/positions
router.include_router(chat.router)               # /{slug}/chat/...
router.include_router(applicants_public.router)  # /{slug}/applicants
