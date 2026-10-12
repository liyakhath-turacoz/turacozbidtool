# Turacoz Bid Tool

A location based marketplace where buyers request offers for products and eligible dealers submit bids. The project contains one FastAPI backend, a React web app, and a Flutter mobile app.

```text
backend/  FastAPI API, WebSocket events, MySQL/MariaDB schema and seed scripts
web/      React + Vite portal for admins, buyers, and dealers
mobile/   Flutter app for Android and web
products/ Optional Icecat product catalog bundle
```

## Requirements

- Python 3.10 or newer
- MariaDB or MySQL
- Node.js and npm for the React app
- Flutter with Dart SDK 3.12.2 or newer for the mobile app

## Database and demo data

The backend connects to a local database named `turacoz_bidtool` by default. Before first setup, copy `.env.example` to `.env` and configure `TURACOZ_DB_PASSWORD`, `TURACOZ_ADMIN_PASSWORD` and a unique `TURACOZ_JWT_SECRET`. The backend loads this private file automatically; explicit process environment variables take precedence. Existing local settings are preserved in `.env`, which is excluded from Git. The SQL setup files contain password placeholders that must be replaced before manual execution.

To initialize an empty local database and add demo records, run:

```powershell
python backend\scripts\seed_test_accounts.py --reset
```

The script securely prompts for the MariaDB/MySQL root password. `--reset` drops the configured database and permanently deletes its current data. To keep an existing database, omit `--reset`:

```powershell
python backend\scripts\seed_test_accounts.py
```

The seed creates 20 buyers, 20 subscribed dealers, saved demo locations, coverage areas, and one sample request with offers if there are no active requests. Demo product records are added only when there are no usable active products linked to active categories. The seed is repeatable and does not truncate product catalogs, categories, or bidding history.

Demo sign-ins:

- Admin: `admin@turacoz` with the password configured in `TURACOZ_ADMIN_PASSWORD`
- Buyers: `buyer1` through `buyer20`; each password matches the username
- Dealers: `dealer1` through `dealer20`; each password matches the username

Set `TURACOZ_ADMIN_PASSWORD` before the first seed. Startup seeding preserves an existing admin password. Database credentials and the signing secret have no built-in defaults; keep the configured values private. Changing the signing secret invalidates existing login sessions.

## Start the backend

Start the MariaDB/MySQL service, then run from the project root:

```powershell
pip install -r backend\requirements.txt
python server.py
```

The API listens on `http://localhost:8000`. Check `http://localhost:8000/health` after the database is available.

### Database storage errors

Startup and `/health` check that every existing application table can be read. Storage/connection failures return HTTP 503. To identify an affected table without changing data, run:

```powershell
python backend\scripts\check_database.py
```

InnoDB errors such as `1030 / 194` or `1812` with "Tablespace is missing" indicate a missing table data file. Restore the affected table from a database backup; Python package reinstallations cannot restore that file. See [MariaDB recovery guidance](https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-troubleshooting/innodb-data-dictionary-troubleshooting).

For the specific case where **only** `product_specifications` has a missing tablespace and every product is an Icecat catalog product with retained highlights, stop the backend and run:

```powershell
python backend\scripts\check_database.py --restore-catalog-specs
```

This explicit recovery snapshots retained product highlights and table metadata under `backend/recovery/`, verifies a populated replacement table, then replaces the unusable table entry. It preserves product IDs and bidding/account records. Specifications edited only in the missing file cannot be recovered from the retained highlights. The tool refuses repairs of healthy tables, manual product catalogs, or other damaged tables. Startup never performs this replacement automatically. Keep recovery snapshots private; they are excluded from Git.

Backend environment variables are listed in [.env.example](.env.example). The backend loads the root `.env` file automatically. Set `TURACOZ_CORS_ORIGINS` to a comma separated list when the web app is hosted on other origins. The default allows the local React and Flutter web development ports.

## Start the React web app

In a second terminal:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. To use a different API host, copy [web/.env.example](web/.env.example) to `web/.env` and set `VITE_API_BASE_URL`.

## Run the Flutter app

For Android Emulator, use `10.0.2.2` to reach the API running on the host computer:

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

For a physical phone, use the computer's LAN address, such as `http://192.168.1.20:8000`, and allow that origin through the local firewall. Flutter web can use the default `http://localhost:8000` API; its local development origin is allowed by default.

Build an Android APK with the API URL reachable from that device:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

## Product catalog

The current local database contains **21,676 products, all active**, verified on 12 October 2026 after removing temporary test records. The database, downloaded catalog shards, account data and private settings are excluded from the Git repository. A fresh clone can seed demo products or import an independently supplied catalog bundle.

When `products/manifest.json` and all referenced compressed catalog shards are present, backend startup imports that catalog once per version by default. Set `TURACOZ_IMPORT_PRODUCTS_ON_STARTUP=false` to disable startup imports and import manually:

```powershell
python backend\scripts\import_product_catalog.py --products-root products
```

The `add_dummy_data.py` seed does not clear catalog data. See [products/README.md](products/README.md) for the bundle format and the explicit `--replace-existing` option.

## Admin panel

**Products / Catalog** searches the complete catalog, with category, brand, status, price and sorting filters and 50 products per page. Product creation and editing validate required fields and price ranges. Archived products remain available to admin and are hidden from buyers. Products with bidding history retain their identity; prices, specifications and status remain editable. Product deletion preserves historical requests and offers. Categories used by products or dealer profiles cannot be deleted until those records are reassigned.

**Buyer Management** includes saved addresses even before a buyer creates a request and shows actual winning purchase prices/counts. **Dealer Management** includes verification, subscription, coverage details, reports and status history. Pending, verified, active, held, suspended, flagged and banned states are available; deletion requires confirmation. Held, suspended and banned accounts lose marketplace access. Admin accounts are protected from marketplace moderation and profile deletion.

## Bidding flow

1. A buyer saves a map pinned location, picks a product, and starts a request.
2. The backend matches subscribed dealers by account/verification rules, product category/item type, and each dealer's configured radius, city, district, or state coverage. Manufacturer/brand does not restrict matching. The configured broadcast cap is applied after sorting eligible matches by distance where pins are available.
3. Eligible dealers receive the request and can submit, update, or withdraw offers before expiry. A withdrawn offer can be submitted again while the request is open and the dealer remains eligible.
4. Each offer is a **final total for all requested units, after discount**. The discount field records savings already included in that total. It is not subtracted again, and the total is not multiplied by quantity.
5. The buyer selects one currently eligible offer; the request becomes awarded and competing active offers become lost. This records offer selection; fulfillment tracking is not implemented.
6. The buyer and winning dealer immediately see each other's contact details and can use a private conversation attached to that winning bid. Either can report the other; admin receives the complaint and can inspect the bid conversation. Subscription covers participation: selecting a winner creates no commission or commission invoice. Other participating dealers see the winning price, terms and final statuses, with private contact fields hidden.

Request expiry is in minutes in the API (`expiry_minutes`), with absolute limits of 1 minute to 72 hours and additional configured duration bounds. Omitting the duration uses the configured default. Positive `radius_km` adds a buyer distance limit; zero uses dealer coverage alone. An optional minimum price decrease applies to revisions; it defaults to zero (disabled), and terms may change at the same total.

Saved location edits preserve locations used by existing requests. Account deletion removes access and closes active activity while retaining bidding and financial history. Schema upgrades run at the next backend startup; details are in [ISSUES.md](ISSUES.md).

Dealer subscription activation is currently a demo flow; no payment provider is connected. Historical commission/payment records are retained for auditing and do not gate contacts or chat.

## Location and live updates

Search an address, area or pincode and choose a result, or select **Use my location** to request browser/device permission. Drag the pin or tap the map, then confirm it before saving. Browser location requires localhost or HTTPS. Denied permissions and failed address lookups have search/manual-address fallbacks. Search uses the backend's cached, paced Nominatim-compatible provider; configure `TURACOZ_GEOCODING_BASE_URL` to change it. Map tiles are attributed to OpenStreetMap.

Radius coverage measures the distance between the dealer's shop pin and the buyer's delivery pin using latitude/longitude. The displayed circle uses the effective radius, capped by the admin setting. Product choices identify categories and item types, across manufacturers. Current subscription and eligibility are rechecked when listing incoming requests, bidding and selecting a winner; login also returns the current subscription state.

Web logins are stored per tab, so separate incognito tabs can use different accounts. Same-account tabs have separate WebSockets and all receive events. Personalized, versioned request snapshots update competing offers and open offer dialogs directly; private bid and support messages are pushed immediately. Reconnection reloads missed offers and open conversations while preserving message drafts. Requests display their IDs to distinguish separate auctions for the same product.

Admin controls default, minimum and maximum bidding duration under **Platform Rules & Categories** on web and **Platform Rules & Settings** on Flutter. Buyers choose within these limits; setting all three durations equal enforces a fixed duration. Existing requests keep the deadline saved at creation. Dealers cannot extend it through revisions.

## End-to-end checks

With the backend and React development server running, execute from the project root:

```powershell
python backend\scripts\e2e_bidding.py
python backend\scripts\e2e_bidding.py --suite live
python backend\scripts\e2e_bidding.py --suite profile
python backend\scripts\e2e_bidding.py --suite admin
```

Install web dependencies first (`npm install` in `web`). The checks use installed Microsoft Edge in headless mode; `E2E_BROWSER` can select another installed Playwright channel. `E2E_API_URL` and `E2E_WEB_URL` override local defaults. Temporary fixture accounts use the existing product catalog and are cleaned up afterward. The browser address responses are mocked for repeatability; login, saved pins, subscriptions, matching, offers and messages use the real API/database. Successful runs write [E2E_RESULTS.md](E2E_RESULTS.md) and [LIVE_E2E_RESULTS.md](LIVE_E2E_RESULTS.md).

The profile suite also checks subscription and deletion buttons using only its temporary account. See [BUSINESS_PROFILE_E2E_RESULTS.md](BUSINESS_PROFILE_E2E_RESULTS.md). Connection reuse and transaction failure checks run with `python -m unittest backend.tests.test_connection_cache`.

The admin suite creates temporary categories/products/accounts, checks the real admin forms and protected API operations, and removes its fixtures afterward. See [ADMIN_E2E_RESULTS.md](ADMIN_E2E_RESULTS.md).

To check the built Flutter web interface, build it with `flutter build web --release` in `mobile`, serve it from the project root with `python -m http.server 5180 --bind 127.0.0.1 --directory mobile/build/web`, and run `python backend\scripts\e2e_bidding.py --suite mobile` in another terminal. Set `E2E_MOBILE_URL` when using a different URL and allow that origin in the backend CORS configuration. Results are written to [MOBILE_WEB_E2E_RESULTS.md](MOBILE_WEB_E2E_RESULTS.md).

## Rebuild existing apps after source changes

The backend serves `web/dist` when a production web bundle is present. To update that bundle, run `npm run build` in `web`. Rebuild the Flutter app using the Android build command above. On Windows, Flutter plugins require Developer Mode/symlink support. See [ISSUES.md](ISSUES.md) for validation details and remaining mobile build limitations.

## Related documentation

- [Web app README](web/README.md)
- [Mobile app README](mobile/README.md)
- [Product catalog README](products/README.md)
- [Current code audit and fixes](ISSUES.md)
