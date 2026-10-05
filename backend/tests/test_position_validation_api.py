"""Validácia pozície v admine (M1, M2, M6).

Neplatný vstup musí skončiť 422 s vysvetlením, nie 500 z databázy, a API
musí vrátiť presne to, čo sa uložilo.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.position import Position
from tests.conftest import make_admin, make_company

PASSWORD = "TajneHeslo123"


def setup(client, seed) -> dict:
    company = make_company(slug="testovacia-firma")
    seed(company, make_admin(company_id=company.id, password=PASSWORD))
    token = client.post(
        "/api/auth/login", json={"email": "admin@firma.sk", "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def body(**overrides) -> dict:
    data = {
        "title": "Kuchár",
        "work_area": "Gastro",
        "location": "Košice",
        "contract_type": "uricity_cas",
    }
    data.update(overrides)
    return data


def create(client, headers, **overrides):
    return client.post("/api/admin/positions", json=body(**overrides), headers=headers)


@pytest.mark.parametrize(
    "overrides",
    [
        {"open_slots": -1},
        {"open_slots": 0},
        {"open_slots": 2**31},              # mimo Integer v DB → bolo 500
        {"salary_amount": -100},
        {"salary_amount": "100000000"},     # mimo Numeric(10,2) → bolo 500
        {"vacation_days": -5},
        {"title": "x" * 256},               # mimo String(255) → bolo 500
        {"title": "   "},                   # prázdny názov prešiel
        {"title": ""},
        {"location": "  "},
        {"working_hours": "x" * 101},
        {"start_date": "9999-12-31"},
        {"start_date": "1900-01-01"},
        {"requirements": {"experience_years": -1}},
    ],
    ids=lambda o: next(iter(o)) + "=" + str(next(iter(o.values())))[:20],
)
def test_invalid_position_is_422_not_500(client, seed, overrides):
    headers = setup(client, seed)

    response = create(client, headers, **overrides)

    assert response.status_code == 422, response.text


def test_text_fields_are_trimmed(client, seed):
    headers = setup(client, seed)

    saved = create(client, headers, title="  Kuchár  ", description="   ").json()

    assert saved["title"] == "Kuchár"
    assert saved["description"] is None


def test_update_cannot_null_a_required_field(client, seed):
    headers = setup(client, seed)
    position_id = create(client, headers).json()["id"]

    response = client.put(
        f"/api/admin/positions/{position_id}", json={"title": None}, headers=headers
    )

    assert response.status_code == 422


def test_update_respects_the_same_bounds(client, seed):
    headers = setup(client, seed)
    position_id = create(client, headers).json()["id"]

    response = client.put(
        f"/api/admin/positions/{position_id}", json={"open_slots": -3}, headers=headers
    )

    assert response.status_code == 422


def test_reasonable_start_date_is_accepted(client, seed):
    headers = setup(client, seed)
    start = (date.today() + timedelta(days=30)).isoformat()

    response = create(client, headers, start_date=start)

    assert response.status_code == 201
    assert response.json()["start_date"] == start


def test_create_returns_the_salary_that_was_stored(client, seed, fetch):
    """M2: POST vracal 1234.567, DB mala 1234.57."""
    headers = setup(client, seed)

    response = create(client, headers, salary_amount="1234.567")

    assert response.status_code == 201
    returned = Decimal(str(response.json()["salary_amount"]))
    stored = fetch(Position, __import__("uuid").UUID(response.json()["id"])).salary_amount
    assert returned == Decimal("1234.57")
    assert returned == stored


def test_update_returns_the_salary_that_was_stored(client, seed):
    headers = setup(client, seed)
    position_id = create(client, headers).json()["id"]

    response = client.put(
        f"/api/admin/positions/{position_id}",
        json={"salary_amount": "999.999"},
        headers=headers,
    )

    assert response.status_code == 200
    assert Decimal(str(response.json()["salary_amount"])) == Decimal("1000.00")
    reread = client.get("/api/admin/positions", headers=headers).json()[0]
    assert Decimal(str(reread["salary_amount"])) == Decimal("1000.00")
