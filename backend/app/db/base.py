from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def utcnow() -> datetime:
    """Aktuálny čas v UTC, vrátane časovej zóny.

    Časové stĺpce sú v DB `TIMESTAMP WITH TIME ZONE`. Naivný `datetime.utcnow()`
    by Postgres vyhodnotil v časovej zóne session, takže na serveri, ktorý nemá
    UTC, by sa všetky uložené časy posunuli. Preto sa píše vždy s zónou.
    """
    return datetime.now(timezone.utc)

engine = create_async_engine(settings.database_url, echo=settings.sql_echo and settings.env != "production",
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
