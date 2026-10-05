"""Add token_version and login lockout to admin_users

`token_version` je generácia tokenov. Ide do JWT ako claim „tv" a pri každom
requeste sa porovná so stĺpcom. Zvýšením čísla sa okamžite zneplatnia všetky
vydané tokeny — to je odhlásenie na serveri aj odrezanie session po zmene hesla.
Bez toho má zmazaný alebo odhlásený admin prístup až do expirácie tokenu.

`failed_login_count` a `locked_until` držia lockout prihlasovania v DB, aby
prežil restart a platil aj pri viacerých instanciách.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "admin_users",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "admin_users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("admin_users", "locked_until")
    op.drop_column("admin_users", "failed_login_count")
    op.drop_column("admin_users", "token_version")
