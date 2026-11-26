from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import engine
from app.seed import seed


def json_response(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def create_item(client, category, **values):
    payload = {
        "name": "Test Salmon",
        "category_id": category,
        "unit": "kilograms",
        "quantity": "2.500",
        "minimum": "1.250",
        "target": "5.000",
        "adjustment_step": "0.125",
        **values,
    }
    return json_response(client.post("/items", json=payload), 201)


def stock(client, item, action, *, key=None, **values):
    return client.post(
        f"/items/{item['id']}/stock/{action}",
        json={"idempotency_key": key or str(uuid4()), **values},
    )


def reverse(client, transaction, *, key=None):
    return client.post(
        f"/transactions/{transaction['id']}/reverse",
        json={"idempotency_key": key or str(uuid4())},
    )


def read_item(client, item):
    return json_response(client.get(f"/items/{item['id']}"))


def history(client, item, **params):
    return json_response(client.get("/transactions", params={"item_id": item["id"], **params}))


def test_migration_and_startup(client):
    assert json_response(client.get("/health/live")) == {"status": "ok"}
    assert json_response(client.get("/health/ready")) == {"status": "ok"}
    assert json_response(client.get("/items")) == []
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001_inventory"
        assert connection.execute(text("""
            SELECT numeric_precision, numeric_scale FROM information_schema.columns
            WHERE table_name = 'items' AND column_name = 'quantity'
        """)).one() == (12, 3)


def test_catalog_create_edit_filter_and_deactivate(client, category):
    item = create_item(client, category, name="  Test Salmon  ", quantity="2.5")
    assert item["name"] == "Test Salmon"
    assert item["quantity"] == "2.500"
    assert item["recommended_replenishment"] == "2.500"
    assert item["active"] is True
    assert item["created_at"] and item["updated_at"]
    assert json_response(client.get("/categories")) == [{"id": category, "name": "Test Seafood"}]
    assert json_response(client.get("/items", params={"search": "SAL", "category_id": category})) == [item]
    assert json_response(client.get("/items", params={"search": "%"})) == []

    edit = client.patch(f"/items/{item['id']}", json={"name": "Salmon loin", "adjustment_step": "0.250"})
    assert json_response(edit)["adjustment_step"] == "0.250"
    assert read_item(client, item)["name"] == "Salmon loin"
    unit_edit = client.patch(f"/items/{item['id']}", json={"unit": "boxes"})
    assert json_response(unit_edit, 409)["error"]["code"] == "unit_has_history"
    assert json_response(client.post(f"/items/{item['id']}/deactivate"))["active"] is False
    assert json_response(client.get("/items")) == []
    assert history(client, item)["transactions"][0]["type"] == "opening"
    assert json_response(stock(client, item, "add"), 409)["error"]["code"] == "inactive_item"


def test_default_step_and_unit_edit_on_empty_stock(client, category):
    item = json_response(client.post("/items", json={
        "name": "Empty stock", "category_id": category, "unit": "bags", "quantity": "-0",
    }), 201)
    assert item["quantity"] == "0.000"
    assert item["adjustment_step"] == "1.000"
    edit = client.patch(f"/items/{item['id']}", json={"unit": "boxes"})
    assert json_response(edit)["unit"] == "boxes"
    added = json_response(stock(client, item, "add"))
    assert (added["unit"], added["resulting_quantity"]) == ("boxes", "1.000")


def test_fractional_add_remove_and_underflow(client, category):
    item = create_item(client, category)
    added = json_response(stock(client, item, "add"))
    assert (added["previous_quantity"], added["quantity_change"], added["resulting_quantity"]) == (
        "2.500", "0.125", "2.625",
    )
    removed = json_response(stock(client, item, "remove", quantity="0.375"))
    assert (removed["quantity_change"], removed["resulting_quantity"]) == ("-0.375", "2.250")
    refused = stock(client, item, "remove", quantity="2.251")
    assert json_response(refused, 409)["error"]["code"] == "insufficient_stock"
    assert read_item(client, item)["quantity"] == "2.250"
    assert [row["type"] for row in history(client, item)["transactions"]] == ["remove", "add", "opening"]


def test_stock_boundaries_and_independent_reporting(client, category):
    item = create_item(client, category, quantity="1.251")
    assert item["stock_status"] == "in_stock"
    assert json_response(client.get("/items/low-stock")) == []
    flagged = json_response(client.patch(f"/items/{item['id']}/report", json={"manual_low": True}))
    assert flagged["manual_low"] and flagged["stock_status"] == "in_stock"
    assert [entry["id"] for entry in json_response(client.get("/items/low-stock"))] == [item["id"]]

    json_response(stock(client, item, "remove", quantity="0.001"))
    assert read_item(client, item)["stock_status"] == "low_stock"
    json_response(stock(client, item, "remove", quantity="1.250"))
    zero = read_item(client, item)
    assert zero["stock_status"] == "out_of_stock"
    assert zero["manual_low"] and zero["recommended_replenishment"] == "5.000"
    resolved = json_response(client.patch(f"/items/{item['id']}/report", json={"manual_low": False}))
    assert not resolved["manual_low"] and resolved["stock_status"] == "out_of_stock"
    assert [entry["id"] for entry in json_response(client.get("/items/low-stock"))] == [item["id"]]


def test_count_history_and_linked_undo(client, category):
    item = create_item(client, category)
    first = json_response(stock(client, item, "remove"))
    count = json_response(stock(client, item, "count", quantity="3.025", reason="Shelf count"))
    assert (count["previous_quantity"], count["resulting_quantity"], count["reason"]) == (
        "2.375", "3.025", "Shelf count",
    )
    assert json_response(reverse(client, first), 409)["error"]["code"] == "reversal_unavailable"
    key = str(uuid4())
    compensation = json_response(reverse(client, count, key=key))
    assert compensation["type"] == "reversal"
    assert compensation["reverses_transaction_id"] == count["id"]
    assert compensation["resulting_quantity"] == "2.375"
    assert json_response(reverse(client, count, key=key))["id"] == compensation["id"]
    assert json_response(reverse(client, count), 409)["error"]["code"] == "reversal_unavailable"

    page = history(client, item, limit=2)
    entries = page["transactions"]
    assert [row["id"] for row in entries] == [compensation["id"], count["id"]]
    assert entries[1]["reversed_by_transaction_id"] == compensation["id"]
    assert not entries[1]["can_reverse"]
    assert [row["type"] for row in history(client, item, before_id=page["next_before_id"])["transactions"]] == [
        "remove", "opening",
    ]


def test_duplicate_request_replays_and_conflicting_payload_fails(client, category):
    item = create_item(client, category)
    key = str(uuid4())
    first = json_response(stock(client, item, "add", key=key, quantity="0.250"))
    assert json_response(stock(client, item, "add", key=key, quantity="0.25")) == first
    assert json_response(stock(client, item, "add", key=key, quantity="0.251"), 409)["error"]["code"] == (
        "request_key_conflict"
    )
    assert read_item(client, item)["quantity"] == "2.750"
    assert len(history(client, item)["transactions"]) == 2


def test_concurrent_stock_adjustments_are_serialized(client, category):
    item = create_item(client, category, quantity="0")
    with ThreadPoolExecutor(max_workers=8) as workers:
        responses = list(workers.map(lambda _: stock(client, item, "add"), range(16)))
    for response in responses:
        json_response(response)
    rows = history(client, item)["transactions"]
    assert read_item(client, item)["quantity"] == "2.000"
    assert len(rows) == 17
    assert all(new["previous_quantity"] == old["resulting_quantity"] for new, old in zip(rows, rows[1:]))


def test_concurrent_duplicates_and_reversals_write_once(client, category):
    item = create_item(client, category)
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as workers:
        writes = list(workers.map(lambda _: stock(client, item, "add", key=key), range(4)))
        added = [json_response(response) for response in writes]
        assert len({entry["id"] for entry in added}) == 1
        undos = list(workers.map(lambda _: reverse(client, added[0]), range(4)))
    assert sorted(response.status_code for response in undos) == [200, 409, 409, 409]
    assert read_item(client, item)["quantity"] == "2.500"
    assert len(history(client, item)["transactions"]) == 3


@pytest.mark.parametrize("field,value", [
    ("quantity", "-0.001"),
    ("quantity", "0.0001"),
    ("quantity", "1000000000.000"),
    ("quantity", "NaN"),
    ("quantity", 0.125),
    ("minimum", False),
    ("minimum", "-1"),
    ("target", "1000000000"),
    ("adjustment_step", "0"),
    ("unit", "gallons"),
    ("name", "  "),
    ("name", "salmon\x00"),
    ("category_id", 2147483648),
])
def test_invalid_catalog_input(client, category, field, value):
    payload = {"name": "Test", "category_id": category, "unit": "litres", field: value}
    assert json_response(client.post("/items", json=payload), 422)["error"]["code"] == "invalid_request"


def test_http_errors_and_quantity_overflow(client, category):
    item = create_item(client, category, quantity="999999999.999")
    assert json_response(stock(client, item, "add"), 409)["error"]["code"] == "quantity_limit"
    assert json_response(stock(client, item, "add", quantity="0"), 422)["error"]["code"] == "invalid_request"
    assert json_response(stock(client, item, "remove", key="invalid"), 422)["error"]["code"] == "invalid_request"
    assert json_response(client.post("/items", json={
        "name": item["name"], "unit": "kilograms", "category_id": category,
    }), 409)["error"]["code"] == "duplicate_item"
    assert json_response(client.post("/items", json={
        "name": "Other", "unit": "kilograms", "category_id": category + 1,
    }), 422)["error"]["code"] == "unknown_category"
    assert json_response(client.patch(f"/items/{item['id']}", json={"quantity": "1"}), 422)
    assert json_response(client.get("/items/999"), 404)["error"]["code"] == "item_not_found"


def test_database_rejects_negative_and_rolls_back_invalid_ledger(client, category):
    item = create_item(client, category)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE items SET quantity = -1 WHERE id = :id"), item)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE items SET quantity = 8 WHERE id = :id"), item)
        connection.execute(text("""
            INSERT INTO stock_transactions (item_id, type, unit, quantity_change, previous_quantity,
                resulting_quantity, request_fingerprint, idempotency_key)
            VALUES (:id, 'add', 'kilograms', 1, 2.500, 8, 'test', gen_random_uuid())
        """), item)
    assert read_item(client, item)["quantity"] == "2.500"
    assert len(history(client, item)["transactions"]) == 1


def test_demo_seed_is_repeatable_and_preserves_changed_quantities(client):
    with Session(engine) as session, session.begin():
        assert seed(session) == 27
    items = json_response(client.get("/items"))
    assert len(items) == 27
    assert len(json_response(client.get("/categories"))) == 9
    assert all(item["name"].startswith("Demo · ") for item in items)
    assert {item["stock_status"] for item in items} == {"out_of_stock", "low_stock", "in_stock"}
    item = next(entry for entry in items if entry["quantity"] == "7.500")
    adjustment = json_response(stock(client, item, "add"))
    json_response(client.patch(f"/items/{item['id']}", json={"name": "Renamed demo item"}))
    with Session(engine) as session, session.begin():
        assert seed(session) == 0
    assert len(json_response(client.get("/items"))) == 27
    assert read_item(client, item)["quantity"] == adjustment["resulting_quantity"]
    assert len(history(client, item)["transactions"]) == 2
