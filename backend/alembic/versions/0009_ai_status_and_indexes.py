"""Add applicants.ai_status and indexes for admin queries

ai_status
---------
Keď AI hodnotenie zlyhalo alebo vypršalo, uchádzač ostal bez skóre a admin
videl „Vyhodnocuje sa" navždy — nevedel rozlíšiť beží od zlyhalo. Nový stĺpec
to rozlišuje (pending / done / failed / skipped), `ai_status_changed_at`
odhalí hodnotenie, ktoré „visí", lebo proces počas behu zomrel.

Existujúci uchádzači: so skóre → done, bez skóre → failed. Hodnotenie im
v tejto chvíli nebeží, takže „pending" by bola rovnaká lož ako doteraz;
failed ponúkne adminovi tlačidlo „Skúsiť znova".

Indexy
------
Postgres na cudzie kľúče indexy sám nezakladá. Zoznam záujemcov, filter na
pozíciu, zoznam pozícií aj prepis chatu tak robili full table scan.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applicants",
        sa.Column("ai_status", sa.String(length=16), nullable=False, server_default="pending"),
    )
    op.add_column(
        "applicants",
        sa.Column(
            "ai_status_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(
        "UPDATE applicants SET ai_status = CASE "
        "WHEN ai_score IS NOT NULL THEN 'done' ELSE 'failed' END"
    )

    op.create_index(
        "ix_applicants_company_submitted", "applicants", ["company_id", "submitted_at"]
    )
    op.create_index("ix_applicants_position_id", "applicants", ["position_id"])
    op.create_index("ix_applicants_company_email", "applicants", ["company_id", "email"])
    op.create_index(
        "ix_positions_company_created", "positions", ["company_id", "created_at"]
    )
    op.create_index("ix_chat_messages_applicant_id", "chat_messages", ["applicant_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_applicant_id", table_name="chat_messages")
    op.drop_index("ix_positions_company_created", table_name="positions")
    op.drop_index("ix_applicants_company_email", table_name="applicants")
    op.drop_index("ix_applicants_position_id", table_name="applicants")
    op.drop_index("ix_applicants_company_submitted", table_name="applicants")
    op.drop_column("applicants", "ai_status_changed_at")
    op.drop_column("applicants", "ai_status")
