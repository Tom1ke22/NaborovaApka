"""Add chat_sessions with a secret claim token

Doteraz stačilo poznať `session_id`, aby sa cudzí chat dal pripojiť k vlastnej
prihláške alebo do neho písať. `session_id` ale bol v URL (/apply?session=…),
takže unikal cez históriu prehliadača, Referer a access logy.

Nová tabuľka drží ku každej session hash tajného claim tokenu. Token server
vráti len pri `chat/start` a vyžaduje ho pri písaní do chatu aj pri odoslaní
prihlášky.

Staršie rozpísané chaty riadok v tejto tabuľke nemajú, preto sa po nasadení
už nedajú pripojiť k prihláške ani v nich pokračovať. Uchádzač si otvorí nový
chat. Chaty už pripojené k prihláškam ostávajú bez zmeny.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_token_hash", sa.String(length=64), nullable=False),
        sa.Column("applicant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"]),
        sa.ForeignKeyConstraint(["applicant_id"], ["applicants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("chat_sessions")
