import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatStartIn(BaseModel):
    position_id: uuid.UUID
    applicant_name: str


class ChatStartOut(BaseModel):
    session_id: str
    greeting: str


class ChatStreamIn(BaseModel):
    session_id: str
    message: str


class ChatMsgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime
