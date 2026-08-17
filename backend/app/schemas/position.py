import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.position import ContractTypeEnum, PositionStatusEnum, SalaryPeriodEnum


class PositionRequirementsIn(BaseModel):
    hygiene_minimum_required: bool = False
    health_certificate_required: bool = False
    experience_required: bool = False
    experience_years: int | None = None
    education_level: str | None = None
    slovak_language_level: str | None = None
    foreign_language_level: str | None = None


class PositionRequirementsOut(PositionRequirementsIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    position_id: uuid.UUID


class PositionCreate(BaseModel):
    title: str
    work_area: str
    open_slots: int = 1
    start_date: date | None = None
    description: str | None = None
    additional_info: str | None = None
    location: str
    contract_type: ContractTypeEnum
    working_hours: str | None = None
    shift_type: str | None = None
    break_info: str | None = None
    work_regime: str | None = None
    salary_amount: Decimal | None = None
    salary_period: SalaryPeriodEnum = SalaryPeriodEnum.monthly
    vacation_days: int | None = None
    meal_allowance: str | None = None
    contact_person: str | None = None
    ai_bot_instructions: str | None = None
    requirements: PositionRequirementsIn = PositionRequirementsIn()


class PositionUpdate(BaseModel):
    title: str | None = None
    work_area: str | None = None
    open_slots: int | None = None
    start_date: date | None = None
    description: str | None = None
    additional_info: str | None = None
    location: str | None = None
    contract_type: ContractTypeEnum | None = None
    working_hours: str | None = None
    shift_type: str | None = None
    break_info: str | None = None
    work_regime: str | None = None
    salary_amount: Decimal | None = None
    salary_period: SalaryPeriodEnum | None = None
    vacation_days: int | None = None
    meal_allowance: str | None = None
    contact_person: str | None = None
    status: PositionStatusEnum | None = None
    ai_bot_instructions: str | None = None
    requirements: PositionRequirementsIn | None = None


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    work_area: str
    open_slots: int
    start_date: date | None
    description: str | None
    additional_info: str | None
    location: str
    contract_type: ContractTypeEnum
    working_hours: str | None
    shift_type: str | None
    break_info: str | None
    work_regime: str | None
    salary_amount: Decimal | None
    salary_period: SalaryPeriodEnum
    vacation_days: int | None
    meal_allowance: str | None
    contact_person: str | None
    status: PositionStatusEnum
    ai_bot_instructions: str | None
    created_at: datetime
    updated_at: datetime
    requirements: PositionRequirementsOut | None = None


class PositionListItem(BaseModel):
    """Skrátený výstup pre verejný zoznam pozícií (karta)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    work_area: str
    location: str
    contract_type: ContractTypeEnum
    salary_amount: Decimal | None
    salary_period: SalaryPeriodEnum
    open_slots: int
    start_date: date | None
