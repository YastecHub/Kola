from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.core.security import require_api_key
from app.models.group import AjoGroup
from app.models.member import GroupMember
from app.schemas.group import GroupCreate, GroupRead
from app.services.squad import SquadError, SquadService

router = APIRouter()


@router.post("/", response_model=GroupRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
async def create_group(payload: GroupCreate, session: AsyncSession = Depends(db_session)) -> AjoGroup:
    group = AjoGroup(
        name=payload.name,
        description=payload.description,
        contribution_amount=payload.contribution_amount,
        contribution_frequency=payload.contribution_frequency,
    )
    session.add(group)
    await session.flush()

    squad = SquadService()
    members: list[GroupMember] = []
    try:
        for member_payload in payload.members:
            member = GroupMember(
                group_id=group.id,
                full_name=member_payload.full_name,
                phone=member_payload.phone,
                email=str(member_payload.email) if member_payload.email else None,
            )
            session.add(member)
            await session.flush()

            va = await squad.create_virtual_account(
                full_name=member.full_name,
                phone=member.phone,
                email=member.email,
                customer_identifier=str(member.id),
            )
            member.squad_customer_id = va.customer_id
            member.squad_va_id = va.va_id
            member.squad_va_number = va.account_number
            member.squad_va_bank = va.bank_name
            members.append(member)

        await session.commit()
    except SquadError as exc:
        await session.rollback()
        logger.exception("Unable to create Squad virtual accounts for group")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to create Squad virtual accounts",
        ) from exc
    except Exception:
        await session.rollback()
        logger.exception("Unable to create group")
        raise

    group.members = members
    return group
