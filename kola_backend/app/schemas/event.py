from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EconomicEventRead(BaseModel):
    id: UUID
    source: str
    event_type: str
    event_id: str | None
    transaction_reference: str | None
    member_id: UUID | None
    group_id: UUID | None
    amount: Decimal | None
    currency: str
    occurred_at: datetime
    verified: bool
    raw_payload: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class WebhookIngestResponse(BaseModel):
    status: str
    event_id: UUID
    event_type: str
