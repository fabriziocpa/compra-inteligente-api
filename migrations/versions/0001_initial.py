"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-12

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("document_id", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False, server_default=""),
    )
    op.create_index("ix_clients_owner_id", "clients", ["owner_id"])

    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("list_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
    )
    op.create_index("ix_vehicles_owner_id", "vehicles", ["owner_id"])

    op.create_table(
        "loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("vehicle_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("initial_payment_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("balloon_pct", sa.Numeric(10, 6), nullable=True),
        sa.Column("term_periods", sa.Integer, nullable=False),
        sa.Column("frequency_days", sa.Integer, nullable=False),
        sa.Column("rate_spec", postgresql.JSONB, nullable=False),
        sa.Column("grace_policy", postgresql.JSONB, nullable=False),
        sa.Column("additional_charges", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
    )
    op.create_index("ix_loans_client_id", "loans", ["client_id"])

    op.create_table(
        "payment_schedule_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "loan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("loans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period", sa.Integer, nullable=False),
        sa.Column("grace_type", sa.String(1), nullable=False),
        sa.Column("initial_balance", sa.Numeric(20, 6), nullable=False),
        sa.Column("interest", sa.Numeric(20, 6), nullable=False),
        sa.Column("payment", sa.Numeric(20, 6), nullable=False),
        sa.Column("amortization", sa.Numeric(20, 6), nullable=False),
        sa.Column("final_balance", sa.Numeric(20, 6), nullable=False),
        sa.UniqueConstraint("loan_id", "period", name="uq_schedule_loan_period"),
    )
    op.create_index("ix_schedule_entries_loan_id", "payment_schedule_entries", ["loan_id"])


def downgrade() -> None:
    op.drop_index("ix_schedule_entries_loan_id", table_name="payment_schedule_entries")
    op.drop_table("payment_schedule_entries")
    op.drop_index("ix_loans_client_id", table_name="loans")
    op.drop_table("loans")
    op.drop_index("ix_vehicles_owner_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_clients_owner_id", table_name="clients")
    op.drop_table("clients")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
