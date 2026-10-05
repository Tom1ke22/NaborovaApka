"""Kontrola, že databáza je na najnovšej migrácii, ešte pred prvým requestom.

V Dockeri spúšťa `alembic upgrade head` entrypoint. Mimo neho (uvicorn
z terminálu, iný hosting) to nikto nestráži a appka so starou schémou
naštartuje „v poriadku" — a potom vracia 500 na UndefinedColumnError pri
prvom dotaze na nový stĺpec. Lepšie je nenaštartovať vôbec s jasnou správou.
"""

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_DIR = Path(__file__).resolve().parents[2]


class DatabaseNotMigrated(RuntimeError):
    pass


def _head_revision() -> str | None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()


async def ensure_database_at_head(database_url: str) -> None:
    """Vyhoď DatabaseNotMigrated, keď DB nie je na head revízii.

    Vlastný engine bez poolu: spojenie sa po kontrole zavrie a neostane
    naviazané na event loop štartu.
    """
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            current = await conn.run_sync(
                lambda sync_conn: MigrationContext.configure(sync_conn).get_current_revision()
            )
    finally:
        await engine.dispose()

    head = _head_revision()
    if current != head:
        raise DatabaseNotMigrated(
            f"Databáza je na revízii {current!r}, kód očakáva {head!r}. "
            "Spusti `alembic upgrade head` (v adresári backend/) a appku znova."
        )
