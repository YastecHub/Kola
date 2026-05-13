"""initial KOLA schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-13 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ajo_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contribution_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("contribution_frequency", sa.String(length=32), nullable=False),
        sa.Column("squad_customer_group_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ajo_groups_name"), "ajo_groups", ["name"], unique=False)

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("squad_customer_id", sa.String(length=128), nullable=True),
        sa.Column("squad_va_id", sa.String(length=128), nullable=True),
        sa.Column("squad_va_number", sa.String(length=32), nullable=True),
        sa.Column("squad_va_bank", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["ajo_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone", name="uq_group_members_phone"),
        sa.UniqueConstraint("squad_va_number", name="uq_group_members_squad_va_number"),
    )
    op.create_index(op.f("ix_group_members_group_id"), "group_members", ["group_id"], unique=False)
    op.create_index(op.f("ix_group_members_phone"), "group_members", ["phone"], unique=False)

    op.create_table(
        "economic_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=True),
        sa.Column("transaction_reference", sa.String(length=255), nullable=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["ajo_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["group_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "event_id", name="uq_economic_events_source_event_id"),
    )
    op.create_index(op.f("ix_economic_events_event_type"), "economic_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_economic_events_member_id"), "economic_events", ["member_id"], unique=False)
    op.create_index(op.f("ix_economic_events_occurred_at"), "economic_events", ["occurred_at"], unique=False)
    op.create_index(
        op.f("ix_economic_events_transaction_reference"),
        "economic_events",
        ["transaction_reference"],
        unique=False,
    )

    op.create_table(
        "kola_score_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verified_events_count", sa.Integer(), nullable=False),
        sa.Column("streak_weeks", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["group_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kola_score_history_member_id"), "kola_score_history", ["member_id"], unique=False)
    op.create_index(op.f("ix_kola_score_history_created_at"), "kola_score_history", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_kola_score_history_created_at"), table_name="kola_score_history")
    op.drop_index(op.f("ix_kola_score_history_member_id"), table_name="kola_score_history")
    op.drop_table("kola_score_history")
    op.drop_index(op.f("ix_economic_events_transaction_reference"), table_name="economic_events")
    op.drop_index(op.f("ix_economic_events_occurred_at"), table_name="economic_events")
    op.drop_index(op.f("ix_economic_events_member_id"), table_name="economic_events")
    op.drop_index(op.f("ix_economic_events_event_type"), table_name="economic_events")
    op.drop_table("economic_events")
    op.drop_index(op.f("ix_group_members_phone"), table_name="group_members")
    op.drop_index(op.f("ix_group_members_group_id"), table_name="group_members")
    op.drop_table("group_members")
    op.drop_index(op.f("ix_ajo_groups_name"), table_name="ajo_groups")
    op.drop_table("ajo_groups")
