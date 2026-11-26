# Database and API contract

## PostgreSQL schema

| Table | Fields and rules |
| --- | --- |
| `categories` | Integer primary key and unique nonblank name. |
| `items` | Integer primary key, unique product name, category foreign key, validated unit, quantity, minimum, target, positive adjustment step, independent manual report flag, active flag, and creation and update timestamps. Deactivated items remain available to the ledger. An item unit can change before its first nonzero stock movement. |
| `stock_transactions` | Integer primary key, item foreign key, type, historical unit, quantity change, prior and resulting quantities, optional reason, timestamp, unique UUID idempotency key, request fingerprint, and optional original transaction reference. An item has one opening entry. A reversal references the same item and each original can have one reversal. |

Alembic revision `0001_inventory` creates the schema. The API container applies migrations before startup. `kitchenpulse-dev_inventory_data` and `kitchenpulse-test_inventory_data` are separate volumes from the prototype's `kitchenpulse_data`. The first migration is for an empty PostgreSQL database.

## Decimal quantities

Quantities, thresholds, targets, adjustment steps and ledger amounts use PostgreSQL `NUMERIC(12,3)` and Python `Decimal`. The API accepts decimal strings such as `"7.500"` and whole JSON integers. Send fractional inputs as strings. It rejects excess fractional precision, values outside the storage range, and quantities below zero. The maximum stored balance is `999999999.999`. Response quantities are strings with exactly three decimal places. The tablet preserves them as strings and formats them for display.

The step defaults to `1.000`. The server uses the current item step when an add or remove request omits `quantity`. The target determines `recommended_replenishment` as `max(0, target - quantity)`. Stock status is `out_of_stock` at zero, `low_stock` above zero and at or below the minimum, and `in_stock` above the minimum. A manual report remains set until explicitly resolved.

## Routes

| Method and path | Behavior |
| --- | --- |
| `GET /categories` | List category IDs and names. Demo seeding provisions the pilot categories. |
| `GET /items` | List active items. Optional `category_id` and `search` filters. |
| `GET /items/low-stock` | List active items that are low, out of stock or manually reported. Same optional filters. |
| `POST /items` | Create an item and its opening ledger entry. |
| `GET /items/{id}`, `PATCH /items/{id}` | Read an item and edit catalog fields. Change quantity through a stock endpoint. |
| `POST /items/{id}/deactivate` | Hide the item from active inventory and preserve history. |
| `POST /items/{id}/stock/add`, `/stock/remove` | Record a positive amount using optional `quantity` or the item step. |
| `POST /items/{id}/stock/count` | Set the absolute quantity, record the prior value and delta, and establish a new count checkpoint. |
| `PATCH /items/{id}/report` | Set `manual_low` to `true` to report or `false` to resolve. |
| `GET /transactions` | Return newest entries by ID, with optional `item_id`, `limit` and `before_id`. Pass `next_before_id` to fetch older entries. |
| `POST /transactions/{id}/reverse` | Record a compensating transaction for an eligible entry. |
| `GET /health/live`, `GET /health/ready` | Check the service and its access to the migrated ledger. |

Stock and reversal requests include a client-generated `idempotency_key` UUID and can include a `reason`. A retry of the same action uses the same UUID. A different payload or operation with that UUID returns HTTP 409. The returned ledger quantities describe the original write. The response also includes current reversal eligibility. Clients read current inventory separately.

Opening entries and reversals are ineligible for undo. An earlier add/remove becomes ineligible when a later absolute count exists. A count can be undone while it is the latest ledger entry for the item. All reversals require an active item and a resulting balance within range. The original and the compensating entries remain visible.

Validation and business errors use `{"error":{"code":"…","message":"…"}}`. Request validation also includes a list of field paths and messages. Interactive schemas and request examples are discoverable in Swagger at `/docs`.
