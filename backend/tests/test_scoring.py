"""Testy deterministického skórovania. Bez AI, bez DB."""

import json
from types import SimpleNamespace

from app.core.ai.schemas import (
    Answer,
    ExperienceFact,
    ExtractedProfile,
    Fact,
    LevelFact,
    Source,
)
from app.core.ai.scoring import (
    UNKNOWN_CREDIT,
    WEIGHTS,
    Requirements,
    _years,
    compute_score,
)

KUCHAR = Requirements(
    hygiene_minimum_required=True,
    health_certificate_required=True,
    experience_required=True,
    experience_years=2,
)

ALL_REQUIREMENTS = Requirements(
    hygiene_minimum_required=True,
    health_certificate_required=True,
    experience_required=True,
    experience_years=2,
    education_level="stredoškolské",
    slovak_language_level="plynulo",
    foreign_language_level="EN-B1",
)


def yes(source=Source.chat, evidence="mám") -> Fact:
    return Fact(value=Answer.yes, source=source, evidence=evidence)


def no(source=Source.chat) -> Fact:
    return Fact(value=Answer.no, source=source, evidence="nemám")


def level(meets: Answer, text: str | None = None, source=Source.cv) -> LevelFact:
    return LevelFact(level=text, meets_requirement=meets, source=source)


def marek(fit: int = 7) -> ExtractedProfile:
    """Príklad zo zadania: má oba doklady a 3 roky praxe v kuchyni."""
    return ExtractedProfile(
        hygiene_minimum=yes(),
        health_certificate=yes(),
        experience=ExperienceFact(years=3, summary="3 roky kuchár", source=Source.chat, evidence="v kuchyni robím 3 roky"),
        overall_fit=fit,
    )


# --------------------------------------------------------------------------- #
# Základné scenáre
# --------------------------------------------------------------------------- #

def test_meets_all_requirements_scores_high():
    result = compute_score(KUCHAR, marek())
    assert result.score >= 8
    assert result.requirements_ratio == 1.0
    assert result.reasoning.startswith("Spĺňa:")
    assert "hygienické minimum" in result.reasoning
    assert "zdravotný preukaz" in result.reasoning
    assert "prax v odbore (3 roky, požadované 2 roky)" in result.reasoning
    assert "Nespĺňa" not in result.reasoning
    assert "Nedoložené" not in result.reasoning


def test_nothing_documented_lands_in_the_middle():
    result = compute_score(ALL_REQUIREMENTS, ExtractedProfile(overall_fit=5))
    assert 4 <= result.score <= 6
    assert result.requirements_ratio == UNKNOWN_CREDIT
    assert result.reasoning.startswith("Nedoložené:")
    assert "Spĺňa" not in result.reasoning


def test_explicitly_fails_everything_scores_minimum():
    profile = ExtractedProfile(
        hygiene_minimum=no(),
        health_certificate=no(),
        experience=ExperienceFact(years=0, source=Source.chat),
        education=level(Answer.no, "základné"),
        slovak_language=level(Answer.no, "základy"),
        foreign_language=level(Answer.no, None),
        overall_fit=1,
    )
    result = compute_score(ALL_REQUIREMENTS, profile)
    assert result.score == 1
    assert result.reasoning.startswith("Nespĺňa:")
    assert "prax v odbore (bez praxe)" not in result.reasoning  # required 2 roky → detail so rokmi
    assert "prax v odbore (0 rokov, požadované 2 roky)" in result.reasoning


def test_no_requirements_uses_overall_fit_directly():
    result = compute_score(Requirements(), ExtractedProfile(overall_fit=8, summary="Skúsený kuchár."))
    assert result.score == 8
    assert result.requirements_ratio is None
    assert result.criteria == []
    assert "nemá zadané požiadavky" in result.reasoning
    assert "Skúsený kuchár." in result.reasoning


# --------------------------------------------------------------------------- #
# Prax
# --------------------------------------------------------------------------- #

def test_partial_experience_gets_proportional_credit():
    profile = ExtractedProfile(experience=ExperienceFact(years=1, source=Source.cv))
    result = compute_score(Requirements(experience_required=True, experience_years=2), profile)
    exp = result.criteria[0]
    assert exp.status == Answer.no
    assert exp.earned == WEIGHTS["experience"] / 2
    assert exp.detail == "1 rok, požadované 2 roky"
    assert "Nespĺňa: prax v odbore (1 rok, požadované 2 roky) [CV]" in result.reasoning


def test_experience_required_without_years_accepts_any_experience():
    profile = ExtractedProfile(experience=ExperienceFact(years=0.5, source=Source.chat))
    result = compute_score(Requirements(experience_required=True), profile)
    exp = result.criteria[0]
    assert exp.status == Answer.yes
    assert exp.earned == WEIGHTS["experience"]
    assert exp.detail == "0,5 roka"


def test_unknown_experience_gets_half_credit():
    result = compute_score(Requirements(experience_required=True, experience_years=3), ExtractedProfile())
    exp = result.criteria[0]
    assert exp.status == Answer.unknown
    assert exp.earned == WEIGHTS["experience"] * UNKNOWN_CREDIT
    assert "Nedoložené: prax v odbore (požadované 3 roky)" in result.reasoning


# --------------------------------------------------------------------------- #
# Zoradenie a determinizmus
# --------------------------------------------------------------------------- #

def test_hard_requirements_dominate_over_model_fit():
    meets_all_low_fit = compute_score(KUCHAR, marek(fit=3))
    missing_docs_high_fit = compute_score(
        KUCHAR,
        ExtractedProfile(
            hygiene_minimum=no(),
            health_certificate=no(),
            experience=ExperienceFact(years=5, source=Source.cv),
            overall_fit=10,
        ),
    )
    assert meets_all_low_fit.score > missing_docs_high_fit.score


def test_fit_breaks_ties_between_equal_candidates():
    strong = compute_score(KUCHAR, marek(fit=9))
    weak = compute_score(KUCHAR, marek(fit=2))
    assert strong.score > weak.score
    assert weak.score >= 8  # stále spĺňa všetko, fit ho nemôže stiahnuť pod požiadavky


def test_same_input_gives_same_output():
    a = compute_score(ALL_REQUIREMENTS, marek())
    b = compute_score(ALL_REQUIREMENTS, marek())
    assert a == b


# --------------------------------------------------------------------------- #
# Zdôvodnenie a serializácia
# --------------------------------------------------------------------------- #

def test_only_active_requirements_are_evaluated():
    result = compute_score(Requirements(hygiene_minimum_required=True), marek())
    assert [c.key for c in result.criteria] == ["hygiene_minimum"]


def test_level_requirements_use_model_judgement():
    profile = ExtractedProfile(
        education=level(Answer.yes, "výučný list kuchár"),
        slovak_language=level(Answer.unknown),
        foreign_language=level(Answer.no, "angličtina základy", source=Source.chat),
    )
    req = Requirements(education_level="stredoškolské", slovak_language_level="plynulo", foreign_language_level="EN-B2")
    result = compute_score(req, profile)
    by_key = {c.key: c for c in result.criteria}
    assert by_key["education"].earned == WEIGHTS["education"]
    assert by_key["slovak_language"].earned == WEIGHTS["slovak_language"] * UNKNOWN_CREDIT
    assert by_key["foreign_language"].earned == 0
    assert "vzdelanie (výučný list kuchár, požadované stredoškolské) [CV]" in result.reasoning
    assert "cudzí jazyk (angličtina základy, požadované EN-B2) [chat]" in result.reasoning
    assert "Nedoložené: slovenčina (požadované plynulo)" in result.reasoning


def test_custom_instruction_findings_are_appended_and_truncated():
    findings = "Varil pre 400 stravníkov denne v školskej jedálni. " * 10
    result = compute_score(KUCHAR, marek().model_copy(update={"custom_instructions_findings": findings}))
    assert "K inštrukciám: Varil pre 400 stravníkov" in result.reasoning
    assert result.reasoning.endswith("…")
    assert len(result.reasoning) < 400


def test_result_serializes_to_json():
    result = compute_score(ALL_REQUIREMENTS, marek())
    data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
    assert data["score"] == result.score
    assert data["criteria"][0]["status"] in {"yes", "no", "unknown"}
    assert data["criteria"][0]["source"] in {"cv", "chat", "both", "none"}


# --------------------------------------------------------------------------- #
# Pomocné veci
# --------------------------------------------------------------------------- #

def test_requirements_from_orm_and_none():
    orm = SimpleNamespace(
        hygiene_minimum_required=True,
        health_certificate_required=False,
        experience_required=True,
        experience_years=4,
        education_level=None,
        slovak_language_level="plynulo",
        foreign_language_level=None,
    )
    req = Requirements.from_orm(orm)
    assert req.experience_years == 4 and req.slovak_language_level == "plynulo"
    assert req.any_active
    assert Requirements.from_orm(None) == Requirements()
    assert not Requirements().any_active


def test_overall_fit_is_clamped_by_schema():
    assert ExtractedProfile(overall_fit=15).overall_fit == 10
    assert ExtractedProfile(overall_fit=0).overall_fit == 1
    assert ExtractedProfile(overall_fit="abc").overall_fit == 5


def test_slovak_year_forms():
    assert _years(1) == "1 rok"
    assert _years(3) == "3 roky"
    assert _years(5) == "5 rokov"
    assert _years(0) == "0 rokov"
    assert _years(2.5) == "2,5 roka"
