"""Testy prihlásenia, odhlásenia a overovania tokenu nad skutočnou databázou.

Token je JWT bez stavu, takže sa nedá „zmazať". Overujeme preto, že sa pri
každom requeste pozrieme do DB a token padne, keď admin zmizol, keď sa odhlásil,
keď si zmenil heslo alebo keď jeho firmu niekto deaktivoval.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update

from tests.conftest import make_admin, make_company, make_position, run

from app.api.v1.endpoints.auth import LOCKOUT_MINUTES, MAX_FAILED_LOGINS
from app.core.security import create_access_token

PASSWORD = "TajneHeslo123"

# Endpoint, na ktorom overujeme platnosť tokenu. Vracia dáta firmy, takže je to
# presne to miesto, kde by neplatný token spôsobil únik osobných údajov.
PROTECTED = "/api/admin/positions"


def login(client, email: str = "admin@firma.sk", password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def setup_admin(seed, *, slug: str = "testovacia-firma", is_active: bool = True):
    company = make_company(slug=slug, is_active=is_active)
    admin = make_admin(company_id=company.id, password=PASSWORD)
    seed(company, admin)
    return company, admin


def execute(db_session_factory, statement) -> None:
    async def go() -> None:
        async with db_session_factory() as session:
            await session.execute(statement)
            await session.commit()

    run(go())


# --------------------------------------------------------------------------- #
# Prihlásenie
# --------------------------------------------------------------------------- #

def test_login_returns_a_working_token(client, seed):
    setup_admin(seed)

    token = login(client).json()["access_token"]

    assert client.get(PROTECTED, headers=auth(token)).status_code == 200


def test_login_with_a_wrong_password_is_401(client, seed):
    setup_admin(seed)
    assert login(client, password="zle-heslo").status_code == 401


def test_login_with_an_unknown_email_is_401_not_500(client, seed):
    """Neznámy email nesmie skončiť chybou servera.

    Regresia: `select(AdminUser)` padne na UndefinedColumnError, keď databáza
    nemá stĺpce z migrácie 0006 — a prejaví sa to ako 500 na každom prihlásení.
    """
    setup_admin(seed)

    response = login(client, email="nikto@firma.sk", password="cokolvek")

    assert response.status_code == 401


def test_unknown_email_and_wrong_password_are_indistinguishable(client, seed):
    """Status aj telo musia byť identické, inak sa dajú enumerovať účty."""
    setup_admin(seed)

    unknown = login(client, email="nikto@firma.sk", password="cokolvek")
    wrong = login(client, password="zle-heslo")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_unknown_email_takes_about_as_long_as_a_wrong_password(client, seed):
    """Bez overenia proti zahodenému hashu je neznámy email citeľne rýchlejší.

    Hranica je voľná zámerne — meriame, že sa bcrypt počíta v oboch cestách,
    nie presný čas, ktorý na CI kolíše.
    """
    import time

    setup_admin(seed)

    def duration(**kwargs) -> float:
        # Prvé volanie zahŕňa výpočet zahodeného hashu, to nemeriame.
        login(client, **kwargs)
        start = time.perf_counter()
        login(client, **kwargs)
        return time.perf_counter() - start

    unknown = duration(email="nikto@firma.sk", password="cokolvek")
    wrong = duration(password="zle-heslo")

    assert unknown > wrong / 2, (
        f"neznámy email {unknown * 1000:.0f} ms vs zlé heslo {wrong * 1000:.0f} ms — "
        "rozdiel prezrádza, ktoré emaily v systéme sú"
    )


def test_unknown_email_creates_no_lockout_state(client, seed, db_session_factory):
    """Neexistujúci email nesmie nikde nič evidovať ani zamykať.

    Inak by sa dalo cez cudzí email zamknúť účet, ktorý ešte len vznikne.
    """
    from sqlalchemy import func, select as sa_select

    from app.models.admin import AdminUser

    setup_admin(seed)

    for _ in range(MAX_FAILED_LOGINS + 3):
        assert login(client, email="nikto@firma.sk", password="cokolvek").status_code == 401

    async def totals():
        async with db_session_factory() as session:
            return (
                await session.scalar(sa_select(func.count(AdminUser.id))),
                await session.scalar(sa_select(func.sum(AdminUser.failed_login_count))),
                await session.scalar(
                    sa_select(func.count(AdminUser.id)).where(AdminUser.locked_until.is_not(None))
                ),
            )

    rows, failed, locked = run(totals())
    assert rows == 1          # nevznikol žiadny nový riadok
    assert failed == 0        # a existujúcemu adminovi sa nič nepripísalo
    assert locked == 0

    # Správne heslo existujúceho admina stále funguje.
    assert login(client).status_code == 200


def test_login_of_a_deactivated_company_is_rejected(client, seed):
    setup_admin(seed, is_active=False)
    assert login(client).status_code == 401


# --------------------------------------------------------------------------- #
# Overenie tokenu proti DB
# --------------------------------------------------------------------------- #

def test_token_of_a_deleted_admin_stops_working(client, seed, db_session_factory):
    """Zmazaný admin nesmie mať prístup až do expirácie tokenu."""
    from app.models.admin import AdminUser

    _, admin = setup_admin(seed)
    token = login(client).json()["access_token"]
    assert client.get(PROTECTED, headers=auth(token)).status_code == 200

    execute(db_session_factory, delete(AdminUser).where(AdminUser.id == admin.id))

    assert client.get(PROTECTED, headers=auth(token)).status_code == 401


def test_token_stops_working_when_the_company_is_deactivated(client, seed, db_session_factory):
    """Deaktivovaná firma nesmie čítať osobné údaje uchádzačov."""
    from app.models.company import Company

    company, _ = setup_admin(seed)
    token = login(client).json()["access_token"]
    assert client.get(PROTECTED, headers=auth(token)).status_code == 200

    execute(
        db_session_factory,
        update(Company).where(Company.id == company.id).values(is_active=False),
    )

    assert client.get(PROTECTED, headers=auth(token)).status_code == 401


def test_deactivated_company_cannot_read_applicant_pii(client, seed, db_session_factory):
    """Toto je ten endpoint, kde by neplatný token znamenal únik osobných údajov."""
    import uuid as uuid_module

    from app.models.applicant import Applicant
    from app.models.company import Company

    company, _ = setup_admin(seed)
    position = make_position(company_id=company.id)
    seed(position)
    seed(
        Applicant(
            id=uuid_module.uuid4(),
            company_id=company.id,
            position_id=position.id,
            first_name="Janko",
            last_name="Hraško",
            phone="+421900000000",
            email="janko@example.com",
        )
    )

    token = login(client).json()["access_token"]
    assert "Hraško" in client.get("/api/admin/applicants", headers=auth(token)).text

    execute(
        db_session_factory,
        update(Company).where(Company.id == company.id).values(is_active=False),
    )

    response = client.get("/api/admin/applicants", headers=auth(token))
    assert response.status_code == 401
    assert "Hraško" not in response.text


def test_token_without_the_version_claim_is_rejected(client, seed):
    """Tokeny vydané pred zavedením generácií nesmú prejsť."""
    company, admin = setup_admin(seed)

    from jose import jwt

    from app.core.config import settings

    payload = {
        "sub": str(admin.id),
        "company_id": str(company.id),
        "role": "recruiter",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    legacy = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    assert client.get(PROTECTED, headers=auth(legacy)).status_code == 401


def test_token_with_a_foreign_company_id_is_rejected(client, seed):
    """company_id v tokene musí sedieť s riadkom admina v DB."""
    _, admin = setup_admin(seed)
    other = make_company(slug="ina-firma")
    seed(other)

    forged = create_access_token(
        user_id=str(admin.id),
        company_id=str(other.id),
        role="recruiter",
        token_version=0,
    )

    assert client.get(PROTECTED, headers=auth(forged)).status_code == 401


def test_token_of_an_unknown_admin_is_rejected(client, seed):
    company, _ = setup_admin(seed)

    forged = create_access_token(
        user_id=str(uuid.uuid4()),
        company_id=str(company.id),
        role="recruiter",
        token_version=0,
    )

    assert client.get(PROTECTED, headers=auth(forged)).status_code == 401


def test_admin_sees_only_their_own_companys_positions(client, seed):
    """Multi-tenancy: company_id ide z tokenu a riadku v DB, nikdy z URL."""
    company, _ = setup_admin(seed)
    other = make_company(slug="ina-firma")
    seed(other, make_position(company_id=other.id, title="Cudzia pozícia"))
    seed(make_position(company_id=company.id, title="Naša pozícia"))

    token = login(client).json()["access_token"]
    titles = [p["title"] for p in client.get(PROTECTED, headers=auth(token)).json()]

    assert titles == ["Naša pozícia"]


# --------------------------------------------------------------------------- #
# Odhlásenie
# --------------------------------------------------------------------------- #

def test_logout_invalidates_the_token(client, seed):
    setup_admin(seed)
    token = login(client).json()["access_token"]

    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 204
    assert client.get(PROTECTED, headers=auth(token)).status_code == 401


def test_logout_invalidates_tokens_on_all_devices(client, seed):
    setup_admin(seed)
    phone = login(client).json()["access_token"]
    laptop = login(client).json()["access_token"]

    client.post("/api/auth/logout", headers=auth(laptop))

    assert client.get(PROTECTED, headers=auth(phone)).status_code == 401


def test_login_after_logout_works_again(client, seed):
    setup_admin(seed)
    client.post("/api/auth/logout", headers=auth(login(client).json()["access_token"]))

    fresh = login(client).json()["access_token"]

    assert client.get(PROTECTED, headers=auth(fresh)).status_code == 200


def test_logout_without_a_token_is_rejected(client, seed):
    setup_admin(seed)
    # Chýbajúcu hlavičku Authorization odmieta HTTPBearer sám, a to s 403.
    # Platí to pre všetky admin endpointy, nielen pre logout.
    assert client.post("/api/auth/logout").status_code == 403


# --------------------------------------------------------------------------- #
# Zmena hesla
# --------------------------------------------------------------------------- #

def test_password_change_cuts_off_existing_sessions(client, seed):
    setup_admin(seed)
    phone = login(client).json()["access_token"]
    laptop = login(client).json()["access_token"]

    response = client.post(
        "/api/auth/password",
        headers=auth(laptop),
        json={"current_password": PASSWORD, "new_password": "NoveTajneHeslo456"},
    )

    assert response.status_code == 200
    # Staré tokeny padli — aj ten, ktorým prišiel request.
    assert client.get(PROTECTED, headers=auth(phone)).status_code == 401
    assert client.get(PROTECTED, headers=auth(laptop)).status_code == 401
    # Nový token z odpovede funguje, admin ostáva prihlásený na tomto zariadení.
    assert client.get(PROTECTED, headers=auth(response.json()["access_token"])).status_code == 200


def test_password_change_needs_the_current_password(client, seed):
    setup_admin(seed)
    token = login(client).json()["access_token"]

    response = client.post(
        "/api/auth/password",
        headers=auth(token),
        json={"current_password": "zle-heslo", "new_password": "NoveTajneHeslo456"},
    )

    assert response.status_code == 400
    assert client.get(PROTECTED, headers=auth(token)).status_code == 200


def test_the_new_password_is_the_one_that_works(client, seed):
    setup_admin(seed)
    token = login(client).json()["access_token"]
    client.post(
        "/api/auth/password",
        headers=auth(token),
        json={"current_password": PASSWORD, "new_password": "NoveTajneHeslo456"},
    )

    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="NoveTajneHeslo456").status_code == 200


# --------------------------------------------------------------------------- #
# Lockout a rate limit prihlasovania
# --------------------------------------------------------------------------- #

def test_account_locks_after_too_many_failed_logins(client, seed):
    setup_admin(seed)

    for attempt in range(MAX_FAILED_LOGINS):
        assert login(client, password="zle-heslo").status_code == 401, f"pokus {attempt + 1}"

    # Ďalší pokus sa už ani neoverí — účet je zamknutý.
    assert login(client, password="zle-heslo").status_code == 429
    # A nepomôže ani správne heslo.
    assert login(client).status_code == 429


def test_lock_expires(client, seed, db_session_factory):
    from app.models.admin import AdminUser

    _, admin = setup_admin(seed)
    for _ in range(MAX_FAILED_LOGINS):
        login(client, password="zle-heslo")
    assert login(client).status_code == 429

    # Posuň zámok do minulosti, akoby už prešlo LOCKOUT_MINUTES.
    execute(
        db_session_factory,
        update(AdminUser)
        .where(AdminUser.id == admin.id)
        .values(locked_until=datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_MINUTES)),
    )

    assert login(client).status_code == 200


def test_successful_login_clears_failed_attempts(client, seed, fetch):
    from app.models.admin import AdminUser

    _, admin = setup_admin(seed)
    for _ in range(MAX_FAILED_LOGINS - 1):
        login(client, password="zle-heslo")

    assert login(client).status_code == 200
    assert fetch(AdminUser, admin.id).failed_login_count == 0


def test_login_is_rate_limited_per_ip(client, seed):
    """Aj hádanie hesiel na rôzne účty z jednej IP musí naraziť na strop."""
    setup_admin(seed)

    statuses = [
        login(client, email=f"neznamy{i}@firma.sk", password="zle-heslo").status_code
        for i in range(12)
    ]

    assert 429 in statuses
