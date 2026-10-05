import uuid
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.ai.scoring import MAX_CUSTOM_REQUIREMENTS
from app.models.position import ContractTypeEnum, PositionStatusEnum, SalaryPeriodEnum

CUSTOM_REQUIREMENT_MAX_CHARS = 200

# --------------------------------------------------------------------------- #
# Hranice vstupov
#
# Každé pole má strop podľa stĺpca v DB. Bez neho prejde validáciou hodnota,
# ktorú Postgres odmietne, a admin dostane 500 namiesto 422 s vysvetlením.
# Texty sa orezávajú o medzery, aby „   " neprešlo ako vyplnený názov.
# --------------------------------------------------------------------------- #

# Numeric(10, 2) v DB: najviac 8 číslic pred desatinnou čiarkou.
MAX_SALARY = Decimal("99999999.99")
MAX_OPEN_SLOTS = 1000
MAX_VACATION_DAYS = 365
MAX_EXPERIENCE_YEARS = 60
# Dlhé texty idú aj do promptu pre model, preto majú strop aj keď je stĺpec Text.
MAX_LONG_TEXT = 10_000
MAX_AI_TEXT = 4_000
# Dátum nástupu: nie pred rokom 2000 (preklep v roku) a najviac 5 rokov dopredu.
EARLIEST_START_DATE = date(2000, 1, 1)
START_DATE_MAX_YEARS_AHEAD = 5


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _strip_or_none(value: object) -> object:
    """Prázdny text po orezaní = nevyplnené pole (NULL), nie prázdny reťazec."""
    value = _strip(value)
    return value or None


def _two_decimals(value: Decimal | None) -> Decimal | None:
    """Zaokrúhli na centy hneď pri vstupe.

    DB stĺpec má 2 desatinné miesta a 1234.567 by zaokrúhlil sám. API by však
    vrátilo pôvodné číslo z requestu a admin by videl inú sumu, než je uložená.
    """
    if value is None:
        return None
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _start_date_in_range(value: date | None) -> date | None:
    if value is None:
        return None
    latest = date.today() + timedelta(days=365 * START_DATE_MAX_YEARS_AHEAD)
    if not EARLIEST_START_DATE <= value <= latest:
        raise ValueError(
            f"Dátum nástupu musí byť medzi {EARLIEST_START_DATE.isoformat()} "
            f"a {latest.isoformat()}"
        )
    return value


def RequiredText(max_length: int):  # noqa: N802 — správa sa ako typ
    return Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=max_length)]


def OptionalText(max_length: int):  # noqa: N802
    # Limit patrí na vnútorný str — na `str | None` by sa pokúsil merať aj None.
    return Annotated[
        Annotated[str, Field(max_length=max_length)] | None, BeforeValidator(_strip_or_none)
    ]


Salary = Annotated[
    Decimal | None, Field(ge=0, le=MAX_SALARY), AfterValidator(_two_decimals)
]
StartDate = Annotated[date | None, AfterValidator(_start_date_in_range)]


class CustomRequirementIn(BaseModel):
    """Jedna vlastná požiadavka, ktorú si firma dopísala vo formulári."""

    label: str = Field(min_length=1, max_length=CUSTOM_REQUIREMENT_MAX_CHARS)
    # Odškrtnutá požiadavka ostáva uložená, len sa nehodnotí. Riadky spred
    # zavedenia príznaku ho nemajú, preto je predvolene zapnutá.
    required: bool = True

    @field_validator("label")
    @classmethod
    def _tidy(cls, v: str) -> str:
        # Popis ide do promptu pre model, preto z neho vyhadzujeme nové riadky
        # a viacnásobné medzery.
        label = " ".join(v.split())
        if not label:
            raise ValueError("Popis požiadavky nemôže byť prázdny")
        return label


class PositionRequirementsIn(BaseModel):
    hygiene_minimum_required: bool = False
    health_certificate_required: bool = False
    experience_required: bool = False
    experience_years: int | None = Field(default=None, ge=0, le=MAX_EXPERIENCE_YEARS)
    education_level: OptionalText(100) = None
    slovak_language_level: OptionalText(50) = None
    foreign_language_level: OptionalText(100) = None
    custom_requirements: list[CustomRequirementIn] = Field(
        default_factory=list, max_length=MAX_CUSTOM_REQUIREMENTS
    )

    @field_validator("custom_requirements", mode="before")
    @classmethod
    def _never_null(cls, v: object) -> object:
        # Riadky založené pred migráciou 0004 môžu mať v stĺpci NULL.
        return v if v is not None else []


class PositionRequirementsOut(PositionRequirementsIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    position_id: uuid.UUID


class PositionCreate(BaseModel):
    title: RequiredText(255)
    work_area: RequiredText(255)
    open_slots: int = Field(default=1, ge=1, le=MAX_OPEN_SLOTS)
    start_date: StartDate = None
    description: OptionalText(MAX_LONG_TEXT) = None
    additional_info: OptionalText(MAX_LONG_TEXT) = None
    location: RequiredText(255)
    contract_type: ContractTypeEnum
    working_hours: OptionalText(100) = None
    shift_type: OptionalText(100) = None
    break_info: OptionalText(100) = None
    work_regime: OptionalText(100) = None
    salary_amount: Salary = None
    salary_period: SalaryPeriodEnum = SalaryPeriodEnum.monthly
    vacation_days: int | None = Field(default=None, ge=0, le=MAX_VACATION_DAYS)
    meal_allowance: OptionalText(255) = None
    contact_person: OptionalText(255) = None
    ai_bot_instructions: OptionalText(MAX_AI_TEXT) = None
    ai_evaluation_notes: OptionalText(MAX_AI_TEXT) = None
    requirements: PositionRequirementsIn = PositionRequirementsIn()


class PositionUpdate(BaseModel):
    """Čiastočná úprava. Rovnaké hranice ako pri založení."""

    title: RequiredText(255) | None = None
    work_area: RequiredText(255) | None = None
    open_slots: int | None = Field(default=None, ge=1, le=MAX_OPEN_SLOTS)
    start_date: StartDate = None
    description: OptionalText(MAX_LONG_TEXT) = None
    additional_info: OptionalText(MAX_LONG_TEXT) = None
    location: RequiredText(255) | None = None
    contract_type: ContractTypeEnum | None = None
    working_hours: OptionalText(100) = None
    shift_type: OptionalText(100) = None
    break_info: OptionalText(100) = None
    work_regime: OptionalText(100) = None
    salary_amount: Salary = None
    salary_period: SalaryPeriodEnum | None = None
    vacation_days: int | None = Field(default=None, ge=0, le=MAX_VACATION_DAYS)
    meal_allowance: OptionalText(255) = None
    contact_person: OptionalText(255) = None
    status: PositionStatusEnum | None = None
    ai_bot_instructions: OptionalText(MAX_AI_TEXT) = None
    ai_evaluation_notes: OptionalText(MAX_AI_TEXT) = None
    requirements: PositionRequirementsIn | None = None

    # Stĺpce NOT NULL. Vynechať ich smie, poslať null nie — inak 500 z DB.
    _NOT_NULLABLE = (
        "title", "work_area", "location", "open_slots",
        "contract_type", "salary_period", "status",
    )

    @model_validator(mode="after")
    def _no_null_for_required(self) -> "PositionUpdate":
        for name in self._NOT_NULLABLE:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"Pole {name} nemôže byť prázdne")
        return self


class PositionOut(BaseModel):
    """Pozícia tak, ako ju smie vidieť uchádzač.

    Zámerne bez `ai_bot_instructions` a `ai_evaluation_notes` — je to interné
    nastavenie náboru a chodí odtiaľto aj verejný endpoint detailu pozície.
    """

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
    created_at: datetime
    updated_at: datetime
    requirements: PositionRequirementsOut | None = None


class AdminPositionOut(PositionOut):
    """Pozícia pre admina. Navyše nesie interné nastavenie AI.

    Zámerne je oddelená od `PositionOut`, ktorý chodí aj na verejné endpointy.
    """

    ai_bot_instructions: str | None = None
    ai_evaluation_notes: str | None = None


class AdminPositionListItem(AdminPositionOut):
    """Riadok admin zoznamu. Počet záujemcov je interný údaj."""

    applicant_count: int = 0


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
