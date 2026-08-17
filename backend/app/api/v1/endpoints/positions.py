import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.models.company import Company
from app.models.event import Event
from app.models.position import Position, PositionStatusEnum
from app.schemas.position import PositionListItem, PositionOut

router = APIRouter(tags=["positions"])


async def _get_active_company(slug: str, db: AsyncSession) -> Company:
    result = await db.execute(
        select(Company).where(Company.slug == slug, Company.is_active == True)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firma nenájdená")
    return company


@router.get("/{slug}/positions", response_model=list[PositionListItem])
async def list_positions(slug: str, db: AsyncSession = Depends(get_db)):
    company = await _get_active_company(slug, db)
    result = await db.execute(
        select(Position)
        .where(Position.company_id == company.id, Position.status == PositionStatusEnum.active)
        .order_by(Position.created_at.desc())
    )
    positions = result.scalars().all()
    db.add(Event(company_id=company.id, event_type="positions_list_view"))
    await db.commit()
    return positions


@router.get("/{slug}/positions/{position_id}", response_model=PositionOut)
async def get_position(slug: str, position_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    company = await _get_active_company(slug, db)
    result = await db.execute(
        select(Position)
        .options(selectinload(Position.requirements))
        .where(
            Position.id == position_id,
            Position.company_id == company.id,
            Position.status == PositionStatusEnum.active,
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pozícia nenájdená")
    db.add(Event(company_id=company.id, event_type="position_view", position_id=position.id))
    await db.commit()
    return position
