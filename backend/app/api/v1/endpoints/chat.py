import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_stub import generate_response
from app.core.limiter import limiter
from app.db.base import AsyncSessionLocal, get_db
from app.models.chat import ChatMessage, MessageRoleEnum
from app.models.company import Company
from app.models.position import Position, PositionStatusEnum
from app.schemas.chat import ChatStartIn, ChatStartOut, ChatStreamIn

router = APIRouter(tags=["chat"])


async def _get_active_company(slug: str, db: AsyncSession) -> Company:
    result = await db.execute(
        select(Company).where(Company.slug == slug, Company.is_active == True)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firma nenájdená")
    return company


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
    greeting = (
        f"Dobrý deň, {body.applicant_name}! "
        f"Som váš HR asistent pre pozíciu {position.title}. "
        "Rád odpovedám na vaše otázky o pracovných podmienkach, náplni práce "
        "alebo ďalších detailoch. Čo vás zaujíma?"
    )

    db.add(ChatMessage(
        company_id=company.id,
        applicant_session_id=session_id,
        position_id=position.id,
        role=MessageRoleEnum.assistant,
        content=greeting,
    ))
    await db.commit()

    return ChatStartOut(session_id=session_id, greeting=greeting)


@router.post("/{slug}/chat/stream")
@limiter.limit("60/minute")
async def chat_stream(request: Request, slug: str, body: ChatStreamIn):
    async def generate():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.applicant_session_id == body.session_id)
                .order_by(ChatMessage.created_at)
            )
            messages = result.scalars().all()

            if not messages:
                yield "data: Relácia nenájdená.\n\n"
                yield "data: [DONE]\n\n"
                return

            position_id = messages[0].position_id
            company_id = messages[0].company_id

            pos_result = await db.execute(select(Position).where(Position.id == position_id))
            position = pos_result.scalar_one_or_none()

            db.add(ChatMessage(
                company_id=company_id,
                applicant_session_id=body.session_id,
                position_id=position_id,
                role=MessageRoleEnum.user,
                content=body.message,
            ))
            await db.commit()

            history = [{"role": msg.role.value, "content": msg.content} for msg in messages]

            applicant_name = "uchádzač"
            if messages and messages[0].role == MessageRoleEnum.assistant:
                greeting = messages[0].content
                if "Dobrý deň, " in greeting and "!" in greeting:
                    start = len("Dobrý deň, ")
                    end = greeting.index("!")
                    applicant_name = greeting[start:end]

            full_response = ""
            async for chunk in generate_response(position, history, body.message, applicant_name):
                full_response += chunk
                yield f"data: {chunk}\n\n"

            yield "data: [DONE]\n\n"

            db.add(ChatMessage(
                company_id=company_id,
                applicant_session_id=body.session_id,
                position_id=position_id,
                role=MessageRoleEnum.assistant,
                content=full_response.strip(),
            ))
            await db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")
