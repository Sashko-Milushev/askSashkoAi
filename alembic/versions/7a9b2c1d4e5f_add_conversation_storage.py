"""add_conversation_storage

Revision ID: 7a9b2c1d4e5f
Revises: 3afa212fb462
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a9b2c1d4e5f"
down_revision: Union[str, Sequence[str], None] = "3afa212fb462"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_sessions_session_id"),
        "conversation_sessions",
        ["session_id"],
        unique=True,
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_messages_conversation_id"),
        "conversation_messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversation_messages_conversation_id"), table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index(op.f("ix_conversation_sessions_session_id"), table_name="conversation_sessions")
    op.drop_table("conversation_sessions")
