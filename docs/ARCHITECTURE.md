# Architecture

KitchenPulse runs a native tablet client and one FastAPI service backed by PostgreSQL. The Compose database is private to its project. The API publishes on loopback by default. The iPad uses an explicit temporary LAN bind during local acceptance testing.

```text
kitchenpulse/
├── compose.yaml, .env.example
├── apps/tablet/
│   ├── App.tsx, index.ts, app.json, .env.example
│   ├── assets/
│   └── src/
│       ├── api/client.ts
│       └── inventory/
│           ├── InventoryScreen.tsx
│           ├── actions.ts
│           └── components.tsx
├── services/api/
│   ├── Dockerfile, requirements.txt, alembic.ini
│   ├── app/
│   │   ├── main.py, db.py, seed.py
│   │   └── inventory/
│   │       ├── models.py, schemas.py, routes.py
│   │       └── service.py
│   ├── migrations/
│   └── tests/
└── docs/
```

## Tablet

`apps/tablet` is the canonical Expo app. It has one landscape screen with inventory, attention and history views. TanStack Query owns cached server state. The UI holds search, category selection, dialogs and in-flight actions in memory. It refreshes affected queries after a stock action and retains the same request UUID for a retry when the outcome is uncertain. The API remains authoritative for decimal balances and stock status.

The original Expo scaffold commit was preserved in the ignored local `.tablet-git-backup/` directory. The root repository can now track the tablet files directly. The retired `apps/mobile/App.tsx` draft is available in root Git history.

## Stock writes

The API validates input before opening a stock transaction. It takes a transaction-scoped PostgreSQL advisory lock keyed by the request UUID and checks for a recorded transaction with that key. New writes then acquire the item's row lock. The item balance and the immutable ledger entry commit together. A matching retry returns the existing transaction. Reusing the UUID with a different operation, item, quantity or reason returns a conflict.

A reversal uses the same write path and inserts a new entry linked to the original transaction. The service checks the current balance, newer physical counts, item activity and previous reversals while it holds the item lock. PostgreSQL constraints protect balances, arithmetic, transaction types, unique keys and the reversal relationship.

The system currently uses a single location. Inventory catalog and ledger are explicit so a later migration can introduce per-location balances. Authentication, offline synchronization, device identity and push alerts belong to later milestones.
