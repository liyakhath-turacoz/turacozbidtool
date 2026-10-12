import assert from 'node:assert/strict';
import {chromium} from 'playwright';

const apiUrl=process.env.E2E_API_URL || 'http://localhost:8000';
const webUrl=process.env.E2E_WEB_URL || 'http://localhost:5173';
const password=process.env.TURACOZ_ADMIN_PASSWORD;
if(!password)throw new Error('Load TURACOZ_ADMIN_PASSWORD from private local settings before running.');
const login=await fetch(apiUrl+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'admin@turacoz',password})});
assert.equal(login.status,200);const session=await login.json();
const call=async(path,method='GET',body)=>{
  const response=await fetch(apiUrl+path,{method,headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.access_token}`},body:body===undefined?undefined:JSON.stringify(body)});
  const result=await response.json();assert(response.ok,`${path}: ${response.status}`);return result;
};
const browser=await chromium.launch({channel:process.env.E2E_BROWSER || 'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const name='Catalog QA '+Date.now();let productId;
const check=label=>console.log('PASS:',label);
const wait=async(fn)=>{let last;const until=Date.now()+20000;do{try{await fn();return;}catch(e){last=e;}await new Promise(resolve=>setTimeout(resolve,100));}while(Date.now()<until);throw last;};
const nav=async name=>page.locator('nav').getByRole('button',{name,exact:true}).click();
const save=async(method)=>{
  const response=page.waitForResponse(r=>new URL(r.url()).pathname.startsWith('/products') && r.request().method()===method);
  await page.getByRole('button',{name:'Save Product',exact:true}).click();
  const result=await response;assert.equal(result.status(),200);const body=await result.json();
  if(body.id)productId=body.id;
  await page.locator('.modal').waitFor({state:'hidden'});return body;
};
try {
  await page.goto(webUrl,{waitUntil:'domcontentloaded'});
  await page.getByLabel('Username',{exact:true}).fill('admin@turacoz');await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.locator('nav').getByRole('button',{name:'Products / Catalog',exact:true}).waitFor();
  for(const endpoint of ['/admin/dashboard','/admin/buyers','/admin/dealers/search','/reports','/admin/product-sources','/admin/product-statistics'])await call(endpoint);
  check('Admin login, dashboard, buyers, dealers, reports, source settings and statistics load');
  await nav('Products / Catalog');await page.locator('.admin-product-card').first().waitFor();
  await page.getByRole('button',{name:'Home Appliances',exact:true}).click();
  await wait(async()=>assert.match(await page.locator('.admin-product-grid').innerText(),/Refrigerator|Oven|Hisense|Gorenje|WindFree/i));
  await page.getByRole('button',{name:'Filters',exact:true}).click();
  assert.equal(await page.getByLabel('Product status filter').count(),0);
  assert.equal(await page.getByPlaceholder('Min Price',{exact:true}).count(),0);
  await page.getByLabel('Product type filter').selectOption('Refrigerators');
  await wait(async()=>assert(await page.locator('.admin-product-card').count()>0));
  const older=await call('/admin/products?limit=1&offset=500');
  assert.equal(older.items.length,1);
  await page.getByRole('button',{name:'+ Add Product',exact:true}).click();
  await page.getByLabel('Product Name (Required)',{exact:true}).fill(name);
  await page.getByLabel('Category (Required)',{exact:true}).selectOption('Home Appliances');
  await page.getByLabel('Subcategory / Item (Optional)',{exact:true}).selectOption('Ovens');
  await page.getByLabel('Brand Name (select or type new)',{exact:true}).fill('Catalog QA');
  await page.getByLabel('Model Name / Number', {exact:true}).fill('Temporary check');
  await page.getByLabel('Min Price (Rs.)',{exact:true}).fill('100');await page.getByLabel('Max Price (Rs.)',{exact:true}).fill('200');
  await page.getByLabel('Specifications',{exact:true}).fill('Warranty: 2 years\nSupport URL: https://example.test:8080/support');
  await save('POST');
  const created=await call('/products/'+productId);assert.equal(created.category,'Home Appliances');assert.equal(created.item,'Ovens');
  assert.equal(created.specifications['Support URL'],'https://example.test:8080/support');
  await wait(async()=>assert.equal(await page.locator('.admin-product-card').count(),1));
  check('Home Appliances filter and product creation save the correct parent/item and specifications');
  await page.locator('.admin-product-card').getByRole('button',{name:'Edit',exact:true}).click();
  await page.locator('.modal').getByLabel('Status',{exact:true}).selectOption('archived');
  await page.getByLabel('Max Price (Rs.)',{exact:true}).fill('250');await save('PUT');
  assert.equal((await call('/products/'+productId)).status,'archived');
  const buyerLogin=await fetch(apiUrl+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'buyer1',password:'buyer1'})});
  const buyer=await buyerLogin.json();const hidden=await fetch(apiUrl+'/products/'+productId,{headers:{Authorization:`Bearer ${buyer.access_token}`}});assert.equal(hidden.status,404);
  check('Editing prices/status works; archived products are hidden from buyers');
  page.once('dialog',dialog=>dialog.accept());
  const deleted=page.waitForResponse(r=>r.url().endsWith('/products/'+productId) && r.request().method()==='DELETE');
  await page.locator('.admin-product-card').getByRole('button',{name:'Delete',exact:true}).click();assert.equal((await deleted).status(),200);
  productId=undefined;await wait(async()=>assert.equal(await page.locator('.admin-product-card').count(),0));
  check('Delete removes the temporary product from the catalog');
  for(const label of ['Buyer Management','Dealer Management','Product Fetch & Reports']){await nav(label);await page.waitForTimeout(400);}
  assert.equal(await page.getByRole('alert').count(),0);assert.deepEqual(errors,[]);
  check('Admin panels open without browser JavaScript errors');
}finally{
  if(productId)await call('/products/'+productId,'DELETE').catch(()=>{});
  await browser.close();
}
