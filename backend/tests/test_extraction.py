"""Testy extrakcie faktov. Gemini sa nevolá, klient je vždy podvrhnutý."""

from types import SimpleNamespace

from tests.conftest import run

from app.core.ai import extraction as extraction_module
from app.core.ai.extraction import _to_profile, build_prompt, extract_profile
from app.core.ai.prompts import CHAT_OPEN, CV_OPEN
from app.core.ai.schemas import Answer, ExtractedProfile, Source

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


def test_company_instructions_are_included():
    position = SimpleNamespace(**{**POSITION.__dict__, "ai_bot_instructions": "Over prax s veľkou kuchyňou."})
    prompt = build_prompt(position, None, "CV", "chat")
    assert "Over prax s veľkou kuchyňou." in prompt


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
