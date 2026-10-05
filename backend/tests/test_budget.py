"""Testy denného stropu na volania AI.

Strop je záchranná brzda proti vyčerpaniu kreditu. Default je vypnutý, aby sa
appka sama neudusila bez toho, aby si to niekto nastavil.
"""

from datetime import date, timedelta

import pytest

from tests.conftest import run

from app.core.ai import budget
from app.core.config import settings


@pytest.fixture
def limit(monkeypatch):
    def configure(value: int):
        monkeypatch.setattr(settings, "ai_daily_call_limit", value)

    return configure


def test_without_a_limit_everything_passes(limit):
    limit(0)
    assert all(budget.try_consume() for _ in range(100))


def test_calls_are_blocked_above_the_limit(limit):
    limit(3)
    assert [budget.try_consume() for _ in range(5)] == [True, True, True, False, False]


def test_usage_reports_what_was_consumed(limit):
    limit(5)
    budget.try_consume()
    budget.try_consume()
    assert budget.usage() == (2, 5)


def test_counter_starts_over_the_next_day(limit, monkeypatch):
    limit(1)
    assert budget.try_consume() is True
    assert budget.try_consume() is False

    # Simuluj zmenu dňa.
    monkeypatch.setattr(budget, "_day", date.today() - timedelta(days=1))
    assert budget.try_consume() is True


def test_chatbot_falls_back_instead_of_failing_when_the_budget_is_gone(limit, monkeypatch):
    """Vyčerpaný strop nesmie uchádzačovi ukázať chybu."""
    from app.core.ai import chat as chat_module
    from app.core.ai.chat import FALLBACK_REPLY, generate_response

    def unexpected_client():
        raise AssertionError("Pri vyčerpanom strope sa klient nesmie ani vytvárať")

    limit(1)
    assert budget.try_consume() is True

    monkeypatch.setattr(chat_module, "get_client", lambda: object())

    async def collect():
        return "".join(
            [chunk async for chunk in generate_response(None, [], "Otázka", "Marek")]
        )

    assert run(collect()) == FALLBACK_REPLY


def test_extraction_is_skipped_when_the_budget_is_gone(limit, monkeypatch):
    from app.core.ai import extraction as extraction_module

    limit(1)
    assert budget.try_consume() is True

    def fail():
        raise AssertionError("Extrakcia sa pri vyčerpanom strope nesmie volať")

    monkeypatch.setattr(extraction_module, "get_client", lambda: object())
    monkeypatch.setattr(extraction_module, "_to_profile", lambda response: fail())

    result = run(extraction_module.extract_profile(None, None, "nejake CV", ""))
    assert result is None
