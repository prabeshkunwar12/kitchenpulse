# KitchenPulse

KitchenPulse is a native inventory station for a kitchen iPad. The private development prototype uses synthetic sushi restaurant stock. It runs an Expo tablet app, a FastAPI API, and PostgreSQL on the development Mac.

## Start the development stack

Install and start Docker Desktop. Use Node compatible with Expo SDK 58 and pnpm 10.8.0 for the tablet. See the [Expo SDK requirements](https://docs.expo.dev/versions/v58.0.0/).

From the repository root, copy `.env.example` to `.env` if needed and set a unique local `POSTGRES_PASSWORD`. For an existing initialized development volume, keep its original password.

```sh
docker compose -p kitchenpulse-dev config --quiet
docker compose -p kitchenpulse-dev up -d --build --wait
docker compose -p kitchenpulse-dev exec -T api alembic current
docker compose -p kitchenpulse-dev exec -T api python -m app.seed
curl --fail http://127.0.0.1:8001/health/ready
```

The API runs migrations before starting. Swagger is at [127.0.0.1:8001/docs](http://127.0.0.1:8001/docs). PostgreSQL is private to Compose. The `kitchenpulse-dev_inventory_data` volume is separate from the original `kitchenpulse_data` volume and its API on port 8000. Seed adds up to 27 labeled demo items and can be run repeatedly. Use synthetic data with this unauthenticated API.

## Run and check the Expo app

```sh
cd apps/tablet
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint
```

Create `.env.local` from the tablet's `.env.example` if it does not already exist. `EXPO_PUBLIC_API_URL` is a client-visible URL. Keep credentials in the root backend environment. Restart Metro after changing the API URL.

For an optional browser preview on the Mac, enable one loopback origin on the API, then export and serve the Expo web bundle.

```sh
# Repository root
WEB_PREVIEW_ORIGIN=http://127.0.0.1:8082 docker compose -p kitchenpulse-dev up -d --wait

# apps/tablet
pnpm exec expo export --platform web
python3 -m http.server 8082 --bind 127.0.0.1 --directory dist
```

Open [127.0.0.1:8082](http://127.0.0.1:8082) so the browser origin matches exactly. Run `docker compose -p kitchenpulse-dev up -d --wait` from the root again to restore the default when finished. From `apps/tablet`, `pnpm exec expo export --platform ios` checks the iOS JavaScript bundle.

## Test on a physical iPad

Physical iPad testing is pending. For a local native build, use full Xcode compatible with the host macOS and SDK 58, then connect and trust the iPad, configure local signing, and enable Developer Mode. A compatible Expo Go runtime can also provide an early preview. See [Expo local builds](https://docs.expo.dev/guides/local-app-development/), [Expo's physical iOS setup](https://docs.expo.dev/get-started/set-up-your-environment/?device=physical&mode=expo-go&platform=ios) and [iOS Developer Mode](https://docs.expo.dev/guides/ios-developer-mode/).

1. On a trusted private LAN, find the Mac's LAN IPv4 address and set `MAC_LAN_IP` in the current shell. From the repository root, temporarily opt in to that interface only.

   ```sh
   API_BIND_HOST="${MAC_LAN_IP:?Set the Mac LAN IPv4 address first}" docker compose -p kitchenpulse-dev up -d --wait
   ```

2. In `apps/tablet/.env.local` set `EXPO_PUBLIC_API_URL=http://<mac-lan-ip>:8001`. With both devices on the same trusted LAN, check the readiness URL from Safari on the iPad. Grant local network access when prompted. If the native build blocks direct-IP HTTP, try the Mac's reachable `.local` hostname or check a narrow development transport configuration. See [Apple's local network permission](https://developer.apple.com/documentation/bundleresources/information-property-list/nslocalnetworkusagedescription) and [local networking transport settings](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsallowslocalnetworking).
3. From `apps/tablet`, run `pnpm exec expo run:ios --device --port 8082` for a locally signed debug build. For a compatible Expo Go preview, run `pnpm exec expo start --lan --port 8082` and open the QR code on the iPad. Keep the API local and leave router port forwarding disabled.
4. In landscape, verify search and category filters, one-tap fractional add and remove, zero and low stock, manual report and clearing, and history with undo. Verify VoiceOver, touch targets, Guided Access, and recovery from a dropped connection. Time several routine adjustments from visible cards against the 2–5 second target. See [Apple Guided Access](https://support.apple.com/en-ca/111795).
5. Restore the tablet URL to its loopback setting for Mac preview and run `docker compose -p kitchenpulse-dev up -d --wait` from the root to restore the API's loopback bind.

## Run the backend tests

Use the named test project and database. The test suite migrates the database and resets **only** its inventory tables between tests. The database has no published host port.

```sh
POSTGRES_DB=kitchenpulse_test docker compose -p kitchenpulse-test up -d --wait db
POSTGRES_DB=kitchenpulse_test docker compose -p kitchenpulse-test run --rm --no-deps --build api python -m pytest -q
```

Run `docker compose -p kitchenpulse-dev exec -T api alembic check` to compare the migrated schema with SQLAlchemy metadata. See the [database and API contract](docs/DATABASE.md) for quantity and reversal rules and the [progress log](docs/PROGRESS.md) for observed results.

## Project documentation

- [Engineering instructions](AGENTS.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database and API contract](docs/DATABASE.md)
- [Roadmap and acceptance criteria](docs/ROADMAP.md)
- [Progress and verification](docs/PROGRESS.md)
- [Changelog](docs/CHANGELOG.md)
- [Decisions](docs/DECISIONS.md)
