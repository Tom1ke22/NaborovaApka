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
    submitted_at: datetime
    position_id: uuid.UUID


class ApplicantDetail(ApplicantRow):
    cv_storage_path: str | None
    ai_score_reasoning: str | None
    qualification_answers: dict
