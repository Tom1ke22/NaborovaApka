"""Testy hraníc verejného API.

Dve veci, ktoré musia držať bez ohľadu na to, čo sa inde zmení:
- interné nastavenie AI (`ai_bot_instructions`, `ai_evaluation_notes`) sa nesmie
  dostať na verejné endpointy,
- verejné endpointy ukazujú len pozície firmy zo slugu a len aktívnych firiem.
"""

from tests.conftest import make_company, make_position

NOTES = "Nechceme nikoho z Košíc."
BOT_INSTRUCTIONS = "Zdôrazni nočné zmeny."


def seed_position(seed, *, slug: str = "testovacia-firma", is_active: bool = True):
    company = make_company(slug=slug, is_active=is_active)
    position = make_position(company_id=company.id)
    position.ai_evaluation_notes = NOTES
    position.ai_bot_instructions = BOT_INSTRUCTIONS
    seed(company, position)
    return company, position


def test_public_position_detail_hides_internal_ai_fields(client, seed):
    _, position = seed_position(seed)

    response = client.get(f"/api/testovacia-firma/positions/{position.id}")

    assert response.status_code == 200
    body = response.text
    assert NOTES not in body
    assert BOT_INSTRUCTIONS not in body
    assert "ai_evaluation_notes" not in response.json()
    assert "ai_bot_instructions" not in response.json()


def test_public_position_list_hides_internal_ai_fields(client, seed):
    seed_position(seed)

    response = client.get("/api/testovacia-firma/positions")

    assert response.status_code == 200
    assert NOTES not in response.text
    assert BOT_INSTRUCTIONS not in response.text


def test_public_list_shows_only_the_companys_own_positions(client, seed):
    seed_position(seed)
    other = make_company(slug="ina-firma")
    seed(other, make_position(company_id=other.id, title="Cudzia pozícia"))

    titles = [p["title"] for p in client.get("/api/testovacia-firma/positions").json()]

    assert titles == ["Kuchár"]


def test_position_of_another_company_is_not_reachable_through_a_foreign_slug(client, seed):
    _, position = seed_position(seed)
    seed(make_company(slug="ina-firma"))

    response = client.get(f"/api/ina-firma/positions/{position.id}")

    assert response.status_code == 404


def test_deactivated_company_is_not_public(client, seed):
    seed_position(seed, slug="vypnuta-firma", is_active=False)

    assert client.get("/api/vypnuta-firma/positions").status_code == 404
