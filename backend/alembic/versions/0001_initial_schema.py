"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Referencie na ENUM typy (create_type=False – vytvárame ich ručne cez SQL)
contract_type_col = postgresql.ENUM(
    "dohoda_o_pracovnej_cinnosti", "kratsi_pracovny_cas", "neuricity_cas",
    "uricity_cas", "dohoda_o_brigadnickej_praci_studenta",
    name="contracttypeenum", create_type=False,
)
salary_period_col = postgresql.ENUM("monthly", "hourly", name="salaryperiodenum", create_type=False)
position_status_col = postgresql.ENUM("active", "archived", name="positionstatusenum", create_type=False)
message_role_col = postgresql.ENUM("user", "assistant", name="messagerolesnum", create_type=False)


def upgrade() -> None:
    # ENUM typy vytvárame iba raz, pred tabuľkami
    op.execute("""
        CREATE TYPE contracttypeenum AS ENUM (
            'dohoda_o_pracovnej_cinnosti', 'kratsi_pracovny_cas',
            'neuricity_cas', 'uricity_cas', 'dohoda_o_brigadnickej_praci_studenta'
        )
    """)
    op.execute("CREATE TYPE salaryperiodenum AS ENUM ('monthly', 'hourly')")
    op.execute("CREATE TYPE positionstatusenum AS ENUM ('active', 'archived')")
    op.execute("CREATE TYPE messagerolesnum AS ENUM ('user', 'assistant')")

    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("work_area", sa.String(255), nullable=False),
        sa.Column("open_slots", sa.Integer, nullable=False, server_default="1"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("additional_info", sa.Text, nullable=True),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("contract_type", contract_type_col, nullable=False),
        sa.Column("working_hours", sa.String(100), nullable=True),
        sa.Column("shift_type", sa.String(100), nullable=True),
        sa.Column("break_info", sa.String(100), nullable=True),
        sa.Column("work_regime", sa.String(100), nullable=True),
        sa.Column("salary_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("salary_period", salary_period_col, nullable=False, server_default="monthly"),
        sa.Column("vacation_days", sa.Integer, nullable=True),
        sa.Column("meal_allowance", sa.String(255), nullable=True),
        sa.Column("contact_person", sa.String(255), nullable=True),
        sa.Column("status", position_status_col, nullable=False, server_default="active"),
        sa.Column("ai_bot_instructions", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "position_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("positions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hygiene_minimum_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("health_certificate_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("experience_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("experience_years", sa.Integer, nullable=True),
        sa.Column("education_level", sa.String(100), nullable=True),
        sa.Column("slovak_language_level", sa.String(50), nullable=True),
        sa.Column("foreign_language_level", sa.String(100), nullable=True),
    )
    op.create_unique_constraint("uq_position_requirements_position_id", "position_requirements", ["position_id"])

    op.create_table(
        "applicants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("positions.id"), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("cv_storage_path", sa.String(500), nullable=True),
        sa.Column("ai_score", sa.SmallInteger, nullable=True),
        sa.Column("ai_score_reasoning", sa.Text, nullable=True),
        sa.Column("qualification_answers", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="recruiter"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_admin_users_email", "admin_users", ["email"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("applicant_session_id", sa.String(100), nullable=False),
        sa.Column("applicant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applicants.id"), nullable=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("positions.id"), nullable=False),
        sa.Column("role", message_role_col, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["applicant_session_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("admin_users")
    op.drop_table("applicants")
    op.drop_table("position_requirements")
    op.drop_table("positions")

    op.execute("DROP TYPE IF EXISTS messagerolesnum")
    op.execute("DROP TYPE IF EXISTS positionstatusenum")
    op.execute("DROP TYPE IF EXISTS salaryperiodenum")
    op.execute("DROP TYPE IF EXISTS contracttypeenum")
