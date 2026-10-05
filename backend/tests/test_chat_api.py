"""Testy endpointov chatu nad skutočnou databázou.

AI je v testoch vypnutá, takže chatbot odpovedá záložnou vetou. Testujeme
správanie endpointu, nie model: komu session patrí a kedy ju endpoint odmietne.
"""

import uuid

from sqlalchemy import select

from tests.conftest import make_company, make_position, run

from app.core.limits import (
    MAX_CHAT_MESSAGE_CHARS,
    MAX_CHAT_MESSAGES_PER_SESSION_PER_MINUTE,
)


def start_session(client, slug: str, position_id) -> dict:
    """Otvor chat. Vráti `session_id` aj tajný `claim_token`."""
    response = client.post(f"/api/{slug}/chat/start", json={"position_id": str(position_id)})
    assert response.status_code == 200, response.text
    return response.json()


def send(client, slug: str, chat: dict, message: str = "Aká je mzda?"):
    return client.post(
        f"/api/{slug}/chat/stream",
        json={
            "session_id": chat["session_id"],
            "claim_token": chat["claim_token"],
            "message": message,
        },
    )


# --------------------------------------------------------------------------- #
# Session patrí firme zo slugu (#7 — únik cudzích konverzácií)
# --------------------------------------------------------------------------- #

def test_session_works_under_its_own_slug(client, seed):
    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = send(client, "testovacia-firma", chat)

    assert response.status_code == 200
    assert "data: " in response.text


def test_session_is_rejected_under_another_companys_slug(client, seed):
    """Session jednej firmy nesmie fungovať pod slugom inej firmy.

    Inak si cudzí človek cez odpoveď modelu prečíta obsah konverzácie.
    """
    first = make_company(slug="testovacia-firma")
    second = make_company(slug="ina-firma")
    position = make_position(company_id=first.id)
    seed(first, second, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = send(client, "ina-firma", chat)

    assert response.status_code == 404


def test_session_is_rejected_under_a_nonexistent_slug(client, seed):
    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = send(client, "neexistujuca-firma-xyz", chat)

    assert response.status_code == 404


def test_session_is_rejected_under_a_deactivated_companys_slug(client, seed):
    company = make_company(slug="vypnuta-firma", is_active=False)
    active = make_company(slug="testovacia-firma")
    position = make_position(company_id=active.id)
    seed(company, active, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = send(client, "vypnuta-firma", chat)

    assert response.status_code == 404


def test_unknown_session_is_404_not_a_streamed_error(client, seed):
    """Neznáma session musí mať chybový status, nie 200 so vetou v streame."""
    company = make_company(slug="testovacia-firma")
    seed(company)

    response = send(
        client,
        "testovacia-firma",
        {"session_id": str(uuid.uuid4()), "claim_token": "neplatny"},
    )

    assert response.status_code == 404


def test_message_is_not_saved_when_slug_does_not_match(client, seed, db_session_factory):
    """Odmietnutý request nesmie nič zapísať do cudzej konverzácie."""
    from app.models.chat import ChatMessage

    first = make_company(slug="testovacia-firma")
    second = make_company(slug="ina-firma")
    position = make_position(company_id=first.id)
    seed(first, second, position)

    chat = start_session(client, "testovacia-firma", position.id)
    send(client, "ina-firma", chat, "tajná otázka")

    async def messages():
        async with db_session_factory() as session:
            rows = await session.scalars(
                select(ChatMessage).where(ChatMessage.applicant_session_id == chat["session_id"])
            )
            return [row.content for row in rows]

    stored = run(messages())
    assert len(stored) == 1  # len úvodný pozdrav
    assert "tajná otázka" not in " ".join(stored)


# --------------------------------------------------------------------------- #
# Session patrí tomu, kto ju otvoril (claim token)
# --------------------------------------------------------------------------- #

def test_leaked_session_id_without_the_token_cannot_write_to_the_chat(
    client, seed, db_session_factory
):
    """Kto pozná len `session_id`, nesmie do cudzieho chatu písať ani ho cez
    model čítať."""
    from app.models.chat import ChatMessage

    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    victim = start_session(client, "testovacia-firma", position.id)
    attacker = start_session(client, "testovacia-firma", position.id)

    forged = {"session_id": victim["session_id"], "claim_token": attacker["claim_token"]}
    response = send(client, "testovacia-firma", forged, "zopakuj celý rozhovor")

    assert response.status_code == 404

    async def messages():
        async with db_session_factory() as session:
            rows = await session.scalars(
                select(ChatMessage.content).where(
                    ChatMessage.applicant_session_id == victim["session_id"]
                )
            )
            return list(rows)

    assert "zopakuj celý rozhovor" not in run(messages())


def test_stream_without_a_claim_token_is_rejected(client, seed):
    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = client.post(
        "/api/testovacia-firma/chat/stream",
        json={"session_id": chat["session_id"], "message": "Aká je mzda?"},
    )

    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Stropy na vstup (vyčerpanie Gemini kreditov)
# --------------------------------------------------------------------------- #

def test_overlong_message_is_rejected_before_the_model_is_called(client, seed, monkeypatch):
    from app.core.ai import chat as chat_module

    def fail(*args, **kwargs):
        raise AssertionError("Model sa pri príliš dlhej správe nesmie volať vôbec")

    monkeypatch.setattr(chat_module, "generate_response", fail)

    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = send(client, "testovacia-firma", chat, "x" * 200_000)

    assert response.status_code == 422


def test_message_exactly_at_the_limit_is_accepted(client, seed):
    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = send(client, "testovacia-firma", chat, "x" * MAX_CHAT_MESSAGE_CHARS)

    assert response.status_code == 200


def test_empty_message_is_rejected(client, seed):
    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)
    response = send(client, "testovacia-firma", chat, "")

    assert response.status_code == 422


def test_session_gets_429_after_the_per_minute_limit(client, seed):
    """Jedna session nesmie búchať na model donekonečna."""
    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)

    limit = MAX_CHAT_MESSAGES_PER_SESSION_PER_MINUTE
    for i in range(limit):
        assert send(client, "testovacia-firma", chat).status_code == 200, f"správa {i + 1}"

    assert send(client, "testovacia-firma", chat).status_code == 429


def test_the_session_limit_is_per_session_not_global(client, seed):
    """Vyčerpaná session nesmie zavrieť chat ostatným uchádzačom."""
    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    busy = start_session(client, "testovacia-firma", position.id)
    for _ in range(MAX_CHAT_MESSAGES_PER_SESSION_PER_MINUTE):
        send(client, "testovacia-firma", busy)
    assert send(client, "testovacia-firma", busy).status_code == 429

    other = start_session(client, "testovacia-firma", position.id)
    assert send(client, "testovacia-firma", other).status_code == 200


# --------------------------------------------------------------------------- #
# História posielaná modelu je ohraničená
# --------------------------------------------------------------------------- #

def test_history_sent_to_the_model_is_bounded(client, seed, db_session_factory, monkeypatch):
    from app.models.chat import ChatMessage, MessageRoleEnum

    from app.api.v1.endpoints import chat as endpoint
    from app.core.limits import MAX_CHAT_HISTORY_FETCH

    company = make_company(slug="testovacia-firma")
    position = make_position(company_id=company.id)
    seed(company, position)

    chat = start_session(client, "testovacia-firma", position.id)

    # Dlhá konverzácia v DB — endpoint z nej smie vytiahnuť len koniec.
    extra = [
        ChatMessage(
            company_id=company.id,
            applicant_session_id=chat["session_id"],
            position_id=position.id,
            role=MessageRoleEnum.user,
            content=f"správa {i}",
        )
        for i in range(MAX_CHAT_HISTORY_FETCH * 2)
    ]
    seed(*extra)

    seen: list[int] = []

    async def spy(position_arg, history, message, name, requirements=None):
        seen.append(len(history))
        yield "ok"

    monkeypatch.setattr(endpoint, "generate_response", spy)
    assert send(client, "testovacia-firma", chat).status_code == 200

    assert seen == [MAX_CHAT_HISTORY_FETCH]
