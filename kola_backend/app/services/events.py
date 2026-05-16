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
<<<<<<< HEAD
from app.services.scoring import score_member
=======
from app.services.ai import score_member_with_ai
>>>>>>> 37105b7fa119671e2cc4326c4a3e2c81a3137fbf
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
            "virtual_account_number",
            "data.virtual_account_number",
            "data.account_number",
            "Body.virtual_account_number",
            "Body.account_number",
            "virtual_account_number",
            "account_number",
        ),
    )
    phone = _first(
        payload,
        (
            "data.customer.mobile_num",
            "data.mobile_num",
            "Body.customer_mobile",
            "Body.mobile_num",
            "customer.mobile_num",
            "phone",
        ),
    )
    customer_id = _first(
        payload,
        (
            "customer_identifier",
            "data.customer_identifier",
            "data.customer_id",
            "data.customer.id",
            "Body.customer_identifier",
            "customer_id",
        ),
    )

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
    event_type = str(
        _first(payload, ("event", "Event", "type", "event_type", "channel", "Body.transaction_type")) or "unknown"
    )
    event_id = _first(
        payload,
        (
            "transaction_uuid",
            "TransactionRef",
            "transaction_reference",
            "id",
            "event_id",
            "data.id",
            "data.transaction_id",
            "Body.transaction_ref",
        ),
    )
    transaction_reference = _first(
        payload,
        (
            "transaction_reference",
            "TransactionRef",
            "data.transaction_ref",
            "data.transaction_reference",
            "data.reference",
            "Body.transaction_ref",
            "Body.transaction_reference",
            "Body.gateway_ref",
            "transaction_ref",
            "reference",
        ),
    )
    amount = parse_amount(
        _first(payload, ("principal_amount", "data.amount", "amount", "data.principal_amount", "Body.amount"))
    )
    currency = str(_first(payload, ("currency", "data.currency", "Body.currency")) or "NGN")
    occurred_at = _parse_timestamp(
        _first(payload, ("transaction_date", "created_at", "data.created_at", "data.transaction_date", "Body.created_at"))
    )
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

<<<<<<< HEAD
    computed_score = score_member(events)
    latest_explanation = latest_score.explanation if latest_score else computed_score.explanation
    score = latest_score.score if latest_score else computed_score.score
    shap = latest_explanation.get("shap", computed_score.shap) if isinstance(latest_explanation, dict) else computed_score.shap
    confidence = latest_explanation.get("confidence", computed_score.confidence) if isinstance(latest_explanation, dict) else computed_score.confidence
    anomaly_flag = latest_explanation.get("anomaly_flag", computed_score.anomaly_flag) if isinstance(latest_explanation, dict) else computed_score.anomaly_flag

    return {
        "member_id": member.id,
        "kola_score": score,
        "score": score,
        "confidence": str(confidence),
        "anomaly_flag": bool(anomaly_flag),
        "shap": shap,
        "explanation": latest_explanation,
=======
    ai_result = await score_member_with_ai(member.id, events)
    if ai_result:
        return {
            "member_id": member.id,
            "kola_score": ai_result["score"],
            "explanation": {
                "basis": "xgboost_shap",
                "shap": ai_result.get("shap", {}),
                "anomaly_flag": ai_result.get("anomaly_flag", False),
                "anomaly_reason": ai_result.get("anomaly_reason"),
                "confidence": ai_result.get("confidence", "Medium"),
                "confidence_detail": ai_result.get("confidence_detail", ""),
                "weeks_squad_verified": ai_result.get("weeks_squad_verified", event_count),
                "probability": ai_result.get("probability"),
            },
            "verified_events_count": event_count,
            "streak_weeks": ai_result.get("weeks_of_history", min(event_count, 12)),
            "last_updated": datetime.now(timezone.utc),
            "events": events,
        }

    fallback_score = min(850, 500 + (event_count * 8))
    return {
        "member_id": member.id,
        "kola_score": latest_score.score if latest_score else fallback_score,
        "explanation": latest_score.explanation
        if latest_score
        else {
            "basis": "provisional_score",
            "reason": "AI score service is not configured or unavailable; score is derived from verified Squad event count.",
        },
>>>>>>> 37105b7fa119671e2cc4326c4a3e2c81a3137fbf
        "verified_events_count": latest_score.verified_events_count if latest_score else event_count,
        "streak_weeks": latest_score.streak_weeks if latest_score else computed_score.streak_weeks,
        "last_updated": latest_score.created_at if latest_score else datetime.now(timezone.utc),
        "events": events,
    }


async def queue_score_recalculation(member_id: UUID | None) -> None:
    if member_id is None:
        logger.info("Stored Squad event without matching member; score recalculation skipped")
        return
    logger.info("Score recalculation queued for member_id={}", member_id)
