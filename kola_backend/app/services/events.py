from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contribution import KolaScoreHistory
from app.models.event import EconomicEvent
from app.models.member import GroupMember
from app.services.squad import parse_amount


def _dig(payload: dict[str, Any], *keys: str) -> Any:
    cursor: Any = payload
    for key in keys:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def _first(payload: dict[str, Any], paths: tuple[str, ...]) -> Any:
    for path in paths:
        value = _dig(payload, *path.split("."))
        if value is not None:
            return value
    return None


def _parse_timestamp(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


async def find_member_for_payload(session: AsyncSession, payload: dict[str, Any]) -> GroupMember | None:
    account_number = _first(
        payload,
        (
            "data.virtual_account_number",
            "data.account_number",
            "virtual_account_number",
            "account_number",
        ),
    )
    phone = _first(payload, ("data.customer.mobile_num", "data.mobile_num", "customer.mobile_num", "phone"))
    customer_id = _first(payload, ("data.customer_id", "data.customer.id", "customer_id"))

    conditions = []
    if account_number:
        conditions.append(GroupMember.squad_va_number == str(account_number))
    if phone:
        conditions.append(GroupMember.phone == str(phone))
    if customer_id:
        conditions.append(GroupMember.squad_customer_id == str(customer_id))

    if not conditions:
        return None

    result = await session.execute(select(GroupMember).where(or_(*conditions)).limit(1))
    return result.scalar_one_or_none()


async def store_squad_event(
    *,
    session: AsyncSession,
    payload: dict[str, Any],
    signature: str,
    verified_transaction: dict[str, Any] | None = None,
) -> EconomicEvent:
    event_type = str(_first(payload, ("event", "type", "event_type")) or "unknown")
    event_id = _first(payload, ("id", "event_id", "data.id", "data.transaction_id"))
    transaction_reference = _first(
        payload,
        (
            "data.transaction_ref",
            "data.transaction_reference",
            "data.reference",
            "transaction_ref",
            "transaction_reference",
            "reference",
        ),
    )
    amount = parse_amount(_first(payload, ("data.amount", "amount", "data.principal_amount")))
    currency = str(_first(payload, ("data.currency", "currency")) or "NGN")
    occurred_at = _parse_timestamp(_first(payload, ("created_at", "data.created_at", "data.transaction_date")))
    member = await find_member_for_payload(session, payload)

    values = {
        "source": "squad",
        "event_type": event_type,
        "event_id": str(event_id) if event_id is not None else None,
        "transaction_reference": str(transaction_reference) if transaction_reference else None,
        "member_id": member.id if member else None,
        "group_id": member.group_id if member else None,
        "amount": amount,
        "currency": currency,
        "occurred_at": occurred_at,
        "signature": signature,
        "raw_payload": {
            "webhook": payload,
            "transaction_verification": verified_transaction,
        },
        "verified": True,
    }

    if values["event_id"]:
        stmt = (
            insert(EconomicEvent)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["source", "event_id"])
            .returning(EconomicEvent)
        )
        result = await session.execute(stmt)
        event = result.scalar_one_or_none()
        if event is not None:
            await session.flush()
            return event

        existing = await session.execute(
            select(EconomicEvent).where(
                EconomicEvent.source == "squad",
                EconomicEvent.event_id == values["event_id"],
            )
        )
        return existing.scalar_one()

    event = EconomicEvent(**values)
    session.add(event)
    await session.flush()
    return event


async def build_score_response(session: AsyncSession, member: GroupMember) -> dict[str, Any]:
    event_count = await session.scalar(
        select(func.count()).select_from(EconomicEvent).where(
            EconomicEvent.member_id == member.id,
            EconomicEvent.verified.is_(True),
        )
    )
    event_count = int(event_count or 0)

    latest_score = await session.scalar(
        select(KolaScoreHistory)
        .where(KolaScoreHistory.member_id == member.id)
        .order_by(desc(KolaScoreHistory.created_at))
        .limit(1)
    )

    events_result = await session.execute(
        select(EconomicEvent)
        .where(EconomicEvent.member_id == member.id)
        .order_by(desc(EconomicEvent.occurred_at))
        .limit(25)
    )
    events = list(events_result.scalars())

    fallback_score = min(850, 500 + (event_count * 8))
    return {
        "member_id": member.id,
        "kola_score": latest_score.score if latest_score else fallback_score,
        "explanation": latest_score.explanation
        if latest_score
        else {
            "basis": "provisional_score",
            "reason": "ML score service is not connected yet; score is derived from verified Squad event count.",
        },
        "verified_events_count": latest_score.verified_events_count if latest_score else event_count,
        "streak_weeks": latest_score.streak_weeks if latest_score else min(event_count, 12),
        "last_updated": latest_score.created_at if latest_score else datetime.now(timezone.utc),
        "events": events,
    }


async def queue_score_recalculation(member_id: UUID | None) -> None:
    if member_id is None:
        logger.info("Stored Squad event without matching member; score recalculation skipped")
        return
    logger.info("Score recalculation queued for member_id={}", member_id)
