"""Admin pohľad na uchádzačov: stav AI hodnotenia, stiahnutie CV, indexy, štart appky.

- Stav hodnotenia (pending / done / failed / skipped): bez neho admin nerozlíši
  „ešte beží" od „zlyhalo" a obnovuje stránku donekonečna.
- CV ide vždy cez autentifikovaný endpoint, nikdy cez podpísaný URL.
- Indexy na stĺpcoch, podľa ktorých admin filtruje.
- Appka so starou schémou DB nenaštartuje.
"""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.models.applicant import Applicant
from tests.conftest import make_admin, make_company, make_position, run

SLUG = "testovacia-firma"
PASSWORD = "TajneHeslo123"


@pytest.fixture
def ai_on(monkeypatch):
    """AI „zapnutá", ale model nahradený. Test si určí, čo extrakcia vráti."""
    from app.core.ai import evaluate as evaluate_module
    from app.core.config import Settings

    monkeypatch.setattr(Settings, "ai_available", property(lambda self: True))
    state = {"result": None}

    async def fake_extract(**kwargs):
        if isinstance(state["result"], Exception):
            raise state["result"]
        return state["result"]

    monkeypatch.setattr(evaluate_module, "extract_profile", fake_extract)
    return state


def a_profile():
    from app.core.ai.schemas import ExperienceFact, ExtractedProfile, Source

    return ExtractedProfile(experience=ExperienceFact(years=3, source=Source.cv), overall_fit=8)


def setup(client, seed):
    company = make_company(slug=SLUG)
    position = make_position(company_id=company.id)
    seed(company, position, make_admin(company_id=company.id, password=PASSWORD))
    token = client.post(
        "/api/auth/login", json={"email": "admin@firma.sk", "password": PASSWORD}
    ).json()["access_token"]
    return company, position, {"Authorization": f"Bearer {token}"}


def submit(client, position_id) -> str:
    response = client.post(
        f"/api/{SLUG}/applicants",
        data={
            "position_id": str(position_id),
            "first_name": "Ján",
            "last_name": "Novák",
            "phone": "+421900000000",
            "email": "jan@example.sk",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def detail(client, headers, applicant_id) -> dict:
    response = client.get(f"/api/admin/applicants/{applicant_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# H2 — stav AI hodnotenia
# --------------------------------------------------------------------------- #

def test_successful_evaluation_is_done(client, seed, ai_on):
    _, position, headers = setup(client, seed)
    ai_on["result"] = a_profile()

    applicant = detail(client, headers, submit(client, position.id))

    assert applicant["ai_status"] == "done"
    assert applicant["ai_score"] is not None


def test_model_without_answer_is_failed_not_pending(client, seed, ai_on):
    """Extrakcia vrátila None (timeout, zlá odpoveď) — nesmie ostať „Vyhodnocuje sa"."""
    _, position, headers = setup(client, seed)
    ai_on["result"] = None

    applicant = detail(client, headers, submit(client, position.id))

    assert applicant["ai_status"] == "failed"
    assert applicant["ai_score"] is None


def test_crash_during_evaluation_is_failed(client, seed, ai_on):
    _, position, headers = setup(client, seed)
    ai_on["result"] = RuntimeError("Gemini spadlo")

    applicant = detail(client, headers, submit(client, position.id))

    assert applicant["ai_status"] == "failed"


def test_disabled_ai_is_skipped_not_pending(client, seed):
    _, position, headers = setup(client, seed)

    applicant = detail(client, headers, submit(client, position.id))

    assert applicant["ai_status"] == "skipped"


def test_pending_that_hangs_too_long_is_shown_as_failed(client, seed, db_session_factory):
    """Proces zomrel uprostred hodnotenia, stav nikto neprepíše."""
    from app.core.limits import AI_EVALUATION_STALE_AFTER_SECONDS
    from app.db.base import utcnow

    company, position, headers = setup(client, seed)
    stuck = Applicant(
        id=uuid.uuid4(), company_id=company.id, position_id=position.id,
        first_name="Ján", last_name="Novák", phone="+421900000000", email="jan@example.sk",
        ai_status="pending",
        ai_status_changed_at=utcnow() - timedelta(seconds=AI_EVALUATION_STALE_AFTER_SECONDS + 60),
    )
    fresh = Applicant(
        id=uuid.uuid4(), company_id=company.id, position_id=position.id,
        first_name="Eva", last_name="Nová", phone="+421900000001", email="eva@example.sk",
        ai_status="pending",
    )
    seed(stuck, fresh)

    assert detail(client, headers, stuck.id)["ai_status"] == "failed"
    assert detail(client, headers, fresh.id)["ai_status"] == "pending"

    statuses = {
        row["id"]: row["ai_status"]
        for row in client.get("/api/admin/applicants", headers=headers).json()
    }
    assert statuses == {str(stuck.id): "failed", str(fresh.id): "pending"}


def test_retry_after_failure_ends_done(client, seed, ai_on):
    _, position, headers = setup(client, seed)
    ai_on["result"] = None
    applicant_id = submit(client, position.id)
    assert detail(client, headers, applicant_id)["ai_status"] == "failed"

    ai_on["result"] = a_profile()
    response = client.post(f"/api/admin/applicants/{applicant_id}/evaluate", headers=headers)

    assert response.status_code == 202
    assert detail(client, headers, applicant_id)["ai_status"] == "done"


# --------------------------------------------------------------------------- #
# H4 — CV len cez autentifikovaný endpoint
# --------------------------------------------------------------------------- #

class _FakeStorage:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    async def load(self, storage_path: str) -> bytes | None:
        return self.files.get(storage_path)

    async def exists(self, storage_path: str) -> bool:
        return storage_path in self.files


def seed_applicant_with_cv(seed, company, position, path="cvs/x.pdf") -> Applicant:
    applicant = Applicant(
        id=uuid.uuid4(), company_id=company.id, position_id=position.id,
        first_name="Ján", last_name="Novák", phone="+421900000000", email="jan@example.sk",
        cv_storage_path=path,
    )
    seed(applicant)
    return applicant


def test_cv_url_is_never_a_signed_storage_url(client, seed, monkeypatch):
    """Aj pri GCS: URL je náš endpoint, nie podpísaný odkaz platný bez prihlásenia."""
    from app.api.v1.endpoints import admin_applicants
    from app.core.config import settings

    monkeypatch.setattr(settings, "storage_backend", "gcs")
    monkeypatch.setattr(
        admin_applicants, "get_storage", lambda: _FakeStorage({"cvs/x.pdf": b"%PDF"})
    )
    company, position, headers = setup(client, seed)
    applicant = seed_applicant_with_cv(seed, company, position)

    url = client.get(f"/api/admin/applicants/{applicant.id}/cv", headers=headers).json()["url"]

    assert url == f"/api/admin/applicants/{applicant.id}/cv/download"


def test_cv_download_streams_through_backend_for_admin(client, seed, monkeypatch):
    from app.api.v1.endpoints import admin_applicants

    company, position, headers = setup(client, seed)
    applicant = seed_applicant_with_cv(seed, company, position)
    monkeypatch.setattr(
        admin_applicants, "get_storage", lambda: _FakeStorage({"cvs/x.pdf": b"%PDF-1.4 cv"})
    )

    response = client.get(f"/api/admin/applicants/{applicant.id}/cv/download", headers=headers)

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 cv"
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"


def test_cv_download_requires_login(client, seed, monkeypatch):
    from app.api.v1.endpoints import admin_applicants

    company, position, _ = setup(client, seed)
    applicant = seed_applicant_with_cv(seed, company, position)
    monkeypatch.setattr(
        admin_applicants, "get_storage", lambda: _FakeStorage({"cvs/x.pdf": b"%PDF"})
    )

    response = client.get(f"/api/admin/applicants/{applicant.id}/cv/download")

    assert response.status_code in (401, 403)


def test_storage_has_no_signed_url_api():
    from app.core.storage import GCSStorage, LocalStorage, StorageBackend

    for cls in (StorageBackend, LocalStorage, GCSStorage):
        assert not hasattr(cls, "generate_signed_url")


# --------------------------------------------------------------------------- #
# H3 — indexy
# --------------------------------------------------------------------------- #

def test_admin_query_columns_are_indexed(db_engine):
    async def indexes() -> set[tuple[str, str]]:
        async with db_engine.connect() as conn:
            rows = await conn.execute(
                text("SELECT tablename, indexdef FROM pg_indexes WHERE schemaname = 'public'")
            )
            return {(row[0], row[1]) for row in rows}

    defs = run(indexes())

    def indexed(table: str, columns: str) -> bool:
        return any(t == table and f"({columns})" in d for t, d in defs)

    assert indexed("applicants", "company_id, submitted_at")
    assert indexed("applicants", "position_id")
    assert indexed("applicants", "company_id, email")
    assert indexed("positions", "company_id, created_at")
    assert indexed("chat_messages", "applicant_id")


# --------------------------------------------------------------------------- #
# H5 — štart so starou schémou
# --------------------------------------------------------------------------- #

def test_startup_passes_when_database_is_at_head(db_engine):
    from app.core.config import settings
    from app.db.revision_check import ensure_database_at_head

    run(ensure_database_at_head(settings.database_url))


def test_app_refuses_to_start_on_an_outdated_database(db_engine, monkeypatch):
    from fastapi.testclient import TestClient

    from app.db import revision_check
    from app.main import app

    monkeypatch.setattr(revision_check, "_head_revision", lambda: "9999_novsia")

    with pytest.raises(revision_check.DatabaseNotMigrated, match="alembic upgrade head"):
        with TestClient(app):
            pass
