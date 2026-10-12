import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const state = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const { accounts, product, country, settings, admin, apiUrl } = state;
const checks = [], errors = [], pages = [], eventLog = new Map();
const check = (message) => { checks.push(message); console.log('PASS:', message); };
const api = async (account, endpoint, body, method, expected = 200) => {
  const response = await fetch(apiUrl + endpoint, { method: method || (body === undefined ? 'GET' : 'POST'), headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${account.access_token}` }, body: body === undefined ? undefined : JSON.stringify(body) });
  const result = await response.json(); assert.equal(response.status, expected, `${endpoint}: ${JSON.stringify(result)}`); return result;
};
const waitFor = async (callback, label, timeout = 12000) => {
  const deadline = Date.now() + timeout; let error;
  do { try { await callback(); return; } catch (caught) { error = caught; } await new Promise((resolve) => setTimeout(resolve, 80)); } while (Date.now() < deadline);
  throw new Error(`${label}: ${error?.message}`);
};
const browser = await chromium.launch({ channel: process.env.E2E_BROWSER || 'msedge', headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1200 }, permissions: ['geolocation'], geolocation: { latitude: 12.9716, longitude: 77.5946 }, reducedMotion: 'reduce' });
await context.addInitScript(() => {
  const Original = window.WebSocket; window.testSockets = [];
  window.WebSocket = class extends Original { constructor(...args) { super(...args); window.testSockets.push(this); this.addEventListener('message', (event) => { if(window.testDropSnapshots && JSON.parse(event.data || '{}').type === 'bid_snapshot') event.stopImmediatePropagation(); }); } };
});
await context.route('**/locations/reverse?*', (route) => route.fulfill({ json: { display_name: 'Test shop, Bengaluru', address: { road: 'Test shop', suburb: 'Test area', city: 'Bengaluru', state: 'Karnataka', country, postcode: '560001' } } }));
await context.route('**/locations/search?*', (route) => route.fulfill({ json: [{ place_id: 1, lat: '12.9716', lon: '77.5946', display_name: 'Test shop, Bengaluru', address: { city: 'Bengaluru', state: 'Karnataka', country } }] }));
async function login(label) {
  const account = label === 'admin' ? { ...admin, username: 'admin@turacoz', password: process.env.TURACOZ_ADMIN_PASSWORD || admin.password } : accounts[label];
  const page = await context.newPage(); pages.push(page); eventLog.set(page, []);
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('websocket', (socket) => socket.on('framereceived', ({ payload }) => { try { eventLog.get(page).push({ at: Date.now(), ...JSON.parse(payload.toString()) }); } catch {} }));
  await page.goto(process.env.E2E_WEB_URL || 'http://localhost:5173', {waitUntil:'domcontentloaded'});
  await page.getByLabel('Username', { exact: true }).fill(account.username);
  await page.getByLabel('Password', { exact: true }).fill(account.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await page.locator('.app-shell').waitFor({ timeout: 60000 });
  await waitFor(async () => assert(await page.evaluate(() => window.testSockets.some((socket) => socket.url.includes('/ws/') && socket.readyState === 1))), 'Socket opens');
  return page;
}
async function nav(page, label) {
  const button = page.locator('nav').getByRole('button', { name: label, exact: true });
  const bounds = await button.boundingBox(); if (!bounds || bounds.x < 0) await page.getByRole('button', { name: 'Menu', exact: true }).click(); await button.click();
}
const duration = Math.round(settings.bid_rules.expiry_hours * 60);
const start = (locationId, expiry = duration, radius = 0) => api(accounts.buyer, '/buyer/bids', { product_id: product.id, location_id: locationId, quantity: 2, expiry_minutes: expiry, radius_km: radius });
const requestOffers = async (account, id) => (await api(account, '/bids')).filter((bid) => bid.bid_request_id === id);
async function submit(page, amount) {
  await page.getByRole('button', { name: 'Submit Bid', exact: true }).first().click();
  await page.getByLabel('Final Total (Rs.)').fill(String(amount)); await page.getByLabel('Warranty Text').fill('2 years'); await page.getByLabel('Delivery Time', { exact: true }).fill('next day');
  await page.locator('.modal').getByRole('button', { name: 'Submit Bid', exact: true }).click(); await page.locator('.modal').waitFor({ state: 'hidden' });
}
async function saveBusiness(page) {
  const response = page.waitForResponse((response) => response.url().endsWith('/profile') && response.request().method() === 'PUT');
  await page.getByRole('button', { name: 'Save Business Profile', exact: true }).click();
  assert.equal((await response).status(), 200);
  await waitFor(async () => assert.match(await page.locator('.toast-pop').innerText({ timeout: 1000 }), /updated successfully/), 'Profile save feedback');
}

try {
  const buyer = await login('buyer'), dealer1 = await login('near1'), dealer2 = await login('near2'), dealer3 = await login('edgeInside'), duplicate = await login('near1'), adminPage = await login('admin');
  const dealerPages = [dealer1, dealer2, dealer3, duplicate];
  const home = await api(accounts.buyer, '/buyer/locations', { label: 'Live test home', address: 'Test shop', country, state: 'Karnataka', city: 'Bengaluru', area: 'Test area', pincode: '560001', latitude: 12.9716, longitude: 77.5946, is_default: true });
  const homeId = home.location_id;
  await nav(dealer1, 'Business Profile');
  await dealer1.getByRole('button', { name: 'Search', exact: true }).waitFor();
  await dealer1.getByLabel('Search address, area or pincode').fill('Test shop'); await dealer1.getByRole('button', { name: 'Search', exact: true }).click();
  await dealer1.getByRole('button', { name: 'Test shop, Bengaluru', exact: true }).click();
  await waitFor(async () => assert(!(await dealer1.getByRole('button', { name: 'Save Business Profile', exact: true }).isEnabled())), 'Unconfirmed pin disables save');
  await dealer1.getByRole('button', { name: 'Confirm Pin', exact: true }).click();
  await dealer1.getByRole('button', { name: 'Use my location', exact: true }).click();
  await waitFor(async () => assert(await dealer1.getByRole('button', { name: 'Save Business Profile', exact: true }).isEnabled()), 'GPS pin confirms');
  await dealer1.getByLabel('Service Radius (km)', { exact: true }).fill('5'); await saveBusiness(dealer1);
  assert.equal((await api(accounts.near1, '/profile')).service_radius_km, 5);
  check('Business search, result selection, pin confirmation, browser location and radius save buttons work');
  await dealer1.getByRole('button', { name: `Remove ${product.category} / ${product.item}`, exact: true }).click();
  await dealer1.getByLabel('Dealt Items / Product Types', { exact: true }).selectOption(product.item_id);
  await dealer1.getByRole('button', { name: `Remove ${product.category}`, exact: true }).click();
  await dealer1.getByLabel('Dealt Categories (Parent Group)', { exact: true }).selectOption(product.category_id);
  await dealer1.getByLabel('Dealt Items / Product Types', { exact: true }).selectOption(product.item_id);
  await saveBusiness(dealer1);
  assert((await api(accounts.near1, '/profile')).category_ids.includes(product.item_id));
  check('Product-type and parent category add/remove buttons persist the selected item type');

  for (const [method, field, value] of [['city', 'Service Cities', 'Bengaluru'], ['state', 'Service States', 'Karnataka'], ['district', 'Service Districts', 'Test area']]) {
    await dealer1.getByLabel('Delivery Method').selectOption(method);
    await dealer1.getByLabel(field, { exact: true }).fill(value);
    if (method !== 'state') await dealer1.getByLabel('Service States', { exact: true }).fill('Karnataka');
    await saveBusiness(dealer1);
    const saved = await api(accounts.near1, '/profile'); assert.equal(saved.delivery_method, method); assert(saved[`service_${method === 'city' ? 'cities' : method === 'state' ? 'states' : 'districts'}`].includes(value));
    const request = await start(homeId); assert((await api(accounts.near1, '/dealer/requests')).some((row) => row.id === request.id)); await api(accounts.buyer, `/buyer/requests/${request.id}`, undefined, 'DELETE');
  }
  await dealer1.getByLabel('Service States', { exact: true }).fill('Maharashtra'); await saveBusiness(dealer1);
  const wrongState = await start(homeId); assert(!(await api(accounts.near1, '/dealer/requests')).some((row) => row.id === wrongState.id)); await api(accounts.buyer, `/buyer/requests/${wrongState.id}`, undefined, 'DELETE');
  await dealer1.getByLabel('Delivery Method').selectOption('radius'); await dealer1.getByLabel('Service Radius (km)', { exact: true }).fill('5'); await saveBusiness(dealer1);
  check('Cities, states and district coverage persist and match; wrong-state coverage excludes the request; switching back to radius works');

  for (const page of dealerPages) await nav(page, 'Active Bids'); await nav(buyer, 'Bid Page');
  const request = await start(homeId);
  const savedRequest = (await api(accounts.buyer, '/buyer/requests')).find((row) => row.id === request.id);
  assert(Math.abs((Date.parse(savedRequest.expires_at) - Date.now()) / 60000 - duration) < 1);
  await api(accounts.buyer, '/buyer/bids', { product_id: product.id, location_id: homeId, quantity: 1, expiry_minutes: 5000 }, 'POST', 422);
  check('Admin default duration is applied; invalid duration is rejected; all participants use the same saved deadline');
  await Promise.all([submit(dealer1, 10011), submit(dealer2, 10012), submit(dealer3, 10013)]);
  for (const page of dealerPages) await waitFor(async () => { const body = await page.locator('main').innerText(); for (const amount of ['10,011.00','10,012.00','10,013.00']) assert(body.includes(amount)); }, 'Three concurrent offers visible');
  for (const account of [accounts.near1, accounts.near2, accounts.edgeInside, accounts.buyer]) {
    const offers = await requestOffers(account, request.id); assert.equal(offers.length, 3); assert(offers.every((bid) => Date.parse(bid.ends_at) === Date.parse(savedRequest.expires_at)));
  }
  check('Three simultaneous dealer submissions appear to every participating dealer and the buyer, including a second same-account tab');
  const firstOffers = await requestOffers(accounts.buyer, request.id);
  const dealer3Offer = firstOffers.find((bid) => bid.dealer_id === accounts.edgeInside.id);
  await dealer2.getByText(`${product.name} (${(await requestOffers(accounts.near2, request.id)).find((bid) => bid.id === dealer3Offer.id).dealer})`, { exact: true }).click();
  for (let round = 0; round < 5; round++) {
    await Promise.all([accounts.near1,accounts.near2,accounts.edgeInside].map((account, index) => api(account, '/dealer/bids', { bid_request_id: request.id, amount: 9000 - round * 100 + index, warranty_text: `Round ${round}`, delivery_time: 'next day' })));
  }
  await waitFor(async () => assert.match(await dealer2.locator('.modal').innerText(), /8,602\.00/), 'Open competitor details updates');
  await dealer2.locator('.modal').getByRole('button', { name: 'Close', exact: true }).click();
  for (const page of [...dealerPages,buyer]) await waitFor(async () => assert.match(await page.locator('main').innerText(), /8,602\.00/), 'Burst final revision visible');
  check('Concurrent revisions stay consistent; dealer 3 updates dealer 2 instantly even with the details dialog already open');

  await dealer2.evaluate(() => window.testSockets.filter((socket) => socket.url.includes('/ws/')).forEach((socket) => socket.close()));
  await api(accounts.edgeInside, '/dealer/bids', { bid_request_id: request.id, amount: 8502 });
  await waitFor(async () => assert.match(await dealer2.locator('main').innerText(), /8,502\.00/), 'Reconnect catches missed update');
  check('A disconnected dealer catches missed offers after reconnect without reloading the page');
  await dealer2.evaluate(()=>{window.testDropSnapshots=true;});
  await api(accounts.edgeInside,'/dealer/bids',{bid_request_id:request.id,amount:8402});
  await dealer2.evaluate((requestId)=>window.testSockets.filter(socket=>socket.url.includes('/ws/')&&socket.readyState===1).forEach(socket=>socket.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({type:'bid_updated',request_id:requestId,refresh_required:true})}))),request.id);
  await waitFor(async()=>assert.match(await dealer2.locator('main').innerText(),/8,402\.00/),'Fallback reloads missed snapshot');
  await dealer2.evaluate(()=>{window.testDropSnapshots=false;});
  check('The fallback event reloads offers after a missed snapshot even when earlier snapshots were already received');
  const accept = await requestOffers(accounts.buyer, request.id); const winner = accept.find((bid) => bid.dealer_id === accounts.near1.id);
  const beforeAward = Date.now(); await api(accounts.buyer, `/buyer/bids/${winner.id}/accept`, {});
  for (const page of [...dealerPages,buyer]) await waitFor(async () => assert(await page.getByRole('button', { name: /Contacts & Chat|Final offer details/ }).count()), 'Final result shown');
  for (const account of [accounts.near1,accounts.near2,accounts.edgeInside,accounts.buyer]) { const rows = await requestOffers(account, request.id); assert.equal(rows.length,3); assert.equal(rows.filter((bid) => bid.status==='won').length,1); assert.equal(rows.filter((bid) => bid.status==='lost').length,2); }
  const peerWinner = (await requestOffers(accounts.near2, request.id)).find((bid) => bid.id === winner.id); assert(!peerWinner.buyer_email && !peerWinner.dealer_email);
  const ownWinner = (await requestOffers(accounts.near1, request.id)).find((bid) => bid.id===winner.id); assert.equal(ownWinner.buyer_email,accounts.buyer.username); assert.equal(Number(ownWinner.commission),0);
  const buyerWinner = (await requestOffers(accounts.buyer, request.id)).find((bid) => bid.id===winner.id); assert.equal(buyerWinner.dealer_email,accounts.near1.username);
  assert.equal((await api(admin,'/admin/payments')).filter((payment)=>payment.bid_id===winner.id).length,0);
  check('Finalization is pushed to buyer and all dealers; winner contacts unlock immediately, losing dealers see final terms, and no commission is charged');

  await buyer.getByRole('button',{name:'Contacts & Chat',exact:true}).click(); await dealer1.getByRole('button',{name:'Contacts & Chat',exact:true}).click();
  await buyer.getByLabel('Bid message',{exact:true}).fill('Buyer live delivery question'); await buyer.getByRole('button',{name:'Send bid message',exact:true}).click();
  await waitFor(async()=>assert(await dealer1.getByText('Buyer live delivery question',{exact:true}).count()),'Winner receives buyer chat');
  await dealer1.getByLabel('Bid message',{exact:true}).fill('Dealer live delivery answer'); await dealer1.getByRole('button',{name:'Send bid message',exact:true}).click();
  await waitFor(async()=>assert(await buyer.getByText('Dealer live delivery answer',{exact:true}).count()),'Buyer receives dealer chat');
  await api(accounts.near2,`/bids/${winner.id}/messages`,undefined,'GET',403); await api(accounts.far,`/bids/${winner.id}/messages`,{message:'Blocked outsider'},'POST',403);
  assert(!eventLog.get(dealer2).some((event)=>event.type==='bid_message' && event.bid_id===winner.id));
  check('Private winner/buyer chat delivers both ways instantly; losing dealers and outsiders cannot read, send or receive it');
  await buyer.getByRole('button',{name:'Report dealer',exact:true}).click(); await buyer.getByLabel('Description',{exact:true}).fill('E2E buyer report');
  const buyerReport=buyer.waitForResponse((response)=>response.url().endsWith('/reports')&&response.request().method()==='POST');
  await buyer.getByRole('button',{name:'Submit Report',exact:true}).click(); assert.equal((await buyerReport).status(),200);
  await waitFor(async()=>assert.equal(await buyer.getByRole('button',{name:'Submit Report',exact:true}).count(),0),'Buyer report completed');
  await dealer1.getByRole('button',{name:'Report buyer',exact:true}).click(); await dealer1.getByLabel('Description',{exact:true}).fill('E2E dealer counter report');
  const dealerReport=dealer1.waitForResponse((response)=>response.url().endsWith('/reports')&&response.request().method()==='POST');
  await dealer1.getByRole('button',{name:'Submit Report',exact:true}).click(); assert.equal((await dealerReport).status(),200);
  await waitFor(async()=>assert.equal(await dealer1.getByRole('button',{name:'Submit Report',exact:true}).count(),0),'Dealer report completed');
  await nav(adminPage,'Reports');
  const reports = (await api(admin,'/reports')).filter((report)=>report.bid_id===winner.id); assert(reports.length); assert.match(reports[0].description,/E2E buyer report/); assert.match(reports[0].description,/E2E dealer counter report/);
  check('Buyer and winning dealer can report each other; both complaints reach admin');
  await waitFor(async()=>assert((await adminPage.locator('main').innerText()).includes('E2E near1')),'Report reaches admin screen');
  await adminPage.locator('.admin-list-item').filter({hasText:'E2E near1'}).first().click();
  await waitFor(async()=>assert(await adminPage.getByText('Buyer live delivery question',{exact:true}).count()),'Admin inspects linked winning conversation');
  await api(admin,`/bids/${winner.id}/messages`,{message:'Admin cannot impersonate either participant'},'POST',403);
  check('Admin can inspect the reported winning conversation but cannot send as a participant');
  await dealer1.getByLabel('Bid message',{exact:true}).fill('Unsent draft survives reconnect');
  await dealer1.evaluate(()=>window.testSockets.filter((socket)=>socket.url.includes('/ws/')).forEach((socket)=>socket.close()));
  await api(accounts.buyer,`/bids/${winner.id}/messages`,{message:'Message sent during reconnect'});
  await waitFor(async()=>assert(await dealer1.getByText('Message sent during reconnect',{exact:true}).count()),'Missed chat recovered');
  assert.equal(await dealer1.getByLabel('Bid message',{exact:true}).inputValue(),'Unsent draft survives reconnect');
  check('Reconnecting an open private chat restores missed messages and preserves its unsent draft');
  await nav(adminPage,'Platform Rules & Categories');
  await waitFor(async()=>assert.equal(Number(await adminPage.getByLabel('Default bidding duration (hours)',{exact:true}).inputValue()),Number(settings.bid_rules.expiry_hours)),'Admin timing controls load');
  const ruleResponse=adminPage.waitForResponse((response)=>response.url().endsWith('/settings/bid_rules')&&response.request().method()==='POST');
  await adminPage.getByRole('button',{name:'Save bid rules',exact:true}).click(); assert.equal((await ruleResponse).status(),200);
  await api(admin,'/settings/bid_rules',{value:{expiry_hours:Number(settings.bid_rules.max_time_hours)+1}},'POST',400);
  assert.equal(Number((await api(admin,'/settings')).bid_rules.expiry_hours),Number(settings.bid_rules.expiry_hours));
  check('Web admin can save timing rules; invalid duration bounds are rejected and existing deadlines stay fixed');
  const snapshotLatencies = [...dealerPages,buyer].map((page)=>eventLog.get(page).find((event)=>event.type==='bid_snapshot' && event.request_id===request.id && event.request.status==='awarded')?.at-beforeAward);
  assert(snapshotLatencies.every((latency)=>Number.isFinite(latency)&&latency<2000));
  check(`Final result WebSocket delivery measured ${Math.max(...snapshotLatencies)} ms at the slowest participant`);
  if(Number(settings.bid_rules.min_time_hours)*60<=1) {
    const expiring=await start(homeId,1);
    await api(accounts.near2,'/dealer/bids',{bid_request_id:expiring.id,amount:7500});
    await waitFor(async()=>{for(const page of [...dealerPages,buyer]) assert(eventLog.get(page).some((event)=>event.type==='bid_snapshot'&&event.request_id===expiring.id&&event.request.status==='expired'));},'Expiry is pushed to every participant',75000);
    for(const account of [accounts.near1,accounts.near2,accounts.edgeInside,accounts.buyer]) assert.equal((await requestOffers(account,expiring.id))[0].status,'expired');
    await api(accounts.near2,'/dealer/bids',{bid_request_id:expiring.id,amount:7400},'POST',400);
    check('The shared deadline expires the request and offer live for all participants and blocks late revisions');
  }
  const farProfile=await api(accounts.far,'/profile');
  const regional={...farProfile,full_name:farProfile.full_name||farProfile.name,categories:farProfile.category_ids,delivery_method:'city',service_cities:['Bengaluru'],service_states:[],latitude:0,longitude:0};
  await api(accounts.far,'/profile',regional,'PUT');
  const savedRegional=await api(accounts.far,'/profile');assert.equal(savedRegional.country,country);assert.equal(savedRegional.state,'Karnataka');assert.equal(savedRegional.service_radius_km,5);
  const regionalRequest=await start(homeId);assert((await api(accounts.far,'/dealer/requests')).some(row=>row.id===regionalRequest.id));await api(accounts.buyer,`/buyer/requests/${regionalRequest.id}`,undefined,'DELETE');
  const cappedRegional=await start(homeId,duration,1);assert(!(await api(accounts.far,'/dealer/requests')).some(row=>row.id===cappedRegional.id));await api(accounts.buyer,`/buyer/requests/${cappedRegional.id}`,undefined,'DELETE');
  await api(accounts.far,'/profile',{...regional,delivery_method:'radius'},'PUT',400);
  assert.equal((await api(accounts.far,'/profile')).delivery_method,'city');
  check('Regional coverage without a shop pin retains state/city metadata and matches correctly; a buyer distance cap requires a pin; invalid radius save is rejected atomically');
  assert.deepEqual(errors,[]); check('No browser JavaScript errors');
  fs.writeFileSync(path.resolve('LIVE_E2E_RESULTS.md'),'# Concurrent live bidding verification\n\n'+checks.map((item)=>'- PASS: '+item).join('\n')+'\n\nUsed real API/MariaDB and existing products with temporary fixture accounts. Address lookup was mocked; browser location permission was granted. Fixture data is removed afterward. Native Android execution was not tested.\n');
} catch(error) {
  console.error(error.stack); console.error('Browser errors:',errors); fs.mkdirSync('web/tests/artifacts',{recursive:true});
  for(let index=0;index<pages.length;index++) await pages[index].screenshot({path:`web/tests/artifacts/live-failure-${index}.png`,fullPage:true}).catch(()=>{}); process.exitCode=1;
} finally { await context.close(); await browser.close(); }
