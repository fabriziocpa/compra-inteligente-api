"""Desglose de los costos/gastos iniciales del crédito.

Columna JSONB ``initial_costs``: lista de ``{name, amount, financed}``.
Los financiados suman ``financed_costs`` (que sigue siendo el insumo del
motor); los «al contado» son informativos.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-08

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'loans',
        sa.Column('initial_costs', JSONB(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('loans', 'initial_costs')
