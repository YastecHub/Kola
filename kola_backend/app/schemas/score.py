from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.event import EconomicEventRead


class ScoreRead(BaseModel):
    member_id: UUID
    kola_score: int
    score: int
    confidence: str
    anomaly_flag: bool
    shap: dict[str, int]
    explanation: dict[str, Any]
    verified_events_count: int
    streak_weeks: int
    last_updated: datetime
    events: list[EconomicEventRead]
