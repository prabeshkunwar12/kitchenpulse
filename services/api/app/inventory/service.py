import hashlib
import json
from uuid import UUID, uuid4

from sqlalchemy import and_, exists, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from .models import Category, Item, StockTransaction, TransactionType
from .schemas import Adjustment, Count, ItemCreate, ItemUpdate, MAX_QUANTITY, StockRequest, ZERO, decimal_string


class InventoryError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def get_item(session: Session, item_id: int, *, lock: bool = False) -> Item:
    statement = select(Item).where(Item.id == item_id)
    if lock:
        statement = statement.with_for_update()
    item = session.scalar(statement)
    if item is None:
        raise InventoryError(404, "item_not_found", "Inventory item not found.")
    return item


def require_active(item: Item) -> None:
    if not item.active:
        raise InventoryError(409, "inactive_item", "This item is inactive.")


def require_category(session: Session, category_id: int) -> None:
    if session.get(Category, category_id) is None:
        raise InventoryError(422, "unknown_category", "Choose an existing category.")


def flush_item(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint == "items_name_key":
            raise InventoryError(409, "duplicate_item", "An item with that name already exists.") from error
        raise


def create_item(session: Session, body: ItemCreate, *, opening_key: UUID | None = None) -> Item:
    require_category(session, body.category_id)
    item = Item(**body.model_dump())
    session.add(item)
    flush_item(session)
    session.add(StockTransaction(
        item_id=item.id,
        type=TransactionType.OPENING,
        unit=item.unit,
        quantity_change=item.quantity,
        previous_quantity=ZERO,
        resulting_quantity=item.quantity,
        idempotency_key=opening_key or uuid4(),
        request_fingerprint="opening",
    ))
    return item


def update_item(session: Session, item: Item, body: ItemUpdate) -> Item:
    fields = body.model_dump(exclude_unset=True)
    if "category_id" in fields:
        require_category(session, fields["category_id"])
    if "unit" in fields and fields["unit"] != item.unit:
        nonzero_history = session.scalar(select(exists().where(
            StockTransaction.item_id == item.id,
            StockTransaction.quantity_change != ZERO,
        )))
        if nonzero_history:
            raise InventoryError(
                409, "unit_has_history", "Use a new item to change units after stock has been recorded.",
            )
    for field, value in fields.items():
        setattr(item, field, value)
    flush_item(session)
    return item


def transaction_query():
    reversal = aliased(StockTransaction)
    later = aliased(StockTransaction)
    reversed_by = select(reversal.id).where(
        reversal.reverses_transaction_id == StockTransaction.id,
    ).correlate(StockTransaction).scalar_subquery()
    superseded = exists(select(later.id).where(
        later.item_id == StockTransaction.item_id,
        later.id > StockTransaction.id,
        or_(StockTransaction.type == TransactionType.COUNT, later.type == TransactionType.COUNT),
    ).correlate(StockTransaction))
    can_reverse = and_(
        Item.active,
        StockTransaction.type.in_([TransactionType.ADD, TransactionType.REMOVE, TransactionType.COUNT]),
        reversed_by.is_(None),
        ~superseded,
        (Item.quantity - StockTransaction.quantity_change).between(ZERO, MAX_QUANTITY),
    )
    return select(
        *StockTransaction.__table__.columns,
        Item.name.label("item_name"),
        reversed_by.label("reversed_by_transaction_id"),
        can_reverse.label("can_reverse"),
    ).select_from(StockTransaction).join(Item, Item.id == StockTransaction.item_id)


def transaction_view(session: Session, transaction_id: int):
    return session.execute(
        transaction_query().where(StockTransaction.id == transaction_id),
    ).one()


def request_fingerprint(operation: TransactionType, target_id: int, body: StockRequest) -> str:
    fields = body.model_dump(mode="json", exclude={"idempotency_key", "quantity"})
    quantity = getattr(body, "quantity", None)
    fields["quantity"] = decimal_string(quantity) if quantity is not None else None
    payload = json.dumps([operation, target_id, fields], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def apply_stock(
    session: Session, operation: TransactionType, target_id: int, body: Adjustment | Count | StockRequest,
):
    fingerprint = request_fingerprint(operation, target_id, body)
    # Serialize a request key even across different item IDs. The item lock then serializes its ledger.
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": str(body.idempotency_key)},
    )
    existing = session.scalar(select(StockTransaction).where(
        StockTransaction.idempotency_key == body.idempotency_key,
    ))
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise InventoryError(409, "request_key_conflict", "This request ID was used for another stock action.")
        return transaction_view(session, existing.id)

    original = None
    if operation == TransactionType.REVERSAL:
        original = session.get(StockTransaction, target_id)
        if original is None:
            raise InventoryError(404, "transaction_not_found", "Stock transaction not found.")

    item = get_item(session, original.item_id if original is not None else target_id, lock=True)
    require_active(item)
    previous = item.quantity

    if original is not None:
        if not transaction_view(session, original.id).can_reverse:
            raise InventoryError(
                409, "reversal_unavailable", "This transaction can no longer be undone. Check the stock history.",
            )
        change = -original.quantity_change
    elif operation == TransactionType.COUNT:
        assert isinstance(body, Count)
        change = body.quantity - previous
    else:
        assert isinstance(body, Adjustment)
        amount = item.adjustment_step if body.quantity is None else body.quantity
        change = amount if operation == TransactionType.ADD else -amount

    resulting = previous + change
    if resulting < ZERO:
        raise InventoryError(409, "insufficient_stock", "There is not enough stock to remove that amount.")
    if resulting > MAX_QUANTITY:
        raise InventoryError(409, "quantity_limit", "The resulting quantity exceeds the storage limit.")

    item.quantity = resulting
    transaction = StockTransaction(
        item_id=item.id,
        type=operation,
        unit=item.unit,
        quantity_change=change,
        previous_quantity=previous,
        resulting_quantity=resulting,
        reason=body.reason,
        idempotency_key=body.idempotency_key,
        request_fingerprint=fingerprint,
        reverses_transaction_id=original.id if original is not None else None,
    )
    session.add(transaction)
    session.flush()
    return transaction_view(session, transaction.id)
