import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chromium} from 'playwright';
const {accounts,apiUrl}=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const account=accounts.unsubscribed,checks=[];
const check=label=>{checks.push(label);console.log('PASS:',label);};
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1200}});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const profile=async()=>{const response=await fetch(apiUrl+'/profile',{headers:{Authorization:`Bearer ${account.access_token}`}});assert.equal(response.status,200);return response.json();};
const wait=async(callback,label)=>{const deadline=Date.now()+15000;let last;do{try{await callback();return;}catch(error){last=error;}await page.waitForTimeout(100);}while(Date.now()<deadline);throw new Error(`${label}: ${last?.message}`);};
async function save(expected){const response=page.waitForResponse(response=>response.url().endsWith('/profile')&&response.request().method()==='PUT');await page.getByRole('button',{name:'Save Business Profile',exact:true}).click();assert.equal((await response).status(),expected);await page.getByRole('button',{name:'Save Business Profile',exact:true}).waitFor();}
try{
  await page.goto(process.env.E2E_WEB_URL||'http://localhost:5173',{waitUntil:'domcontentloaded'});await page.getByLabel('Username',{exact:true}).fill(account.username);await page.getByLabel('Password',{exact:true}).fill(account.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('.app-shell').waitFor({timeout:60000});
  await page.locator('nav').getByRole('button',{name:'My shop',exact:true}).click();await page.getByLabel('Service Radius (km)',{exact:true}).fill('0');await save(422);assert.equal((await profile()).service_radius_km,5);
  check('Invalid radius is rejected without silently using a default or overwriting the saved profile');
  await wait(async()=>assert(!(await page.locator('.loading-bar').count())),'Save action ends');
  await page.getByLabel('Service Radius (km)',{exact:true}).fill('5');await page.getByLabel('Operating Branches',{exact:true}).fill('Test branch one, Test branch two');await page.getByLabel('Store Phone',{exact:true}).fill('9990001234');await page.getByLabel('Shop Name',{exact:true}).fill('E2E saved shop');await save(200);
  const saved=await profile();assert.equal(saved.business_name,'E2E saved shop');assert.equal(saved.phone,'9990001234');assert.deepEqual(saved.branches,['Test branch one','Test branch two']);check('Shop, phone and operating branches persist through Save Business Profile');
  const subscription=page.waitForResponse(response=>response.url().endsWith('/dealer/subscription/activate')&&response.request().method()==='POST');await page.locator('main').getByRole('button',{name:'Activate',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Activate (demo, no payment)',exact:true}).click();assert.equal((await subscription).status(),200);await page.getByRole('dialog').getByText('Your subscription is active').waitFor();await page.getByRole('dialog').getByRole('button',{name:'Done',exact:true}).click();await page.locator('main').getByText('Your subscription is active').waitFor();assert((await profile()).subscribed);check('Business-profile subscription button activates the demo subscription and updates its displayed status');
  const deletion=page.waitForResponse(response=>response.url().endsWith('/profile')&&response.request().method()==='DELETE');await page.getByRole('button',{name:'Delete account',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Delete my account',exact:true}).click();assert.equal((await deletion).status(),200);await page.getByRole('button',{name:'Sign in',exact:true}).waitFor();
  const blocked=await fetch(apiUrl+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:account.username,password:account.password})});assert.equal(blocked.status,401);check('Delete Account confirms, removes access, logs out and prevents another login for the deleted fixture');
  assert.deepEqual(errors,[]);check('No browser JavaScript errors');fs.writeFileSync('BUSINESS_PROFILE_E2E_RESULTS.md','# Business-profile control verification\n\n'+checks.map(label=>'- PASS: '+label).join('\n')+'\n\nUsed only a temporary fixture account. Account deletion was tested against that fixture; catalog and real accounts were preserved.\n');
}catch(error){console.error(error.stack);await page.screenshot({path:'web/tests/artifacts/business-profile-failure.png'}).catch(()=>{});process.exitCode=1;}finally{await browser.close();}
