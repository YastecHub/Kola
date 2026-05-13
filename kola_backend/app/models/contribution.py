from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.member import GroupMember


class KolaScoreHistory(Base):
    __tablename__ = "kola_score_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    verified_events_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_weeks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    member: Mapped[GroupMember] = relationship("GroupMember", back_populates="scores", lazy="selectin")
