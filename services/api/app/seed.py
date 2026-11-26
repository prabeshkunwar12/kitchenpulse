"""Load synthetic sushi restaurant inventory into the local development database."""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import engine
from app.inventory.models import Category, Item, StockTransaction, TransactionType, Unit
from app.inventory.schemas import ItemCreate
from app.inventory.service import create_item


@dataclass(frozen=True)
class DemoProduct:
    name: str
    unit: Unit
    quantity: str
    minimum: str
    target: str
    step: str = "1"
    manual_low: bool = False


DEMO_PRODUCTS = {
    "Seafood": [
        DemoProduct("Salmon fillets", Unit.KILOGRAMS, "7.500", "3", "12", "0.250"),
        DemoProduct("Tuna loin", Unit.KILOGRAMS, "1.250", "1.500", "5", "0.250"),
        DemoProduct("Cooked shrimp", Unit.BAGS, "6", "2", "10"),
    ],
    "Meat": [
        DemoProduct("Chicken thighs", Unit.KILOGRAMS, "4.750", "2", "8", "0.250"),
        DemoProduct("Pork cutlets", Unit.PIECES, "0", "8", "24"),
        DemoProduct("Sliced beef", Unit.KILOGRAMS, "3.250", "1", "6", "0.250"),
    ],
    "Vegetables": [
        DemoProduct("Avocados", Unit.PIECES, "18", "8", "36"),
        DemoProduct("English cucumbers", Unit.PIECES, "5", "5", "16"),
        DemoProduct("Scallions", Unit.GRAMS, "725", "200", "1000", "50"),
    ],
    "Dry goods": [
        DemoProduct("Sushi rice", Unit.BAGS, "8", "3", "12"),
        DemoProduct("Nori sheets", Unit.BOXES, "3", "2", "6", manual_low=True),
        DemoProduct("White sesame seeds", Unit.KILOGRAMS, "0.625", "0.250", "2", "0.125"),
    ],
    "Sauces": [
        DemoProduct("Soy sauce", Unit.LITRES, "5.500", "2", "8", "0.500"),
        DemoProduct("Spicy mayo", Unit.BOTTLES, "2", "3", "8"),
        DemoProduct("Rice vinegar", Unit.LITRES, "3.750", "1", "5", "0.250"),
    ],
    "Frozen products": [
        DemoProduct("Edamame", Unit.BAGS, "12", "4", "18"),
        DemoProduct("Vegetable gyoza", Unit.BOXES, "0", "2", "6"),
        DemoProduct("Tempura shrimp", Unit.CASES, "3", "1", "5"),
    ],
    "Packaging": [
        DemoProduct("Takeout sushi trays", Unit.CASES, "5", "2", "8"),
        DemoProduct("Chopsticks", Unit.BOXES, "2", "2", "6"),
        DemoProduct("Sauce cups", Unit.CASES, "4", "1", "6"),
    ],
    "Cleaning supplies": [
        DemoProduct("Sanitizer concentrate", Unit.BOTTLES, "2", "1", "4"),
        DemoProduct("Dish detergent", Unit.BUCKETS, "1", "1", "3"),
        DemoProduct("Disposable gloves", Unit.BOXES, "7", "2", "10"),
    ],
    "Beverages": [
        DemoProduct("Sparkling water", Unit.CASES, "4", "1", "8"),
        DemoProduct("Ramune", Unit.BOTTLES, "0", "12", "36"),
        DemoProduct("Cold green tea", Unit.BOTTLES, "16", "6", "30"),
    ],
}


def seed(session: Session) -> int:
    # Keep concurrent seed invocations from racing on the same demo catalog.
    session.execute(text("SELECT pg_advisory_xact_lock(687220471)"))
    category_ids = dict(session.execute(select(Category.name, Category.id)).all())
    item_names = set(session.scalars(select(Item.name)))
    opening_keys = set(session.scalars(select(StockTransaction.idempotency_key).where(
        StockTransaction.type == TransactionType.OPENING,
    )))
    created = 0

    for name, products in DEMO_PRODUCTS.items():
        if name not in category_ids:
            category = Category(name=name)
            session.add(category)
            session.flush()
            category_ids[name] = category.id

        for product in products:
            label = f"Demo · {product.name}"
            opening_key = uuid5(NAMESPACE_URL, f"kitchenpulse/demo/{name}/{product.name}")
            if opening_key in opening_keys or label in item_names:
                continue
            item = create_item(session, ItemCreate(
                name=label,
                category_id=category_ids[name],
                unit=product.unit,
                quantity=product.quantity,
                minimum=product.minimum,
                target=product.target,
                adjustment_step=product.step,
            ), opening_key=opening_key)
            item.manual_low = product.manual_low
            created += 1

    return created


if __name__ == "__main__":
    with Session(engine) as session, session.begin():
        total = seed(session)
    print(f"Created {total} demonstration items.")
