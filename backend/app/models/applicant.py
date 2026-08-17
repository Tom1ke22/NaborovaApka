import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    cv_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    ai_score_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualification_answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    submitted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="applicants")
    position: Mapped["Position"] = relationship(back_populates="applicants")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="applicant")
