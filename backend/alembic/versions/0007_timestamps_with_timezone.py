"""Unify companies.created_at and events.created_at to TIMESTAMP WITH TIME ZONE

Migrácia 0001 vytvorila časové stĺpce s časovou zónou, migrácia 0002 (firmy a
eventy) bez nej. Schéma tak bola nekonzistentná a modely jednu z tých dvoch
podôb nutne popisovali nesprávne — `alembic check` to vypísal ako drift.

Zjednocujeme na `TIMESTAMP WITH TIME ZONE`, lebo tak to má zvyšok schémy a
appka časy vždy zapisuje v UTC. Doterajšie hodnoty sú naivné UTC (zapisoval ich
`datetime.utcnow()`), preto sa prevádzajú explicitne cez `AT TIME ZONE 'UTC'` —
bez toho by ich Postgres vyhodnotil v časovej zóne session a na serveri bez UTC
by sa posunuli.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("companies", "events")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN created_at "
            f"TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN created_at "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'"
        )
