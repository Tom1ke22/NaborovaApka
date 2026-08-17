import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MessageRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_id", "applicant_session_id"),
        Index("ix_chat_messages_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    applicant_session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    applicant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=True
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False
    )
    role: Mapped[MessageRoleEnum] = mapped_column(Enum(MessageRoleEnum), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    applicant: Mapped["Applicant | None"] = relationship(back_populates="chat_messages")
    position: Mapped["Position"] = relationship(back_populates="chat_messages")
