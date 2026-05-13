from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.member import GroupMember


class AjoGroup(TimestampMixin, Base):
    __tablename__ = "ajo_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contribution_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    contribution_frequency: Mapped[str] = mapped_column(String(32), default="weekly", nullable=False)
    squad_customer_group_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    members: Mapped[list[GroupMember]] = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
