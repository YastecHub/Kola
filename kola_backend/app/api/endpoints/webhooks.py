from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.schemas.event import WebhookIngestResponse
from app.services.events import queue_score_recalculation, store_squad_event
from app.services.squad import SquadError, SquadService

router = APIRouter()


def _get_signature(*, x_squad_signature: str | None, x_signature: str | None) -> str:
    signature = x_squad_signature or x_signature
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Squad webhook signature",
        )
    return signature


@router.post("/squad", response_model=WebhookIngestResponse)
async def ingest_squad_webhook(
    request: Request,
    session: AsyncSession = Depends(db_session),
    x_squad_signature: str | None = Header(default=None),
    x_signature: str | None = Header(default=None),
    x_squad_encrypted_body: str | None = Header(default=None),
) -> WebhookIngestResponse:
    raw_body = await request.body()
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        logger.warning("Rejected Squad webhook with invalid JSON")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    signature = _get_signature(
        x_squad_signature=x_squad_signature,
        x_signature=x_signature or x_squad_encrypted_body,
    )
    squad = SquadService()

    if not squad.verify_webhook_signature(raw_body, signature, payload):
        logger.warning("Rejected Squad webhook with invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    verification = None
    data = payload.get("data") or payload.get("Body") or {}
    transaction_reference = (
        payload.get("transaction_reference")
        or payload.get("TransactionRef")
        or data.get("transaction_ref")
        or data.get("transaction_reference")
        or data.get("reference")
    )
    if transaction_reference:
        try:
            verification = await squad.verify_transaction(str(transaction_reference))
        except SquadError as exc:
            logger.exception("Transaction verification failed for reference={}", transaction_reference)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to verify transaction with Squad",
            ) from exc

    event = await store_squad_event(
        session=session,
        payload=payload,
        signature=signature,
        verified_transaction=verification,
    )
    await session.commit()
    await queue_score_recalculation(event.member_id)

    logger.info("Stored verified Squad event event_id={} type={}", event.id, event.event_type)
    return WebhookIngestResponse(status="accepted", event_id=event.id, event_type=event.event_type)
