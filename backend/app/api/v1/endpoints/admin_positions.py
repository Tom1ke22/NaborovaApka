import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_company_id
from app.db.base import get_db
from app.models.position import Position, PositionRequirements, PositionStatusEnum
from app.schemas.position import PositionCreate, PositionOut, PositionUpdate

router = APIRouter(prefix="/admin/positions", tags=["admin-positions"])


@router.get("", response_model=list[PositionOut])
async def admin_list_positions(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    result = await db.execute(
        select(Position)
        .options(selectinload(Position.requirements))
        .where(Position.company_id == company_id)
        .order_by(Position.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
async def admin_create_position(
    body: PositionCreate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    position = Position(company_id=company_id, **body.model_dump(exclude={"requirements"}))
    db.add(position)
    await db.flush()

    requirements = PositionRequirements(position_id=position.id, **body.requirements.model_dump())
    db.add(requirements)
    await db.commit()

    result = await db.execute(
        select(Position).options(selectinload(Position.requirements)).where(Position.id == position.id)
    )
    return result.scalar_one()


@router.put("/{position_id}", response_model=PositionOut)
async def admin_update_position(
    position_id: uuid.UUID,
    body: PositionUpdate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    result = await db.execute(
        select(Position)
        .options(selectinload(Position.requirements))
        .where(Position.id == position_id, Position.company_id == company_id)
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pozícia nenájdená")

    for field, value in body.model_dump(exclude_unset=True, exclude={"requirements"}).items():
        setattr(position, field, value)
    position.updated_at = datetime.utcnow()

    if body.requirements is not None:
        for field, value in body.requirements.model_dump(exclude_unset=True).items():
            setattr(position.requirements, field, value)

    await db.commit()
    result = await db.execute(
        select(Position).options(selectinload(Position.requirements)).where(Position.id == position.id)
    )
    return result.scalar_one()


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_archive_position(
    position_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    result = await db.execute(
        select(Position).where(Position.id == position_id, Position.company_id == company_id)
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pozícia nenájdená")
    position.status = PositionStatusEnum.archived
    position.updated_at = datetime.utcnow()
    await db.commit()
