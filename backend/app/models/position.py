import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, Enum, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ContractTypeEnum(str, enum.Enum):
    dohoda_o_pracovnej_cinnosti = "dohoda_o_pracovnej_cinnosti"
    kratsi_pracovny_cas = "kratsi_pracovny_cas"
    neuricity_cas = "neuricity_cas"
    uricity_cas = "uricity_cas"
    dohoda_o_brigadnickej_praci_studenta = "dohoda_o_brigadnickej_praci_studenta"


class SalaryPeriodEnum(str, enum.Enum):
    monthly = "monthly"
    hourly = "hourly"


class PositionStatusEnum(str, enum.Enum):
    active = "active"
    archived = "archived"


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    work_area: Mapped[str] = mapped_column(String(255), nullable=False)
    open_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_type: Mapped[ContractTypeEnum] = mapped_column(Enum(ContractTypeEnum), nullable=False)
    working_hours: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shift_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    break_info: Mapped[str | None] = mapped_column(String(100), nullable=True)
    work_regime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salary_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    salary_period: Mapped[SalaryPeriodEnum] = mapped_column(
        Enum(SalaryPeriodEnum), nullable=False, default=SalaryPeriodEnum.monthly
    )
    vacation_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meal_allowance: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PositionStatusEnum] = mapped_column(
        Enum(PositionStatusEnum), nullable=False, default=PositionStatusEnum.active
    )
    ai_bot_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="positions")
    requirements: Mapped["PositionRequirements"] = relationship(
        back_populates="position", uselist=False, cascade="all, delete-orphan"
    )
    applicants: Mapped[list["Applicant"]] = relationship(back_populates="position")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="position")


class PositionRequirements(Base):
    __tablename__ = "position_requirements"
    __table_args__ = (UniqueConstraint("position_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False
    )
    hygiene_minimum_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    health_certificate_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    experience_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slovak_language_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    foreign_language_level: Mapped[str | None] = mapped_column(String(100), nullable=True)

    position: Mapped["Position"] = relationship(back_populates="requirements")
