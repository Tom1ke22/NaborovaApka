import json
import uuid
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ai.chat import generate_response
from app.core.limiter import WindowRateLimiter, limiter
from app.core.limits import (
    MAX_CHAT_HISTORY_FETCH,
    MAX_CHAT_MESSAGES_PER_SESSION_PER_MINUTE,
)
from app.core.security import hash_claim_token, new_claim_token, verify_claim_token
from app.db.base import AsyncSessionLocal, get_db
from app.models.chat import ChatMessage, ChatSession, MessageRoleEnum
from app.models.company import Company
from app.models.position import Position, PositionStatusEnum
from app.schemas.chat import ChatStartIn, ChatStartOut, ChatStreamIn

router = APIRouter(tags=["chat"])

# Limit na session. Limit na IP rieši dekorátor `limiter.limit`, ten však sám
# nestačí: jedna session za jednou IP je presne ten prípad, keď sa dá do
# nekonečna búchať na model, a naopak za NAT-om alebo mobilnou sieťou zdieľa
# jednu IP veľa uchádzačov.
_session_limiter = WindowRateLimiter(
    limit=MAX_CHAT_MESSAGES_PER_SESSION_PER_MINUTE,
    window_seconds=60.0,
)


POSITION_CLOSED = (
    "Táto pozícia bola medzitým uzavretá, preto už nie je možné pokračovať "
    "v rozhovore ani sa na ňu prihlásiť."
)


@dataclass(frozen=True)
class _SessionContext:
    """Overená session: komu patrí, na akú pozíciu a čo už bolo povedané."""

    company_id: uuid.UUID
    position_id: uuid.UUID
    position: Position | None
    history: list[dict]
    applicant_name: str


def _sse(payload: dict) -> str:
    """Zabaľ dáta do jedného SSE rámca.

    Obsah posielame ako JSON, nie ako holý text. Odpoveď modelu totiž bežne
    obsahuje nové riadky a tie by holý formát `data: <text>` rozsekali na
    viac rámcov a odpoveď by sa v prehliadači rozpadla.
    """
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _get_active_company(slug: str, db: AsyncSession) -> Company:
    result = await db.execute(
        select(Company).where(Company.slug == slug, Company.is_active == True)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firma nenájdená")
    return company


def _name_from_greeting(greeting: str) -> str:
    """Vytiahni meno uchádzača z úvodného pozdravu, ktorý zložil `chat_start`."""
    if "Dobrý deň, " in greeting and "!" in greeting:
        start = len("Dobrý deň, ")
        end = greeting.index("!")
        if end > start:
            return greeting[start:end]
    return "uchádzač"


async def _load_session(
    session_id: str, claim_token: str, company_id: uuid.UUID, db: AsyncSession
) -> _SessionContext:
    """Nájdi session a over, že patrí tejto firme a volajúcemu.

    Dotazy sú VŽDY filtrované aj na `company_id` firmy zo slugu v URL. Bez toho
    by sa session jednej firmy dala použiť pod slugom inej (alebo neexistujúcej)
    firmy a cudzí človek by si cez odpoveď modelu prečítal obsah konverzácie.

    Samotné `session_id` nestačí, musí sedieť aj claim token. Inak by ktokoľvek,
    komu `session_id` unikol, písal do cudzieho chatu a cez model ho čítal.
    Zlý token, iný slug aj neexistujúca session vyzerajú rovnako: 404.
    """
    chat_session = await db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.company_id == company_id
        )
    )
    if chat_session is None or not verify_claim_token(
        claim_token, chat_session.claim_token_hash
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relácia nenájdená")

    first = await db.scalar(
        select(ChatMessage)
        .where(
            ChatMessage.applicant_session_id == session_id,
            ChatMessage.company_id == company_id,
        )
        .order_by(ChatMessage.created_at)
        .limit(1)
    )
    if first is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relácia nenájdená")

    # Len posledných N správ. Session s tisíckami správ nesmie vytiahnuť celú
    # tabuľku do pamäti ani nafúknuť prompt.
    recent = (
        await db.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.applicant_session_id == session_id,
                ChatMessage.company_id == company_id,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(MAX_CHAT_HISTORY_FETCH)
        )
    ).all()

    position = await db.scalar(
        select(Position)
        .where(Position.id == first.position_id, Position.company_id == company_id)
        .options(selectinload(Position.requirements))
    )
    # Pozícia uzavretá počas rozhovoru: chat končí. Bot by inak ďalej lákal
    # na miesto, na ktoré sa už nedá prihlásiť (prihláška by vrátila 404).
    if position is None or position.status != PositionStatusEnum.active:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=POSITION_CLOSED)

    history = [
        {"role": msg.role.value, "content": msg.content} for msg in reversed(recent)
    ]

    return _SessionContext(
        company_id=company_id,
        position_id=first.position_id,
        position=position,
        history=history,
        applicant_name=_name_from_greeting(first.content)
        if first.role == MessageRoleEnum.assistant
        else "uchádzač",
    )


@router.post("/{slug}/chat/start", response_model=ChatStartOut)
@limiter.limit("20/minute")
async def chat_start(request: Request, slug: str, body: ChatStartIn, db: AsyncSession = Depends(get_db)):
    company = await _get_active_company(slug, db)

    result = await db.execute(
        select(Position).where(
            Position.id == body.position_id,
            Position.company_id == company.id,
            Position.status == PositionStatusEnum.active,
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pozícia nenájdená")

    session_id = str(uuid.uuid4())
    claim_token = new_claim_token()
    # Meno je nepovinné. Bez neho pozdravíme neutrálne — pozor na tvar
    # pozdravu, `chat_stream` si z neho meno spätne vyťahuje.
    name = (body.applicant_name or "").strip()
    greeting = (
        f"Dobrý deň, {name}! " if name else "Dobrý deň! "
    ) + (
        f"Som váš HR asistent pre pozíciu {position.title}. "
        "Rád odpovedám na vaše otázky o pracovných podmienkach, náplni práce "
        "alebo ďalších detailoch. Čo vás zaujíma?"
    )

    db.add(ChatSession(
        id=session_id,
        company_id=company.id,
        position_id=position.id,
        claim_token_hash=hash_claim_token(claim_token),
    ))
    db.add(ChatMessage(
        company_id=company.id,
        applicant_session_id=session_id,
        position_id=position.id,
        role=MessageRoleEnum.assistant,
        content=greeting,
    ))
    await db.commit()

    return ChatStartOut(session_id=session_id, claim_token=claim_token, greeting=greeting)


@router.post("/{slug}/chat/stream")
@limiter.limit("60/minute")
async def chat_stream(
    request: Request,
    slug: str,
    body: ChatStreamIn,
    db: AsyncSession = Depends(get_db),
):
    # Všetko overenie beží TU, nie v generátore. Keď sa chyba zistí až počas
    # streamu, odpoveď má status 200 a volajúci nemá ako rozoznať „nenájdené"
    # od platnej odpovede.
    company = await _get_active_company(slug, db)
    context = await _load_session(body.session_id, body.claim_token, company.id, db)

    if not _session_limiter.hit(body.session_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Priveľa správ za krátky čas. Skúste to, prosím, o minútu.",
        )

    async def generate():
        # Vlastná DB relácia: tá z requestu sa zatvorí hneď, ako sa začne
        # streamovať odpoveď.
        async with AsyncSessionLocal() as stream_db:
            stream_db.add(ChatMessage(
                company_id=context.company_id,
                applicant_session_id=body.session_id,
                position_id=context.position_id,
                role=MessageRoleEnum.user,
                content=body.message,
            ))
            await stream_db.commit()

            full_response = ""
            async for chunk in generate_response(
                context.position,
                context.history,
                body.message,
                context.applicant_name,
                requirements=context.position.requirements if context.position else None,
            ):
                full_response += chunk
                yield _sse({"t": chunk})

            yield _sse({"done": True})

            # Odpoveď ukladáme až po dostreamovaní, aby sa do histórie
            # dostalo presne to, čo uchádzač videl.
            if full_response.strip():
                stream_db.add(ChatMessage(
                    company_id=context.company_id,
                    applicant_session_id=body.session_id,
                    position_id=context.position_id,
                    role=MessageRoleEnum.assistant,
                    content=full_response.strip(),
                ))
                await stream_db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")
