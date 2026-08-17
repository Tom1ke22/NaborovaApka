import uuid
from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    positions: Mapped[list["Position"]] = relationship(back_populates="company")
    applicants: Mapped[list["Applicant"]] = relationship(back_populates="company")
    admin_users: Mapped[list["AdminUser"]] = relationship(back_populates="company")
    events: Mapped[list["Event"]] = relationship(back_populates="company")
