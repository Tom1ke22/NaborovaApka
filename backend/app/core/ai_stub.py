import asyncio
from collections.abc import AsyncGenerator

from app.models.position import Position


async def generate_response(
    position: Position,
    history: list[dict],
    user_message: str,
    applicant_name: str,
) -> AsyncGenerator[str, None]:
    """Stub AI — replace with Totti integration."""
    response = (
        f"Ďakujem za vašu správu, {applicant_name}. "
        f"Pozícia {position.title} je stále otvorená"
        + (f" v lokalite {position.location}" if position.location else "")
        + ". Totto AI bude čoskoro integrovaný a bude vedieť odpovedať na vaše "
        "konkrétne otázky. Ak máte záujem o túto pozíciu, kliknite na tlačidlo "
        "'Mám záujem'."
    )
    for word in response.split(" "):
        yield word + " "
        await asyncio.sleep(0.04)


# Totto integration interface — implement this function when Totti is ready.
# Expected signature:
#   async def generate_response(position, history, user_message, applicant_name)
#   -> AsyncGenerator[str, None]  (yield text chunks)
