"""Testy odoslania prihlášky a pripojenia chatu k uchádzačovi.

`session_id` je len identifikátor a môže uniknúť (história, Referer, logy).
Chat sa preto k prihláške pripojí iba s tajným claim tokenom, ktorý dostal
ten, kto chat otvoril. Inak by útočník s cudzím `session_id` pripojil cudzí
rozhovor k vlastnej prihláške a admin by ho videl pod jeho menom.
"""

import uuid

from sqlalchemy import select

from app.models.chat import ChatMessage
from tests.conftest import make_company, make_position, run

SLUG = "testovacia-firma"
SECRET = "Mám diagnostikovanú epilepsiu, potrebujem len denné zmeny."


def start_chat(client, position_id) -> dict:
    response = client.post(f"/api/{SLUG}/chat/start", json={"position_id": str(position_id)})
    assert response.status_code == 200, response.text
    return response.json()


def say(client, chat: dict, message: str) -> None:
    response = client.post(
        f"/api/{SLUG}/chat/stream",
        json={
            "session_id": chat["session_id"],
            "claim_token": chat["claim_token"],
            "message": message,
        },
    )
    assert response.status_code == 200, response.text


def submit(client, *, position_id, session_id: str = "", claim_token: str = "", name="Ján"):
    response = client.post(
        f"/api/{SLUG}/applicants",
        data={
            "position_id": str(position_id),
            "session_id": session_id,
            "claim_token": claim_token,
            "first_name": name,
            "last_name": "Novák",
            "phone": "+421900000000",
            "email": f"{name.lower()}@example.sk",
        },
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


def chat_of(db_session_factory, applicant_id) -> list[str]:
    async def go():
        async with db_session_factory() as session:
            rows = await session.scalars(
                select(ChatMessage.content).where(ChatMessage.applicant_id == applicant_id)
            )
            return list(rows)

    return run(go())


def seed_position(seed):
    company = make_company(slug=SLUG)
    position = make_position(company_id=company.id)
    seed(company, position)
    return position


def test_owner_who_chatted_gets_the_chat_attached(client, seed, db_session_factory):
    position = seed_position(seed)
    chat = start_chat(client, position.id)
    say(client, chat, SECRET)

    applicant_id = submit(
        client,
        position_id=position.id,
        session_id=chat["session_id"],
        claim_token=chat["claim_token"],
    )

    assert SECRET in chat_of(db_session_factory, applicant_id)


def test_attacker_with_a_leaked_in_flight_session_id_does_not_get_the_chat(
    client, seed, db_session_factory
):
    """Presne útok z re-testu: tá istá pozícia, obeť ešte neodoslala prihlášku."""
    position = seed_position(seed)
    victim = start_chat(client, position.id)
    say(client, victim, SECRET)

    attacker = submit(
        client, position_id=position.id, session_id=victim["session_id"], name="Útočník"
    )

    assert chat_of(db_session_factory, attacker) == []

    # Obeť po útoku normálne odošle a chat dostane ona.
    owner = submit(
        client,
        position_id=position.id,
        session_id=victim["session_id"],
        claim_token=victim["claim_token"],
    )
    assert SECRET in chat_of(db_session_factory, owner)


def test_attacker_with_own_token_cannot_claim_someone_elses_session(
    client, seed, db_session_factory
):
    """Platný token jednej session neotvára inú session."""
    position = seed_position(seed)
    victim = start_chat(client, position.id)
    say(client, victim, SECRET)
    own = start_chat(client, position.id)

    attacker = submit(
        client,
        position_id=position.id,
        session_id=victim["session_id"],
        claim_token=own["claim_token"],
        name="Útočník",
    )

    assert SECRET not in chat_of(db_session_factory, attacker)


def test_chat_is_attached_only_once(client, seed, db_session_factory):
    position = seed_position(seed)
    chat = start_chat(client, position.id)
    say(client, chat, SECRET)

    first = submit(
        client, position_id=position.id,
        session_id=chat["session_id"], claim_token=chat["claim_token"],
    )
    second = submit(
        client, position_id=position.id,
        session_id=chat["session_id"], claim_token=chat["claim_token"], name="Peter",
    )

    assert SECRET in chat_of(db_session_factory, first)
    assert chat_of(db_session_factory, second) == []


def test_chat_of_another_position_is_not_attached(client, seed, db_session_factory):
    company = make_company(slug=SLUG)
    position = make_position(company_id=company.id)
    other_position = make_position(company_id=company.id, title="Čašník")
    seed(company, position, other_position)
    chat = start_chat(client, other_position.id)
    say(client, chat, SECRET)

    applicant_id = submit(
        client, position_id=position.id,
        session_id=chat["session_id"], claim_token=chat["claim_token"],
    )

    assert chat_of(db_session_factory, applicant_id) == []


def test_application_without_chat_is_accepted(client, seed):
    position = seed_position(seed)

    submit(client, position_id=position.id)
