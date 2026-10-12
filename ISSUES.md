# Code audit and fixes

This report covers the FastAPI backend, React web app, Flutter app, and local seed scripts. The initial review was static; subsequent startup/database repair and browser/API end-to-end checks are described below. Native Android execution remains unverified.

## Fixed in this pass

### Bidding and dealer matching

- **Expiry values used inconsistent units.** The UI selected values in minutes while the API called them hours, and the API default could expire a request after 24 minutes. The API now exposes `expiry_minutes`, defaults to 24 hours, and accepts legacy `expiry_hours` payloads using the old minute values.
- **Dealer coverage settings were stored but ignored.** Dealer matching now applies the selected radius, city, district, or state coverage mode alongside category/item type. Manufacturer/brand is not an eligibility restriction. District matching uses the buyer location's city or area because the schema has no separate district field.
- **A dealer selecting a parent category alone missed its products with subcategories.** Parent-only coverage now applies across that category; once a dealer chooses specific subcategories, matching narrows to those items.
- **Service cities and operating branches shared one field.** Web and mobile now edit these values separately and migrate older branch-only city coverage into the service-cities field.
- **Regional dealer coverage unnecessarily depended on a map pin.** State, city, and district matches can now use saved coverage lists without dealer coordinates; radius matching still requires a confirmed dealer pin and radius.
- **Unsubscribed dealers counted as matches.** Requests now match and notify only active subscribers, so buyers do not create requests that have no dealers able to respond.
- **Saving a dealer pin could move another user's location.** Profile updates now reuse a location only when its coordinates also match. A different pin creates a separate row, and clearing a dealer location removes its old radius pin.
- **Dealer category selections could not be cleared.** Saving an empty selection removes old category links. Category references are now validated before the transaction commits, so invalid or ambiguous selections return an actionable error and preserve the previous profile.
- **Unsubscribed dealers could poll and bid on requests.** Incoming requests and bid submission now require an active dealer subscription. The demo seeder creates subscribed demo dealers.
- **Bid acceptance and submissions could race.** Accept, submit, withdraw, and cancel operations now lock the bid request row and recheck its state before changing bids. Acceptance only marks other active offers as lost.
- **Expiry task cleanup could remove a replacement task.** Cleanup now removes only the task instance that completed and logs failures.
- **Buyer notes were dropped when the API `notes` field was used.** They are now stored with request fields.

### Authentication, exports, and products

- **WebSocket connections had no authentication.** Both clients now pass their access token; the backend checks that it belongs to the requested user. Each account supports multiple sockets and disconnect cleanup removes only the affected socket.
- **Held and suspended accounts could keep using old access tokens.** Login and authenticated API requests now block held, suspended, banned, and deleted account statuses.
- **Inactive products were still accessible by guessing their IDs.** Product detail now applies the same active-product visibility rule as the list endpoint, while admins retain access.
- **Inactive products could still be added to a cart.** The API now accepts only active products and hides inactive items from cart results.
- **Cross-origin access allowed every website.** CORS now uses an explicit origin allowlist, configurable with `TURACOZ_CORS_ORIGINS`.
- **The default Flutter web development port was missing from CORS.** The local Flutter web port (5000) is now allowed alongside the React and alternate Flutter ports.
- **Every backend restart reset the admin password and status.** Startup now creates the seeded admin only when the account does not exist. Configure `TURACOZ_ADMIN_PASSWORD` before initial seeding to set the local initial password.
- **CSV links omitted authorization and returned 401.** Web exports now use authenticated downloads. Flutter web downloads a CSV; native Flutter copies the authenticated CSV contents to the clipboard.
- **Commission gating conflicted with subscription billing.** Selecting a winner creates no commission/invoice. Both apps immediately reveal contacts to the buyer and winning dealer and open private bid chat. Historical payment records remain auditable.
- **Private contacts appeared in competitor responses.** Nonwinning dealers see final prices and terms but no buyer/winner private contact fields. Awarded reports use participant identities immediately, without checking payment status.
- **Manual product specs disappeared after save.** Product lists and detail responses now merge saved specification rows with catalog highlights. Non-admin product lists no longer include inactive items.
- **Product exports contained only the first page.** The backend now paginates through the full product list when exporting.
- **Invalid product prices, bid values, radii, and coordinates could reach SQL errors.** Request models now validate price ordering, numeric bounds, and non-finite values.

### Demo data and documentation

- **The demo seeder truncated product, category, and bid tables.** `add_dummy_data.py` is now additive and repeatable. It reuses usable active products, creates sample products when none are linked to active categories, and creates an example request only when there are no active requests.
- **The sample seeder read its new request inside an older database snapshot.** It now opens a fresh connection after creating the request before selecting dealers to receive offers.
- **The setup script reset the database every time and used a hardcoded root password.** Reset now requires typing `RESET`, and the root password is prompted securely. Android build setup now asks for an API address reachable from the device; the batch script now respects a URL entered at that prompt.
- Rewrote the root README and this report, corrected the Android emulator API URL guidance, and added backend/web environment templates.

## Additional system and bidding logic fixes

- **Withdrawn offers could not be submitted again.** The unique request/dealer key remains intact; a dealer now reuses their withdrawn offer record while the request is open. Withdrawal returns the request to their incoming list and each withdrawal is counted in the audit history.
- **A notification was treated as permanent eligibility.** Incoming requests, active offer visibility, submission, and acceptance now check current subscription, account status, verification/rating rules, product availability, category/item type and service coverage. The request retains its original policy for skipping flagged dealers.
- **Verification had two conflicting states.** Admin approval now updates the dealer profile as well as the account. Profile editing cannot self-verify a dealer. Pending dealers can participate only when admin verification is explicitly disabled.
- **Saved bid settings did not affect bidding.** Duration bounds, default duration, dealer broadcast cap, maximum radius, minimum dealer rating, and optional minimum price decrease now apply. A price decrease rule allows terms-only revisions at the same total and defaults to disabled. Partial setting saves preserve other rules; legacy expiry/commission keys are translated and invalid legacy duration values fall back to valid limits.
- **The buyer radius was overwritten by a profile value and then ignored.** An explicit positive request radius is now an additional distance limit; zero uses dealer coverage alone. Dealer radius coverage always applies. Dealer matching sorts pinned matches by distance before applying the broadcast cap, with stable ID ordering for ties.
- **Same place names could match across regions.** City/district matching now checks selected or pinned states, and coverage checks country. Unsupported coverage methods no longer silently become radius coverage.
- **Category names could identify the wrong item.** Web and mobile dealer profiles now save category IDs and display parent/item labels. Selecting an item includes its parent automatically. Legacy names remain supported when they resolve unambiguously.
- **Prices lacked a consistent meaning.** `amount` is the final total for the complete requested quantity. `discount_amount` records savings already included in that total. Commission is calculated once from that final total, with two decimal rounding; both clients display paise and explain the pricing fields. Cart bidding preserves cart quantity, and rebidding loads the original product by ID.
- **Delivery text was lost or given an invented unit.** Mobile now preserves values such as `24 hours` and `3 days`; both clients display the recorded delivery terms. Loss reasons now state that the buyer selected another offer, without inventing the buyer's reasons from different warranty text.
- **Database and host clocks could disagree.** Mutation deadlines and expiry timers use the database clock. Clients receive expiry timestamps with an explicit UTC offset. A scheduled expiry event is still sent when another API call has already marked the request expired.
- **Concurrent changes could leave stale decisions.** Eligibility reads use committed data; bid submission/acceptance also lock the dealer account/profile. Deadline conditions are checked when writing offers or awarding a request. Retry acceptance/cancellation is idempotent, and lock conflicts return a retryable response instead of an unhandled database error.
- **Realtime updates could arrive before commit.** Submission and withdrawal events are now sent after the transaction commits, so clients refresh committed offers. Socket send failures remove only the failing connection; long-lived sockets recheck account access and token expiry.
- **Saved locations could duplicate, lose their default, or move old requests.** Location rows are now immutable unless an identical row can be reused. All location edits serialize per buyer, enforce the cap, merge duplicates, and synchronize a single default with the buyer profile. Profile saves replace the default saved entry rather than inserting another one. The schema now enforces active location uniqueness.
- **Concurrent cart access could create separate active carts.** Cart creation serializes per buyer, and existing duplicate carts merge into one active cart with quantities retained within the supported limit.
- **Cancelled requests disappeared from history.** The API can include closed requests, including requests with no offers. Both clients distinguish customer cancellation from expiry and keep request history visible. Active offer dialogs exclude withdrawn offers and disable unavailable dealers; buyers can cancel an active request with or without offers. Dealer history shows only the dealer's own offers and includes all closed outcomes. Eligibility is calculated once per request when listing offers, and web expiry refreshes are grouped by request.
- **History filters and financial totals omitted records.** Filters now use actual statuses; admin history includes lost offers. Bid and commission history no longer silently stop at 200 records. Revenue charts use payment dates, and dashboard counts apply expiry before calculating metrics.
- **Payment states could be changed incoherently.** Commission transitions now reject refunds of unpaid records and reopening settled/refunded records. Repeating the same status preserves the payment date; refunds retain the original payment timestamp. Dealer payment requires the actual winning offer of an awarded request. Invalid commission settings cannot silently waive a fee.
- **Deleting an account erased marketplace records.** Account deletion now removes access and closes active requests/offers while retaining awarded bids, invoices, commissions, and disputes. Reading audit logs no longer deletes records used for withdrawal counting and financial review.
- **Failed actions discarded entered data.** Web forms reset only after a successful mutation and prevent duplicate in-flight actions. Mobile bid setup/offer dialogs retain input after failure. Failed profile loads cannot be saved over existing business data. Logged-out account data is cleared and late responses from an old session cannot populate a new account.
- **Product status controls had no effect.** Product status is now saved, and older mobile payloads that omit it preserve the existing status. Inactive/deleted categories prevent new matching. Product identity/category changes are blocked once bidding history exists, and category edits reject self-parenting, extra hierarchy levels, duplicate names under a parent, and moving referenced categories.
- Removed mobile default-state and webhook setting controls that had no implemented effect. Category editing uses the real taxonomy endpoints rather than a separate settings list.

### Schema upgrade

Backend startup adds `bid_requests.skip_flagged_dealers` and enforces unique active buyer locations with a regular nullable column maintained by the save/delete transactions. This avoids MariaDB's rejection of the previous generated-column expression. Existing requests default to skipping flagged dealers. Duplicate active saved entries for the same buyer/location are consolidated, and defaults are synchronized. These migrations completed during startup verification on the local MariaDB database.

## Realtime, location and subscription fixes

### Concurrent bidding and subscription policy

- Participating dealers can read all offers for their request, including won/lost offers after selection. Read access remains when a profile changes; submission and selection still recheck current eligibility. Request IDs distinguish separate auctions for the same product.
- Versioned, personalized WebSocket snapshots directly update offer lists, request state and already-open dialogs in React and Flutter. Private bid and report messages are pushed as records instead of waiting for a complete dashboard reload. Open conversations reload missed messages on reconnect while preserving drafts.
- Expiry checks previously used broad UPDATE JOIN statements that deadlocked concurrent live readers/submissions. Updates now lock only due request IDs in a consistent order. Notification reads no longer delete old rows and contend with new notifications; the seven-day display window remains.
- Request creation, offer submission/revision and selection run their database transactions in worker threads so row locks do not block the WebSocket event loop. Flutter login now allows 30 seconds for a busy backend and reports timeouts distinctly. Live snapshots update Flutter dashboard counts and refresh notification badges.
- Idle database connections are reused without sharing active transactions between threads. Broken/expired connections are discarded, reads/writes have bounded timeouts, and failed transactions roll back before reuse. Writes are never automatically replayed after a transport failure. Dealer dashboard expiry completes before nested repository reads, avoiding a wait on its own transaction.
- A failed snapshot explicitly requests an offer reload. Both clients honor that fallback even after receiving earlier snapshots, instead of refreshing only notifications.
- Selecting a winner creates no commission/invoice. Buyer and winner immediately receive contacts and an authorized private bid conversation. Losing dealers see the final winning price/terms, without private contacts or chat. Admin can read the winning conversation linked to a report but cannot send as either participant.
- Buyer/dealer reports reach admin and counter-disputes share the existing thread. A request lock serializes simultaneous reports to avoid duplicate threads or overwritten descriptions. Report identities follow winning selection instead of historical commission status.
- Web admin now exposes default/minimum/maximum bidding duration, broadcast cap, price decrease, maximum radius and verification/rating controls. Flutter exposes the same duration bounds. Requests retain their saved deadline when rules change or dealers revise offers.
- Business-profile coverage fields enable only applicable controls. Category add/remove controls have accessible names; profile drafts survive background updates. Regional coverage retains city/state/country metadata without requiring a shop pin. Radius coverage rejects missing city/state/pin and invalid radius values.
- Startup adds `bid_messages` with bid/sender foreign keys and a conversation/time index; existing bidding and historical financial records are preserved.

- **Same-account tabs repeatedly closed each other's sockets.** The manager now maintains a set of authenticated connections per account and broadcasts events to every connected tab/device. Clients cancel old reconnect timers, use a bounded exponential retry delay, and batch event refreshes. React heartbeat replies do not trigger data refreshes; Flutter realtime refreshes avoid the full-screen loading indicator.
- **Different incognito tabs shared one account.** React and Flutter web now keep login state in sessionStorage. Separate tabs can use different accounts, and reload retains that tab's account. Native app storage is unchanged.
- **The browser map estimated coordinates from clicks on an iframe overlay.** Leaflet now supplies exact coordinates from map taps and marker drags. Search shows up to five selectable places; browser/device location requests permission on an explicit action. Pin changes clear stale address fields, and save actions require confirmation. Failed lookups retain a manual-address fallback.
- **Dealer range was hard to inspect.** Both clients draw radius coverage in meters around the shop pin, using the admin-capped effective range. Distance calculations clamp floating-point rounding at the Haversine boundary.
- **A postal-address unique index rejected different shop pins.** Runtime migration removes `locations.uq_location` and adds a nonunique latitude/longitude index, preserving existing rows and references. The end-to-end fixture setup discovered this failure with nearby shops sharing the same city/area/pincode.
- **Manufacturer choices excluded otherwise eligible item dealers.** Matching now uses category and item type; brand metadata does not restrict delivery eligibility. Both dealer profile editors show product/item type choices. Selecting a parent alone covers its children; selecting specific child items narrows that parent.
- **Subscription state was absent from login.** Dealer login returns the current subscription flag. Incoming requests, offer submission/revision and winner acceptance independently recheck it, including revocation after login.
- **Live events omitted the acting dealer's other tabs and dealers who had not offered yet.** Submission/withdrawal now update the acting account's sockets; award notifications include invited observers so their open requests close promptly.
- **Open support conversations stayed stale.** Both clients refresh the currently open thread when report/message events arrive, preserving the draft. React bucket versions prevent an older response from overwriting newer live data.
- **WebSocket tokens appeared in access logs.** Server log filters redact query tokens while preserving Uvicorn's access formatter.
- Location lookup now uses shared authenticated API endpoints, bounded caching, and paced requests to a configurable Nominatim-compatible provider. A live provider search returned five results during verification. Browser end-to-end tests mock only address lookup responses for repeatability.

### Database storage repair

- MariaDB's log confirmed that `product_specifications.ibd` was missing. The other application tables were readable; this was an InnoDB storage problem.
- Added a read-only diagnostic command, startup/readiness probes, and HTTP 503 responses for unavailable database/storage failures. Rollback errors no longer mask the original connection failure. Database error details stay in backend logs.
- Added explicit recovery limited to missing catalog specification tablespaces. It backs up retained highlights and available metadata, builds and verifies a separate populated table, and replaces only the unusable specification table entry. Startup never drops a damaged table automatically.
- Recovered 145,529 specification rows from retained highlights for 21,676 catalog products. Recovery snapshots are under `backend/recovery/`. Custom specification edits stored only in the missing file cannot be reconstructed from those highlights.
- Product create/update now synchronize highlights with specification rows in the same transaction, keeping product responses consistent and retaining a second representation for future recovery.

## Known limitations

- Dealer subscription activation is a demo action with no payment provider. New awards create no commission or invoice. Historical financial records are preserved and their amounts do not represent newly collected subscription payments.
- Saved locations store city, area, and state but not a distinct district. District coverage therefore compares configured district names with buyer city/area text.
- The API stores refresh tokens but has no refresh-token endpoint; after an access token expires, the user must sign in again.
- The CSV export route builds the response in memory. It is suitable for local/demo data but should be changed to streaming for a very large catalog.
- Location search depends on the public OpenStreetMap Nominatim service and can time out. A confirmed map pin is still required for bidding.
- Legacy settings for notification timing/webhooks, branch/category caps, and automatic report-based bans are not implemented. The current editable bidding controls are the rules described above.
- Awarding a bid records selection of an offer; delivery and fulfillment tracking are not implemented.

## Validation status

The initial review used Python/JavaScript parsing, SQL parameter checks and Dart analysis. Subsequent database repair verified local startup, migrations, all-table probes, buyer/dealer login and product list/detail reads. Product write consistency was checked in a rolled-back transaction; simulated storage failures returned HTTP 503 and duplicates HTTP 409.

The browser/API checks use a real MariaDB database, existing catalog products, one temporary buyer and seven temporary dealers. They passed these scenarios:

1. Buyer browser geolocation saves an exact pin. Only subscribed dealers with the correct item type and coverage receive the request; 4.99 km is inside a 5 km radius and 5.01 km is outside. Two dealers submit/revise competing offers with live buyer/dealer displays and select a winner.
2. Revoking a dealer subscription after login blocks further offers and acceptance of the old offer. Another eligible dealer can win.
3. Searching and changing the buyer's saved location changes which shop receives the request. A buyer distance cap narrows eligibility further. Cancellation and live open-thread messaging work.

Separate incognito tabs retain different logins; same-account tabs remain connected without idle reconnect loops. No browser JavaScript errors were recorded. Temporary test accounts, requests, messages and locations are removed afterward. See [E2E_RESULTS.md](E2E_RESULTS.md).

React production build and Flutter web release build succeeded. Dart analysis found no type errors; existing lint/unused-code warnings remain. Native Android execution and rebuilding the APK have not been verified. The backend is stopped after verification so it can be started manually.

### Final verification — 12 October 2026

- 12 connection-cache/transaction unit tests passed, including concurrent leases, stale connections, rollback failures and interruption handling.
- 11 original browser/API regression checks passed: exact pins, radius boundary, item type, subscription revocation, live offers, cancellation, location changes and separate-tab sessions.
- 18 concurrent live checks passed with three bidding dealers, a buyer, duplicate account tab and admin. Winner/loser states, open dialogs, snapshot fallback, private chat, reports, admin timing and actual expiry were exercised. Final result delivery measured 108 ms at the slowest participant in this local run.
- 5 additional business-profile checks passed: invalid radius preserves saved data, shop/phone/branches save, demo subscription activation, and confirmed deletion of a temporary fixture account.
- 7 Flutter web checks passed against the release build: three separate logins, competing offers, dashboard counts, open request dialog, immediate winning contacts, and private chat sent through Flutter controls in both directions.
- All 33 database tables were readable. React production and Flutter web release builds succeeded; Dart analysis had no errors, with existing warnings remaining.
- Existing catalog products were used. Temporary fixture accounts, requests, messages and locations were cleaned up; native Android execution remains unverified.

Detailed results: [original scenarios](E2E_RESULTS.md), [concurrent bidding](LIVE_E2E_RESULTS.md), [business-profile controls](BUSINESS_PROFILE_E2E_RESULTS.md), [Flutter web](MOBILE_WEB_E2E_RESULTS.md).

### Admin audit — 12 October 2026

- Admin product search previously filtered only the first 250 loaded products. The new admin catalog endpoint searches all products and returns total counts, global brand choices, server filters, stable sorting and 50-item pages. The current local database has 21,676 products, all active.
- Manual products with null location/model values failed when reopened and saved. Editor drafts normalize those values, show local save errors/loading, validate required fields and price ranges, and support archived status. Specification values retain colons in URLs and JSON. Creation searches for the newly added product so it is immediately visible.
- Products with bid history lock identifying fields while allowing price/specification/status changes. Product deletion preserves winning history. Categories/items used by products or dealer profiles cannot be removed until reassigned.
- Buyer lists/details now use saved addresses even before bidding and show actual awarded purchase counts/prices. Buyer and dealer detail routes validate the account role.
- Dealer management exposes every moderation state, current verification/subscription and regional coverage, filed/received reports and status reasons/actors. Multiple service locations produce one dealer entry with all cities/states. Removed the old 200-account list limit.
- Account deletion requires confirmation. Admin accounts cannot be moderated through buyer/dealer routes or deleted through marketplace profile controls. Seeding refuses an empty admin password.
- Local credentials load from private `.env` with explicit environment overrides. Removed embedded database/admin passwords and signing-key defaults from published source; replaced the old local signing fallback with a private random secret. Existing admin/database passwords remain unchanged. Private data, uploads, recovery snapshots, fixture tokens, downloaded catalog files and builds are excluded from Git.
- The production web fallback now rejects paths outside its build directory, including attempts to read private configuration files.
- Ten admin browser/API checks and four admin/web protection unit checks passed. The 12 connection/transaction unit checks, 11 original bidding checks and 18 live bidding checks passed; all 33 database tables were readable and the React production build succeeded. Temporary records were removed. See [ADMIN_E2E_RESULTS.md](ADMIN_E2E_RESULTS.md).

## Catalog filters, source imports and age audit — 12 October 2026

- Inspected `products/` first. There is no nested `products/products` directory. The existing data is a manifest and 29 compressed category shards; no dummy replacement was needed.
- Buyer and admin catalog queries now filter and paginate the entire database by category, item type, manufacturer, year and 29 normalized specification facets. React and Flutter use the same API and taxonomy; no review-rating filter was added.
- Added Home Appliances and appliance item types without changing existing product IDs or dealer category relationships. Dealer product matching continues to use the shared parent/item IDs.
- Found catalog-added dates being used as release dates in the legacy Icecat builder. Removed that fallback. Fourteen confirmed pre-2017 Samsung tablet variants were retired after private backups; historical bids remain. Other confirmed 2017/2020 model years were corrected and retained.
- Current database: 21,710 active available records, including 48 newly imported records from Icecat, TechAPI, Samsung and OPPO. Detailed category/year/brand counts are in PRODUCT_CATALOG_REPORT.md and private CSV reports.
- Added admin Product Fetch & Reports in both frontends: source configuration, type selection, fetch now, hourly/daily/fixed schedules, custom public JSON feeds, durable import history and statistics. Schedules default to disabled.
- Added 12 official manufacturer adapters after inspecting live listing structures. Removed the unhosted Mobile Specs project. Articles without sufficient product/release information remain review links. See PRODUCT_SOURCES_GUIDE.md for supported sources and limitations.
- Source imports use stable identities, skip unchanged/removed/inactive products, preserve manual specification overrides and prices, and reject older provider versions. Recovery handles interrupted jobs; downloads and run durations are bounded.
- Fixed Apple Atom parsing selecting enclosure images instead of article links; Samsung publication metadata; future availability checks; invalid year/specification/source settings returning useful errors; and zero-price imported records displaying misleading price ranges.
- Verification: React production build and Flutter web release build succeeded. Python compilation passed. A temporary backend on port 8001 started successfully; admin/buyer login, full catalog specification filtering, statistics/CSV routes, invalid-filter responses and buyer rejection from admin source routes were checked. Native Android execution and a new browser walkthrough were not performed for this catalog change.
- Remaining data limitation: 21,644 surviving legacy records still have unverified release years, so their exact ages cannot be certified from catalog-added dates. The age report distinguishes these from verified releases. New imports apply the three-year rule using release/availability evidence.
