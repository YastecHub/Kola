from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.member import MemberCreate, MemberRead


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, examples=["Balogun Market Ajo"])
    description: str | None = Field(default=None, examples=["Weekly trader contribution group"])
    contribution_amount: Decimal | None = Field(default=None, ge=0, examples=["5000.00"])
    contribution_frequency: str = Field("weekly", max_length=32, examples=["weekly"])
    beneficiary_account: str | None = Field(
        default=None,
        examples=["4920299492"],
        description="10-digit GTBank settlement account required by Squad virtual accounts.",
    )
    members: list[MemberCreate] = Field(..., min_length=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Balogun Market Ajo",
                "description": "Weekly trader contribution group",
                "contribution_amount": "5000.00",
                "contribution_frequency": "weekly",
                "beneficiary_account": "4920299492",
                "members": [
                    {
                        "full_name": "Amina Bello",
                        "phone": "08012345678",
                        "email": "amina@example.com",
                        "middle_name": "Ngozi",
                        "bvn": "22343211654",
                        "dob": "07/19/1990",
                        "gender": "2",
                        "address": "22 Broad Street, Lagos",
                    }
                ],
            }
        }
    )


class GroupRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    contribution_amount: Decimal | None
    contribution_frequency: str
    created_at: datetime
    members: list[MemberRead]

    model_config = ConfigDict(from_attributes=True)
