"""Testy extrakcie faktov. Gemini sa nevolá, klient je vždy podvrhnutý."""

from types import SimpleNamespace

from tests.conftest import run

from app.core.ai import extraction as extraction_module
from app.core.ai.extraction import (
    TRUNCATED_MARKER,
    _to_profile,
    build_prompt,
    extract_profile,
)
from app.core.ai.prompts import CHAT_OPEN, CV_OPEN
from app.core.ai.schemas import Answer, ExtractedProfile, Source
from app.core.limits import (
    EXTRACTION_MAX_OUTPUT_TOKENS,
    MAX_CHAT_TRANSCRIPT_CHARS,
    MAX_CV_CHARS,
)

POSITION = SimpleNamespace(
    title="Kuchár",
    work_area="Gastro",
    location="Žilina",
    contract_type="neuricity_cas",
    working_hours=None,
    shift_type=None,
    break_info=None,
    work_regime=None,
    salary_amount=None,
    salary_period="monthly",
    vacation_days=None,
    meal_allowance=None,
    start_date=None,
    open_slots=1,
    contact_person=None,
    description=None,
    additional_info=None,
    ai_bot_instructions=None,
    ai_evaluation_notes=None,
)

PROFILE_JSON = (
    '{"hygiene_minimum": {"value": "yes", "source": "cv", "evidence": "osvedčenie"},'
    ' "overall_fit": 8, "summary": "Skúsený kuchár."}'
)


def fake_client(response=None, *, fail: bool = False) -> SimpleNamespace:
    async def generate_content(*, model, contents, config):
        if fail:
            raise RuntimeError("Gemini je nedostupné")
        return response

    return SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    )


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #

def test_prompt_contains_position_and_wrapped_candidate_text():
    prompt = build_prompt(POSITION, None, "Kuchár, 3 roky praxe", "Uchádzač: mám zdravotný preukaz")
    assert "Názov pozície: Kuchár" in prompt
    assert CV_OPEN in prompt
    assert CHAT_OPEN in prompt
    assert "3 roky praxe" in prompt


def test_missing_cv_is_stated_explicitly():
    prompt = build_prompt(POSITION, None, "", "Uchádzač: ahoj")
    assert CV_OPEN not in prompt
    assert "Hodnoť len z chatu." in prompt


def test_missing_chat_is_stated_explicitly():
    prompt = build_prompt(POSITION, None, "CV text", "")
    assert CHAT_OPEN not in prompt
    assert "Chat: uchádzač si nepísal s asistentom." in prompt


def test_internal_notes_are_included():
    position = SimpleNamespace(
        **{**POSITION.__dict__, "ai_evaluation_notes": "Over prax s veľkou kuchyňou."}
    )
    prompt = build_prompt(position, None, "CV", "chat")
    assert "Over prax s veľkou kuchyňou." in prompt


def test_chatbot_instructions_do_not_reach_the_evaluator():
    """Pokyny pre chatbota hovoria, čo povedať — nie podľa čoho hodnotiť."""
    position = SimpleNamespace(
        **{**POSITION.__dict__, "ai_bot_instructions": "Zdôrazni možnosť ubytovania."}
    )
    prompt = build_prompt(position, None, "CV", "chat")
    assert "ubytovania" not in prompt


# --------------------------------------------------------------------------- #
# Stropy na dĺžku promptu (cena volania)
# --------------------------------------------------------------------------- #

def test_overlong_cv_text_is_capped():
    prompt = build_prompt(POSITION, None, "x" * (MAX_CV_CHARS * 3), "chat")
    assert "x" * MAX_CV_CHARS in prompt
    assert "x" * (MAX_CV_CHARS + 1) not in prompt
    assert TRUNCATED_MARKER in prompt


def test_overlong_chat_transcript_is_capped():
    prompt = build_prompt(POSITION, None, "CV", "y" * (MAX_CHAT_TRANSCRIPT_CHARS * 3))
    assert "y" * MAX_CHAT_TRANSCRIPT_CHARS in prompt
    assert "y" * (MAX_CHAT_TRANSCRIPT_CHARS + 1) not in prompt
    assert TRUNCATED_MARKER in prompt


def test_capping_keeps_the_end_of_the_transcript():
    """Relevantné odpovede bývajú v neskorších správach, tie musia ostať."""
    transcript = "stará správa " + "z" * MAX_CHAT_TRANSCRIPT_CHARS + " POSLEDNÁ VETA"
    prompt = build_prompt(POSITION, None, "CV", transcript)
    assert "POSLEDNÁ VETA" in prompt
    assert "stará správa" not in prompt


def test_text_within_the_limit_is_untouched():
    prompt = build_prompt(POSITION, None, "krátke CV", "krátky chat")
    assert TRUNCATED_MARKER not in prompt
    assert "krátke CV" in prompt


# --------------------------------------------------------------------------- #
# Čítanie odpovede modelu
# --------------------------------------------------------------------------- #

def test_parsed_pydantic_object_is_used_directly():
    profile = ExtractedProfile(overall_fit=9)
    assert _to_profile(SimpleNamespace(parsed=profile, text=None)) is profile


def test_parsed_dict_is_validated():
    result = _to_profile(SimpleNamespace(parsed={"overall_fit": 7}, text=None))
    assert result.overall_fit == 7


def test_json_text_is_parsed_when_parsed_field_is_empty():
    result = _to_profile(SimpleNamespace(parsed=None, text=PROFILE_JSON))
    assert result.overall_fit == 8
    assert result.hygiene_minimum.value == Answer.yes
    assert result.hygiene_minimum.source == Source.cv


def test_empty_response_gives_none():
    assert _to_profile(SimpleNamespace(parsed=None, text=None)) is None


# --------------------------------------------------------------------------- #
# Celé volanie
# --------------------------------------------------------------------------- #

def test_happy_path_returns_profile(monkeypatch):
    response = SimpleNamespace(parsed=None, text=PROFILE_JSON)
    monkeypatch.setattr(extraction_module, "get_client", lambda: fake_client(response))
    profile = run(extract_profile(POSITION, None, "CV text", "Uchádzač: ahoj"))
    assert profile is not None
    assert profile.summary == "Skúsený kuchár."


def test_without_api_key_returns_none():
    assert run(extract_profile(POSITION, None, "CV text", "chat")) is None


def test_no_cv_and_no_chat_skips_the_call(monkeypatch):
    called = False

    def get_client():
        nonlocal called
        called = True
        return fake_client(SimpleNamespace(parsed=None, text=PROFILE_JSON))

    monkeypatch.setattr(extraction_module, "get_client", get_client)
    assert run(extract_profile(POSITION, None, "   ", "")) is None


def test_failed_call_returns_none_instead_of_raising(monkeypatch):
    monkeypatch.setattr(extraction_module, "get_client", lambda: fake_client(fail=True))
    assert run(extract_profile(POSITION, None, "CV", "chat")) is None


def test_unparseable_answer_returns_none(monkeypatch):
    response = SimpleNamespace(parsed=None, text="toto nie je JSON")
    monkeypatch.setattr(extraction_module, "get_client", lambda: fake_client(response))
    assert run(extract_profile(POSITION, None, "CV", "chat")) is None


def test_request_sets_max_output_tokens(monkeypatch):
    """Bez stropu na výstup sa dá cena jedného volania nafúknuť bez hranice."""
    captured = {}

    async def generate_content(*, model, contents, config):
        captured["config"] = config
        captured["model"] = model
        return SimpleNamespace(parsed=None, text=PROFILE_JSON)

    client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    )
    monkeypatch.setattr(extraction_module, "get_client", lambda: client)

    assert run(extract_profile(POSITION, None, "CV text", "chat")) is not None
    assert captured["config"].max_output_tokens == EXTRACTION_MAX_OUTPUT_TOKENS


# --------------------------------------------------------------------------- #
# Prompt musí modelu zakázať vydávať tvrdenie z chatu za doklad z CV
# --------------------------------------------------------------------------- #

def test_prompt_forbids_relabelling_a_chat_claim_as_cv():
    rules = extraction_module.SYSTEM_RULES
    assert "source nastav na cv IBA ak je fakt naozaj napísaný v životopise" in rules
    assert "Keď to\n  uchádzač iba povedal v chate, daj chat" in rules


def test_prompt_requires_a_quote_for_cv_evidence():
    rules = extraction_module.SYSTEM_RULES
    assert "Ak citáciu z životopisu nemáš, nepíš cv." in rules


def test_prompt_tells_the_model_to_discount_unverified_claims_in_overall_fit():
    assert "za\n  nedoložené tvrdenia odhad znižuj" in extraction_module.SYSTEM_RULES


def test_schema_descriptions_steer_the_source_field():
    """Popisy polí model vidí, preto tam to rozlíšenie musí byť tiež."""
    from app.core.ai.schemas import ExtractedProfile as Profile

    source_desc = Profile.model_fields["hygiene_minimum"].annotation.model_fields["source"].description
    assert "NIKDY neoznačuj ako cv" in source_desc
