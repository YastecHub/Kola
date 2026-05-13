from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.member import MemberCreate, MemberRead


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    contribution_amount: Decimal | None = Field(default=None, ge=0)
    contribution_frequency: str = Field("weekly", max_length=32)
    members: list[MemberCreate] = Field(..., min_length=1)


class GroupRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    contribution_amount: Decimal | None
    contribution_frequency: str
    created_at: datetime
    members: list[MemberRead]

    model_config = ConfigDict(from_attributes=True)
