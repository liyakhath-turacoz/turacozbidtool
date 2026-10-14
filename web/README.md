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

## Interface and design system

The interface is built around the **quote slip**: a bid is a quote, and quotes live on slips of paper. Requests and offers are drawn as slips with notched edges, a perforation line, a live countdown, and a highlighter swipe behind the lowest price. Everything else stays flat and quiet.

| File | What it holds |
| --- | --- |
| [src/styles.css](src/styles.css) | All styling. Colours, type, radii and shadows are tokens at the top of the file (`--brand`, `--tag`, `--paper`, `--go`, `--warn`, `--bad`). Change the brand there. |
| [src/ui.jsx](src/ui.jsx) | Shared pieces: accessible `Modal` (focus trap, Escape, restores focus, shows server errors inside itself), `ConfirmProvider` / `useConfirm()`, `Countdown`, `Status`, `Panel`, `Section`. |
| [src/bidding.jsx](src/bidding.jsx) | The bidding screens' building blocks: `RequestSlip`, `MyBidSlip`, `OfferSlip`, `BidSheet` (dealer), `BidSetupModal` (buyer), `CompareOffersModal`. |
| [src/format.js](src/format.js) | Pure helpers with unit tests in [tests/format.test.mjs](tests/format.test.mjs): rupee formatting with Indian grouping, countdown labels, "where do I stand" ranking. |

Conventions to keep:

- Fonts (Bricolage Grotesque and IBM Plex Sans) are bundled through `@fontsource`, so the app looks the same offline.
- Sentence-case labels. Buttons say what happens ("Submit bid", "Accept offer"), and the same action keeps the same name in dialogs and toasts.
- Money is `money(value)`: `₹1,50,000`, no paise when whole, and a dash instead of a made-up zero for missing values.
- Destructive or irreversible actions (accept an offer, withdraw, cancel, delete, ban) go through `useConfirm()` and state the consequence. Do not use `window.confirm`, `alert` or `prompt`.
- Failed actions show their message inside the open dialog (the `Modal` reads the app error), not only in the page banner behind it.
- Lists show placeholders while loading (`SlipSkeletons`) so an empty state never flashes before data arrives.
- Keyboard focus is always visible, motion respects `prefers-reduced-motion`, tap targets are at least 44px on touch screens, and phones get a bottom tab bar.

Run the helper tests with `npm test`. The browser suites are described in the project README.
