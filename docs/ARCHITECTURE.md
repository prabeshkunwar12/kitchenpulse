# Architecture

## Current workspace

`services/api/main.py` contains FastAPI routes, SQLAlchemy models and database logic in one file. The Dockerfile is colocated, but root `compose.yaml` builds from the missing `./api` directory. `apps/tablet` contains the Expo entry point, dependencies and assets. It renders the template screen. `apps/mobile/App.tsx` contains the inventory UI prototype and has no runnable package of its own.

## Proposed structure

```text
kitchenpulse/
├── AGENTS.md
├── README.md
├── compose.yaml
├── .env.example
├── apps/
│   └── tablet/
│       ├── App.tsx, index.ts, app.json
│       ├── .env.example
│       ├── assets/
│       └── src/
│           ├── api/
│           └── inventory/
├── services/
│   └── api/
│       ├── Dockerfile, requirements.txt, alembic.ini
│       ├── app/
│       │   ├── main.py, config.py, db.py
│       │   └── inventory/
│       │       ├── routes.py, schemas.py, models.py
│       │       └── service.py
│       ├── migrations/
│       └── tests/
└── docs/
```

Adopt `apps/tablet` as the sole Expo app. Carry over useful UI behavior from the spare screen and retire it after verifying parity and preserving its history. Keep infrastructure files in the root while Compose is the only deployment mechanism. The empty `infrastructure/` directory can house future Terraform when that work begins.

The project root has no Git repository today. The tablet scaffold has a nested repository and an untracked `.env`. Phase 1 should establish a root repository, preserve the nested history, and verify that the tablet sources and lockfile can be tracked without staging the environment file. Resolve the root `tablet/` ignore rule as part of consolidation. Confirm the import approach before relocating repository metadata.

## Runtime and write flow

The React Native app calls typed FastAPI REST endpoints. TanStack Query owns cached server state and invalidates or refreshes affected views after mutations. Keep short-lived UI state local. Introduce Expo Router when multiple routes are necessary. PostgreSQL holds the authoritative balance and transaction ledger. The container network connects FastAPI to PostgreSQL. The Mac publishes the API on loopback for local development and on an explicitly selected interface for device validation.

A stock action creates one idempotency key. Within a database transaction, the service claims the key through a uniqueness constraint, locks the item, validates the proposed balance, and commits the new quantity with one ledger entry and the durable request outcome. A competing delivery waits for the first claim to resolve, then returns its recorded outcome if the request matches. A conflicting reuse fails. The client refreshes current stock after a replay so an earlier response cannot overwrite a newer balance. Undo follows the same write path with an explicit link to the original movement and eligibility checks.

Use a single deployment and location for Phase 1. Keep category, item identity and movements explicit so a later migration can distinguish an item catalog from per-location balances and enforce location-scoped uniqueness. Tenancy, location authorization, offline synchronization and notifications receive concrete designs in later phases.
