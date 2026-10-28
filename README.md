# Turacoz Bid Tool

A location-based bidding marketplace where buyers request offers and eligible dealers submit bids. The repository contains a FastAPI backend, a React web portal, and a Flutter mobile app.

## Components

- `backend/` — FastAPI routes, WebSocket updates, MariaDB/MySQL schema and catalog import tools.
- `web/` — React + Vite portal for buyers, dealers, and administrators.
- `mobile/` — Flutter app for Android and web.
- `product_catalog/` — current India catalog and locally stored product images.
- `products/` — optional Open Icecat bundle and import instructions.

The current India store catalog contains 9,195 listed variants across 238 brands and 16 departments. Product availability, price, and stock are point-in-time claims; confirm them with the linked store before purchase. Details are in [product_catalog/README.md](product_catalog/README.md).

## Requirements

- Python 3.10 or newer
- MariaDB or MySQL
- Node.js and npm
- Flutter and Dart SDK 3.12.2 or newer for mobile builds

## Local setup

Copy `.env.example` to `.env` and set `TURACOZ_DB_PASSWORD`, `TURACOZ_ADMIN_PASSWORD`, and a unique `TURACOZ_JWT_SECRET`. Keep `.env` private. Create the configured database (`turacoz_bidtool` by default) and ensure the database service is running. On startup, the backend applies schema setup and initializes the configured admin account.

Install backend dependencies and start the API from the repository root:

```powershell
pip install -r backend\requirements.txt
python server.py
```

Install and run the web app in a second terminal:

```powershell
cd web
npm install
npm run dev
```

The web app runs at `http://localhost:5173` and the API at `http://localhost:8000` by default. Set `TURACOZ_CORS_ORIGINS` in `.env` when the browser app uses another origin. To create a production web bundle, run `npm run build` from `web/`; the backend serves `web/dist` when it is present.

For Android emulator use `http://10.0.2.2:8000` as the API base URL. For a physical device, use the computer's LAN address.

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Build a release APK with `flutter build apk --release --dart-define=API_BASE_URL=http://10.0.2.2:8000`.

## Catalog import

The bundled India catalog is the current buyer catalog. The India-first ingestion pipeline stages retailer inventory and enriches exact matches with Icecat; publication requires verified India stock and recent manufacturer release evidence (see the catalogue README). Legacy global source fetches remain hidden and cannot overwrite visible catalogue variants. Startup bundle import is disabled unless `TURACOZ_IMPORT_PRODUCTS_ON_STARTUP=true` is configured.

## Product search and requests

The API embeds Tantivy, a Rust inverted index installed with the backend requirements. It supports typo and prefix matching, English/Hinglish aliases, and product-type, brand and specification facets. Buyer browsing groups variants by hardware model; the variant selector supplies the exact product ID for bidding or cart actions. No separate search server is required.

Search indexes are disposable runtime data under `backend/search_engine/indexes/`. Startup opens or builds the index. To rebuild explicitly, run `python backend/scripts/ingest_india_catalog.py search-index`. See [search setup](backend/search_engine/README.md).

Buyers can describe a custom product from web or mobile search. These descriptions stay private to the buyer and matching bid workflows. A request with no matching shop remains active until its deadline; eligible shops can discover it on subsequent request polls. Catalogue IDs and historical bid/cart references are retained.

The catalogue is still a verified subset, not a complete India-market database. The [catalogue README](product_catalog/README.md) records counts, remaining quality issues and the model-level release-date research process.

## Deployment

Use a private production `.env`, a managed MariaDB/MySQL instance, and a production web build. Configure HTTPS, allowed CORS origins, persistent database backups, and appropriate network access before exposing the API. Do not commit secrets or production credentials. Component-specific setup is documented in [web/README.md](web/README.md) and [mobile/README.md](mobile/README.md).
