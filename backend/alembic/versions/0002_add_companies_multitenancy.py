"""Add companies, events, company_id multi-tenancy

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- companies ---
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_companies_slug", "companies", ["slug"])

    # --- events ---
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("position_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("positions.id"), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_events_company_id", "events", ["company_id"])
    op.create_index("ix_events_created_at", "events", ["created_at"])
    op.create_index("ix_events_event_type", "events", ["event_type"])

    # --- company_id na existujúce tabuľky ---
    # Tabuľky sú prázdne v dev (reset volumes), preto NOT NULL bez default
    op.add_column("positions", sa.Column(
        "company_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("companies.id"), nullable=False
    ))
    op.add_column("applicants", sa.Column(
        "company_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("companies.id"), nullable=False
    ))
    op.add_column("chat_messages", sa.Column(
        "company_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("companies.id"), nullable=False
    ))
    op.add_column("admin_users", sa.Column(
        "company_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("companies.id"), nullable=False
    ))


def downgrade() -> None:
    op.drop_column("admin_users", "company_id")
    op.drop_column("chat_messages", "company_id")
    op.drop_column("applicants", "company_id")
    op.drop_column("positions", "company_id")

    op.drop_index("ix_events_event_type", "events")
    op.drop_index("ix_events_created_at", "events")
    op.drop_index("ix_events_company_id", "events")
    op.drop_table("events")
    op.drop_table("companies")
