from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class MemberCreate(BaseModel):
    full_name: str
    phone: str
    email: EmailStr | None = None
    middle_name: str | None = None
    bvn: str | None = None
    dob: str | None = None
    gender: str | None = None
    address: str | None = None


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
