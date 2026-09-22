"""Deterministický výpočet skóre uchádzača (1–10) a jeho zdôvodnenia.

Tu sa nevolá žiadna AI. Vstupom sú požiadavky pozície (to, čo sekretárka
zaškrtla vo formulári) a fakty, ktoré model vytiahol z CV a chatu
(`ExtractedProfile`). Rovnaký vstup dá vždy rovnaké skóre, takže sa dá
obhájiť aj otestovať.

Ako sa skóre počíta
-------------------
1. Počíta sa len s požiadavkami, ktoré má pozícia zapnuté. Každá má váhu
   (`WEIGHTS`). Splnená požiadavka dá plné body, nedoložená polovicu
   (nedoložené neznamená nemá), výslovne nesplnená nula. Prax pod
   požadovanou hranicou dá pomerné body.
2. Pomer získaných a možných bodov tvorí 80 % skóre. Zvyšných 20 % je
   celkový odhad vhodnosti od modelu (`overall_fit`), aby sa dali zoradiť
   aj uchádzači, ktorí spĺňajú všetko rovnako.
3. Ak pozícia nemá žiadne požiadavky, skóre je priamo `overall_fit`.

Skóre slúži iba na zoradenie. Nikoho nevyraďuje.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.core.ai.schemas import Answer, ExtractedProfile, Source

# Váhy požiadaviek. Meniť tu, nie v kóde nižšie.
WEIGHTS: dict[str, float] = {
    "experience": 3,
    "education": 2,
    "hygiene_minimum": 2,
    "health_certificate": 2,
    "slovak_language": 1,
    "foreign_language": 1,
}

UNKNOWN_CREDIT = 0.5        # podiel bodov za nedoloženú požiadavku
REQUIREMENTS_SHARE = 0.8    # podiel požiadaviek na výslednom skóre
FIT_SHARE = 0.2             # podiel celkového odhadu modelu
MAX_FINDINGS_CHARS = 220    # orezanie poznámky k vlastným inštrukciám v zdôvodnení

LABELS: dict[str, str] = {
    "experience": "prax v odbore",
    "education": "vzdelanie",
    "hygiene_minimum": "hygienické minimum",
    "health_certificate": "zdravotný preukaz",
    "slovak_language": "slovenčina",
    "foreign_language": "cudzí jazyk",
}

SOURCE_LABELS: dict[Source, str] = {
    Source.cv: "CV",
    Source.chat: "chat",
    Source.both: "CV a chat",
    Source.none: "",
}


@dataclass(frozen=True)
class Requirements:
    """Požiadavky pozície odpojené od ORM, aby sa skórovanie dalo testovať bez DB."""

    hygiene_minimum_required: bool = False
    health_certificate_required: bool = False
    experience_required: bool = False
    experience_years: int | None = None
    education_level: str | None = None
    slovak_language_level: str | None = None
    foreign_language_level: str | None = None

    @classmethod
    def from_orm(cls, req: Any) -> "Requirements":
        """Vytvor z `PositionRequirements` (alebo z None, ak pozícia požiadavky nemá)."""
        if req is None:
            return cls()
        return cls(**{name: getattr(req, name) for name in cls.__dataclass_fields__})

    @property
    def any_active(self) -> bool:
        return (
            self.hygiene_minimum_required
            or self.health_certificate_required
            or self.experience_required
            or bool(self.education_level)
            or bool(self.slovak_language_level)
            or bool(self.foreign_language_level)
        )


@dataclass(frozen=True)
class CriterionResult:
    """Výsledok jednej požiadavky. Ukladá sa do JSONB, aby admin videl rozpis."""

    key: str
    label: str
    status: Answer
    weight: float
    earned: float
    detail: str      # ľudský popis, napr. "3 roky, požadované 2 roky"
    source: Source


@dataclass(frozen=True)
class ScoreResult:
    score: int
    reasoning: str
    criteria: list[CriterionResult]
    requirements_ratio: float | None   # None, ak pozícia nemá požiadavky
    overall_fit: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "reasoning": self.reasoning,
            "requirements_ratio": self.requirements_ratio,
            "overall_fit": self.overall_fit,
            "criteria": [
                {**asdict(c), "status": c.status.value, "source": c.source.value}
                for c in self.criteria
            ],
        }


# --------------------------------------------------------------------------- #
# Verejná funkcia
# --------------------------------------------------------------------------- #

def compute_score(requirements: Requirements, profile: ExtractedProfile) -> ScoreResult:
    """Porovnaj požiadavky pozície s profilom uchádzača a vráť skóre 1–10 so zdôvodnením."""
    criteria = _evaluate_criteria(requirements, profile)
    fit = _clamp(profile.overall_fit)

    if not criteria:
        score = fit
        ratio = None
    else:
        possible = sum(c.weight for c in criteria)
        earned = sum(c.earned for c in criteria)
        ratio = earned / possible if possible else 0.0
        fit_ratio = (fit - 1) / 9
        combined = REQUIREMENTS_SHARE * ratio + FIT_SHARE * fit_ratio
        score = _clamp(1 + round(9 * combined))

    reasoning = _build_reasoning(criteria, profile, has_requirements=bool(criteria))
    return ScoreResult(
        score=score,
        reasoning=reasoning,
        criteria=criteria,
        requirements_ratio=ratio,
        overall_fit=fit,
    )


# --------------------------------------------------------------------------- #
# Vyhodnotenie jednotlivých požiadaviek
# --------------------------------------------------------------------------- #

def _evaluate_criteria(req: Requirements, profile: ExtractedProfile) -> list[CriterionResult]:
    results: list[CriterionResult] = []

    if req.experience_required:
        results.append(_evaluate_experience(req, profile))

    if req.education_level:
        results.append(_evaluate_level("education", profile.education, req.education_level))

    if req.hygiene_minimum_required:
        results.append(_evaluate_binary("hygiene_minimum", profile.hygiene_minimum))

    if req.health_certificate_required:
        results.append(_evaluate_binary("health_certificate", profile.health_certificate))

    if req.slovak_language_level:
        results.append(_evaluate_level("slovak_language", profile.slovak_language, req.slovak_language_level))

    if req.foreign_language_level:
        results.append(_evaluate_level("foreign_language", profile.foreign_language, req.foreign_language_level))

    return results


def _evaluate_binary(key: str, fact) -> CriterionResult:
    weight = WEIGHTS[key]
    earned = weight * _credit(fact.value)
    return CriterionResult(
        key=key,
        label=LABELS[key],
        status=fact.value,
        weight=weight,
        earned=earned,
        detail="",
        source=fact.source,
    )


def _evaluate_level(key: str, fact, required_level: str) -> CriterionResult:
    weight = WEIGHTS[key]
    status = fact.meets_requirement
    earned = weight * _credit(status)
    if fact.level:
        detail = f"{fact.level}, požadované {required_level}"
    else:
        detail = f"požadované {required_level}"
    return CriterionResult(
        key=key,
        label=LABELS[key],
        status=status,
        weight=weight,
        earned=earned,
        detail=detail,
        source=fact.source,
    )


def _evaluate_experience(req: Requirements, profile: ExtractedProfile) -> CriterionResult:
    weight = WEIGHTS["experience"]
    exp = profile.experience
    years = exp.years
    required = req.experience_years or 0

    if years is None:
        status, earned = Answer.unknown, weight * UNKNOWN_CREDIT
        detail = f"požadované {_years(required)}" if required else ""
    elif required <= 0:
        # Sekretárka zaškrtla prax bez počtu rokov: stačí akákoľvek prax.
        status = Answer.yes if years > 0 else Answer.no
        earned = weight if years > 0 else 0.0
        detail = _years(years) if years > 0 else "bez praxe"
    elif years >= required:
        status, earned = Answer.yes, weight
        detail = f"{_years(years)}, požadované {_years(required)}"
    else:
        # Menej rokov než treba: pomerné body, ale status "nespĺňa".
        status, earned = Answer.no, weight * (years / required)
        detail = f"{_years(years)}, požadované {_years(required)}"

    return CriterionResult(
        key="experience",
        label=LABELS["experience"],
        status=status,
        weight=weight,
        earned=round(earned, 3),
        detail=detail,
        source=exp.source,
    )


def _credit(answer: Answer) -> float:
    if answer == Answer.yes:
        return 1.0
    if answer == Answer.unknown:
        return UNKNOWN_CREDIT
    return 0.0


# --------------------------------------------------------------------------- #
# Zdôvodnenie
# --------------------------------------------------------------------------- #

def _build_reasoning(
    criteria: list[CriterionResult],
    profile: ExtractedProfile,
    *,
    has_requirements: bool,
) -> str:
    parts: list[str] = []

    if has_requirements:
        met = [c for c in criteria if c.status == Answer.yes]
        unmet = [c for c in criteria if c.status == Answer.no]
        unknown = [c for c in criteria if c.status == Answer.unknown]
        if met:
            parts.append("Spĺňa: " + ", ".join(_describe(c) for c in met) + ".")
        if unmet:
            parts.append("Nespĺňa: " + ", ".join(_describe(c) for c in unmet) + ".")
        if unknown:
            parts.append("Nedoložené: " + ", ".join(_describe(c) for c in unknown) + ".")
    else:
        parts.append("Pozícia nemá zadané požiadavky, skóre vychádza z celkového odhadu vhodnosti.")
        if profile.summary:
            parts.append(_truncate(profile.summary))

    if profile.custom_instructions_findings:
        parts.append("K inštrukciám: " + _truncate(profile.custom_instructions_findings))

    return " ".join(parts)


def _describe(c: CriterionResult) -> str:
    text = c.label
    if c.detail:
        text += f" ({c.detail})"
    src = SOURCE_LABELS.get(c.source, "")
    if src and c.status != Answer.unknown:
        text += f" [{src}]"
    return text


def _truncate(text: str, limit: int = MAX_FINDINGS_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _years(n: float) -> str:
    """Slovenské skloňovanie: 1 rok, 2–4 roky, 5+ rokov, 2,5 roka."""
    if n != int(n):
        return f"{n:.1f}".replace(".", ",") + " roka"
    n = int(n)
    if n == 1:
        return "1 rok"
    if 2 <= n <= 4:
        return f"{n} roky"
    return f"{n} rokov"


def _clamp(n: int) -> int:
    return max(1, min(10, int(n)))
