# KitchenPulse engineering instructions

KitchenPulse is a restaurant inventory application for a dedicated iPad and a future management interface. The first milestone is a local, native iPad flow backed by FastAPI and PostgreSQL on the development Mac. Use synthetic Yumi Sushi–style inventory during development.

## Working agreements

- Start by reading [progress](docs/PROGRESS.md), the relevant [requirements](docs/REQUIREMENTS.md), and the [roadmap](docs/ROADMAP.md). Follow the instructions in `apps/tablet/AGENTS.md` for Expo work.
- Inspect existing code and local state first. Explain the proposed change and affected files, implement in small steps, run relevant checks, fix issues, update the docs, and report what ran and what remains.
- Update `docs/PROGRESS.md` after each significant session. Record material decisions, assumptions, open questions, and technical debt. Update requirements, architecture, schema, roadmap, and changelog as their contents change.
- Preserve existing user work, data, and repository history. Ask before major architecture decisions when requirements materially affect them. Obtain explicit approval before pushing, deploying publicly, incurring cloud costs, or taking destructive action.
- Use local environment variables and checked-in examples with placeholders. Keep actual credentials out of Git, logs, and Expo public variables. Use an isolated, trusted LAN for demo-device testing. Use synthetic data until operational security is ready.

## Architecture and quality

- Keep a modular monolith. Use React Native, Expo and TypeScript on the tablet, and FastAPI, SQLAlchemy, Pydantic and PostgreSQL for the REST API. Use Alembic for schema changes and pytest for backend verification.
- Keep request validation, inventory rules and UI independent. Write balances and corresponding movements atomically, prevent duplicate updates, and preserve audit history through linked compensating moves. Exercise write paths and concurrency on PostgreSQL.
- Make routine stock actions reachable in one tap from the item card. Design for landscape, obvious status, large touch targets, assistive technology, slow networks and uncertain write results.
- Add TanStack Query when integrating server state. Add routing and shared client state only when needed. SQLite offline sync, the management dashboard, AWS, Terraform, and other later-phase technology follow the roadmap. Keep Kubernetes, Kafka, and microservices outside the initial architecture.
- Verify the normal user entry points. Report the specific checks executed and any gaps. Use representative local and physical-device evidence before marking the iPad milestone complete.
