"""Štruktúra faktov, ktoré AI vytiahne zo životopisu a z chatu.

`ExtractedProfile` slúži zároveň ako JSON schéma pre štruktúrovaný výstup
modelu (Gemini `response_schema`). Preto platí:
- žiadne zložité typy, iba str / float / int / bool / enum / vnorené modely,
- žiadne obmedzenia typu ge/le v schéme (nie všetky podporuje strict mód),
  rozsah overujeme validátorom v Pythone,
- každé pole má popis, ktorý model vidí a riadi sa ním.

Deterministické veci (porovnanie rokov praxe, váhy, výsledné číslo) rieši
`scoring.py`. Model rozhoduje len tam, kde je porovnanie nejasné
(napr. či „výučný list v odbore kuchár" spĺňa „stredoškolské vzdelanie").
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Answer(str, Enum):
    yes = "yes"          # doložené / spĺňa
    no = "no"            # výslovne nespĺňa alebo nemá
    unknown = "unknown"  # z CV ani chatu sa to nedá zistiť


class Source(str, Enum):
    cv = "cv"
    chat = "chat"
    both = "both"
    none = "none"


class Fact(BaseModel):
    """Binárny fakt, napr. či má uchádzač zdravotný preukaz."""

    value: Answer = Field(
        default=Answer.unknown,
        description="yes = doložené alebo potvrdené, no = výslovne nemá, unknown = nezistené",
    )
    source: Source = Field(
        default=Source.none,
        description=(
            "Odkiaľ fakt pochádza: cv ak je napísaný v životopise, chat ak to uchádzač "
            "iba povedal v chate, both ak je na oboch miestach, none ak je unknown. "
            "Tvrdenie z chatu NIKDY neoznačuj ako cv"
        ),
    )
    evidence: str | None = Field(
        default=None,
        description=(
            "Doslovná citácia (jedna veta) z toho zdroja, ktorý si uviedol v source; "
            "null ak nezistené. Pri source=cv musí byť citácia zo životopisu"
        ),
    )


class ExperienceFact(BaseModel):
    """Prax relevantná pre danú pozíciu."""

    years: float | None = Field(
        default=None,
        description="Počet rokov praxe RELEVANTNEJ pre túto pozíciu; null ak sa nedá zistiť",
    )
    summary: str | None = Field(
        default=None,
        description="Jedna veta: kde a ako dlho pracoval na relevantných pozíciách",
    )
    source: Source = Field(
        default=Source.none,
        description=(
            "cv ak sú roky praxe vyčítateľné zo životopisu, chat ak ich uchádzač iba "
            "povedal, both ak oboje, none ak nezistené"
        ),
    )
    evidence: str | None = Field(
        default=None, description="Doslovná citácia dokladajúca prax z uvedeného zdroja"
    )


class LevelFact(BaseModel):
    """Fakt s úrovňou (vzdelanie, slovenčina, cudzí jazyk) a posúdením, či spĺňa požiadavku."""

    level: str | None = Field(
        default=None,
        description="Úroveň tak, ako ju uchádzač uvádza, napr. 'stredoškolské s maturitou' alebo 'angličtina B2'",
    )
    meets_requirement: Answer = Field(
        default=Answer.unknown,
        description=(
            "Či úroveň spĺňa požiadavku pozície: yes / no / unknown. "
            "unknown ak pozícia túto požiadavku nemá alebo sa úroveň nedá zistiť"
        ),
    )
    source: Source = Field(
        default=Source.none,
        description=(
            "cv ak je úroveň uvedená v životopise, chat ak ju uchádzač iba povedal, "
            "both ak oboje, none ak nezistené"
        ),
    )
    evidence: str | None = Field(
        default=None, description="Doslovná citácia dokladajúca úroveň z uvedeného zdroja"
    )


class CustomFact(BaseModel):
    """Posúdenie jednej vlastnej požiadavky, ktorú si firma dopísala k pozícii."""

    key: str = Field(
        default="",
        description=(
            "Kľúč požiadavky presne tak, ako je uvedený v zadaní, napríklad custom_1. "
            "Nevymýšľaj vlastné kľúče"
        ),
    )
    value: Answer = Field(
        default=Answer.unknown,
        description="yes = uchádzač požiadavku spĺňa, no = výslovne nespĺňa, unknown = nedoložené",
    )
    source: Source = Field(
        default=Source.none,
        description=(
            "cv ak je to v životopise, chat ak to uchádzač iba povedal, both ak oboje, "
            "none ak je unknown"
        ),
    )
    evidence: str | None = Field(
        default=None,
        description=(
            "Doslovná citácia z uvedeného zdroja, ktorá posúdenie dokladá; "
            "null ak nezistené"
        ),
    )


class ExtractedProfile(BaseModel):
    """Všetko, čo model zistil o uchádzačovi. Ukladá sa do applicants.qualification_answers."""

    hygiene_minimum: Fact = Field(
        default_factory=Fact, description="Má osvedčenie o hygienickom minime (odborná spôsobilosť)?"
    )
    health_certificate: Fact = Field(
        default_factory=Fact, description="Má zdravotný preukaz pre prácu s potravinami?"
    )
    experience: ExperienceFact = Field(default_factory=ExperienceFact)
    education: LevelFact = Field(default_factory=LevelFact, description="Najvyššie dosiahnuté vzdelanie")
    slovak_language: LevelFact = Field(default_factory=LevelFact, description="Úroveň slovenčiny")
    foreign_language: LevelFact = Field(
        default_factory=LevelFact,
        description="Cudzie jazyky a úrovne, napr. 'angličtina B2, nemčina základy'",
    )
    custom_requirements: list[CustomFact] = Field(
        default_factory=list,
        description=(
            "Posúdenie vlastných požiadaviek pozície — jeden záznam ku každému kľúču "
            "custom_N zo zadania, v rovnakom poradí. Prázdny zoznam, ak pozícia "
            "žiadne vlastné požiadavky nemá"
        ),
    )
    custom_instructions_findings: str | None = Field(
        default=None,
        description=(
            "Čo sa zistilo k interným poznámkam firmy k hodnoteniu (ak pozícia nejaké má), "
            "jedna až dve vety; null ak poznámky nie sú alebo sa nič nezistilo"
        ),
    )
    overall_fit: int = Field(
        default=5,
        description=(
            "Celkový odhad vhodnosti uchádzača pre pozíciu na škále 1 (nevhodný) až 10 (ideálny), "
            "berie do úvahy kvalitu praxe a interné poznámky firmy k hodnoteniu"
        ),
    )
    summary: str | None = Field(
        default=None, description="Jedna až dve vety zhrnutia uchádzača po slovensky"
    )

    @field_validator("overall_fit", mode="before")
    @classmethod
    def _clamp_fit(cls, v: object) -> int:
        try:
            n = int(round(float(v)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 5
        return max(1, min(10, n))
