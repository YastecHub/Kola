from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.core.security import require_api_key
from app.models.member import GroupMember
from app.schemas.score import ScoreRead
from app.services.events import build_score_response

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/trader/{phone_or_id}", response_model=ScoreRead)
async def get_trader_score(phone_or_id: str, session: AsyncSession = Depends(db_session)) -> dict:
    conditions = [GroupMember.phone == phone_or_id]
    try:
        conditions.append(GroupMember.id == UUID(phone_or_id))
    except ValueError:
        pass

    result = await session.execute(select(GroupMember).where(or_(*conditions)).limit(1))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return await build_score_response(session, member)


@router.get("/{member_id}", response_model=ScoreRead)
async def get_member_score(member_id: UUID, session: AsyncSession = Depends(db_session)) -> dict:
    member = await session.get(GroupMember, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return await build_score_response(session, member)
