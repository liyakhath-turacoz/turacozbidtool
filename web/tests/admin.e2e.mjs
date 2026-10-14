import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chromium} from 'playwright';
const statePath=process.argv[2],state=JSON.parse(fs.readFileSync(statePath,'utf8'));
const {accounts,admin,apiUrl,country}=state;
const prefix=country+' admin',checks=[],errors=[];
state.adminResources={products:[],categories:[]};
const track=(kind,id)=>{state.adminResources[kind].push(id);fs.writeFileSync(statePath,JSON.stringify(state));};
const api=async(account,endpoint,body,method,expected=200)=>{const response=await fetch(apiUrl+endpoint,{method:method||(body===undefined?'GET':'POST'),headers:{'Content-Type':'application/json',Authorization:`Bearer ${account.access_token}`},body:body===undefined?undefined:JSON.stringify(body)});const result=await response.json();assert.equal(response.status,expected,`${endpoint}: ${JSON.stringify(result)}`);return result;};
const wait=async(callback,label)=>{let last;const deadline=Date.now()+15000;do{try{await callback();return;}catch(error){last=error;}await new Promise(resolve=>setTimeout(resolve,100));}while(Date.now()<deadline);throw new Error(`${label}: ${last?.message}`);};
const check=label=>{checks.push(label);console.log('PASS:',label);};
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1200}});
page.on('pageerror',error=>errors.push(error.message));
async function nav(name){await page.locator('nav').getByRole('button',{name,exact:true}).click();}
async function searchProducts(text){await page.getByLabel('Search products',{exact:true}).fill(text);await page.getByRole('button',{name:'Search',exact:true}).click();await wait(async()=>assert.equal(await page.getByRole('status').count(),0),'Catalog search finishes');}
async function saveProduct(method='POST'){const response=page.waitForResponse(response=>response.url().includes('/products')&&response.request().method()===method);await page.getByRole('button',{name:'Save Product',exact:true}).click();const result=await response;assert.equal(result.status(),200);const saved=await result.json();if(saved.id)track('products',saved.id);await page.locator('.modal').waitFor({state:'hidden'});return saved;}
try{
  await api(admin,`/admin/users/${admin.id}/status`,{status:'deleted'},'POST',400);
  await api(admin,'/profile',undefined,'DELETE',403);
  const branchDealers=await api(admin,'/admin/dealers');
  const branchDealer=branchDealers.filter(dealer=>dealer.id===accounts.near2.id);assert.equal(branchDealer.length,1);assert.match(branchDealer[0].city,/Bengaluru/);assert.match(branchDealer[0].city,/Mysuru/);
  const searchedBranch=(await api(admin,'/admin/dealers/search')).filter(dealer=>dealer.id===accounts.near2.id);assert.equal(searchedBranch.length,1);assert.match(searchedBranch[0].city,/Mysuru/);
  check('Admin accounts cannot be moderated/deleted, and multiple dealer service locations produce one account with all cities');
  const totalBefore=(await api(admin,'/admin/products?limit=1')).catalog_total;
  const parent=await api(admin,'/admin/categories',{name:prefix+' parent'});track('categories',parent.id);
  const child=await api(admin,'/admin/categories',{name:prefix+' item',parent_id:parent.id});track('categories',child.id);
  await page.goto('http://localhost:5173',{waitUntil:'domcontentloaded'});await page.getByLabel('Username',{exact:true}).fill('admin@turacoz');await page.getByLabel('Password',{exact:true}).fill(admin.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('.app-shell').waitFor({timeout:60000});
  await nav('Products / Catalog');await wait(async()=>assert.match(await page.locator('main').innerText(),new RegExp(totalBefore.toLocaleString()+' products in the catalog')),'Full catalog count');
  const first=await api(admin,'/admin/products?limit=50&offset=0'),second=await api(admin,'/admin/products?limit=50&offset=50');assert.equal(first.items.length,50);assert.equal(second.items.length,50);assert(!second.items.some(item=>first.items.some(other=>other.id===item.id)));
  await page.getByRole('button',{name:'Next products',exact:true}).click();await wait(async()=>assert.match(await page.locator('main').innerText(),/Page 2 of/),'Next page');await page.getByRole('button',{name:'Previous products',exact:true}).click();
  const older=(await api(admin,'/admin/products?limit=1&offset=300')).items[0];await searchProducts(older.id);await wait(async()=>assert.equal(await page.locator('.admin-product-card').count(),1),'Search beyond first 250');
  check('Admin shows the complete product count, pages without duplicate rows, and finds products beyond the first 250');
  await page.getByRole('button',{name:'+ Add Product',exact:true}).click();await page.getByLabel('Product Name (Required)',{exact:true}).fill(prefix+' product');await page.getByLabel('Category (Required)').selectOption(prefix+' parent');await page.getByLabel('Subcategory / Item').selectOption(prefix+' item');await page.getByLabel('Brand Name').fill('Fixture brand');await page.getByLabel('Model Name').fill('Fixture model');await page.getByLabel('Min Price (Rs.)',{exact:true}).fill('100');await page.getByLabel('Max Price (Rs.)',{exact:true}).fill('200');await page.getByLabel('Specifications',{exact:true}).fill('Support URL: https://example.test:8080/support\nWarranty: 2 years');
  const created=await saveProduct();const productId=created.id;
  const detail=await api(admin,`/products/${productId}`);assert.equal(detail.specifications['Support URL'],'https://example.test:8080/support');assert.equal(detail.item,prefix+' item');
  check('Add Product saves category/item, brand, model, prices and specification values containing colons');
  await searchProducts(prefix+' product');await page.locator('.admin-product-card').getByRole('button',{name:'Edit',exact:true}).click();await page.locator('.modal').getByLabel('Status').selectOption('archived');await page.getByLabel('Max Price (Rs.)',{exact:true}).fill('250');await saveProduct('PUT');assert.equal((await api(admin,`/products/${productId}`)).status,'archived');
  await searchProducts(prefix+' product');await wait(async()=>assert.equal(await page.locator('.admin-product-card').count(),1),'Archived product stays listed for admin');
  await api(accounts.buyer,`/products/${productId}`,undefined,'GET',404);await api(admin,`/admin/categories/${child.id}`,undefined,'DELETE',409);await api(admin,`/admin/categories/${parent.id}`,undefined,'DELETE',409);
  check('Archived products remain editable by admin and hidden from buyers; deleting a used category/item is blocked');
  const valid={name:prefix+' product',category:parent.id,subcategory:child.id,brand:'Fixture brand',model:'Fixture model',price_min:100,price_max:250,status:'active',specifications:detail.specifications};
  await api(admin,`/products/${productId}`,valid,'PUT');await api(admin,`/products/${productId}`,{...valid,price_min:300},'PUT',422);await api(accounts.buyer,'/products',valid,'POST',403);await api(accounts.near1,`/products/${productId}`,valid,'PUT',403);await api(accounts.buyer,'/admin/products',undefined,'GET',403);
  assert.equal((await api(admin,`/products/${productId}`)).price_min,'100.00');check('Invalid prices roll back and non-admin accounts cannot create, edit or list admin products');
  const location=await api(accounts.buyer,'/buyer/locations',{label:prefix+' home',address:'Test street',country,state:'Karnataka',city:'Bengaluru',area:'Test area',pincode:'560001',latitude:12.9716,longitude:77.5946,is_default:true});
  const buyerDetails=await api(admin,`/admin/buyers/${accounts.buyer.id}/details`);assert.equal(buyerDetails.locations.length,1);assert.equal(buyerDetails.basic.purchase_count,0);
  await nav('Buyer Management');await page.getByPlaceholder('Search Name, ID, Phone, Email, Pincode...').fill(accounts.buyer.username);await page.locator('.admin-list-item').filter({hasText:accounts.buyer.username}).first().click();await page.locator('.modal').waitFor();assert.match(await page.locator('.modal').innerText(),new RegExp(prefix+' home'));await page.getByRole('button',{name:'Close',exact:true}).click();
  check('Admin buyer details show saved locations before any request exists and accurate purchase counts');
  await api(admin,`/admin/dealers/${accounts.buyer.id}/details`,undefined,'GET',404);await api(admin,`/admin/buyers/${accounts.near1.id}/details`,undefined,'GET',404);await api(accounts.buyer,`/admin/buyers/${accounts.buyer.id}/details`,undefined,'GET',403);
  const profile=await api(accounts.near1,'/profile');await api(accounts.near1,'/profile',{...profile,full_name:profile.owner_name || 'E2E near1',categories:[child.id]},'PUT');
  await nav('Dealer Management');await page.getByPlaceholder('Search Name, Business, Phone, Category, State, District, Brand...').fill(accounts.near1.username);
  const dealerRow=page.locator('.admin-list-item').filter({hasText:accounts.near1.username}).first();
  for(const status of ['pending','held','suspended','banned','verified']){const response=page.waitForResponse(response=>response.url().endsWith(`/admin/users/${accounts.near1.id}/status`)&&response.request().method()==='POST');await dealerRow.getByTitle('Change status').selectOption(status);if(['held','suspended','banned'].includes(status)){await page.getByRole('dialog').getByRole('button',{name:status[0].toUpperCase()+status.slice(1),exact:true}).click();}assert.equal((await response).status(),200);await wait(async()=>assert.equal(await dealerRow.getByTitle('Change status').inputValue(),status),'Moderation persists');if(['held','suspended','banned'].includes(status))await api(accounts.near1,'/profile',undefined,'GET',403);}
  const dealerDetails=await api(admin,`/admin/dealers/${accounts.near1.id}/details`);assert.equal(dealerDetails.basic.verification_status,'verified');assert(dealerDetails.basic.subscribed);assert(dealerDetails.timeline.length>=5);
  await dealerRow.click();await page.locator('.modal').waitFor();assert.match(await page.locator('.modal').innerText(),/pending → held/);await page.getByRole('button',{name:'Close',exact:true}).click();
  check('All moderation states display correctly, held/suspended/banned access is blocked, approval restores verification, and timeline records changes');
  const request=await api(accounts.buyer,'/buyer/bids',{product_id:productId,location_id:location.location_id,quantity:1,expiry_minutes:30});const bid=await api(accounts.near1,'/dealer/bids',{bid_request_id:request.id,amount:180});await api(accounts.buyer,`/buyer/bids/${bid.id}/accept`,{});
  const purchased=await api(admin,`/admin/buyers/${accounts.buyer.id}/details`);assert.equal(purchased.basic.purchase_count,1);assert.equal(purchased.bids[0].winning_amount,'180.00');await api(admin,`/products/${productId}`,{...valid,name:prefix+' changed identity'},'PUT',409);
  await nav('Products / Catalog');await searchProducts(prefix+' product');await page.locator('.admin-product-card').getByRole('button',{name:'Edit',exact:true}).click();assert(await page.getByLabel('Product Name (Required)',{exact:true}).isDisabled());await page.getByLabel('Max Price (Rs.)',{exact:true}).fill('275');await saveProduct('PUT');
  check('Winning purchases count correctly; products with bid history lock identity but allow price/spec/status edits');
  await page.locator('.admin-product-card').getByRole('button',{name:'Delete',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Delete product',exact:true}).click();await wait(async()=>assert.equal(await page.locator('.admin-product-card').count(),0),'Product deletion updates catalog');assert((await api(admin,'/bids')).some(record=>record.id===bid.id&&record.status==='won'));
  await nav('Buyer Management');await page.getByPlaceholder('Search Name, ID, Phone, Email, Pincode...').fill(accounts.buyer.username);const buyerRow=page.locator('.admin-list-item').filter({hasText:accounts.buyer.username}).first();await buyerRow.getByTitle('Change status').selectOption('deleted');await page.getByRole('dialog').getByRole('button',{name:'Cancel',exact:true}).click();assert.equal((await api(admin,`/admin/buyers/${accounts.buyer.id}/details`)).basic.status,'active');
  check('Product deletion retains winning history and account deletion requires confirmation');
  assert.deepEqual(errors,[]);check('No admin browser JavaScript errors');
  fs.writeFileSync('ADMIN_E2E_RESULTS.md','# Admin panel verification\n\n'+checks.map(label=>'- PASS: '+label).join('\n')+'\n\nUsed the real database and temporary products/categories/accounts. Fixture records are removed after testing.\n');
}catch(error){console.error(error.stack);await page.screenshot({path:'web/tests/artifacts/admin-failure.png',fullPage:true}).catch(()=>{});process.exitCode=1;}finally{await browser.close();}
