"""Deterministický výpočet skóre uchádzača (1–10) a jeho zdôvodnenia.

Tu sa nevolá žiadna AI. Vstupom sú požiadavky pozície (to, čo sekretárka
zaškrtla vo formulári) a fakty, ktoré model vytiahol z CV a chatu
(`ExtractedProfile`). Rovnaký vstup dá vždy rovnaké skóre, takže sa dá
obhájiť aj otestovať.

Ako sa skóre počíta
-------------------
1. Počíta sa len s požiadavkami, ktoré má pozícia zapnuté. Každá má váhu
   (`WEIGHTS`) a koeficient podľa toho, ako dobre je splnenie podložené
   (`CREDIT`). Prax pod požadovanou hranicou dá pomerné body.
2. Pomer získaných a možných bodov tvorí 80 % skóre. Zvyšných 20 % je
   celkový odhad vhodnosti od modelu (`overall_fit`), aby sa dali zoradiť
   aj uchádzači, ktorí spĺňajú všetko rovnako.
3. Ak pozícia nemá žiadne požiadavky, skóre je priamo `overall_fit`.

Prečo nestačí áno/nie/neviem
----------------------------
Model vracia `Answer` (yes/no/unknown), ale „mám hygienické minimum" napísané
v chate nie je to isté ako osvedčenie vypísané v životopise. Prvé je tvrdenie
uchádzača, druhé je doklad. Keby sa oboje rátalo rovnako, stačilo by si
v chate povedať čokoľvek a skóre vyletí — a náborár by pri tom videl zelený
fajk, akoby to bolo overené.

Preto sa k odpovedi modelu pridáva `Verdict`, ktorý berie do úvahy aj zdroj
a citáciu. Plné body dostane len fakt doložený v životopise.

Skóre slúži iba na zoradenie. Nikoho nevyraďuje.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
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

CUSTOM_WEIGHT = 2.0         # váha jednej vlastnej požiadavky
MAX_CUSTOM_REQUIREMENTS = 10  # koľko vlastných požiadaviek pustíme do promptu
REQUIREMENTS_SHARE = 0.8    # podiel požiadaviek na výslednom skóre
FIT_SHARE = 0.2             # podiel celkového odhadu modelu
MAX_FINDINGS_CHARS = 220    # orezanie poznámky k vlastným inštrukciám v zdôvodnení


class Verdict(str, Enum):
    """Ako je splnenie požiadavky podložené.

    Na rozdiel od `Answer` (čo povedal model) sem vstupuje aj zdroj faktu a to,
    či k nemu model dal citáciu. Práve toto rozlíšenie vidí náborár v UI a
    práve podľa toho sa prideľujú body.
    """

    documented = "documented"      # doložené v životopise, s citáciou
    claimed = "claimed"            # uchádzač to tvrdí v chate, neoverené
    undocumented = "undocumented"  # nedoložené — nevieme, či má alebo nemá
    unmet = "unmet"                # výslovne nespĺňa


# Podiel bodov podľa toho, ako je splnenie podložené.
#
# `claimed` je zámerne nad `undocumented`: ten, kto povedal „mám to", je na tom
# lepšie než ten, kto nepovedal nič — ale horšie než ten, kto to má v CV.
# `undocumented` ostáva na polovici, lebo nedoložené neznamená nemá.
CREDIT: dict[Verdict, float] = {
    Verdict.documented: 1.0,
    Verdict.claimed: 0.7,
    Verdict.undocumented: 0.5,
    Verdict.unmet: 0.0,
}

# Spätne kompatibilné aliasy. `UNKNOWN_CREDIT` používa aj zdôvodnenie v testoch.
UNKNOWN_CREDIT = CREDIT[Verdict.undocumented]
CLAIMED_CREDIT = CREDIT[Verdict.claimed]

# Zdroje, ktoré považujeme za doklad. `both` znamená, že fakt je aj v CV.
CV_SOURCES = (Source.cv, Source.both)

# Má sa pre „doložené" vyžadovať aj citácia zo životopisu?
#
# Zapnuté: fakt bez citácie spadne na `claimed`. Dôvod je praktický — UI pod
# zeleným fajkom vypisuje práve tú citáciu, takže bez nej by náborár videl
# „doložené" a nemal by čo overiť. Prompt citáciu pri source=cv vyžaduje.
#
# Keby model citácie vynechával a doložené fakty tým padali do „tvrdí",
# prepni na False — rozlíšenie CV vs. chat funguje aj bez toho.
REQUIRE_EVIDENCE_FOR_CV = True

VERDICT_LABELS: dict[Verdict, str] = {
    Verdict.documented: "Doložené v životopise",
    Verdict.claimed: "Tvrdí v chate, neoverené",
    Verdict.unmet: "Nespĺňa",
    Verdict.undocumented: "Nedoložené",
}

LABELS: dict[str, str] = {
    "experience": "prax v odbore",
    "education": "vzdelanie",
    "hygiene_minimum": "hygienické minimum",
    "health_certificate": "zdravotný preukaz",
    "slovak_language": "slovenčina",
    "foreign_language": "cudzí jazyk",
}


def custom_requirement_labels(raw: Any) -> list[str]:
    """Znormalizuj vlastné požiadavky na zoznam popisov.

    Znesie oba tvary, ktoré po systéme chodia: JSON z databázy
    (`[{"label": "vodičský preukaz B"}, …]`) aj hotový zoznam textov
    z dataclassy `Requirements`. Prázdne a odškrtnuté položky vypadnú.
    """
    if not raw:
        return []

    labels: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            # Odškrtnutú požiadavku firma nechce hodnotiť, ale chce si ju
            # nechať vo formulári — do promptu ani do skóre nesmie.
            if item.get("required") is False:
                continue
            label = item.get("label")
        else:
            label = item
        if isinstance(label, str) and label.strip():
            labels.append(" ".join(label.split()))
    return labels[:MAX_CUSTOM_REQUIREMENTS]


def custom_key(index: int) -> str:
    """Kľúč vlastnej požiadavky. Musí sedieť medzi promptom a skórovaním."""
    return f"custom_{index + 1}"


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
    # Popisy vlastných požiadaviek v poradí, v akom ich firma zadala.
    custom_requirements: tuple[str, ...] = ()

    @classmethod
    def from_orm(cls, req: Any) -> "Requirements":
        """Vytvor z `PositionRequirements` (alebo z None, ak pozícia požiadavky nemá)."""
        if req is None:
            return cls()
        values = {
            name: getattr(req, name)
            for name in cls.__dataclass_fields__
            if name != "custom_requirements"
        }
        values["custom_requirements"] = tuple(
            custom_requirement_labels(getattr(req, "custom_requirements", None))
        )
        return cls(**values)

    @property
    def any_active(self) -> bool:
        return (
            self.hygiene_minimum_required
            or self.health_certificate_required
            or self.experience_required
            or bool(self.education_level)
            or bool(self.slovak_language_level)
            or bool(self.foreign_language_level)
            or bool(self.custom_requirements)
        )


@dataclass(frozen=True)
class CriterionResult:
    """Výsledok jednej požiadavky. Ukladá sa do JSONB, aby admin videl rozpis."""

    key: str
    label: str
    # `status` je odpoveď modelu (áno/nie/neviem), `verdict` je to, ako sme ju
    # po zohľadnení zdroja vyhodnotili my. Body aj UI idú podľa `verdict`;
    # `status` ostáva, aby sa dalo dohľadať, čo model vlastne tvrdil.
    status: Answer
    verdict: Verdict
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
                {
                    **asdict(c),
                    "status": c.status.value,
                    "verdict": c.verdict.value,
                    "source": c.source.value,
                }
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

    results.extend(_evaluate_custom(req, profile))

    return results


def _evaluate_custom(req: Requirements, profile: ExtractedProfile) -> list[CriterionResult]:
    """Vlastné požiadavky firmy. Model k nim vracia záznam podľa kľúča `custom_N`."""
    facts = {fact.key: fact for fact in profile.custom_requirements}

    results: list[CriterionResult] = []
    for index, label in enumerate(req.custom_requirements):
        key = custom_key(index)
        fact = facts.get(key)
        # Keď model na požiadavku neodpovedal, berieme to ako nedoložené —
        # rovnako ako keby napísal unknown. Mlčanie nesmie uchádzačovi uškodiť.
        answer = fact.value if fact else Answer.unknown
        source = fact.source if fact else Source.none
        evidence = fact.evidence if fact else None
        verdict = _verdict(answer, source, evidence)
        results.append(
            CriterionResult(
                key=key,
                label=label,
                status=answer,
                verdict=verdict,
                weight=CUSTOM_WEIGHT,
                earned=round(CUSTOM_WEIGHT * _credit(verdict), 3),
                detail="",
                source=source,
            )
        )
    return results


def _evaluate_binary(key: str, fact) -> CriterionResult:
    weight = WEIGHTS[key]
    verdict = _verdict(fact.value, fact.source, fact.evidence)
    return CriterionResult(
        key=key,
        label=LABELS[key],
        status=fact.value,
        verdict=verdict,
        weight=weight,
        earned=round(weight * _credit(verdict), 3),
        detail="",
        source=fact.source,
    )


def _evaluate_level(key: str, fact, required_level: str) -> CriterionResult:
    weight = WEIGHTS[key]
    status = fact.meets_requirement
    verdict = _verdict(status, fact.source, fact.evidence)
    if fact.level:
        detail = f"{fact.level}, požadované {required_level}"
    else:
        detail = f"požadované {required_level}"
    return CriterionResult(
        key=key,
        label=LABELS[key],
        status=status,
        verdict=verdict,
        weight=weight,
        earned=round(weight * _credit(verdict), 3),
        detail=detail,
        source=fact.source,
    )


def _evaluate_experience(req: Requirements, profile: ExtractedProfile) -> CriterionResult:
    weight = WEIGHTS["experience"]
    exp = profile.experience
    years = exp.years
    required = req.experience_years or 0

    if years is None:
        status, verdict = Answer.unknown, Verdict.undocumented
        earned = weight * _credit(verdict)
        detail = f"požadované {_years(required)}" if required else ""
    elif required <= 0:
        # Sekretárka zaškrtla prax bez počtu rokov: stačí akákoľvek prax.
        status = Answer.yes if years > 0 else Answer.no
        verdict = (
            _verdict(Answer.yes, exp.source, exp.evidence) if years > 0 else Verdict.unmet
        )
        earned = weight * _credit(verdict)
        detail = _years(years) if years > 0 else "bez praxe"
    elif years >= required:
        status = Answer.yes
        verdict = _verdict(Answer.yes, exp.source, exp.evidence)
        earned = weight * _credit(verdict)
        detail = f"{_years(years)}, požadované {_years(required)}"
    else:
        # Menej rokov než treba: pomerné body, ale verdikt „nespĺňa". Roky,
        # ktoré uchádzač iba povedal v chate, krátime tým istým koeficientom
        # ako hociktoré iné neoverené tvrdenie — inak by sa dalo skóre zvýšiť
        # vymysleným počtom rokov.
        status, verdict = Answer.no, Verdict.unmet
        earned = weight * (years / required) * _claim_factor(exp.source, exp.evidence)
        detail = f"{_years(years)}, požadované {_years(required)}"

    return CriterionResult(
        key="experience",
        label=LABELS["experience"],
        status=status,
        verdict=verdict,
        weight=weight,
        earned=round(earned, 3),
        detail=detail,
        source=exp.source,
    )


def _verdict(answer: Answer, source: Source, evidence: str | None) -> Verdict:
    """Z odpovede modelu a zdroja faktu urob verdikt, podľa ktorého sa boduje.

    Splnenie uznáme ako doložené len vtedy, keď fakt pochádza zo životopisu
    (a podľa `REQUIRE_EVIDENCE_FOR_CV` aj keď k nemu model dal citáciu).
    Všetko ostatné, čo model označil ako splnené, je tvrdenie uchádzača.
    """
    if answer == Answer.no:
        return Verdict.unmet
    if answer == Answer.unknown:
        return Verdict.undocumented

    from_cv = source in CV_SOURCES
    has_evidence = bool((evidence or "").strip())
    if from_cv and (has_evidence or not REQUIRE_EVIDENCE_FOR_CV):
        return Verdict.documented
    return Verdict.claimed


def _claim_factor(source: Source, evidence: str | None) -> float:
    """Koeficient na pomerné body podľa toho, či je údaj doložený."""
    return _credit(_verdict(Answer.yes, source, evidence))


def _credit(verdict: Verdict) -> float:
    return CREDIT[verdict]


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
        # Poradie je úmyselné: najprv čo je doložené, potom čo je len tvrdené.
        # Náborár tak hneď vidí, čo z toho stojí na papieri a čo na slove.
        for verdict in (
            Verdict.documented,
            Verdict.claimed,
            Verdict.unmet,
            Verdict.undocumented,
        ):
            group = [c for c in criteria if c.verdict == verdict]
            if group:
                parts.append(
                    f"{VERDICT_LABELS[verdict]}: "
                    + ", ".join(_describe(c) for c in group)
                    + "."
                )
    else:
        parts.append("Pozícia nemá zadané požiadavky, skóre vychádza z celkového odhadu vhodnosti.")
        if profile.summary:
            parts.append(_truncate(profile.summary))

    if profile.custom_instructions_findings:
        parts.append("K interným poznámkam: " + _truncate(profile.custom_instructions_findings))

    return " ".join(parts)


def _describe(c: CriterionResult) -> str:
    text = c.label
    if c.detail:
        text += f" ({c.detail})"
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
