import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_company_id
from app.db.base import get_db, utcnow
from app.models.applicant import Applicant
from app.models.position import Position, PositionRequirements, PositionStatusEnum
from app.schemas.position import (
    AdminPositionListItem,
    AdminPositionOut,
    PositionCreate,
    PositionUpdate,
)

router = APIRouter(prefix="/admin/positions", tags=["admin-positions"])


async def _load_saved(db: AsyncSession, position_id: uuid.UUID) -> Position:
    """Pozícia presne tak, ako je uložená v DB.

    `populate_existing` je nutné: objekt je po commite stále v identity map
    s hodnotami z requestu (expire_on_commit=False) a obyčajný SELECT by ich
    neprepísal. Odpoveď by potom ukazovala niečo iné, než je uložené.
    """
    result = await db.execute(
        select(Position)
        .options(selectinload(Position.requirements))
        .where(Position.id == position_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


@router.get("", response_model=list[AdminPositionListItem])
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
    positions = result.scalars().all()

    # Počty jedným dotazom, nie per pozícia.
    counts = await db.execute(
        select(Applicant.position_id, func.count(Applicant.id))
        .where(Applicant.company_id == company_id)
        .group_by(Applicant.position_id)
    )
    counts_by_position = dict(counts.all())

    return [
        AdminPositionListItem.model_validate(position).model_copy(
            update={"applicant_count": counts_by_position.get(position.id, 0)}
        )
        for position in positions
    ]


@router.post("", response_model=AdminPositionOut, status_code=status.HTTP_201_CREATED)
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
    return await _load_saved(db, position.id)


@router.put("/{position_id}", response_model=AdminPositionOut)
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
    position.updated_at = utcnow()

    if body.requirements is not None:
        for field, value in body.requirements.model_dump(exclude_unset=True).items():
            setattr(position.requirements, field, value)

    await db.commit()
    return await _load_saved(db, position.id)


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
    position.updated_at = utcnow()
    await db.commit()
