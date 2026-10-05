"""Testy deterministického skórovania. Bez AI, bez DB."""

import json

import pytest
from types import SimpleNamespace

from app.core.ai.schemas import (
    Answer,
    CustomFact,
    ExperienceFact,
    ExtractedProfile,
    Fact,
    LevelFact,
    Source,
)
from app.core.ai.scoring import (
    CLAIMED_CREDIT,
    CUSTOM_WEIGHT,
    MAX_CUSTOM_REQUIREMENTS,
    UNKNOWN_CREDIT,
    WEIGHTS,
    Requirements,
    Verdict,
    _years,
    compute_score,
    custom_requirement_labels,
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


def documented_yes(evidence="osvedčenie o odbornej spôsobilosti") -> Fact:
    """Splnené a doložené v životopise — jediný spôsob, ako dostať plné body."""
    return Fact(value=Answer.yes, source=Source.cv, evidence=evidence)


def no(source=Source.chat) -> Fact:
    return Fact(value=Answer.no, source=source, evidence="nemám")


def level(meets: Answer, text: str | None = None, source=Source.cv, evidence=None) -> LevelFact:
    return LevelFact(level=text, meets_requirement=meets, source=source, evidence=evidence)


def marek(fit: int = 7) -> ExtractedProfile:
    """Príklad zo zadania, ale všetko iba POVEDAL v chate — nič nedoložil."""
    return ExtractedProfile(
        hygiene_minimum=yes(),
        health_certificate=yes(),
        experience=ExperienceFact(years=3, summary="3 roky kuchár", source=Source.chat, evidence="v kuchyni robím 3 roky"),
        overall_fit=fit,
    )


def marek_s_cv(fit: int = 7) -> ExtractedProfile:
    """Ten istý uchádzač, ale všetko má vypísané v životopise."""
    return ExtractedProfile(
        hygiene_minimum=documented_yes(),
        health_certificate=documented_yes("zdravotný preukaz platný do 2027"),
        experience=ExperienceFact(
            years=3, summary="3 roky kuchár", source=Source.cv,
            evidence="Kuchár, Hotel Lux, 2021–2024",
        ),
        overall_fit=fit,
    )


# --------------------------------------------------------------------------- #
# Základné scenáre
# --------------------------------------------------------------------------- #

def test_documented_candidate_scores_high():
    result = compute_score(KUCHAR, marek_s_cv())
    assert result.score >= 8
    assert result.requirements_ratio == 1.0
    assert result.reasoning.startswith("Doložené v životopise:")
    assert "hygienické minimum" in result.reasoning
    assert "zdravotný preukaz" in result.reasoning
    assert "prax v odbore (3 roky, požadované 2 roky)" in result.reasoning
    assert "Nespĺňa" not in result.reasoning
    assert "Nedoložené" not in result.reasoning
    assert "neoverené" not in result.reasoning


def test_claims_alone_do_not_score_as_full_compliance():
    """To je ten prípad, čo dával 8/10 za holé tvrdenie v chate."""
    claimed = compute_score(KUCHAR, marek())
    documented = compute_score(KUCHAR, marek_s_cv())

    assert claimed.score < documented.score
    assert claimed.requirements_ratio == pytest.approx(CLAIMED_CREDIT)
    assert all(c.verdict == Verdict.claimed for c in claimed.criteria)
    assert claimed.reasoning.startswith("Tvrdí v chate, neoverené:")
    assert "Doložené v životopise" not in claimed.reasoning


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
    profile = ExtractedProfile(
        experience=ExperienceFact(years=1, source=Source.cv, evidence="Kuchár 2023–2024")
    )
    result = compute_score(Requirements(experience_required=True, experience_years=2), profile)
    exp = result.criteria[0]
    assert exp.status == Answer.no
    assert exp.verdict == Verdict.unmet
    assert exp.earned == WEIGHTS["experience"] / 2
    assert exp.detail == "1 rok, požadované 2 roky"
    assert "Nespĺňa: prax v odbore (1 rok, požadované 2 roky)" in result.reasoning


def test_unverified_years_are_discounted_too():
    """Vymyslený počet rokov v chate nesmie dať toľko bodov ako roky z CV."""
    req = Requirements(experience_required=True, experience_years=2)
    from_cv = compute_score(
        req,
        ExtractedProfile(experience=ExperienceFact(years=1, source=Source.cv, evidence="Kuchár 2023")),
    )
    from_chat = compute_score(
        req, ExtractedProfile(experience=ExperienceFact(years=1, source=Source.chat, evidence="robím rok"))
    )
    assert from_chat.criteria[0].earned < from_cv.criteria[0].earned
    assert from_chat.criteria[0].earned == round(WEIGHTS["experience"] / 2 * CLAIMED_CREDIT, 3)


def test_experience_required_without_years_accepts_any_experience():
    profile = ExtractedProfile(
        experience=ExperienceFact(years=0.5, source=Source.cv, evidence="Pomocný kuchár, pol roka")
    )
    result = compute_score(Requirements(experience_required=True), profile)
    exp = result.criteria[0]
    assert exp.status == Answer.yes
    assert exp.verdict == Verdict.documented
    assert exp.earned == WEIGHTS["experience"]
    assert exp.detail == "0,5 roka"


def test_unknown_experience_gets_half_credit():
    result = compute_score(Requirements(experience_required=True, experience_years=3), ExtractedProfile())
    exp = result.criteria[0]
    assert exp.status == Answer.unknown
    assert exp.verdict == Verdict.undocumented
    assert exp.earned == WEIGHTS["experience"] * UNKNOWN_CREDIT
    assert "Nedoložené: prax v odbore (požadované 3 roky)" in result.reasoning


# --------------------------------------------------------------------------- #
# Zoradenie a determinizmus
# --------------------------------------------------------------------------- #

def test_hard_requirements_dominate_over_model_fit():
    meets_all_low_fit = compute_score(KUCHAR, marek_s_cv(fit=3))
    missing_docs_high_fit = compute_score(
        KUCHAR,
        ExtractedProfile(
            hygiene_minimum=no(),
            health_certificate=no(),
            experience=ExperienceFact(years=5, source=Source.cv, evidence="5 rokov kuchár"),
            overall_fit=10,
        ),
    )
    assert meets_all_low_fit.score > missing_docs_high_fit.score


def test_fit_breaks_ties_between_equal_candidates():
    strong = compute_score(KUCHAR, marek_s_cv(fit=9))
    weak = compute_score(KUCHAR, marek_s_cv(fit=2))
    assert strong.score > weak.score
    # Všetko doložené, takže fit ho nestiahne pod úroveň požiadaviek.
    assert weak.score >= 8


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
        education=level(Answer.yes, "výučný list kuchár", evidence="Výučný list v odbore kuchár"),
        slovak_language=level(Answer.unknown),
        foreign_language=level(Answer.no, "angličtina základy", source=Source.chat),
    )
    req = Requirements(education_level="stredoškolské", slovak_language_level="plynulo", foreign_language_level="EN-B2")
    result = compute_score(req, profile)
    by_key = {c.key: c for c in result.criteria}
    assert by_key["education"].earned == WEIGHTS["education"]
    assert by_key["slovak_language"].earned == WEIGHTS["slovak_language"] * UNKNOWN_CREDIT
    assert by_key["foreign_language"].earned == 0
    assert "vzdelanie (výučný list kuchár, požadované stredoškolské)" in result.reasoning
    assert "cudzí jazyk (angličtina základy, požadované EN-B2)" in result.reasoning
    assert "Nedoložené: slovenčina (požadované plynulo)" in result.reasoning


def test_custom_instruction_findings_are_appended_and_truncated():
    findings = "Varil pre 400 stravníkov denne v školskej jedálni. " * 10
    result = compute_score(KUCHAR, marek().model_copy(update={"custom_instructions_findings": findings}))
    assert "K interným poznámkam: Varil pre 400 stravníkov" in result.reasoning
    assert result.reasoning.endswith("…")
    assert len(result.reasoning) < 400


def test_result_serializes_to_json():
    result = compute_score(ALL_REQUIREMENTS, marek())
    data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
    assert data["score"] == result.score
    assert data["criteria"][0]["status"] in {"yes", "no", "unknown"}
    assert data["criteria"][0]["source"] in {"cv", "chat", "both", "none"}


# --------------------------------------------------------------------------- #
# Vlastné požiadavky
# --------------------------------------------------------------------------- #

VODIC = Requirements(custom_requirements=("vodičský preukaz B", "práca v noci"))


def custom(key: str, value: Answer, source=Source.cv) -> CustomFact:
    return CustomFact(key=key, value=value, source=source, evidence="v CV")


def test_custom_requirements_are_scored_by_key_not_by_order():
    profile = ExtractedProfile(
        custom_requirements=[
            custom("custom_2", Answer.no),
            custom("custom_1", Answer.yes),
        ],
        overall_fit=5,
    )
    result = compute_score(VODIC, profile)
    by_key = {c.key: c for c in result.criteria}

    assert by_key["custom_1"].label == "vodičský preukaz B"
    assert by_key["custom_1"].status == Answer.yes
    assert by_key["custom_1"].earned == CUSTOM_WEIGHT
    assert by_key["custom_2"].label == "práca v noci"
    assert by_key["custom_2"].earned == 0.0
    assert result.requirements_ratio == 0.5


def test_custom_requirement_without_answer_counts_as_unknown():
    result = compute_score(VODIC, ExtractedProfile(overall_fit=5))
    assert [c.status for c in result.criteria] == [Answer.unknown, Answer.unknown]
    assert all(c.earned == CUSTOM_WEIGHT * UNKNOWN_CREDIT for c in result.criteria)
    assert "Nedoložené: vodičský preukaz B, práca v noci." in result.reasoning


def test_custom_requirements_mix_with_fixed_ones():
    req = Requirements(hygiene_minimum_required=True, custom_requirements=("vlastné auto",))
    profile = ExtractedProfile(
        hygiene_minimum=documented_yes(),
        custom_requirements=[custom("custom_1", Answer.yes)],
        overall_fit=8,
    )
    result = compute_score(req, profile)
    assert [c.key for c in result.criteria] == ["hygiene_minimum", "custom_1"]
    assert result.requirements_ratio == 1.0
    assert result.score == 10


def test_custom_requirement_labels_normalizes_both_shapes():
    assert custom_requirement_labels([{"label": "  vodičák   B "}]) == ["vodičák B"]
    assert custom_requirement_labels(["vodičák B"]) == ["vodičák B"]
    assert custom_requirement_labels([{"label": "  "}, {}, None, ""]) == []
    assert custom_requirement_labels(None) == []
    many = [{"label": f"p{i}"} for i in range(MAX_CUSTOM_REQUIREMENTS + 5)]
    assert len(custom_requirement_labels(many)) == MAX_CUSTOM_REQUIREMENTS


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
        custom_requirements=[{"label": "vodičský preukaz B"}],
    )
    req = Requirements.from_orm(orm)
    assert req.experience_years == 4 and req.slovak_language_level == "plynulo"
    assert req.custom_requirements == ("vodičský preukaz B",)
    assert req.any_active
    assert Requirements.from_orm(None) == Requirements()
    assert not Requirements().any_active


def test_requirements_from_orm_survives_missing_custom_column():
    """Riadky spred migrácie 0004 stĺpec nemajú — nesmie to spadnúť."""
    orm = SimpleNamespace(
        hygiene_minimum_required=False,
        health_certificate_required=False,
        experience_required=False,
        experience_years=None,
        education_level=None,
        slovak_language_level=None,
        foreign_language_level=None,
    )
    assert Requirements.from_orm(orm).custom_requirements == ()


def test_only_custom_requirements_make_position_active():
    assert Requirements(custom_requirements=("vlastné auto",)).any_active


def test_unchecked_custom_requirements_are_not_scored():
    """Odškrtnutá požiadavka ostáva uložená, ale do promptu ani skóre nejde."""
    orm = SimpleNamespace(
        hygiene_minimum_required=False,
        health_certificate_required=False,
        experience_required=False,
        experience_years=None,
        education_level=None,
        slovak_language_level=None,
        foreign_language_level=None,
        custom_requirements=[
            {"label": "vodičský preukaz B", "required": False},
            {"label": "práca v noci", "required": True},
        ],
    )
    req = Requirements.from_orm(orm)
    assert req.custom_requirements == ("práca v noci",)


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


# --------------------------------------------------------------------------- #
# Tri stavy: doložené v CV · tvrdené v chate · nedoložené
# --------------------------------------------------------------------------- #

def single_hygiene(fact: Fact) -> tuple:
    """Pozícia s jedinou požiadavkou, nech je kritérium izolované."""
    result = compute_score(
        Requirements(hygiene_minimum_required=True),
        ExtractedProfile(hygiene_minimum=fact, overall_fit=5),
    )
    return result, result.criteria[0]


def test_cv_evidence_is_documented():
    _, c = single_hygiene(Fact(value=Answer.yes, source=Source.cv, evidence="osvedčenie o odbornej spôsobilosti"))
    assert c.verdict == Verdict.documented
    assert c.earned == WEIGHTS["hygiene_minimum"]


def test_both_sources_count_as_documented():
    """Keď je fakt v CV aj v chate, stále je doložený."""
    _, c = single_hygiene(Fact(value=Answer.yes, source=Source.both, evidence="osvedčenie"))
    assert c.verdict == Verdict.documented


def test_chat_claim_is_only_claimed():
    _, c = single_hygiene(Fact(value=Answer.yes, source=Source.chat, evidence="mám hygienické minimum"))
    assert c.verdict == Verdict.claimed
    assert c.earned == round(WEIGHTS["hygiene_minimum"] * CLAIMED_CREDIT, 3)


def test_yes_without_any_source_is_not_documented():
    """Model povedal áno, ale nevie odkiaľ — to nie je doklad."""
    _, c = single_hygiene(Fact(value=Answer.yes, source=Source.none, evidence=None))
    assert c.verdict == Verdict.claimed


def test_cv_without_a_quote_is_not_documented():
    """Zelený fajk bez citácie by náborár nemal čo overiť."""
    _, c = single_hygiene(Fact(value=Answer.yes, source=Source.cv, evidence=None))
    assert c.verdict == Verdict.claimed


def test_blank_quote_does_not_count_as_evidence():
    _, c = single_hygiene(Fact(value=Answer.yes, source=Source.cv, evidence="   "))
    assert c.verdict == Verdict.claimed


def test_missing_fact_is_undocumented():
    _, c = single_hygiene(Fact(value=Answer.unknown, source=Source.none))
    assert c.verdict == Verdict.undocumented
    assert c.earned == WEIGHTS["hygiene_minimum"] * UNKNOWN_CREDIT


def test_explicit_no_is_unmet_regardless_of_source():
    for source in (Source.cv, Source.chat, Source.both, Source.none):
        _, c = single_hygiene(Fact(value=Answer.no, source=source, evidence="nemám"))
        assert c.verdict == Verdict.unmet, source
        assert c.earned == 0.0


def test_credit_order_documented_beats_claimed_beats_undocumented():
    """Poradie koeficientov je to, čo celé rozlíšenie drží."""
    documented, _ = single_hygiene(Fact(value=Answer.yes, source=Source.cv, evidence="osvedčenie"))
    claimed, _ = single_hygiene(Fact(value=Answer.yes, source=Source.chat, evidence="mám"))
    undocumented, _ = single_hygiene(Fact(value=Answer.unknown, source=Source.none))
    unmet, _ = single_hygiene(Fact(value=Answer.no, source=Source.cv, evidence="nemám"))

    ratios = [r.requirements_ratio for r in (documented, claimed, undocumented, unmet)]
    assert ratios == sorted(ratios, reverse=True)
    assert len(set(ratios)) == 4  # žiadne dva stavy nesplývajú


def test_reasoning_separates_documented_from_claimed():
    profile = ExtractedProfile(
        hygiene_minimum=documented_yes(),
        health_certificate=yes(source=Source.chat, evidence="preukaz mám doma"),
        overall_fit=6,
    )
    req = Requirements(hygiene_minimum_required=True, health_certificate_required=True)
    reasoning = compute_score(req, profile).reasoning

    assert "Doložené v životopise: hygienické minimum." in reasoning
    assert "Tvrdí v chate, neoverené: zdravotný preukaz." in reasoning
    # Náborár nesmie z textu nadobudnúť dojem, že preukaz je overený.
    assert "Doložené v životopise: hygienické minimum, zdravotný preukaz" not in reasoning


def test_verdict_is_serialized_for_the_frontend():
    result = compute_score(KUCHAR, marek_s_cv())
    payload = json.loads(json.dumps(result.to_dict()))
    assert {c["verdict"] for c in payload["criteria"]} == {"documented"}
    # `status` ostáva, aby sa dalo dohľadať, čo tvrdil model.
    assert all("status" in c and "source" in c for c in payload["criteria"])
