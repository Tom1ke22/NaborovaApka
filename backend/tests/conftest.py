"""Spoločné nastavenie testov.

`app.core.config` vytvára `Settings()` hneď pri importe, takže povinné
premenné musia existovať skôr, než ktorýkoľvek test naimportuje appku.
AI tu držíme vypnutú, aby žiaden test omylom nevolal skutočné API.

Testy sú dvoch druhov:

- Jednotkové — bežia vždy, nič nepotrebujú.
- Integračné (fixture `client`) — potrebujú PostgreSQL, lebo modely používajú
  typy JSONB a UUID, ktoré sqlite nemá. Keď databáza nie je dostupná, tieto
  testy sa preskočia, nie zlyhajú. Adresu vieš prepísať cez TEST_DATABASE_URL.
"""

import os

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/recruitment_test",
)

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("AI_ENABLED", "false")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("ENV", "test")

import asyncio  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402


def run(coro) -> Any:
    """Spusti korutínu v teste. Nahrádza pytest-asyncio, nech nepribúda závislosť."""
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _reset_ai_client():
    """Po každom teste zahoď uloženého Gemini klienta."""
    from app.core.ai.client import reset_client

    reset_client()
    yield
    reset_client()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Limity sú v pamäti procesu, takže by presakovali medzi testami."""
    from app.api.v1.endpoints.chat import _session_limiter
    from app.core.ai import budget
    from app.core.limiter import limiter

    def clear() -> None:
        limiter.reset()
        _session_limiter.reset()
        budget.reset()

    clear()
    yield
    clear()


# --------------------------------------------------------------------------- #
# Integračné testy nad skutočnou databázou
# --------------------------------------------------------------------------- #

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config():
    """Alembic config namierený na testovaciu databázu.

    URL si `alembic/env.py` berie zo `settings.database_url`, a tá je vyššie
    prepnutá na TEST_DATABASE_URL, takže sa tu nemusí nastavovať.
    """
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


@pytest.fixture(scope="session")
def db_engine():
    """Engine nad testovacou databázou. Preskočí testy, keď nie je dostupná.

    Schému staviame `alembic upgrade head`, nie `Base.metadata.create_all`.
    Rozdiel je dôležitý: create_all stavia tabuľky z modelov, takže by nikdy
    neodhalil, že migrácia na nový stĺpec chýba — a presne to sa už raz stalo
    (login vracal 500 na UndefinedColumnError, pretože DB bola na 0005).
    Takto testy bežia nad tou istou schémou, akú dostane produkcia.

    NullPool preto, že TestClient si pre každý test otvára vlastný event loop a
    spojenia asyncpg sa medzi loopmi prenášať nedajú.
    """
    from alembic import command
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    import app.main  # noqa: F401  — naimportuje všetky modely do Base.metadata

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    async def wipe() -> None:
        # Od nuly, aby migrácie prebehli celé. Beží to výhradne nad
        # TEST_DATABASE_URL, nie nad vývojovou databázou.
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))

    try:
        run(wipe())
    except Exception as exc:  # noqa: BLE001
        run(engine.dispose())
        pytest.skip(
            "Testovacia databáza nie je dostupná, integračné testy sa preskakujú "
            f"({type(exc).__name__}). Spusti PostgreSQL alebo nastav TEST_DATABASE_URL.",
            allow_module_level=True,
        )

    command.upgrade(alembic_config(), "head")

    yield engine
    run(engine.dispose())


@pytest.fixture
def db_session_factory(db_engine, monkeypatch):
    """Čistá databáza a session factory nasmerovaná na testovací engine."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.base import Base

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)

    async def truncate() -> None:
        async with db_engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))

    run(truncate())

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    # `get_db` čita AsyncSessionLocal z modulu pri každom volaní, chat endpoint
    # a AI hodnotenie si ju naimportovali priamo — preto všetky miesta.
    monkeypatch.setattr("app.db.base.AsyncSessionLocal", factory)
    monkeypatch.setattr("app.api.v1.endpoints.chat.AsyncSessionLocal", factory)
    monkeypatch.setattr("app.core.ai.evaluate.AsyncSessionLocal", factory)

    return factory


@pytest.fixture
def client(db_session_factory):
    """HTTP klient nad appkou so skutočnou databázou."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed(db_session_factory):
    """Pomocník na vkladanie dát priamo do DB."""

    def insert(*objects) -> None:
        async def go() -> None:
            async with db_session_factory() as session:
                session.add_all(objects)
                await session.commit()

        run(go())

    return insert


@pytest.fixture
def fetch(db_session_factory):
    """Pomocník na načítanie riadku z DB podľa primárneho kľúča."""

    def get(model, pk):
        async def go():
            async with db_session_factory() as session:
                return await session.get(model, pk)

        return run(go())

    return get


def make_company(*, slug: str, is_active: bool = True):
    from app.models.company import Company

    return Company(
        id=uuid.uuid4(), name=f"Firma {slug}", slug=slug, is_active=is_active
    )


def make_position(*, company_id, title: str = "Kuchár"):
    from app.models.position import Position, PositionStatusEnum

    return Position(
        id=uuid.uuid4(),
        company_id=company_id,
        title=title,
        work_area="Gastro",
        location="Košice",
        contract_type="neuricity_cas",
        status=PositionStatusEnum.active,
    )


def make_admin(*, company_id, email: str = "admin@firma.sk", password: str = "TajneHeslo123"):
    from app.core.security import hash_password
    from app.models.admin import AdminUser

    return AdminUser(
        id=uuid.uuid4(),
        company_id=company_id,
        email=email,
        password_hash=hash_password(password),
        role="recruiter",
    )


class MemoryStorage:
    """Úložisko CV v pamäti. Nahrádza disk (/app/uploads) aj GCS v testoch."""

    def __init__(self) -> None:
        from datetime import datetime, timezone

        self.files: dict[str, bytes] = {}
        self.modified: dict[str, "datetime"] = {}
        self._now = lambda: datetime.now(timezone.utc)

    async def save(self, data: bytes, filename: str) -> str:
        path = f"mem/cvs/{filename}"
        self.files[path] = data
        self.modified[path] = self._now()
        return path

    async def load(self, storage_path: str) -> bytes | None:
        return self.files.get(storage_path)

    async def exists(self, storage_path: str) -> bool:
        return storage_path in self.files

    async def delete(self, storage_path: str) -> None:
        self.files.pop(storage_path, None)
        self.modified.pop(storage_path, None)

    async def list_files(self):
        from app.core.storage import StoredFile

        return [StoredFile(path=p, modified_at=self.modified[p]) for p in self.files]


@pytest.fixture
def memory_storage(monkeypatch) -> MemoryStorage:
    storage = MemoryStorage()
    for module in (
        "app.api.v1.endpoints.applicants_public",
        "app.api.v1.endpoints.admin_applicants",
        "app.core.ai.evaluate",
    ):
        monkeypatch.setattr(f"{module}.get_storage", lambda: storage)
    return storage


def make_docx() -> bytes:
    """Najmenší ZIP, ktorý vyzerá ako DOCX (má word/document.xml)."""
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()
