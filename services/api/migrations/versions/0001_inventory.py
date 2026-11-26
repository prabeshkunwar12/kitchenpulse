"""Create the inventory catalog and stock ledger.

Revision ID: 0001_inventory
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_inventory"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_category_name"),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("minimum", sa.Numeric(12, 3), nullable=False),
        sa.Column("target", sa.Numeric(12, 3), nullable=False),
        sa.Column("adjustment_step", sa.Numeric(12, 3), server_default="1", nullable=False),
        sa.Column("manual_low", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_item_name"),
        sa.CheckConstraint(
            "unit IN ('boxes','bags','cases','pieces','kilograms','grams','litres','bottles','buckets')",
            name="ck_item_unit",
        ),
        sa.CheckConstraint("quantity BETWEEN 0 AND 999999999.999", name="ck_item_quantity"),
        sa.CheckConstraint("minimum BETWEEN 0 AND 999999999.999", name="ck_item_minimum"),
        sa.CheckConstraint("target BETWEEN 0 AND 999999999.999", name="ck_item_target"),
        sa.CheckConstraint("adjustment_step BETWEEN 0.001 AND 999999999.999", name="ck_item_step"),
    )
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_table(
        "stock_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("type", sa.String(12), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("quantity_change", sa.Numeric(12, 3), nullable=False),
        sa.Column("previous_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("resulting_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("reason", sa.String(250)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False, unique=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("reverses_transaction_id", sa.Integer(), unique=True),
        sa.UniqueConstraint("item_id", "id", name="uq_stock_transactions_item_id_id"),
        sa.ForeignKeyConstraint(
            ["item_id", "reverses_transaction_id"],
            ["stock_transactions.item_id", "stock_transactions.id"],
            name="fk_stock_transactions_reverses_same_item",
        ),
        sa.CheckConstraint(
            "previous_quantity BETWEEN 0 AND 999999999.999"
            " AND resulting_quantity BETWEEN 0 AND 999999999.999",
            name="ck_stock_transaction_balances",
        ),
        sa.CheckConstraint(
            "resulting_quantity = previous_quantity + quantity_change",
            name="ck_stock_transaction_arithmetic",
        ),
        sa.CheckConstraint(
            "(type = 'opening' AND previous_quantity = 0)"
            " OR (type = 'add' AND quantity_change > 0)"
            " OR (type = 'remove' AND quantity_change < 0)"
            " OR type IN ('count', 'reversal')",
            name="ck_stock_transaction_type",
        ),
        sa.CheckConstraint(
            "(type = 'reversal') = (reverses_transaction_id IS NOT NULL)"
            " AND (reverses_transaction_id IS NULL OR reverses_transaction_id <> id)",
            name="ck_stock_transaction_reversal",
        ),
    )
    op.create_index(
        "uq_stock_transactions_one_opening", "stock_transactions", ["item_id"],
        unique=True, postgresql_where=sa.text("type = 'opening'"),
    )


def downgrade() -> None:
    op.drop_table("stock_transactions")
    op.drop_table("items")
    op.drop_table("categories")
