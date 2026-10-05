import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class MessageRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class ChatSession(Base):
    """Kto smie chat používať a pripojiť k prihláške.

    `id` je verejný identifikátor (to isté ako `ChatMessage.applicant_session_id`).
    Sám o sebe nič neoprávňuje — môže uniknúť z histórie prehliadača, logov
    alebo cez Referer. Oprávnenie dáva až tajný claim token, ktorý server vráti
    len pri `chat/start` a ukladá si z neho iba hash. Bez neho sa do chatu nedá
    písať ani ho pripojiť k prihláške.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False
    )
    claim_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Prihláška, ku ktorej sa chat pripojil. Nastaví sa raz a už sa nemení.
    applicant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_id", "applicant_session_id"),
        Index("ix_chat_messages_created_at", "created_at"),
        # Prepis chatu v detaile uchádzača a pri AI hodnotení.
        Index("ix_chat_messages_applicant_id", "applicant_id"),
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    applicant: Mapped["Applicant | None"] = relationship(back_populates="chat_messages")
    position: Mapped["Position"] = relationship(back_populates="chat_messages")
