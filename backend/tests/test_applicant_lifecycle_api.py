"""Prihláška od odoslania po výmaz (M5, M7, M8, M9, M11, M12) a chat na
uzavretej pozícii (M10).
"""

import uuid
from datetime import timedelta

import pytest

from app.models.applicant import Applicant
from app.models.chat import ChatMessage, ChatSession
from tests.conftest import make_admin, make_company, make_docx, make_position, run

SLUG = "testovacia-firma"
PASSWORD = "TajneHeslo123"
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def setup(client, seed):
    company = make_company(slug=SLUG)
    position = make_position(company_id=company.id)
    seed(company, position, make_admin(company_id=company.id, password=PASSWORD))
    token = client.post(
        "/api/auth/login", json={"email": "admin@firma.sk", "password": PASSWORD}
    ).json()["access_token"]
    return company, position, {"Authorization": f"Bearer {token}"}


def submit(client, position_id, *, cv=None, **fields):
    data = {
        "position_id": str(position_id),
        "first_name": "Ján",
        "last_name": "Novák",
        "phone": "+421 900 000 000",
        "email": "jan@example.sk",
    }
    data.update(fields)
    files = {"cv": cv} if cv else None
    return client.post(f"/api/{SLUG}/applicants", data=data, files=files)


# --------------------------------------------------------------------------- #
# M5 — údaje uchádzača
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "fields",
    [
        {"email": "nie-je-email"},
        {"email": "jan@"},
        {"first_name": "x" * 300},          # bolo 500 (String(100))
        {"last_name": "x" * 101},
        {"first_name": "   "},
        {"phone": "123"},
        {"phone": "+421 900\r\n000 000"},
        {"phone": "9" * 31},
    ],
    ids=lambda f: next(iter(f)),
)
def test_invalid_applicant_data_is_422(client, seed, fields):
    _, position, _ = setup(client, seed)

    response = submit(client, position.id, **fields)

    assert response.status_code == 422, response.text


def test_names_and_email_are_normalized(client, seed, fetch):
    _, position, _ = setup(client, seed)

    response = submit(
        client, position.id, first_name="  Ján   Peter ", email="  Jan.Novak@Example.SK "
    )

    assert response.status_code == 201
    stored = fetch(Applicant, uuid.UUID(response.json()["id"]))
    assert stored.first_name == "Ján Peter"
    assert stored.email == "jan.novak@example.sk"


def test_crlf_in_name_is_never_stored(client, seed, fetch):
    _, position, _ = setup(client, seed)

    response = submit(client, position.id, last_name="Novák\r\nBcc: x@y.sk\t")

    assert response.status_code == 201
    stored = fetch(Applicant, uuid.UUID(response.json()["id"])).last_name
    assert "\r" not in stored and "\n" not in stored and "\t" not in stored


# --------------------------------------------------------------------------- #
# M9 — typ CV podľa obsahu
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "name, content",
    [
        ("cv.pdf", b"MZ\x90\x00 tu je exe"),
        ("cv.pdf", b"<html><script>alert(1)</script></html>"),
        ("cv.docx", b"PK\x03\x04 rozbity zip"),
        ("cv.docx", PDF),                    # PDF s príponou .docx
        ("cv.pdf", make_docx()),             # DOCX s príponou .pdf
    ],
    ids=["exe", "html", "broken-zip", "pdf-as-docx", "docx-as-pdf"],
)
def test_cv_with_fake_extension_is_rejected(client, seed, memory_storage, name, content):
    _, position, _ = setup(client, seed)

    response = submit(client, position.id, cv=(name, content, "application/octet-stream"))

    assert response.status_code == 400
    assert memory_storage.files == {}


@pytest.mark.parametrize("name, content", [("cv.pdf", PDF), ("cv.docx", make_docx())])
def test_real_pdf_and_docx_are_accepted(client, seed, memory_storage, name, content):
    _, position, _ = setup(client, seed)

    response = submit(client, position.id, cv=(name, content, "application/octet-stream"))

    assert response.status_code == 201
    assert len(memory_storage.files) == 1


# --------------------------------------------------------------------------- #
# M12 — opakované prihlášky
# --------------------------------------------------------------------------- #

def test_repeated_application_is_flagged_not_rejected(client, seed):
    _, position, headers = setup(client, seed)
    first = submit(client, position.id, email="jan@example.sk").json()["id"]
    second = submit(client, position.id, email="JAN@example.sk").json()["id"]
    other = submit(client, position.id, email="eva@example.sk").json()["id"]

    rows = {r["id"]: r for r in client.get("/api/admin/applicants", headers=headers).json()}

    assert rows[first]["other_applications"] == 1
    assert rows[second]["other_applications"] == 1
    assert rows[other]["other_applications"] == 0
    detail = client.get(f"/api/admin/applicants/{first}", headers=headers).json()
    assert detail["other_applications"] == 1


# --------------------------------------------------------------------------- #
# M7 — GDPR výmaz
# --------------------------------------------------------------------------- #

def test_delete_removes_applicant_chat_and_cv(
    client, seed, memory_storage, db_session_factory
):
    from sqlalchemy import select

    _, position, headers = setup(client, seed)
    chat = client.post(
        f"/api/{SLUG}/chat/start", json={"position_id": str(position.id)}
    ).json()
    applicant_id = submit(
        client, position.id, cv=("cv.pdf", PDF, "application/pdf"),
        session_id=chat["session_id"], claim_token=chat["claim_token"],
    ).json()["id"]
    assert len(memory_storage.files) == 1

    response = client.delete(f"/api/admin/applicants/{applicant_id}", headers=headers)

    assert response.status_code == 204
    assert memory_storage.files == {}
    assert client.get(f"/api/admin/applicants/{applicant_id}", headers=headers).status_code == 404

    async def leftovers():
        async with db_session_factory() as session:
            messages = (await session.scalars(
                select(ChatMessage).where(ChatMessage.applicant_session_id == chat["session_id"])
            )).all()
            sessions = (await session.scalars(
                select(ChatSession).where(ChatSession.id == chat["session_id"])
            )).all()
            return messages, sessions

    messages, sessions = run(leftovers())
    assert messages == []
    assert sessions == []


def test_delete_needs_login_and_own_company(client, seed):
    _, position, headers = setup(client, seed)
    applicant_id = submit(client, position.id).json()["id"]

    other = make_company(slug="ina-firma")
    seed(other, make_admin(company_id=other.id, email="ina@firma.sk", password=PASSWORD))
    foreign = client.post(
        "/api/auth/login", json={"email": "ina@firma.sk", "password": PASSWORD}
    ).json()["access_token"]

    assert client.delete(f"/api/admin/applicants/{applicant_id}").status_code in (401, 403)
    assert client.delete(
        f"/api/admin/applicants/{applicant_id}",
        headers={"Authorization": f"Bearer {foreign}"},
    ).status_code == 404
    assert client.get(f"/api/admin/applicants/{applicant_id}", headers=headers).status_code == 200


# --------------------------------------------------------------------------- #
# M8 — úklid osirelých CV
# --------------------------------------------------------------------------- #

def test_cleanup_removes_only_old_unreferenced_files(
    client, seed, memory_storage, db_session_factory
):
    from app.core.cv_cleanup import MIN_ORPHAN_AGE, delete_orphan_cvs

    _, position, _ = setup(client, seed)
    submit(client, position.id, cv=("cv.pdf", PDF, "application/pdf"))
    (kept,) = memory_storage.files

    old = memory_storage._now() - MIN_ORPHAN_AGE - timedelta(minutes=5)
    for path, age in (("mem/cvs/sirota.pdf", old), ("mem/cvs/cerstva.pdf", None)):
        memory_storage.files[path] = PDF
        memory_storage.modified[path] = age or memory_storage._now()

    async def go(dry_run):
        async with db_session_factory() as db:
            return await delete_orphan_cvs(db, memory_storage, dry_run=dry_run)

    dry = run(go(True))
    assert dry.deleted == ["mem/cvs/sirota.pdf"]
    assert "mem/cvs/sirota.pdf" in memory_storage.files

    result = run(go(False))
    assert result.deleted == ["mem/cvs/sirota.pdf"]
    assert result.kept_recent == 1
    assert set(memory_storage.files) == {kept, "mem/cvs/cerstva.pdf"}


# --------------------------------------------------------------------------- #
# M11 — chýbajúci súbor CV
# --------------------------------------------------------------------------- #

def test_missing_cv_file_says_so_instead_of_try_again(client, seed, memory_storage):
    _, position, headers = setup(client, seed)
    applicant_id = submit(
        client, position.id, cv=("cv.pdf", PDF, "application/pdf")
    ).json()["id"]
    memory_storage.files.clear()

    response = client.get(f"/api/admin/applicants/{applicant_id}/cv", headers=headers)

    assert response.status_code == 410
    assert "nepomôže" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# M10 — chat na pozícii uzavretej počas rozhovoru
# --------------------------------------------------------------------------- #

def test_chat_ends_when_position_is_archived_mid_conversation(client, seed):
    _, position, headers = setup(client, seed)
    chat = client.post(
        f"/api/{SLUG}/chat/start", json={"position_id": str(position.id)}
    ).json()

    def say():
        return client.post(
            f"/api/{SLUG}/chat/stream",
            json={
                "session_id": chat["session_id"],
                "claim_token": chat["claim_token"],
                "message": "Aká je mzda?",
            },
        )

    assert say().status_code == 200

    assert client.delete(f"/api/admin/positions/{position.id}", headers=headers).status_code == 204

    response = say()
    assert response.status_code == 410
    assert "uzavretá" in response.json()["detail"]
