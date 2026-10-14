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

Import the product catalogue **before** seeding (or run the seed again afterwards). The seed links the demo dealers to the categories that exist when it runs, so dealers seeded before the import do not match any imported product and buyers see "No subscribed dealers match this product". The seed is repeatable, so re-running it after an import is safe.

The seed creates 20 buyers, 20 subscribed dealers, saved demo locations, coverage areas, and one sample request with offers if there are no active requests. Demo product records are added only when there are no usable active products linked to active categories. The seed is repeatable and does not truncate product catalogs, categories, or bidding history.

Demo sign-ins:

- Admin: `admin@turacoz` with the password configured in `TURACOZ_ADMIN_PASSWORD`
- Buyers: `buyer1` through `buyer20`; each password matches the username
- Dealers: `dealer1` through `dealer20`; each password matches the username

Set `TURACOZ_ADMIN_PASSWORD` before the first seed. Startup seeding preserves an existing admin password. Database credentials and the signing secret have no built-in defaults; keep the configured values private. Changing the signing secret invalidates existing login sessions.

### Visible product catalogue

The current visible catalogue contains 2,083 products across 16 departments and 314 manufacturer/company names. Its source rows are in `product_catalog/all_products.csv`; category totals and provenance notes are in `product_catalog/README.md`. The import script is resumable and preserves old product IDs while hiding old rows from browsing:

```powershell
python backend\catalogue_app_import.py --apply
```

The importer saves previous product visibility values in `product_catalog/app_catalog_visibility_backup.csv`. It does not delete products referenced by bids or carts. Older Icecat bundle imports stay hidden from buyer/dealer catalog search.

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

The current local database contains **21,720 available products, all active**, audited on 12 October 2026. Fourteen confirmed pre-2017 variants were retired with bidding history retained; verified recent source imports were added. Legacy release years still need verification. The database, downloaded catalog shards, account data and private settings are excluded from the Git repository. A fresh clone can seed demo products or import an independently supplied catalog bundle.

When `products/manifest.json` and all referenced compressed catalog shards are present, backend startup imports that catalog once per version by default. Set `TURACOZ_IMPORT_PRODUCTS_ON_STARTUP=false` to disable startup imports and import manually:

```powershell
python backend\scripts\import_product_catalog.py --products-root products
```

The `add_dummy_data.py` seed does not clear catalog data. See [products/README.md](products/README.md) for the bundle format and the explicit `--replace-existing` option.

See [PRODUCT_CATALOG_REPORT.md](PRODUCT_CATALOG_REPORT.md) for category/year/brand totals and [PRODUCT_SOURCES_GUIDE.md](PRODUCT_SOURCES_GUIDE.md) for the 12 manufacturer adapters, TechAPI, Icecat downloads and source configuration. Buyer and admin product filters include only category, product type, manufacturer and release year, with full-database pagination and no review-rating filters. Appliances have their own parent category.

## Admin panel

**Products / Catalog** searches the complete catalog, with category, product type, manufacturer and release-year filters, sorting and 50 products per page. Product creation and editing validate required fields and price ranges. Archived products remain available to admin and are hidden from buyers. Products with bidding history retain their identity; prices, specifications and status remain editable. Product deletion preserves historical requests and offers. Categories used by products or dealer profiles cannot be deleted until those records are reassigned.

**Product Fetch & Reports** supports manual imports, hourly intervals, daily local times, fixed one-time schedules, custom public JSON feeds, durable job history, review links and CSV statistics. New imports require release evidence and a three-year age limit. Credentials remain in private server settings. Restart an already running backend to load the new routes.

**Buyer Management** includes saved addresses even before a buyer creates a request and shows actual winning purchase prices/counts. **Dealer Management** includes verification, subscription, coverage details, reports and status history. Pending, verified, active, held, suspended, flagged and banned states are available; deletion requires confirmation. Held, suspended and banned accounts lose marketplace access. Admin accounts are protected from marketplace moderation and profile deletion.

## Bidding flow

1. A buyer saves a map pinned location, picks a product, and starts a request.
2. A request goes to **every** dealer who deals in the product and whose own service area covers the buyer's location. A dealer receives it only if they have an active subscription and an account that is **active or verified**; pending, flagged, rejected, held, suspended and banned accounts never receive requests. Category and item type say what a dealer deals in (no categories ticked means every product), and the dealer's own radius, city, district or state coverage is the only geographic rule. A dealer who ticks specific companies under **My shop** only receives requests for those companies; with none ticked, every company matches. There is no limit on how many dealers are notified, and a distance sent by a buyer client is ignored.
3. Eligible dealers receive the request and can submit, update, or withdraw offers before expiry. A withdrawn offer can be submitted again while the request is open and the dealer remains eligible.
4. Each offer is a **final total for all requested units, after discount**. The discount field records savings already included in that total. It is not subtracted again, and the total is not multiplied by quantity.
5. The buyer selects one currently eligible offer. The accept call carries a fingerprint of the terms the buyer was shown, so if the dealer revised price, warranty, delivery or extras a moment earlier, the server answers 409 and the buyer reviews the new terms instead of being awarded different ones; the request becomes awarded and competing active offers become lost. This records offer selection; fulfillment tracking is not implemented.
6. The buyer and winning dealer immediately see each other's contact details and can use a private conversation attached to that winning bid. Either can report the other; admin receives the complaint and can inspect the bid conversation. Subscription covers participation: selecting a winner creates no commission or commission invoice. Other participating dealers see the winning price, terms and final statuses, with private contact fields hidden.

Request expiry is in minutes in the API (`expiry_minutes`), with absolute limits of 1 minute to 72 hours and additional configured duration bounds. Omitting the duration uses the configured default. The request `radius_km` and `skip_flagged_dealers` fields are still accepted so older clients keep working, but they no longer change who is reached. An optional minimum price decrease applies to revisions; it defaults to zero (disabled), and terms may change at the same total.

Saved location edits preserve locations used by existing requests. Account deletion removes access and closes active activity while retaining bidding and financial history. Schema upgrades run at the next backend startup; details are in [ISSUES.md](ISSUES.md).

Dealer subscriptions are paid through Razorpay (see "Subscription payments" below). Until payments are switched on the subscription button is a free demo activation. Historical commission/payment records are retained for auditing and do not gate contacts or chat.

## Location and live updates

Search an address, area or pincode and choose a result, or select **Use my location** to request browser/device permission. Drag the pin or tap the map, then confirm it before saving. Browser location requires localhost or HTTPS. Denied permissions and failed address lookups have search/manual-address fallbacks. Search uses the backend's cached, paced Nominatim-compatible provider; configure `TURACOZ_GEOCODING_BASE_URL` to change it. Map tiles are attributed to OpenStreetMap.

Radius coverage measures the distance between the dealer's shop pin and the buyer's delivery pin using latitude/longitude. The displayed circle uses the effective radius, capped by the admin setting. Product choices identify categories and item types, across manufacturers. Current subscription and eligibility are rechecked when listing incoming requests, bidding and selecting a winner; login also returns the current subscription state.

Web logins are stored per tab, so separate incognito tabs can use different accounts. Same-account tabs have separate WebSockets and all receive events. Personalized, versioned request snapshots update competing offers and open offer dialogs directly; private bid and support messages are pushed immediately. Reconnection reloads missed offers and open conversations while preserving message drafts. Requests are identified by product, quantity, area and countdown rather than raw IDs.

Admin controls default, minimum and maximum bidding duration under **Platform Rules & Categories** on web and **Platform Rules & Settings** on Flutter. Buyers choose within these limits; setting all three durations equal enforces a fixed duration. Existing requests keep the deadline saved at creation. Dealers cannot extend it through revisions.

## What buyers see on a bid

Every bid a buyer receives shows the real shop: its name, owner, phone, email, address and GST number, plus the payment details the shop has saved (a UPI ID and, optionally, bank account details with copy buttons). Buyers can compare and contact shops before they accept. Shops still see each other only as "Dealer 1", "Dealer 2" and so on, and never see each other's contact or payment details. A shop adds its payment details under **My shop, How buyers pay you**; the bid form tells the shop what the buyer will see.

Payment details are stored with the shop's profile and are not encrypted. Shops are told to prefer UPI, and bank details are optional.

## Subscription payments

Dealers pay their subscription through the platform. The price is fixed on the server (default ₹999 for 30 days) and the browser never sets the amount.

| Mode | Set with | What it does |
| --- | --- | --- |
| `razorpay` | `TURACOZ_PAYMENT_MODE=razorpay` plus the Razorpay keys below | Real payments. UPI, cards and netbanking on Razorpay's own payment window; card and bank details never reach this server. |
| `test` | `TURACOZ_PAYMENT_MODE=test` | A built-in fake gateway that follows the same order, payment and signature steps. No money moves. For development and automated checks. |
| `demo` | `TURACOZ_PAYMENT_MODE=demo` | The old one-click free activation. This is the default when no mode is set and no Razorpay keys are present. **Set `razorpay` before going live**, or any dealer can subscribe for free. |

To switch on real payments:

1. Create a Razorpay account and, in the dashboard, generate API keys (use *test* keys first).
2. Put `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` and `TURACOZ_PAYMENT_MODE=razorpay` in `.env` (see [.env.example](.env.example)).
3. In the Razorpay dashboard add a webhook that points to `https://<your-api-address>/payments/razorpay/webhook`, enable the `payment.captured` and `order.paid` events, and put its secret in `RAZORPAY_WEBHOOK_SECRET`. The webhook completes a payment even when the dealer closes the browser before returning.
4. Restart the backend. Try a test payment with Razorpay's test card or UPI details before using live keys.

How it works: the dealer chooses **Subscribe** or **Renew**, the server creates an order for the fixed amount, and Razorpay's window collects the payment. The server then checks Razorpay's signature (HMAC-SHA256 with your key secret) before it extends the subscription, and the webhook does the same check independently. Repeating a payment or webhook never adds days twice, a payment for the wrong amount is rejected, and one dealer cannot claim another dealer's payment. Renewing early keeps the days already paid for; paying after expiry starts a fresh period. When the period ends the shop stops receiving requests and is told so; the dealer app warns seven days before. Each payment is recorded in `subscription_payments` (shown to the dealer under **My shop, Subscription**) and counted in the admin dashboard revenue; admins can list payments at `GET /admin/subscription-payments`.

Not included: GST invoices or receipts, refunds, and automatic renewal (a recurring mandate). The Flutter app still calls the free activation, which is refused once real payments are on; dealers pay in the web app.

## Dealer product catalogue and the common product database

Dealers tell the platform which products they sell, under **My products**:

- **Add from the catalogue.** Search the common database and tick **I sell this**.
- **Add a product that is not listed.** Type it in. The product is checked against the catalogue first, and only a genuinely new product is created.
- **Upload your catalogue.** A CSV or Excel (.xlsx) file, up to 3,000 products and 5 MB, using the headings in the template (**Download template**). Everyday headings such as `Product Name`, `Make`, `Model No`, `EAN` and `MRP` are understood.

There is one common product database and a product is never stored twice. Each product is recognised by independent signals: a valid barcode (GTIN/EAN/UPC), brand plus part number, brand plus model number, and brand plus the words of the name (case, punctuation, word order and spacing of units like "55 inch" and "55inch" are ignored; a "+" matters, so "Galaxy S24" and "Galaxy S24+" stay different). A match links the shop to the existing product. Products that are only *similar* are never merged automatically: the shop is asked "Is yours one of these?". The same name with a different model number is a different product. A database table (`product_identities`) lets each signal belong to exactly one product, so even two shops adding the same new product at the same moment create it once. Admin product creation and renaming use the same check and refuse a copy with a clear message.

A product a shop lists always reaches that shop: it receives requests for it even outside the categories or companies it ticked, as long as the request is inside the shop's own service area. New products added by dealers appear in the buyer catalogue straight away (source `dealer`, status `dealer_added`); an admin can edit or archive them like any other product.

Existing duplicates in an imported catalogue can be listed (read-only) with:

```powershell
python backend\scripts\audit_product_duplicates.py
python backend\scripts\audit_product_duplicates.py --csv duplicates.csv
```

An admin then decides which copy to keep and archives the others. If the matching rules in `backend/product_identity.py` ever change, raise `KEY_VERSION` there and the stored keys are rebuilt on the next catalogue action.

## End-to-end checks

With the backend and React development server running, execute from the project root:

```powershell
python backend\scripts\e2e_bidding.py
python backend\scripts\e2e_bidding.py --suite live
python backend\scripts\e2e_bidding.py --suite profile
python backend\scripts\e2e_bidding.py --suite admin
```

Install web dependencies first (`npm install` in `web`). The checks use installed Microsoft Edge in headless mode; `E2E_BROWSER` can select another installed Playwright channel. `E2E_API_URL` and `E2E_WEB_URL` override local defaults. Temporary fixture accounts use the existing product catalog and are cleaned up afterward. The browser address responses are mocked for repeatability; login, saved pins, subscriptions, matching, offers and messages use the real API/database. Successful runs write [E2E_RESULTS.md](E2E_RESULTS.md) and [LIVE_E2E_RESULTS.md](LIVE_E2E_RESULTS.md).

The profile suite also checks subscription and deletion buttons using only its temporary account. See [BUSINESS_PROFILE_E2E_RESULTS.md](BUSINESS_PROFILE_E2E_RESULTS.md). Backend unit tests run with `python -m unittest discover -s backend/tests -p "test_*.py"` from the project root, and the web helper tests with `npm test` in `web`. The `live` and `mobile` browser suites target features that were removed earlier (buyer and dealer chat, the old dealer item fields) and need rewriting before they can pass again; the `bidding`, `profile` and `admin` suites match the current interface.

The admin suite creates temporary categories/products/accounts, checks the real admin forms and protected API operations, and removes its fixtures afterward. See [ADMIN_E2E_RESULTS.md](ADMIN_E2E_RESULTS.md).

To check the built Flutter web interface, build it with `flutter build web --release` in `mobile`, serve it from the project root with `python -m http.server 5180 --bind 127.0.0.1 --directory mobile/build/web`, and run `python backend\scripts\e2e_bidding.py --suite mobile` in another terminal. Set `E2E_MOBILE_URL` when using a different URL and allow that origin in the backend CORS configuration. Results are written to [MOBILE_WEB_E2E_RESULTS.md](MOBILE_WEB_E2E_RESULTS.md).

## Rebuild existing apps after source changes

The backend serves `web/dist` when a production web bundle is present. To update that bundle, run `npm run build` in `web`. Rebuild the Flutter app using the Android build command above. On Windows, Flutter plugins require Developer Mode/symlink support. See [ISSUES.md](ISSUES.md) for validation details and remaining mobile build limitations.

## Related documentation

- [Web app README](web/README.md)
- [Mobile app README](mobile/README.md)
- [Product catalog README](products/README.md)
- [Current code audit and fixes](ISSUES.md)

## Catalog response errors and verification

If a product request returned HTML (`Unexpected token <`), the previous running backend had not loaded the catalog routes and its website fallback answered the request. Unknown API paths now return JSON 404, both clients show useful errors, and the buyer catalog supports retrying the request. Restart the backend after Python changes and refresh the browser after frontend builds.

The catalog has four filter groups. Product images are constrained to their own area above the name, specification summary and actions. [ICECAT_DATA_REPORT.md](ICECAT_DATA_REPORT.md) explains appliance coverage and how to download the larger source index.

Catalog regression checks against an existing local buyer account:

```powershell
$env:E2E_WEB_URL = "http://localhost:8000"
node web\tests\catalog.e2e.mjs
node web\tests\catalog_pages.e2e.mjs
```

`web/tests/admin_catalog.e2e.mjs` additionally checks admin panels and creates, edits, archives and deletes one temporary product. It requires the existing admin password in `TURACOZ_ADMIN_PASSWORD`; credentials are not embedded in the test.

The built site can be opened at `http://localhost:8000` or `http://127.0.0.1:8000`; its default API URL uses that same origin. Explicit `VITE_API_BASE_URL` / `API_BASE_URL` settings take precedence.
