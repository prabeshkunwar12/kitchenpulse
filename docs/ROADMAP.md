# Roadmap

| Phase | Milestone |
| --- | --- |
| 1 · Core inventory MVP | Native iPad app on a trusted LAN with a Mac-hosted FastAPI API and PostgreSQL, validated with synthetic inventory. |
| 2 · Restaurant usability | Product photographs, improved tablet workflows, inventory configuration, physical counts, quick deliveries, waste, suppliers, purchasing lists and employee testing. |
| 3 · Production readiness | Authentication, roles, device registration, offline storage and synchronization, push notifications, broader automation, hardening and backups. |
| 4 · Cloud infrastructure | AWS, Terraform, registries, GitHub Actions CI/CD, staging and production, monitoring and logging. |
| 5 · Business intelligence | Next.js management dashboard, multi-location support, valuation, supplier price and waste analysis, purchasing reports and Power BI. |
| 6 · Advanced automation | Forecasting, machine learning, POS integration, recipes, NFC and QR codes, and smart inventory hardware. |

## Phase 1 implementation and acceptance criteria

### 1.1 Establish reproducible local startup

- Affected areas include root Compose and Git configuration, API Dockerfile and health routes, and environment examples for root and tablet.
- Correct the API build context. Use required environment values and a loopback default. Leave PostgreSQL accessible only inside Compose. Set a project name and published port that avoid collisions with the running prototype. Add liveness and database readiness endpoints.
- Plan a root Git repository and preserve the tablet's nested history. Verify ignore rules for source files, local secrets, generated assets and caches before the first commit.
- **Accept when** a clean checkout can follow the README, build and start with example configuration and user-provided values, reach readiness, and show Swagger. The process has a documented way to isolate its PostgreSQL volume and can be restarted without affecting the original stack.

### 1.2 Add migrations, catalog and demo inventory

- Affected areas include API configuration, SQLAlchemy models, Pydantic schemas, FastAPI routes, Alembic and seed command.
- Confirm quantity precision and the disposition of the existing volume. Add category records, item create/list/get/update/archive, category management, units and thresholds. Add bounded and normalized input validation, typed responses and clear errors for conflicting identifiers. Prevent existing item units being silently reinterpreted.
- **Accept when** migrations bootstrap a clean PostgreSQL database and can be checked at head. Seed creates representative items in normal, low, out-of-stock and manually reported states. Repeating seed does not duplicate data or reset balances. Tests cover CRUD, invalid category and unit values, duplicate names, filtered reads, and archive preserving history.

### 1.3 Make stock changes, reports and undo reliable

- Affected areas include the API inventory service and routes, ledger migration, and PostgreSQL integration tests.
- Keep automatic threshold status and manual reports independent. Add explicit out-of-stock status and paginated history. Accept client-generated idempotency keys for stock mutations and enforce transactional replay. Add linked compensating moves and define which movement types can be undone. Report writes set an explicit state.
- **Accept when** opening stock, additions and removals produce correct balances with matching ledger entries, exact-threshold and zero cases display correctly, and a report can be set or cleared without changing quantity. Tests show that underflow, invalid deltas, unavailable reversals and forced rollbacks leave quantity and ledger consistent. Parallel stock changes serialize, retries with the same key do not double-write, conflicting reuse fails, and concurrent undo produces one compensation.

### 1.4 Connect the native tablet

- Affected areas include the tablet entry point and Expo config, API client, inventory screen and components, and tablet lint and typecheck commands.
- Implement the inventory workflow in `apps/tablet`, using behavior from the spare prototype. Add TanStack Query for server state, category and text filters, a landscape card grid, a view of low-stock and out-of-stock items, manual report controls, and history with undo. Use understandable error feedback, per-item pending state and reconciliation for uncertain writes.
- **Accept when** the SDK-compatible client shows real API data and a single tap adjusts a visible item. Search and category filters work together. Users can distinguish zero, automatic low stock and manual reports. History and undo update the affected item and views. Loss of connectivity shows a recoverable error and retry does not duplicate a write. Typecheck and lint pass.

### 1.5 Verify on the Mac and physical iPad

- Affected areas include the Compose runbook, acceptance checklist and progress log. Prepare a locally signed iOS build when signing and the device are available.
- **Accept when** a separate local stack can be started from the README, seeded and restarted with balances and history intact. On the intended iPad, verify LAN reachability, landscape layout, VoiceOver, touch targets, Guided Access, all stock workflows and network recovery. Time several routine add/remove actions from a visible card and record the observed range against the 2–5 second target. Record the macOS, iPadOS, device and build used.

A compatible Expo Go runtime can provide early UI feedback. Final sign-off requires the intended iPad and verification of the KitchenPulse build and Guided Access. Confirm signing, the pilot device and its network access before declaring the milestone complete.
