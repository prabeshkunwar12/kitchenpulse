import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
    Index, Numeric, String, UniqueConstraint, Uuid, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Unit(StrEnum):
    BOXES = "boxes"
    BAGS = "bags"
    CASES = "cases"
    PIECES = "pieces"
    KILOGRAMS = "kilograms"
    GRAMS = "grams"
    LITRES = "litres"
    BOTTLES = "bottles"
    BUCKETS = "buckets"


class TransactionType(StrEnum):
    OPENING = "opening"
    ADD = "add"
    REMOVE = "remove"
    COUNT = "count"
    REVERSAL = "reversal"


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("length(btrim(name)) > 0", name="ck_category_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_item_name"),
        CheckConstraint(
            "unit IN ('boxes','bags','cases','pieces','kilograms','grams','litres','bottles','buckets')",
            name="ck_item_unit",
        ),
        CheckConstraint("quantity BETWEEN 0 AND 999999999.999", name="ck_item_quantity"),
        CheckConstraint("minimum BETWEEN 0 AND 999999999.999", name="ck_item_minimum"),
        CheckConstraint("target BETWEEN 0 AND 999999999.999", name="ck_item_target"),
        CheckConstraint("adjustment_step BETWEEN 0.001 AND 999999999.999", name="ck_item_step"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    unit: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    minimum: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    target: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    adjustment_step: Mapped[Decimal] = mapped_column(Numeric(12, 3), server_default="1")
    manual_low: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )


class StockTransaction(Base):
    __tablename__ = "stock_transactions"
    __table_args__ = (
        UniqueConstraint("item_id", "id", name="uq_stock_transactions_item_id_id"),
        ForeignKeyConstraint(
            ["item_id", "reverses_transaction_id"],
            ["stock_transactions.item_id", "stock_transactions.id"],
            name="fk_stock_transactions_reverses_same_item",
        ),
        CheckConstraint(
            "previous_quantity BETWEEN 0 AND 999999999.999"
            " AND resulting_quantity BETWEEN 0 AND 999999999.999",
            name="ck_stock_transaction_balances",
        ),
        CheckConstraint(
            "resulting_quantity = previous_quantity + quantity_change",
            name="ck_stock_transaction_arithmetic",
        ),
        CheckConstraint(
            "(type = 'opening' AND previous_quantity = 0)"
            " OR (type = 'add' AND quantity_change > 0)"
            " OR (type = 'remove' AND quantity_change < 0)"
            " OR type IN ('count', 'reversal')",
            name="ck_stock_transaction_type",
        ),
        CheckConstraint(
            "(type = 'reversal') = (reverses_transaction_id IS NOT NULL)"
            " AND (reverses_transaction_id IS NULL OR reverses_transaction_id <> id)",
            name="ck_stock_transaction_reversal",
        ),
        Index(
            "uq_stock_transactions_one_opening", "item_id", unique=True,
            postgresql_where=text("type = 'opening'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    type: Mapped[str] = mapped_column(String(12))
    unit: Mapped[str] = mapped_column(String(20))
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    previous_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    resulting_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    reason: Mapped[str | None] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    reverses_transaction_id: Mapped[int | None] = mapped_column(unique=True)
