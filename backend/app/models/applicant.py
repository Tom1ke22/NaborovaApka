import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class AiStatusEnum(str, enum.Enum):
    """Stav AI hodnotenia uchádzača.

    Bez neho admin nerozlíši „ešte beží" od „zlyhalo" — oboje je len prázdne
    skóre. Ukladá sa ako text, nie ako PG enum, aby pridanie stavu nevyžadovalo
    ALTER TYPE.
    """

    pending = "pending"   # čaká na model alebo práve beží
    done = "done"         # skóre je uložené
    failed = "failed"     # model zlyhal / vypršal čas — dá sa skúsiť znova
    skipped = "skipped"   # AI je vypnutá, hodnotenie sa nespúšťalo


class Applicant(Base):
    __tablename__ = "applicants"
    __table_args__ = (
        # Zoznam záujemcov v admine: firma, zoradené od najnovších.
        Index("ix_applicants_company_submitted", "company_id", "submitted_at"),
        # Filter zoznamu na pozíciu a počty záujemcov na pozíciách.
        Index("ix_applicants_position_id", "position_id"),
        # Dohľadanie opakovaných prihlášok toho istého človeka vo firme.
        Index("ix_applicants_company_email", "company_id", "email"),
    )

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
    ai_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AiStatusEnum.pending.value,
        server_default=AiStatusEnum.pending.value,
    )
    # Kedy sa stav naposledy zmenil. Podľa toho sa pozná hodnotenie, ktoré
    # „visí" v pending, lebo proces počas behu zomrel (pozri effective_ai_status).
    ai_status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    qualification_answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    company: Mapped["Company"] = relationship(back_populates="applicants")
    position: Mapped["Position"] = relationship(back_populates="applicants")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="applicant")
