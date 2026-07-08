"""Modelo Interbank de Compra Inteligente: costes financiados, desgravamen
en la cuota y sub-cronograma del cuotón (período N+1).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'loans',
        sa.Column('financed_costs', sa.Numeric(precision=20, scale=6),
                  nullable=False, server_default='0'),
    )
    op.add_column(
        'loans',
        sa.Column('desgravamen_monthly_pct', sa.Numeric(precision=12, scale=8),
                  nullable=False, server_default='0'),
    )
    for col in (
        'insurance',
        'balloon_initial',
        'balloon_interest',
        'balloon_insurance',
        'balloon_amortization',
        'balloon_final',
    ):
        op.add_column(
            'payment_schedule_entries',
            sa.Column(col, sa.Numeric(precision=20, scale=6),
                      nullable=False, server_default='0'),
        )


def downgrade() -> None:
    for col in (
        'balloon_final',
        'balloon_amortization',
        'balloon_insurance',
        'balloon_interest',
        'balloon_initial',
        'insurance',
    ):
        op.drop_column('payment_schedule_entries', col)
    op.drop_column('loans', 'desgravamen_monthly_pct')
    op.drop_column('loans', 'financed_costs')
