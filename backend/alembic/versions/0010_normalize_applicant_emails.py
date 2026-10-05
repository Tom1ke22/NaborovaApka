"""Normalize applicants.email to lowercase

Nové prihlášky ukladajú e-mail v malých písmenách (Jan@x.sk = jan@x.sk), aby
sa dali spárovať opakované prihlášky toho istého človeka obyčajným indexom
na (company_id, email). Staré riadky sa zjednotia, inak by sa so svojimi
novšími prihláškami nespárovali.

Downgrade nič nerobí — pôvodnú veľkosť písmen si nepamätáme a pre funkčnosť
nie je potrebná.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE applicants SET email = lower(trim(email)) WHERE email <> lower(trim(email))")


def downgrade() -> None:
    pass
