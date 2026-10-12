# Turacoz Bid Tool Web

React + Vite portal for admins, buyers, and dealers. It uses the shared FastAPI backend.

```powershell
npm install
npm run dev
```

The development server uses `http://localhost:5173`; the API defaults to `http://localhost:8000`. Copy [.env.example](.env.example) to `.env` to change `VITE_API_BASE_URL`. If you open the portal on another host or port, add that exact origin to the backend's `TURACOZ_CORS_ORIGINS` list.

Product, bid, and report CSV exports use the current authenticated session.

Each tab keeps its own login in sessionStorage. Same-account tabs receive WebSocket updates independently. Locations use an interactive Leaflet map with search result choices, browser location permission, draggable pins and dealer radius circles.

Live request snapshots update every participating dealer's competing offers and open dialogs. On selection, the buyer and winner immediately receive contacts and private bid chat; no commission is charged. Admin sees reports from either participant and can inspect the linked winning conversation. Admin timing controls are under **Platform Rules & Categories**.

For the browser/API scenarios, start the API and this app, then run `python backend\scripts\e2e_bidding.py` and `python backend\scripts\e2e_bidding.py --suite live` from the project root. See [E2E_RESULTS.md](../E2E_RESULTS.md) and [LIVE_E2E_RESULTS.md](../LIVE_E2E_RESULTS.md).

Admin catalog search covers every product with server pagination/filtering. Buyer management shows saved addresses and winning purchases; dealer management shows verification/subscription, coverage, reports and moderation history. Product/category/account deletion uses confirmation and preserves bid history. Run `python backend\scripts\e2e_bidding.py --suite admin` for admin form/API checks; see [ADMIN_E2E_RESULTS.md](../ADMIN_E2E_RESULTS.md).
