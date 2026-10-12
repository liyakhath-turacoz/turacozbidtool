import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chromium} from 'playwright';
const {accounts,product,country,apiUrl}=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const checks=[],errors=[],pages=[];
const check=(label)=>{checks.push(label);console.log('PASS:',label);};
const api=async(account,endpoint,body,expected=200)=>{const response=await fetch(apiUrl+endpoint,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${account.access_token}`},body:body===undefined?undefined:JSON.stringify(body)});const result=await response.json();assert.equal(response.status,expected,JSON.stringify(result));return result;};
const waitFor=async(callback,label,timeout=20000)=>{const deadline=Date.now()+timeout;let last;do{try{await callback();return;}catch(error){last=error;}await new Promise(resolve=>setTimeout(resolve,150));}while(Date.now()<deadline);throw new Error(`${label}: ${last?.message}`);};
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1200},reducedMotion:'reduce'});
async function typeField(page,locator,text){await locator.click();await page.waitForTimeout(1000);await locator.fill(text);await waitFor(async()=>assert.equal(await locator.inputValue(),text),'Flutter input accepts the complete text');await page.keyboard.press('Tab');}
async function login(label){
  const page=await context.newPage();pages.push(page);page.on('pageerror',error=>errors.push(error.message));let connected=false;
  page.on('websocket',socket=>{if(socket.url().includes('/ws/')) connected=true;});
  await page.goto(process.env.E2E_MOBILE_URL||'http://localhost:5180',{waitUntil:'domcontentloaded'});
  await page.locator('flt-semantics-placeholder').waitFor({timeout:45000});await page.locator('flt-semantics-placeholder').evaluate(element=>element.click());
  await typeField(page,page.getByRole('textbox',{name:'Username',exact:true}),accounts[label].username);await typeField(page,page.getByRole('textbox',{name:'Password',exact:true}),accounts[label].password);
  const response=page.waitForResponse(response=>response.url().endsWith('/auth/login')&&response.request().method()==='POST');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();const loggedIn=await response;const credentials=loggedIn.request().postDataJSON();assert(credentials.username===accounts[label].username&&credentials.password===accounts[label].password,'Flutter submitted the full credentials');assert.equal(loggedIn.status(),200);await waitFor(async()=>assert(connected),'Flutter login opens socket',45000);return page;
}
async function nav(page,label){const button=page.getByRole('button',{name:new RegExp('^'+label+'(?: Tab|$)')});if(!(await button.count())) await page.getByRole('button',{name:'Menu',exact:true}).click();await button.click();}
const content=page=>page.locator('body').ariaSnapshot();
try{
  const buyer=await login('buyer'),dealer1=await login('near1'),dealer2=await login('near2');
  await nav(buyer,'Bid Page');await nav(dealer1,'Active Bids');await nav(dealer2,'Active Bids');
  check('Flutter web logs three different accounts into separate tabs and opens live sockets');
  const home=await api(accounts.buyer,'/buyer/locations',{label:'Flutter home',address:'Test shop',country,state:'Karnataka',city:'Bengaluru',area:'Test area',latitude:12.9716,longitude:77.5946,is_default:true});
  const request=await api(accounts.buyer,'/buyer/bids',{product_id:product.id,location_id:home.location_id,quantity:2,expiry_minutes:30});
  await waitFor(async()=>assert.match(await content(dealer2),/Submit Bid/),'New request reaches Flutter dealer');
  await Promise.all([api(accounts.near1,'/dealer/bids',{bid_request_id:request.id,amount:6201}),api(accounts.near2,'/dealer/bids',{bid_request_id:request.id,amount:6202}),api(accounts.edgeInside,'/dealer/bids',{bid_request_id:request.id,amount:6203})]);
  for(const page of pages) await waitFor(async()=>{const text=await content(page);for(const price of ['6,201.00','6,202.00','6,203.00']) assert(text.includes(price));},'All offers live in Flutter');
  check('Three concurrent dealer offers appear in Flutter buyer and dealer screens');
  await nav(dealer1,'Dealer Dashboard');
  await waitFor(async()=>assert.match(await content(dealer1),/1 Submitted Bids/),'Flutter dashboard count updates');
  await nav(dealer1,'Active Bids');
  check('Flutter dashboard counts update from live bid snapshots');
  await buyer.getByRole('button',{name:new RegExp('Qty: 2')}).click();
  await api(accounts.edgeInside,'/dealer/bids',{bid_request_id:request.id,amount:6103});
  await waitFor(async()=>assert.match(await content(buyer),/6,103\.00/),'Flutter open buyer dialog updates');
  await buyer.keyboard.press('Escape');
  check('An already-open Flutter buyer request dialog updates competing offers instantly');
  const winner=(await api(accounts.buyer,'/bids')).find(bid=>bid.bid_request_id===request.id&&bid.dealer_id===accounts.near1.id);
  await api(accounts.buyer,`/buyer/bids/${winner.id}/accept`,{});
  await waitFor(async()=>assert(await buyer.getByRole('button',{name:'Contacts & Chat',exact:true}).count()),'Flutter buyer finalization');
  await waitFor(async()=>assert(await dealer1.getByRole('button',{name:'Contacts & Chat',exact:true}).count()),'Flutter winner finalization');
  await waitFor(async()=>assert(await dealer2.getByRole('button',{name:'Final offer details',exact:true}).count()),'Flutter losing dealer finalization');
  await buyer.getByRole('button',{name:'Contacts & Chat',exact:true}).click();await dealer1.getByRole('button',{name:'Contacts & Chat',exact:true}).click();
  await waitFor(async()=>assert((await content(dealer1)).includes(accounts.buyer.username)),'Flutter winner contact renders');await waitFor(async()=>assert((await content(buyer)).includes(accounts.near1.username)),'Flutter buyer contact renders');
  check('Flutter buyer and winner immediately receive contacts; losing dealer receives the final offer');
  await typeField(buyer,buyer.getByRole('textbox',{name:/Bid message/}),'Flutter buyer instant question');
  await waitFor(async()=>assert((await content(buyer)).includes(`${4000-'Flutter buyer instant question'.length} characters remaining`)),'Flutter buyer message controller receives complete text');
  const buyerMessage=buyer.waitForResponse(response=>response.url().endsWith(`/bids/${winner.id}/messages`)&&response.request().method()==='POST');
  await buyer.getByRole('button',{name:'Send bid message',exact:true}).click();assert.equal((await buyerMessage).request().postDataJSON().message,'Flutter buyer instant question');
  await waitFor(async()=>assert.match(await content(dealer1),/Flutter buyer instant question/),'Flutter winner receives chat');
  await typeField(dealer1,dealer1.getByRole('textbox',{name:/Bid message/}),'Flutter dealer instant answer');
  await waitFor(async()=>assert((await content(dealer1)).includes(`${4000-'Flutter dealer instant answer'.length} characters remaining`)),'Flutter dealer message controller receives complete text');
  const dealerMessage=dealer1.waitForResponse(response=>response.url().endsWith(`/bids/${winner.id}/messages`)&&response.request().method()==='POST');
  await dealer1.getByRole('button',{name:'Send bid message',exact:true}).click();assert.equal((await dealerMessage).request().postDataJSON().message,'Flutter dealer instant answer');
  await waitFor(async()=>assert.match(await content(buyer),/Flutter dealer instant answer/),'Flutter buyer receives chat');
  check('Flutter private bid chat sends and receives instantly in both directions');
  assert.deepEqual(errors,[]);check('No Flutter web browser errors');
  fs.writeFileSync('MOBILE_WEB_E2E_RESULTS.md','# Flutter web end-to-end verification\n\n'+checks.map(label=>'- PASS: '+label).join('\n')+'\n\nExecuted the release Flutter web build with real API/MariaDB and temporary fixture accounts. Offers were submitted through the API; login, dialogs and private chat used Flutter controls. Native Android execution was not tested.\n');
}catch(error){console.error(error.stack);for(let i=0;i<pages.length;i++){let snapshot=await content(pages[i]).catch(()=>'');for(const account of Object.values(accounts))snapshot=snapshot.replaceAll(account.password,'[redacted]');console.error(`Flutter page ${i}:`,snapshot.slice(0,4000));await pages[i].screenshot({path:`web/tests/artifacts/mobile-failure-${i}.png`}).catch(()=>{});}process.exitCode=1;}
finally{await context.close();await browser.close();}
