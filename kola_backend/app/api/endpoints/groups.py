from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.core.security import require_api_key
from app.models.group import AjoGroup
from app.models.member import GroupMember
from app.schemas.group import GroupCreate, GroupRead
from app.schemas.member import MemberRead
from app.services.squad import SquadError, SquadService

router = APIRouter()


@router.post("/", response_model=GroupRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
async def create_group(payload: GroupCreate, session: AsyncSession = Depends(db_session)) -> GroupRead:
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
                middle_name=member_payload.middle_name,
                bvn=member_payload.bvn,
                dob=member_payload.dob,
                gender=member_payload.gender,
                address=member_payload.address,
                beneficiary_account=payload.beneficiary_account,
            )
            member.squad_customer_id = va.customer_id
            member.squad_va_id = va.va_id
            member.squad_va_number = va.account_number
            member.squad_va_bank = va.bank_name
            members.append(member)

        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        logger.warning("Unable to create group due to duplicate or invalid database value")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group member phone or virtual account already exists",
        ) from exc
    except SquadError as exc:
        await session.rollback()
        logger.exception("Unable to create Squad virtual accounts for group")
        detail: dict[str, object] = {"message": "Unable to create Squad virtual accounts"}
        if exc.status_code is not None:
            detail["squad_status_code"] = exc.status_code
        if exc.response_body is not None:
            detail["squad_response"] = exc.response_body
        if exc.upstream_url is not None:
            detail["upstream_url"] = exc.upstream_url
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from exc
    except Exception:
        await session.rollback()
        logger.exception("Unable to create group")
        raise

    return GroupRead(
        id=group.id,
        name=group.name,
        description=group.description,
        contribution_amount=group.contribution_amount,
        contribution_frequency=group.contribution_frequency,
        created_at=group.created_at,
        members=[MemberRead.model_validate(member) for member in members],
    )
