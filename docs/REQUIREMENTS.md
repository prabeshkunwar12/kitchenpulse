# Requirements

KitchenPulse helps kitchen employees update stock in 2–5 seconds and gives management accurate quantities and visibility into low stock. The first test environment is Yumi Sushi in Prince Edward Island. The local milestone uses synthetic inventory and a single location.

## Phase 1 functional requirements

| ID | Requirement | Scope |
| --- | --- | --- |
| F1 | Catalog | Create, list, retrieve, edit and remove items from active inventory through the API. Maintain categories as records and assign each item a category, unit and minimum quantity. Preserve items referenced by history. |
| F2 | Stock movements | Add or remove one configured unit with one tap. Show current quantity and unit. Initial balances and subsequent changes produce ledger entries. Reject invalid input and stock underflow. |
| F3 | Stock status | Mark zero as out of stock and quantities at or below minimum as requiring attention. Support setting and clearing a manual report independently of the threshold. |
| F4 | History and undo | Display recent movements with item, signed amount, unit, resulting balance and timestamp. Undo an eligible change once through a linked compensating entry. An unavailable undo explains the conflict and changes no stock. |
| F5 | Native tablet | Show readable landscape cards with search, explicit category filtering, an attention view and history. Provide accessible touch controls and status feedback. Evaluate Guided Access on the intended iPad. |
| F6 | Local operation | Run FastAPI and PostgreSQL via Docker Compose on the Mac. Apply migrations, load synthetic seed data, and connect the tablet over the local network. Expose typed OpenAPI contracts and readiness checks. |

Management can configure Phase 1 inventory using the API. The tablet inventory configuration interface, product photography and formal physical counts belong to Phase 2. Recognizable category labels can ship in Phase 1. The alert mechanism in Phase 1 is in-app stock status. External push alerts and delivery are later work.

Later management workflows include real-time stock monitoring, automatic low-stock notifications and purchasing lists, supplier and employee management, financial reporting, inventory analytics, and multi-location management. See the [roadmap](ROADMAP.md) for sequencing.

## Non-functional requirements

| ID | Requirement | Acceptance signal |
| --- | --- | --- |
| N1 | Fast interaction | Starting from a visible item, the employee can record a routine stock change with one tap and see confirmation. Target 2–5 seconds for representative tasks on the pilot iPad. |
| N2 | Data integrity | Concurrent writes serialize per item. A balance and its movement commit together. Retrying a request cannot cause the same action twice. Database constraints protect ledger and stock invariants. |
| N3 | Usability and accessibility | Use text and color to distinguish attention states. Controls have meaningful VoiceOver labels and at least 44 × 44 point touch targets. Show loading, empty, failure and retry states. |
| N4 | Recoverability | Inventory survives an API and database restart. Confirmed and uncertain writes are visibly distinct. A recoverable network failure can be reconciled without repeating a movement. |
| N5 | Secure development | Configuration comes from environment variables. PostgreSQL stays private to Compose. Use loopback by default and explicitly opt into a trusted LAN for device testing. Keep trial data synthetic. |
| N6 | Maintainability | Favor typed request/response models, readable modules, repeatable dependency setup, migrations, automated database tests and a documented startup path. |

## Pending product inputs

- Which pilot items need fractional units from day one? The starter uses integers. Quantities such as kilograms and litres can represent whole packages. Fractional quantities require an explicit precision choice and decimal-safe storage and transport.
- Is any inventory in the existing PostgreSQL volume worth preserving? Confirm before adopting or migrating that volume.
- Which iPad model and iPadOS version will the pilot use, and can it use Developer Mode, local signing and a trusted network? Verify with the intended device before selecting a build path.
- Confirm whether management expects a manual report to persist until explicitly cleared after replenishment. The proposal preserves the report until cleared and always computes threshold status from current stock.
