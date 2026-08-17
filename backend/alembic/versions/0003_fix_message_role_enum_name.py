"""Fix message role enum name (messagerolesnum -> messageroleenum)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE messagerolesnum RENAME TO messageroleenum")


def downgrade() -> None:
    op.execute("ALTER TYPE messageroleenum RENAME TO messagerolesnum")
