from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_session

from . import service
from .models import Category, Item, StockTransaction, TransactionType
from .schemas import (
    Adjustment, CategoryRead, Count, HistoryPage, ItemCreate, ItemRead, ItemUpdate,
    Report, StockRequest, TransactionRead,
)

router = APIRouter()
Database = Annotated[Session, Depends(get_session)]
ResourceId = Annotated[int, Path(gt=0, le=2147483647)]
CategoryFilter = Annotated[int | None, Query(gt=0, le=2147483647)]
SearchFilter = Annotated[str | None, Query(max_length=100, pattern=r"^[^\x00]*$")]


@router.get("/categories", response_model=list[CategoryRead])
def categories(session: Database):
    return session.scalars(select(Category).order_by(Category.name, Category.id)).all()


def catalog_query(category_id: int | None, search: str | None):
    statement = select(Item).where(Item.active)
    if category_id is not None:
        statement = statement.where(Item.category_id == category_id)
    if search and search.strip():
        statement = statement.where(Item.name.icontains(search.strip(), autoescape=True))
    return statement.order_by(Item.name, Item.id)


@router.get("/items", response_model=list[ItemRead])
def items(session: Database, category_id: CategoryFilter = None, search: SearchFilter = None):
    return session.scalars(catalog_query(category_id, search)).all()


@router.get("/items/low-stock", response_model=list[ItemRead])
def low_stock(session: Database, category_id: CategoryFilter = None, search: SearchFilter = None):
    statement = catalog_query(category_id, search).where(or_(Item.quantity <= Item.minimum, Item.manual_low))
    return session.scalars(statement).all()


@router.post("/items", status_code=201, response_model=ItemRead)
def create(body: ItemCreate, session: Database):
    with session.begin():
        item = service.create_item(session, body)
        return ItemRead.model_validate(item)


@router.get("/items/{item_id}", response_model=ItemRead)
def item(item_id: ResourceId, session: Database):
    return service.get_item(session, item_id)


@router.patch("/items/{item_id}", response_model=ItemRead)
def edit(item_id: ResourceId, body: ItemUpdate, session: Database):
    with session.begin():
        entry = service.get_item(session, item_id, lock=True)
        return ItemRead.model_validate(service.update_item(session, entry, body))


@router.post("/items/{item_id}/deactivate", response_model=ItemRead)
def deactivate(item_id: ResourceId, session: Database):
    with session.begin():
        entry = service.get_item(session, item_id, lock=True)
        entry.active = False
        session.flush()
        return ItemRead.model_validate(entry)


def stock(session: Session, operation: TransactionType, target_id: int, body: StockRequest):
    with session.begin():
        return TransactionRead.model_validate(service.apply_stock(session, operation, target_id, body))


@router.post("/items/{item_id}/stock/add", response_model=TransactionRead)
def add(item_id: ResourceId, body: Adjustment, session: Database):
    return stock(session, TransactionType.ADD, item_id, body)


@router.post("/items/{item_id}/stock/remove", response_model=TransactionRead)
def remove(item_id: ResourceId, body: Adjustment, session: Database):
    return stock(session, TransactionType.REMOVE, item_id, body)


@router.post("/items/{item_id}/stock/count", response_model=TransactionRead)
def count(item_id: ResourceId, body: Count, session: Database):
    return stock(session, TransactionType.COUNT, item_id, body)


@router.patch("/items/{item_id}/report", response_model=ItemRead)
def report(item_id: ResourceId, body: Report, session: Database):
    with session.begin():
        entry = service.get_item(session, item_id, lock=True)
        service.require_active(entry)
        entry.manual_low = body.manual_low
        session.flush()
        return ItemRead.model_validate(entry)


@router.get("/transactions", response_model=HistoryPage)
def history(
    session: Database,
    item_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
    before_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    statement = service.transaction_query().order_by(StockTransaction.id.desc()).limit(limit + 1)
    if item_id is not None:
        statement = statement.where(StockTransaction.item_id == item_id)
    if before_id is not None:
        statement = statement.where(StockTransaction.id < before_id)
    entries = session.execute(statement).all()
    return HistoryPage(
        transactions=[TransactionRead.model_validate(entry) for entry in entries[:limit]],
        next_before_id=entries[limit - 1].id if len(entries) > limit else None,
    )


@router.post("/transactions/{transaction_id}/reverse", response_model=TransactionRead)
def reverse(transaction_id: ResourceId, body: StockRequest, session: Database):
    return stock(session, TransactionType.REVERSAL, transaction_id, body)
