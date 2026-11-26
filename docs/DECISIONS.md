# Architecture decisions

## ADR 001 · Local modular monolith

**Status** Accepted.

Use one FastAPI service backed by PostgreSQL, with code organized around inventory. Run the API and database under Compose. Keep the Expo tablet a separate REST client.

## ADR 002 · Canonical Expo application

**Status** Implemented in Sprint 1.

Use `apps/tablet` and its existing Expo entry point, assets and dependency lock. The previous inventory UI informed the new screen. Preserve the original tablet Git metadata locally in `.tablet-git-backup/` and let the root repository track the app. Keep the former screen in root Git history.

## ADR 003 · Decimal ledger and request retries

**Status** Implemented in Sprint 1.

Store decimal quantities and ledger values as `NUMERIC(12,3)` and use Python `Decimal`. Transmit fractional inputs and all decimal responses as strings. Use one durable request UUID per stock action, enforced by the ledger's unique key and a transaction-scoped lock. Record undo as a linked compensation. A physical count makes earlier stock changes ineligible for undo, and a count itself can only be reversed while it is the latest ledger entry.

## ADR 004 · Private device verification

**Status** Local API and app implemented. Physical verification pending.

Default to a loopback API bind. For device testing, use an explicit temporary LAN interface on a trusted network. Keep the local browser preview opt-in and allow an explicit loopback web origin. Confirm iPad model, signing, Developer Mode, LAN access, and Guided Access for the intended tablet. See [Expo local builds](https://docs.expo.dev/guides/local-app-development/) and [Apple Guided Access](https://support.apple.com/en-ca/111795).

## ADR 005 · Legacy and test volume isolation

**Status** Implemented in Sprint 1.

The original one-item database matched the original README's demo and opening stock entry in a read-only check. Preserve that volume. Use independent Compose projects and volumes for development and tests. Tests require the exact `kitchenpulse_test` database and use it to reset inventory between cases.
