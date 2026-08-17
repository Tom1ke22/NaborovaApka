import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_company_id", "company_id"),
        Index("ix_events_created_at", "created_at"),
        Index("ix_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="events")
