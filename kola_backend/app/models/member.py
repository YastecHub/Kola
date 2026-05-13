from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.contribution import KolaScoreHistory
    from app.models.event import EconomicEvent
    from app.models.group import AjoGroup


class GroupMember(TimestampMixin, Base):
    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_group_members_phone"),
        UniqueConstraint("squad_va_number", name="uq_group_members_squad_va_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ajo_groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    squad_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    squad_va_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    squad_va_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    squad_va_bank: Mapped[str | None] = mapped_column(String(128), nullable=True)

    group: Mapped[AjoGroup] = relationship("AjoGroup", back_populates="members", lazy="selectin")
    events: Mapped[list[EconomicEvent]] = relationship("EconomicEvent", back_populates="member", lazy="selectin")
    scores: Mapped[list[KolaScoreHistory]] = relationship("KolaScoreHistory", back_populates="member", lazy="selectin")
