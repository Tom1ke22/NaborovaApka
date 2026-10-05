import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicantRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str
    ai_score: int | None
    # pending | done | failed | skipped. „Visiaci" pending sa tu už ukáže
    # ako failed (pozri effective_ai_status).
    ai_status: str
    # Koľko ďalších prihlášok má firma od toho istého e-mailu. Opakované
    # prihlášky sa neodmietajú, len označia.
    other_applications: int = 0
    submitted_at: datetime
    position_id: uuid.UUID
    position_title: str


class ApplicantDetail(ApplicantRow):
    cv_storage_path: str | None
    ai_score_reasoning: str | None
    qualification_answers: dict
