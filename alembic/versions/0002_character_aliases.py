"""Add aliases column to characters

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    char_cols = {c["name"] for c in inspector.get_columns("characters")}
    if "aliases" not in char_cols:
        bind.execute(sa.text("ALTER TABLE characters ADD COLUMN aliases JSON"))


def downgrade() -> None:
    pass
