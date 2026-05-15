from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MemberCreate(BaseModel):
    full_name: str = Field(..., examples=["Amina Bello"])
    phone: str = Field(..., examples=["08012345678"])
    email: EmailStr | None = Field(default=None, examples=["amina@example.com"])
    middle_name: str | None = Field(default=None, examples=["Ngozi"])
    bvn: str | None = Field(default=None, examples=["22343211654"])
    dob: str | None = Field(default=None, examples=["07/19/1990"])
    gender: str | None = Field(default=None, examples=["2"], description="'1' for male, '2' for female")
    address: str | None = Field(default=None, examples=["22 Broad Street, Lagos"])


class MemberRead(BaseModel):
    id: UUID
    group_id: UUID
    full_name: str
    phone: str
    email: str | None
    squad_customer_id: str | None
    squad_va_id: str | None
    squad_va_number: str | None
    squad_va_bank: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
