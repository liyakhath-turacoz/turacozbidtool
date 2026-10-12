import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { chromium } from 'playwright';

const fixturesPath = process.argv[2];
const state = JSON.parse(fs.readFileSync(fixturesPath, 'utf8'));
const { accounts, product, country, settings, admin, apiUrl } = state;
const webUrl = process.env.E2E_WEB_URL || 'http://localhost:5173';
const checks = [];
const check = (description) => { checks.push(description); console.log('PASS:', description); };
const api = async (account, endpoint, body, method, expected = 200) => {
  const response = await fetch(apiUrl + endpoint, { method: method || (body === undefined ? 'GET' : 'POST'), headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${account.access_token}` }, body: body === undefined ? undefined : JSON.stringify(body) });
  const result = await response.json();
  assert.equal(response.status, expected, `${endpoint}: ${JSON.stringify(result)}`);
  return result;
};
const eventually = async (callback, description) => {
  const deadline = Date.now() + 15000;
  let error;
  while (Date.now() < deadline) {
    try { await callback(); return; } catch (caught) { error = caught; }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(`${description}: ${error?.message}`);
};
const browser = await chromium.launch({ channel: process.env.E2E_BROWSER || 'msedge', headless: true });
const context = await browser.newContext({ viewport: { width: 1400, height: 1000 }, permissions: ['geolocation'], geolocation: { latitude: 12.9716, longitude: 77.5946 }, reducedMotion: 'reduce' });
const pages = [];
const socketCounts = new Map();
const events = new Map();
const errors = [];

await context.route('**/locations/reverse?*', (route) => route.fulfill({ json: { display_name: 'Test delivery road, Bengaluru', address: { road: 'Test delivery road', suburb: 'Test area', city: 'Bengaluru', state: 'Karnataka', country, postcode: '560001' } } }));
await context.route('**/locations/search?*', (route) => route.fulfill({ json: [{ place_id: 1, lat: '12.9716', lon: '77.5946', display_name: 'Test area, Bengaluru', address: { city: 'Bengaluru', state: 'Karnataka', country } }, { place_id: 2, lat: '13.0716', lon: '77.5946', display_name: 'Northern test area, Bengaluru', address: { city: 'Bengaluru', state: 'Karnataka', country } }] }));

async function login(label) {
  const account = accounts[label];
  const page = await context.newPage(); pages.push(page);
  socketCounts.set(page, { opened: 0, closed: 0 }); events.set(page, []);
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('websocket', (socket) => {
    socketCounts.get(page).opened++;
    socket.on('close', () => socketCounts.get(page).closed++);
    socket.on('framereceived', ({ payload }) => { try { events.get(page).push(JSON.parse(payload.toString())); } catch {} });
  });
  await page.goto(webUrl, { waitUntil: 'domcontentloaded' });
  assert(await page.getByLabel('Username', { exact: true }).isVisible(), 'New tab must have its own login');
  await page.getByLabel('Username', { exact: true }).fill(account.username);
  await page.getByLabel('Password', { exact: true }).fill(account.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('.app-shell').waitFor();
  await eventually(async () => assert(socketCounts.get(page).opened > 0), 'WebSocket opens');
  return page;
}
async function navigate(page, name) {
  const nav = page.locator('nav').getByRole('button', { name, exact: true });
  const bounds = await nav.boundingBox();
  if (!bounds || bounds.x < 0 || !(await nav.isVisible())) await page.getByRole('button', { name: 'Menu', exact: true }).click();
  await nav.click();
}
async function submitUi(page, amount) {
  await page.getByRole('button', { name: 'Submit Bid', exact: true }).first().click();
  await page.getByLabel('Final Total (Rs.)').fill(String(amount));
  await page.getByLabel('Warranty Text').fill('1 year');
  await page.getByLabel('Delivery Time', { exact: true }).fill('2 days');
  await page.locator('.modal').getByRole('button', { name: 'Submit Bid', exact: true }).click();
  await page.locator('.modal').waitFor({ state: 'hidden' });
}
const duration = Math.round((settings.bid_rules?.expiry_hours || 24) * 60);
const start = (locationId, radius = 0) => api(accounts.buyer, '/buyer/bids', { product_id: product.id, location_id: locationId, quantity: 2, expiry_minutes: duration, radius_km: radius });

try {
  const buyerPage = await login('buyer');
  const near1Page = await login('near1');
  const near2Page = await login('near2');
  const sameAccountPage = await login('near1');
  assert.equal(await buyerPage.evaluate(() => JSON.parse(sessionStorage.getItem('turacoz_bid_tool_web_session')).role), 'buyer');
  assert.equal(await near2Page.evaluate(() => JSON.parse(sessionStorage.getItem('turacoz_bid_tool_web_session')).id), accounts.near2.id);
  await buyerPage.reload(); await buyerPage.locator('.app-shell').waitFor();
  assert.equal(await buyerPage.evaluate(() => JSON.parse(sessionStorage.getItem('turacoz_bid_tool_web_session')).id), accounts.buyer.id);
  check('Separate incognito tabs retain different accounts, including after reload');
  await navigate(buyerPage, 'Profile');
  await buyerPage.getByRole('button', { name: 'Use my location', exact: true }).click();
  await eventually(async () => assert.match(await buyerPage.getByLabel('City', { exact: true }).inputValue(), /Bengaluru/), 'Browser geolocation fills address');
  await buyerPage.getByLabel('Location name', { exact: true }).fill('E2E home');
  await buyerPage.getByRole('button', { name: 'Save Location', exact: true }).click();
  await eventually(async () => assert.equal((await api(accounts.buyer, '/buyer/locations')).length, 1), 'Location saved');
  const home = (await api(accounts.buyer, '/buyer/locations'))[0];
  assert(Math.abs(Number(home.latitude) - 12.9716) < 0.0000001);
  check('Buyer browser location and confirmed pin save exact latitude/longitude');
  await navigate(near1Page, 'Business Profile');
  await near1Page.locator('.location-map .leaflet-marker-icon').waitFor();
  assert.match(await near1Page.locator('.location-help').innerText(), /5 km/);
  assert(await near1Page.getByLabel('Dealt Items / Product Types').count());
  await navigate(near1Page, 'Active Bids');
  await navigate(near2Page, 'Active Bids');
  await navigate(sameAccountPage, 'Active Bids');
  await navigate(buyerPage, 'Bid Page');
  await buyerPage.getByRole('button', { name: 'Start Bid', exact: true }).click();
  await buyerPage.getByLabel('Quantity', { exact: true }).fill('2');
  await buyerPage.locator('.modal').getByRole('button', { name: 'Start Bid', exact: true }).click();
  await buyerPage.locator('.modal').waitFor({ state: 'hidden' });
  const request1 = (await api(accounts.buyer, '/buyer/requests'))[0];
  assert.equal(request1.product_id, product.id);
  const eligible = [];
  for (const [label, account] of Object.entries(accounts)) {
    if (account.role !== 'dealer') continue;
    const requests = await api(account, '/dealer/requests');
    if (requests.some((row) => row.id === request1.id)) eligible.push(label);
  }
  assert.deepEqual(eligible.sort(), ['edgeInside', 'near1', 'near2']);
  check('Only subscribed dealers with the selected item and buyer inside their circular range receive the request (4.99 km included, 5.01 km excluded)');
  for (const label of ['far', 'wrongItem', 'unsubscribed']) await api(accounts[label], '/dealer/bids', { bid_request_id: request1.id, amount: 10000 }, 'POST', 403);
  assert.equal((await api(accounts.unsubscribed, '/auth/login', { username: accounts.unsubscribed.username, password: accounts.unsubscribed.password })).subscribed, false);
  check('Out-of-range, wrong-item and unsubscribed accounts cannot submit; login returns current subscription');
  await eventually(async () => assert(await near1Page.getByRole('button', { name: 'Submit Bid', exact: true }).count()), 'New request arrives live');
  await submitUi(near1Page, 9000);
  await eventually(async () => assert.match(await near2Page.locator('main').innerText(), /9,000\.00/), 'Competitor sees first bid live');
  await eventually(async () => assert.match(await sameAccountPage.locator('main').innerText(), /9,000\.00/), 'Same-account tab sees own submission');
  await submitUi(near2Page, 8500);
  await eventually(async () => assert.match(await near1Page.locator('main').innerText(), /8,500\.00/), 'First dealer sees competing offer');
  await near1Page.getByRole('button', { name: 'Edit', exact: true }).click();
  await near1Page.getByLabel('Final Total (Rs.)').fill('8000');
  await near1Page.locator('.modal').getByRole('button', { name: 'Submit Bid', exact: true }).click();
  await near1Page.locator('.modal').waitFor({ state: 'hidden' });
  await eventually(async () => assert.match(await buyerPage.locator('main').innerText(), /8,000\.00/), 'Buyer sees revised bid live');
  await eventually(async () => assert.match(await near2Page.locator('main').innerText(), /8,000\.00/), 'Competitor sees revision live');
  const offers1 = (await api(accounts.buyer, '/bids')).filter((row) => row.bid_request_id === request1.id);
  const winner = offers1.find((row) => row.dealer_id === accounts.near1.id);
  await api(accounts.buyer, `/buyer/bids/${winner.id}/accept`, {});
  await eventually(async () => assert(!(await api(accounts.near2, '/bids')).some((row) => row.bid_request_id === request1.id && ['active', 'updated'].includes(row.status))), 'Losing bidder closes');
  check('Live request, competitor bids, own-tab updates, bid revision and winner selection work without refresh');

  const request2 = await start(home.location_id);
  const first = await api(accounts.near1, '/dealer/bids', { bid_request_id: request2.id, amount: 7000 });
  execFileSync('python', ['backend/scripts/e2e_bidding.py', '--revoke', accounts.near1.id, '--fixtures', fixturesPath], { stdio: 'pipe' });
  assert.equal((await api(accounts.near1, '/auth/login', { username: accounts.near1.username, password: accounts.near1.password })).subscribed, false);
  assert.equal((await api(accounts.near1, '/dealer/requests')).length, 0);
  await api(accounts.near1, '/dealer/bids', { bid_request_id: request2.id, amount: 6000 }, 'POST', 403);
  assert.equal((await api(accounts.buyer, '/bids')).find((row) => row.id === first.id).selectable, false);
  const forbidden = await fetch(apiUrl + `/buyer/bids/${first.id}/accept`, { method: 'POST', headers: { Authorization: `Bearer ${accounts.buyer.access_token}` } });
  assert.notEqual(forbidden.status, 200);
  const second = await api(accounts.near2, '/dealer/bids', { bid_request_id: request2.id, amount: 7200 });
  await api(accounts.buyer, `/buyer/bids/${second.id}/accept`, {});
  check('Subscription revoked after login blocks bid changes and acceptance of that offer; eligible dealer still wins');

  await navigate(buyerPage, 'Profile');
  await buyerPage.getByRole('button', { name: 'New Location', exact: true }).click();
  await buyerPage.getByLabel('Search address, area or pincode').fill('Northern test area');
  await buyerPage.getByRole('button', { name: 'Search', exact: true }).click();
  await buyerPage.getByRole('button', { name: 'Northern test area, Bengaluru', exact: true }).click();
  assert.equal(await buyerPage.getByRole('button', { name: 'Save Location', exact: true }).isEnabled(), false);
  await buyerPage.getByRole('button', { name: 'Confirm Pin', exact: true }).click();
  await buyerPage.getByLabel('Location name', { exact: true }).fill('E2E north office');
  await buyerPage.getByRole('button', { name: 'Save Location', exact: true }).click();
  await eventually(async () => assert.equal((await api(accounts.buyer, '/buyer/locations')).length, 2), 'Second location saved');
  const office = (await api(accounts.buyer, '/buyer/locations')).find((row) => row.label === 'E2E north office');
  const request3 = await start(office.location_id);
  const receiving = [];
  for (const [label, account] of Object.entries(accounts)) if (account.role === 'dealer' && (await api(account, '/dealer/requests')).some((row) => row.id === request3.id)) receiving.push(label);
  assert.deepEqual(receiving, ['far']);
  await api(accounts.far, '/dealer/bids', { bid_request_id: request3.id, amount: 10000 });
  await api(accounts.buyer, `/buyer/requests/${request3.id}`, undefined, 'DELETE');
  check('Changing buyer pin switches delivery eligibility: formerly distant shop receives new-location request; old nearby shops do not');
  const capped = await start(home.location_id, 2);
  const cappedReceiving = [];
  for (const [label, account] of Object.entries(accounts)) if (account.role === 'dealer' && (await api(account, '/dealer/requests')).some((row) => row.id === capped.id)) cappedReceiving.push(label);
  assert.deepEqual(cappedReceiving, ['near2']);
  await api(accounts.buyer, `/buyer/requests/${capped.id}`, undefined, 'DELETE');
  check('Buyer distance cap adds a stricter limit to the dealer radius');

  const report = await api(accounts.buyer, '/reports', { bid_id: winner.id, reason: 'E2E Live conversation', description: 'Temporary message test' });
  await navigate(buyerPage, 'Reports / Support');
  await eventually(async () => assert(await buyerPage.getByText('E2E Live conversation', { exact: true }).count()), 'Report reaches browser');
  await buyerPage.getByText('E2E Live conversation', { exact: true }).click();
  await eventually(async () => assert(await buyerPage.getByRole('button', { name: 'Send message', exact: true }).count()), 'Thread opens');
  await api(admin, `/reports/${report.id}/messages`, { recipient_group: 'both', message: 'Instant reply for E2E buyer' });
  await eventually(async () => assert(await buyerPage.getByText('Instant reply for E2E buyer', { exact: true }).count()), 'Message appears in open thread');
  check('WebSocket message updates an already-open conversation instantly');
  const before = new Map(pages.map((page) => [page, { ...socketCounts.get(page) }]));
  await new Promise((resolve) => setTimeout(resolve, 8000));
  for (const page of pages) assert.deepEqual(socketCounts.get(page), before.get(page), 'Idle tabs must not continually reconnect');
  assert(events.get(sameAccountPage).some((event) => event.type === 'new_bid'));
  check('Multiple sockets for the same account stay connected and receive events; no idle reconnect/refresh loop');
  assert.deepEqual(errors, []);
  check('No browser JavaScript errors');
  fs.writeFileSync(path.resolve('E2E_RESULTS.md'), '# End-to-end verification\n\n' + checks.map((item) => '- PASS: ' + item).join('\n') + '\n\nBrowser geolocation used granted test permissions. Address lookup responses were mocked for repeatability; matching, login, subscription, bids and messages used the running API and MariaDB. Temporary fixtures were cleaned up after the run. Native Android execution was not tested.\n');
} catch (error) {
  console.error('Browser errors:', errors);
  fs.mkdirSync(path.resolve('web/tests/artifacts'), { recursive: true });
  for (let index = 0; index < pages.length; index++) await pages[index].screenshot({ path: path.resolve(`web/tests/artifacts/failure-${index}.png`), fullPage: true }).catch(() => {});
  console.error(error.stack);
  process.exitCode = 1;
} finally {
  await context.close();
  await browser.close();
}
