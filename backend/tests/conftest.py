"""Spoločné nastavenie testov.

`app.core.config` vytvára `Settings()` hneď pri importe, takže povinné
premenné musia existovať skôr, než ktorýkoľvek test naimportuje appku.
AI tu držíme vypnutú, aby žiaden test omylom nevolal skutočné API.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("AI_ENABLED", "false")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("ENV", "test")

import asyncio  # noqa: E402
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
