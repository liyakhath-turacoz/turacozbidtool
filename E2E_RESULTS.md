# End-to-end verification

- PASS: Separate incognito tabs retain different accounts, including after reload
- PASS: Buyer browser location and confirmed pin save exact latitude/longitude
- PASS: Only subscribed dealers with the selected item and buyer inside their circular range receive the request (4.99 km included, 5.01 km excluded)
- PASS: Out-of-range, wrong-item and unsubscribed accounts cannot submit; login returns current subscription
- PASS: Live request, competitor bids, own-tab updates, bid revision and winner selection work without refresh
- PASS: Subscription revoked after login blocks bid changes and acceptance of that offer; eligible dealer still wins
- PASS: Changing buyer pin switches delivery eligibility: formerly distant shop receives new-location request; old nearby shops do not
- PASS: Buyer distance cap adds a stricter limit to the dealer radius
- PASS: WebSocket message updates an already-open conversation instantly
- PASS: Multiple sockets for the same account stay connected and receive events; no idle reconnect/refresh loop
- PASS: No browser JavaScript errors

Browser geolocation used granted test permissions. Address lookup responses were mocked for repeatability; matching, login, subscription, bids and messages used the running API and MariaDB. Temporary fixtures were cleaned up after the run. Native Android execution was not tested.
