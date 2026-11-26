# Architecture decisions

## ADR 001 · Local modular monolith

**Status** Accepted from the project brief.

Use one FastAPI service backed by PostgreSQL, with modules organized around inventory. Keep the native tablet as a separate client. Run the initial stack with Compose. This minimizes deployment and debugging work while allowing data and service boundaries to be tested.

## ADR 002 · Canonical Expo application

**Status** Proposed.

Use the existing `apps/tablet` scaffold and port the useful behavior from `apps/mobile/App.tsx`. The scaffold already contains the Expo entry point, package lock, native configuration and assets. Consolidate into the root repository while preserving the nested history. Confirm the import procedure before changing Git metadata.

## ADR 003 · Stock ledger and request retries

**Status** Proposed.

Use PostgreSQL and update the item's balance, movement entry, and deduplication record in one transaction. Undo records a compensating entry linked to the original. Derive reversal status from that link. This adds durable auditability and makes a retry after lost connectivity safe. Verify lock ordering, concurrent delivery and duplicate-key behavior against PostgreSQL.

## ADR 004 · Local iPad verification

**Status** Proposed, subject to target device and signing access.

Use a local native iOS build for milestone sign-off. Confirm the iPad model, iPadOS, signing and Developer Mode. Use a loopback-only API for Mac development and explicitly opt into LAN reachability for device tests. Check local network permission and iOS transport behavior on the intended build. See [Expo local builds](https://docs.expo.dev/guides/local-app-development/) and [Apple Guided Access](https://support.apple.com/en-ca/111795).

## Decisions awaiting input

- Confirm integer package quantities or fractional precision and the relevant units before committing the schema.
- Confirm the existing PostgreSQL volume's value and whether Phase 1 needs a tested import.
- Confirm manual-report clearing behavior and preserve the proposed API-only configuration flow for Phase 1 unless day-one workflows require a change.
