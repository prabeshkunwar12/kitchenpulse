# Progress

## 2026-11-26 · Initial repository assessment

The existing Docker stack serves read requests from the current backend source, and the Expo scaffold typechecks. Phase 1 implementation is pending. This session changed project documentation only.

### Workspace inventory

| Area | State |
| --- | --- |
| Root | Compose, a root ignore file, VS Code Python environment setting, and the initial README. No root Git repository. The root ignore pattern `tablet/` would exclude the canonical tablet directory when setting up Git. |
| `services/api` | One 89-line Python module, a Python 3.12 slim Dockerfile, and direct dependency pins for FastAPI, Uvicorn, SQLAlchemy and psycopg. Pydantic is used via the FastAPI dependency tree. No Alembic, pytest suite, seed command or API readiness route. |
| `apps/tablet` | Nested Git repository with an initial scaffold commit and an untracked, unignored `.env`. Expo SDK 58, React Native 0.88.1, React 19.3.0, strict TypeScript and a pnpm lockfile. It contains app configuration, a registered entry point, template screen, Expo scaffold license, development tooling instructions/settings, app icons and splash assets. Expo caches and installed dependencies are generated. |
| `apps/mobile` | One React Native prototype screen with hardwired REST calls and no standalone package or native entry point. |
| `docs` and `infrastructure` | Initially empty. Persistent docs are now in place. Infrastructure is reserved for later work. |

### Mac and checks

| Tool or check | Result |
| --- | --- |
| Host and tooling | Apple silicon (arm64), macOS 26.5.2. Git 2.49.0, Homebrew 5.1.6, Node 22.14.0 (arm64), npm 10.9.2, pnpm 10.8.0 and Corepack present. GitHub CLI and host `psql` were absent from PATH. |
| Python | Host Python 3.13.3 with pip 25.1.1. The inspected host interpreter lacked the backend and test dependencies. The Dockerfile uses Python 3.12. The backend source passed a Python AST parse. |
| Docker Desktop | Client and daemon 29.3.1, Compose v5.1.1. Daemon access required permission outside the sandbox. The existing API container was running and the PostgreSQL container reported healthy. The container and workspace `main.py` SHA-256 checksums matched. |
| Compose | `docker compose config --quiet` passed. Inspecting the resolved build context confirmed that `./api` is missing. The existing stack already owns port 8000 and publishes it on IPv4 and IPv6 host interfaces. A clean build was not attempted against this configuration. |
| Existing API | Read-only `GET /openapi.json`, `GET /items` and `GET /history` returned HTTP 200 on localhost after network sandbox access was granted. No write path or restart was tested against the existing inventory. |
| Expo | `pnpm exec tsc --noEmit` passed for the scaffold. Public config reported SDK 58, portrait orientation and tablet support. `pnpm exec eslint .` could not run because ESLint is absent. The separate prototype is outside this typecheck. |
| iOS | Xcode Command Line Tools are selected. Full Xcode and Simulator were unavailable to the checks. No physical device, SDK-matched preview, local signing, LAN reachability or Guided Access session was verified. |

### Requirements coverage and risks

| Priority | Finding | Phase 1 handling |
| --- | --- | --- |
| Blocker | Compose resolves a missing build directory. The runnable tablet app is a portrait placeholder and never calls the API. README previously described creating another scaffold and copying from an obsolete path. | Correct Compose and integrate the inventory UI into the existing scaffold. Keep verification repeatable from the root README. |
| High | The current API binds to all host interfaces and exposes unauthenticated reads and writes over HTTP. Compose holds static development credentials. The nested repository does not ignore its local environment file. | Use local environment values, a loopback default, an explicit trusted LAN test bind and synthetic data. Keep PostgreSQL private and add env examples and Git ignore coverage. |
| High | Create/list exist; item detail, metadata edits, removal or archival, real category records and demo seeding are missing. Unit/category accept free text, whitespace and coercible quantities can pass, and numeric ranges and database checks are incomplete. Concurrent duplicate names can escape the preliminary lookup and cause an unhandled uniqueness failure. | Add validated catalog CRUD, database constraints, stable category references, typed contracts, safe uniqueness errors and a repeatable seed. |
| High | Stock changes update quantity and movement in one SQLAlchemy transaction with an item row lock on PostgreSQL. No durable request identity exists. SQLite fallback lacks equivalent row locking. An uncertain response can lead to repeated changes. | Use PostgreSQL as the Phase 1 authority, enforce idempotency, and exercise retries and concurrent writes in PostgreSQL. |
| High | Undo locks the target row and compensates, but mutates a `reversed` flag and adds an unlinked row carrying the same flag. Opening balances are currently undoable. History size is fixed and new actions cannot distinguish original, reversed and compensating entries through an explicit relationship. | Record typed, linked compensation; define eligibility; enforce uniqueness and history pagination. Verify rejected and concurrent undo paths. |
| Medium | Calculated low stock and manual reporting work in the source. The original combined flag conflates zero, threshold and manual report in the UI. No push notification exists. | Show independent stock and report indicators. Push remains Phase 3. |
| Medium | The draft offers text search, stock buttons, reporting, history and an undo confirmation. It has no explicit category filter, accessible labels, loading or empty states, per-item mutation handling or safe retry. Refresh makes redundant requests and errors may expose raw response bodies. | Implement Phase 1 tablet interaction checks, typed network errors, clear feedback and a single workflow for reconciling writes. |
| Medium | Startup schema creation offers no migration tracking or safe upgrade story. Existing PostgreSQL data has unknown value. History joins the current item name, so renames affect older display labels. No actor/device identity is recorded. | Start with a separate development volume and migrations. Decide legacy handling before migrating. Preserve sufficient historical context. Authentication and device attribution follow Phase 3. |
| Deferred | Physical counts, photography and tablet configuration are absent. Management, offline sync, purchasing, push, cloud and analytics are later milestones. | Follow the [roadmap](ROADMAP.md). |

### Next session

Start Phase 1.1. Correct the Compose context, configure a separate local project and port, and verify a clean PostgreSQL-backed startup. Establish root Git tracking while preserving the nested repository history. Confirm quantity precision and the existing volume's disposition before writing the first migration. Device access and signing can be checked in parallel with local backend work.
