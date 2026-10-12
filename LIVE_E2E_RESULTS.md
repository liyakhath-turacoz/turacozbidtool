# Concurrent live bidding verification

- PASS: Business search, result selection, pin confirmation, browser location and radius save buttons work
- PASS: Product-type and parent category add/remove buttons persist the selected item type
- PASS: Cities, states and district coverage persist and match; wrong-state coverage excludes the request; switching back to radius works
- PASS: Admin default duration is applied; invalid duration is rejected; all participants use the same saved deadline
- PASS: Three simultaneous dealer submissions appear to every participating dealer and the buyer, including a second same-account tab
- PASS: Concurrent revisions stay consistent; dealer 3 updates dealer 2 instantly even with the details dialog already open
- PASS: A disconnected dealer catches missed offers after reconnect without reloading the page
- PASS: The fallback event reloads offers after a missed snapshot even when earlier snapshots were already received
- PASS: Finalization is pushed to buyer and all dealers; winner contacts unlock immediately, losing dealers see final terms, and no commission is charged
- PASS: Private winner/buyer chat delivers both ways instantly; losing dealers and outsiders cannot read, send or receive it
- PASS: Buyer and winning dealer can report each other; both complaints reach admin
- PASS: Admin can inspect the reported winning conversation but cannot send as a participant
- PASS: Reconnecting an open private chat restores missed messages and preserves its unsent draft
- PASS: Web admin can save timing rules; invalid duration bounds are rejected and existing deadlines stay fixed
- PASS: Final result WebSocket delivery measured 34 ms at the slowest participant
- PASS: The shared deadline expires the request and offer live for all participants and blocks late revisions
- PASS: Regional coverage without a shop pin retains state/city metadata and matches correctly; a buyer distance cap requires a pin; invalid radius save is rejected atomically
- PASS: No browser JavaScript errors

Used real API/MariaDB and existing products with temporary fixture accounts. Address lookup was mocked; browser location permission was granted. Fixture data is removed afterward. Native Android execution was not tested.
