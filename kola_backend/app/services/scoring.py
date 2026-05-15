from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from statistics import pstdev

from app.models.event import EconomicEvent


@dataclass(frozen=True)
class ScoreResult:
    score: int
    confidence: str
    anomaly_flag: bool
    shap: dict[str, int]
    explanation: dict[str, object]
    streak_weeks: int


def _event_amount(event: EconomicEvent) -> Decimal:
    return event.amount or Decimal("0")


def _weekly_streak(events: list[EconomicEvent]) -> int:
    if not events:
        return 0

    ordered = sorted(events, key=lambda event: event.occurred_at, reverse=True)
    weeks: list[tuple[int, int]] = []
    for event in ordered:
        year_week = event.occurred_at.isocalendar()[:2]
        if year_week not in weeks:
            weeks.append(year_week)

    return min(len(weeks), 52)


def _amount_volatility(events: list[EconomicEvent]) -> float:
    amounts = [float(_event_amount(event)) for event in events if _event_amount(event) > 0]
    if len(amounts) < 2:
        return 0.0
    average = sum(amounts) / len(amounts)
    if average == 0:
        return 0.0
    return pstdev(amounts) / average


def score_member(events: list[EconomicEvent]) -> ScoreResult:
    verified_events = [event for event in events if event.verified]
    streak_weeks = _weekly_streak(verified_events)
    event_count = len(verified_events)
    volatility = _amount_volatility(verified_events)

    now = datetime.now(timezone.utc)
    latest_event = max((event.occurred_at for event in verified_events), default=None)
    days_since_latest = (now - latest_event).days if latest_event else 999

    trade_events = [
        event
        for event in verified_events
        if "supplier" in event.event_type.lower()
        or "trade" in event.event_type.lower()
        or "payment" in event.event_type.lower()
    ]
    late_events = [event for event in verified_events if "late" in event.event_type.lower()]

    shap = {
        "streak": min(24, streak_weeks * 2),
        "trade": min(18, len(trade_events) * 3),
        "catchup": 10 if late_events and days_since_latest <= 7 else 6 if event_count else 0,
        "collector": min(12, event_count),
        "amount_std": -8 if volatility > 0.35 else -4 if volatility > 0.18 else 4,
    }

    raw_score = 560 + sum(shap.values()) + min(150, event_count * 8)
    score = max(300, min(850, raw_score))
    anomaly_flag = volatility > 0.45 or days_since_latest > 21

    if score >= 760:
        confidence = "Excellent - Low Risk"
    elif score >= 700:
        confidence = "Good - Low Risk"
    elif score >= 640:
        confidence = "Fair - Watch"
    else:
        confidence = "Thin File - Review"

    return ScoreResult(
        score=score,
        confidence=confidence,
        anomaly_flag=anomaly_flag,
        shap=shap,
        explanation={
            "basis": "behavioral_score_v1",
            "model": "KOLA deterministic SHAP baseline",
            "features": {
                "verified_events_count": event_count,
                "streak_weeks": streak_weeks,
                "trade_events_count": len(trade_events),
                "late_events_count": len(late_events),
                "amount_volatility": round(volatility, 4),
                "days_since_latest_event": days_since_latest,
            },
            "confidence": confidence,
            "anomaly_flag": anomaly_flag,
            "shap": shap,
        },
        streak_weeks=streak_weeks,
    )
