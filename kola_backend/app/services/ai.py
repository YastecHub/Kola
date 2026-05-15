from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from loguru import logger

from app.core.config import settings
from app.models.event import EconomicEvent


def _event_week(event: EconomicEvent) -> int:
    occurred_at = event.occurred_at
    if occurred_at is None:
        return 1
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    age_days = max(0, (datetime.now(timezone.utc) - occurred_at).days)
    return (age_days // 7) + 1


def build_ai_score_payload(member_id: UUID, events: list[EconomicEvent]) -> dict[str, Any]:
    return {
        "member_id": str(member_id),
        "collector_trust": 0,
        "collector_trust_source": "squad_verified",
        "events": [
            {
                "type": event.event_type,
                "week": _event_week(event),
                "amount": float(event.amount or 0),
                "source": "squad_verified" if event.verified else "unverified",
            }
            for event in events
        ],
    }


async def score_member_with_ai(member_id: UUID, events: list[EconomicEvent]) -> dict[str, Any] | None:
    if not settings.kola_ai_url:
        return None

    payload = build_ai_score_payload(member_id, events)
    url = f"{str(settings.kola_ai_url).rstrip('/')}/score"
    try:
        async with httpx.AsyncClient(timeout=settings.kola_ai_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers={"x-api-key": settings.kola_ai_key})
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "KOLA AI service rejected score request: status={} body={}",
            exc.response.status_code,
            exc.response.text,
        )
        return None
    except httpx.HTTPError as exc:
        logger.warning("KOLA AI service unreachable: {}; using fallback", exc)
        return None
    except Exception as exc:
        logger.warning("KOLA AI service returned an invalid score response: {}; using fallback", exc)
        return None

    if "score" not in data:
        logger.warning("KOLA AI response missing score field; using fallback")
        return None
    return data
