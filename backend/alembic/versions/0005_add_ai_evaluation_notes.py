"""Add ai_evaluation_notes to positions

Interné poznámky pre hodnotiaci model. Oddelené od `ai_bot_instructions`,
ktoré ide chatbotovi — uchádzač nemá vidieť, podľa čoho sa bodujeme.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "positions",
        sa.Column("ai_evaluation_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("positions", "ai_evaluation_notes")
