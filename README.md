# KitchenPulse

KitchenPulse is a restaurant inventory station for iPad. Kitchen staff should be able to update stock in one tap, while management can see current quantities and items requiring attention. The first local milestone uses synthetic inventory for a Yumi Sushi–style kitchen in Prince Edward Island.

## Current starter

The project contains a FastAPI prototype in `services/api`, an Expo scaffold in `apps/tablet`, and a separate inventory UI draft in `apps/mobile/App.tsx`. The Expo scaffold opens its template screen. The root Compose definition references an absent `./api` build directory. See the [assessment and verification results](docs/PROGRESS.md) and the [Phase 1 plan](docs/ROADMAP.md#phase-1-implementation-and-acceptance-criteria).

## Inspect the existing stack

On the assessed Mac, an existing KitchenPulse Compose project publishes port 8000. These commands inspect it without changing inventory. Use a different port or project name when bringing up an isolated future development or test stack. Keep the existing volume intact until its contents and migration needs have been confirmed.

```sh
docker info --format '{{.ServerVersion}}'
docker compose version
docker compose ls
docker compose config --quiet
curl --fail --silent --show-error http://127.0.0.1:8000/openapi.json -o /dev/null
```

Swagger for the existing instance is available at [localhost:8000/docs](http://localhost:8000/docs). `GET /items` and `GET /history` can be checked there. A valid Compose parse alone does not verify that the build context exists. The current instance publishes on all host interfaces and serves an unauthenticated API. Keep it on a trusted network and use synthetic data.

## Start the current Expo scaffold

Use a Node release supported by Expo SDK 58 and pnpm. The assessed Mac's Node 22.14.0 satisfies the SDK and lockfile minimum on the Node 22 line. See the [Expo SDK 58 requirements](https://docs.expo.dev/versions/v58.0.0/).

```sh
cd apps/tablet
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
pnpm start
```

This opens the Expo template. A compatible Expo Go runtime can preview it when available for the target device. Check the current Expo account and device installation requirements before relying on it. See [Expo's physical iOS setup](https://docs.expo.dev/get-started/set-up-your-environment/?device=physical&mode=expo-go&platform=ios).

## Phase 1 local runbook

These steps describe the workflow once the [planned startup and integration work](docs/ROADMAP.md) lands.

1. Start Docker Desktop. Copy the future root `.env.example` to `.env` and supply local values for PostgreSQL and the API bind. Use loopback for Mac-only work. Choose a spare host port and a distinct Compose project name while the prototype is running.
2. Build and start the new project. Apply the migrations with the new project's Alembic configuration, then run its explicit demo seed command. Use the same project name for every command.

   ```sh
   docker compose -p kitchenpulse-dev config --quiet
   docker compose -p kitchenpulse-dev up -d --build
   docker compose -p kitchenpulse-dev exec api alembic upgrade head
   docker compose -p kitchenpulse-dev ps
   ```

3. Check readiness and Swagger on the selected port. Run the backend pytest suite against an isolated migrated PostgreSQL database. Run the tablet typecheck and lint commands from `apps/tablet`.
4. For physical-device testing, opt into a trusted LAN bind and set `EXPO_PUBLIC_API_URL=http://<mac-lan-address>:<host-port>` in `apps/tablet/.env`. The endpoint is public app configuration. The iPad and Mac should be able to reach each other on the same trusted network. If the app cannot connect, verify the Mac's API bind, firewall, Wi-Fi client isolation, iPad local-network permission, and the build's transport settings. See [local network permission](https://developer.apple.com/documentation/bundleresources/information-property-list/nslocalnetworkusagedescription) and [Apple's local networking transport settings](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsallowslocalnetworking).
5. Use full Xcode compatible with the installed macOS and the Expo SDK. Connect and trust the intended iPad and complete local signing and Developer Mode setup. After the app is configured for local native development, run `pnpm exec expo run:ios --device` from `apps/tablet`. The build and the iPad can be checked with [Expo's local build guide](https://docs.expo.dev/guides/local-app-development/) and [iOS Developer Mode guide](https://docs.expo.dev/guides/ios-developer-mode/).

### Smoke and acceptance tests

| Where | Verify |
| --- | --- |
| PostgreSQL and API | Clean migration and repeatable seed. Create, read, edit and archive an item. Add and remove stock, hit minimum and zero, set and clear a manual report, and undo an eligible movement. Check that history agrees with the resulting balance. Restart only the new development stack and confirm data remains. |
| Automated database tests | Negative, zero, out-of-range and invalid quantities as appropriate to each operation. Duplicate requests, concurrent movements, concurrent undo, constraints, and rollback. Use a disposable test database. |
| Physical iPad | Open in landscape, locate an item by category and search, adjust in one tap, review history and undo. Check temporary loss of Wi-Fi and safe retry. Verify VoiceOver, touch targets, readable stock status and Guided Access. Record device, OS, build and observed task times. See [Apple's Guided Access instructions](https://support.apple.com/en-ca/111795). |

## Project documentation

- [Engineering instructions](AGENTS.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database](docs/DATABASE.md)
- [Roadmap and acceptance criteria](docs/ROADMAP.md)
- [Progress and initial assessment](docs/PROGRESS.md)
- [Changelog](docs/CHANGELOG.md)
- [Decisions](docs/DECISIONS.md)
