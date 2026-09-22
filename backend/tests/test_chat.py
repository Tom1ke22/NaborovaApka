"""Testy chatbota. Gemini sa nevolá, klient je vždy podvrhnutý."""

from types import SimpleNamespace

from tests.conftest import run

from app.core.ai import chat as chat_module
from app.core.ai.chat import (
    FALLBACK_REPLY,
    INTEREST_CTA,
    INTEREST_CTA_AFTER_MESSAGES,
    MAX_HISTORY_MESSAGES,
    build_contents,
    build_system_instruction,
    generate_response,
    should_offer_interest,
)

POSITION = SimpleNamespace(
    title="Kuchár",
    work_area="Gastro",
    location="Košice",
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


class FakeStream:
    """Napodobňuje asynchrónny stream odpovedí z Gemini."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = list(chunks)

    def __aiter__(self) -> "FakeStream":
        return self

    async def __anext__(self) -> SimpleNamespace:
        if not self._chunks:
            raise StopAsyncIteration
        return SimpleNamespace(text=self._chunks.pop(0))


def fake_client(chunks: list[str] | None = None, *, fail: bool = False) -> SimpleNamespace:
    async def generate_content_stream(*, model, contents, config):
        if fail:
            raise RuntimeError("Gemini je nedostupné")
        return FakeStream(chunks or [])

    return SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate_content_stream))
    )


async def collect(agen) -> str:
    return "".join([chunk async for chunk in agen])


# --------------------------------------------------------------------------- #
# Zostavenie konverzácie pre model
# --------------------------------------------------------------------------- #

def test_roles_are_translated_for_gemini():
    contents = build_contents(
        [{"role": "user", "content": "Ahoj"}, {"role": "assistant", "content": "Zdravím"}],
        "Aká je mzda?",
    )
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert contents[-1]["parts"][0]["text"] == "Aká je mzda?"


def test_leading_greeting_is_dropped():
    """Gemini neprijme konverzáciu, ktorá začína odpoveďou modelu."""
    contents = build_contents([{"role": "assistant", "content": "Dobrý deň!"}], "Ahoj")
    assert [c["role"] for c in contents] == ["user"]
    assert contents[0]["parts"][0]["text"] == "Ahoj"


def test_empty_messages_are_skipped():
    contents = build_contents(
        [{"role": "user", "content": "  "}, {"role": "user", "content": "Mám záujem"}],
        "Kedy nástup?",
    )
    assert len(contents) == 2


def test_long_history_is_trimmed():
    history = [{"role": "user", "content": f"správa {i}"} for i in range(60)]
    contents = build_contents(history, "posledná")
    assert len(contents) == MAX_HISTORY_MESSAGES + 1
    assert contents[0]["parts"][0]["text"] == "správa 40"


def test_overlong_user_message_is_cut():
    contents = build_contents([], "x" * 9000)
    assert len(contents[-1]["parts"][0]["text"]) == chat_module.MAX_USER_MESSAGE_CHARS


# --------------------------------------------------------------------------- #
# Systémová inštrukcia
# --------------------------------------------------------------------------- #

def test_system_instruction_contains_rules_and_position():
    text = build_system_instruction(POSITION, None, "Marek")
    assert "Vždy po slovensky" in text
    assert "Názov pozície: Kuchár" in text
    assert "Meno uchádzača: Marek" in text


def test_model_is_told_not_to_greet_again():
    text = build_system_instruction(POSITION, None, "Marek")
    assert "Nikdy nezačínaj odpoveď pozdravom" in text


def test_model_is_told_not_to_mention_the_button():
    text = build_system_instruction(POSITION, None, "Marek")
    assert "Nikdy sám nespomínaj tlačidlo" in text


def test_company_instructions_are_included():
    position = SimpleNamespace(**{**POSITION.__dict__, "ai_bot_instructions": "Zdôrazni nočné zmeny."})
    text = build_system_instruction(position, None, "Marek")
    assert "Zdôrazni nočné zmeny." in text


def test_requirements_reach_the_bot():
    requirements = SimpleNamespace(
        hygiene_minimum_required=True,
        health_certificate_required=False,
        experience_required=False,
        experience_years=None,
        education_level=None,
        slovak_language_level=None,
        foreign_language_level=None,
    )
    text = build_system_instruction(POSITION, requirements, "Marek")
    assert "hygienické minimum" in text


# --------------------------------------------------------------------------- #
# Streamovanie
# --------------------------------------------------------------------------- #

def test_chunks_are_streamed_through(monkeypatch):
    monkeypatch.setattr(chat_module, "get_client", lambda: fake_client(["Mzda je ", "1500 €."]))
    answer = run(collect(generate_response(POSITION, [], "Aká je mzda?", "Marek")))
    assert answer == "Mzda je 1500 €."


def test_without_api_key_user_gets_fallback_not_an_error():
    """Bez kľúča get_client() vráti None a uchádzač musí dostať zrozumiteľnú vetu."""
    answer = run(collect(generate_response(POSITION, [], "Aká je mzda?", "Marek")))
    assert answer == FALLBACK_REPLY


def test_failed_call_falls_back_instead_of_raising(monkeypatch):
    monkeypatch.setattr(chat_module, "get_client", lambda: fake_client(fail=True))
    answer = run(collect(generate_response(POSITION, [], "Aká je mzda?", "Marek")))
    assert answer == FALLBACK_REPLY


def test_empty_model_answer_falls_back(monkeypatch):
    monkeypatch.setattr(chat_module, "get_client", lambda: fake_client([]))
    answer = run(collect(generate_response(POSITION, [], "Aká je mzda?", "Marek")))
    assert answer == FALLBACK_REPLY


def test_fallback_is_not_appended_after_a_real_answer(monkeypatch):
    monkeypatch.setattr(chat_module, "get_client", lambda: fake_client(["Hotovo."]))
    answer = run(collect(generate_response(POSITION, [], "Otázka", "Marek")))
    assert FALLBACK_REPLY not in answer


# --------------------------------------------------------------------------- #
# Výzva na tlačidlo „Mám záujem“
# --------------------------------------------------------------------------- #

def history_with(user_messages: int) -> list[dict]:
    """História, v ktorej už uchádzač poslal `user_messages` správ."""
    history: list[dict] = [{"role": "assistant", "content": "Dobrý deň, Janko!"}]
    for i in range(user_messages):
        history.append({"role": "user", "content": f"otázka {i}"})
        history.append({"role": "assistant", "content": f"odpoveď {i}"})
    return history


def test_interest_cta_is_held_back_for_the_first_messages():
    for already_sent in range(INTEREST_CTA_AFTER_MESSAGES - 1):
        assert not should_offer_interest(history_with(already_sent))


def test_interest_cta_starts_at_the_configured_message():
    assert should_offer_interest(history_with(INTEREST_CTA_AFTER_MESSAGES - 1))
    assert should_offer_interest(history_with(INTEREST_CTA_AFTER_MESSAGES + 5))


def test_first_answer_has_no_interest_cta(monkeypatch):
    monkeypatch.setattr(chat_module, "get_client", lambda: fake_client(["Mzda je 1500 €."]))
    answer = run(collect(generate_response(POSITION, history_with(0), "Aká je mzda?", "Janko")))
    assert answer == "Mzda je 1500 €."


def test_fourth_answer_ends_with_the_interest_cta(monkeypatch):
    monkeypatch.setattr(chat_module, "get_client", lambda: fake_client(["Nástup je v októbri."]))
    history = history_with(INTEREST_CTA_AFTER_MESSAGES - 1)
    answer = run(collect(generate_response(POSITION, history, "Kedy nástup?", "Janko")))
    assert answer == f"Nástup je v októbri. {INTEREST_CTA}"


def test_interest_cta_is_not_duplicated(monkeypatch):
    monkeypatch.setattr(chat_module, "get_client", lambda: fake_client([INTEREST_CTA]))
    history = history_with(INTEREST_CTA_AFTER_MESSAGES - 1)
    answer = run(collect(generate_response(POSITION, history, "Kedy nástup?", "Janko")))
    assert answer.count("Mám záujem") == 1


def test_fallback_gets_the_interest_cta_too():
    """Bez kľúča uchádzač stále dostane vetu aj výzvu, keď na ňu prišiel rad."""
    history = history_with(INTEREST_CTA_AFTER_MESSAGES - 1)
    answer = run(collect(generate_response(POSITION, history, "Otázka", "Janko")))
    assert answer == f"{FALLBACK_REPLY} {INTEREST_CTA}"


def test_early_fallback_has_no_interest_cta():
    answer = run(collect(generate_response(POSITION, history_with(0), "Otázka", "Janko")))
    assert answer == FALLBACK_REPLY
