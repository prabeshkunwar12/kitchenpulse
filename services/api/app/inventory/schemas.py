from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, StrictBool, StringConstraints,
    computed_field, model_validator,
)

from .models import TransactionType, Unit

MAX_QUANTITY = Decimal("999999999.999")
ZERO = Decimal("0.000")


def decimal_input(value: object) -> object:
    if type(value) in (str, int, Decimal):
        return value
    raise ValueError("Use a decimal string or a whole JSON integer.")


def decimal_string(value: Decimal) -> str:
    return format(ZERO if value.is_zero() else value, ".3f")


Quantity = Annotated[
    Decimal, BeforeValidator(decimal_input, json_schema_input_type=str | int),
    Field(ge=ZERO, le=MAX_QUANTITY, max_digits=12, decimal_places=3, allow_inf_nan=False),
]
PositiveQuantity = Annotated[Quantity, Field(gt=ZERO)]
DecimalOutput = Annotated[
    Decimal, PlainSerializer(decimal_string, return_type=str, when_used="json"),
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^\x00]+$")]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250, pattern=r"^[^\x00]+$")]
CategoryId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ItemCreate(Input):
    name: Name
    category_id: CategoryId
    unit: Unit
    quantity: Quantity = ZERO
    minimum: Quantity = ZERO
    target: Quantity = ZERO
    adjustment_step: PositiveQuantity = Decimal("1.000")


class ItemUpdate(Input):
    name: Name | None = None
    category_id: CategoryId | None = None
    unit: Unit | None = None
    minimum: Quantity | None = None
    target: Quantity | None = None
    adjustment_step: PositiveQuantity | None = None

    @model_validator(mode="after")
    def require_values(self):
        if not self.model_fields_set:
            raise ValueError("Supply at least one field to update.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Item fields cannot be null.")
        return self


class StockStatus(StrEnum):
    OUT = "out_of_stock"
    LOW = "low_stock"
    IN = "in_stock"


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category_id: int
    unit: Unit
    quantity: DecimalOutput
    minimum: DecimalOutput
    target: DecimalOutput
    adjustment_step: DecimalOutput
    manual_low: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def stock_status(self) -> StockStatus:
        if self.quantity == ZERO:
            return StockStatus.OUT
        return StockStatus.LOW if self.quantity <= self.minimum else StockStatus.IN

    @computed_field
    @property
    def recommended_replenishment(self) -> DecimalOutput:
        return max(ZERO, self.target - self.quantity)


class StockRequest(Input):
    idempotency_key: UUID
    reason: Reason | None = None


class Adjustment(StockRequest):
    quantity: PositiveQuantity | None = None


class Count(StockRequest):
    quantity: Quantity


class Report(Input):
    manual_low: StrictBool


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    item_name: str
    unit: Unit
    type: TransactionType
    quantity_change: DecimalOutput
    previous_quantity: DecimalOutput
    resulting_quantity: DecimalOutput
    reason: str | None
    created_at: datetime
    idempotency_key: UUID
    reverses_transaction_id: int | None
    reversed_by_transaction_id: int | None
    can_reverse: bool


class HistoryPage(BaseModel):
    transactions: list[TransactionRead]
    next_before_id: int | None
