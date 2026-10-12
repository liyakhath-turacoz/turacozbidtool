import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chromium} from 'playwright';

// Read-only catalog checks against an existing buyer account. No fixture products or bids.
const apiUrl=process.env.E2E_API_URL || 'http://localhost:8000';
const webUrl=process.env.E2E_WEB_URL || 'http://localhost:5173';
const browser=await chromium.launch({channel:process.env.E2E_BROWSER || 'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1100}});
const page=await context.newPage();
const errors=[];
page.on('pageerror',error=>errors.push(error.message));
const check=label=>console.log('PASS:',label);
const wait=async(checkState)=>{
  const deadline=Date.now()+20000;let last;
  do {try {await checkState();return;}catch(error){last=error;}await new Promise(resolve=>setTimeout(resolve,100));}while(Date.now()<deadline);
  throw last;
};
try {
  const unknown=await fetch(apiUrl+'/catalog/unknown-catalog-route',{headers:{Accept:'application/json'}});
  assert.equal(unknown.status,404);assert.match(unknown.headers.get('content-type'),/application\/json/);
  assert.equal(typeof (await unknown.json()).detail,'string');
  check('Unknown catalog API routes return JSON 404 instead of the website');
  await page.goto(webUrl,{waitUntil:'domcontentloaded'});
  await page.getByLabel('Username',{exact:true}).fill(process.env.E2E_BUYER || 'buyer1');
  await page.getByLabel('Password',{exact:true}).fill(process.env.E2E_BUYER_PASSWORD || 'buyer1');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.locator('.product-card').first().waitFor();
  assert.deepEqual((await page.locator('.filter-panel .catalog-facet summary').allTextContents()).map(label=>label.replace(/\s+\(\d+\)$/,'')),['Categories','Product type','Brand / manufacturer','Release year']);
  assert.equal(await page.locator('.filter-panel input[type="number"]').count(),0);
  check('Catalog filters contain only category, item type, manufacturer and release year');
  const filter=page.locator('.filter-panel');
  const option=name=>filter.getByRole('checkbox',{name:new RegExp('^'+name+'(?:\\s|$)')});
  const choose=async(name,checked)=>{
    const response=page.waitForResponse(r=>r.url().includes('/catalog/search?') && r.request().method()==='GET');
    await option(name).setChecked(checked);
    const result=await (await response).json();
    await wait(async()=>assert.match(await page.locator('.catalog-summary').innerText(),new RegExp(result.total.toLocaleString('en-US')+' matching products')));
    await wait(async()=>assert.equal(await page.locator('.product-card').count(),result.items.length));
    return result;
  };
  await choose('Electronics',true);
  await filter.getByLabel('Search product type filters').fill('Smartphones');
  await choose('Smartphones',true);
  assert(await option('Home Appliances').isVisible());
  assert(await option('Tablets').isVisible());
  await filter.getByLabel('Search product type filters').fill('Smart');
  check('Other parent categories and sibling product types remain available after filtering');
  await choose('Home Appliances',true);
  let result=await choose('Electronics',false);
  assert(result.total>0);assert(result.items.every(item=>item.category==='Home Appliances'));
  assert.equal(await option('Smartphones').count(),0);
  check(`Switching categories clears old item filters and shows ${result.total} household products`);
  result=await choose('Refrigerators',true);
  assert(result.total>0);assert(result.items.every(item=>item.item==='Refrigerators'));
  assert(await option('Ovens').isVisible());
  check(`Buyer can browse ${result.total} refrigerators`);
  await choose('Refrigerators',false);
  result=await choose('Ovens',true);
  assert(result.total>0);assert(result.items.every(item=>item.item==='Ovens'));
  assert(await option('Refrigerators').isVisible());
  check(`Buyer can browse ${result.total} ovens`);
  await choose('Ovens',false);
  for (const item of ['Air conditioners','Microwave ovens','Washing machines','Dishwashers','Freezers']) {
    result=await choose(item,true);
    assert(result.total>0);assert(result.items.every(product=>product.item===item));
    check(`${item}: ${result.total} visible products`);
    await choose(item,false);
  }
  let injectHtml=true;
  const htmlRoute=async route=>{
    if(injectHtml){injectHtml=false;await route.fulfill({status:200,contentType:'text/html',body:'<!doctype html><html><body>Website fallback</body></html>'});}
    else await route.continue();
  };
  await context.route('**/catalog/search?*',htmlRoute);
  await page.getByRole('button',{name:'Search',exact:true}).click();
  await page.getByRole('button',{name:'Retry loading products'}).waitFor();
  assert.match(await page.getByRole('alert').innerText(),/webpage instead of API data/);
  assert.equal(await page.locator('.product-card').count(),0);
  await context.unroute('**/catalog/search?*',htmlRoute);
  await page.getByRole('button',{name:'Retry loading products'}).click();
  await page.locator('.product-card').first().waitFor();
  await wait(async()=>assert.equal(await page.getByRole('alert').count(),0));
  check('Repeated Search requests refresh data; HTML errors show a useful message and Retry restores the catalog');
  await page.getByRole('button',{name:'Reset',exact:true}).click();
  await wait(async()=>assert.equal(await page.locator('.product-card').count(),50));
  await page.getByRole('button',{name:'Load more products',exact:true}).click();
  await wait(async()=>assert.equal(await page.locator('.product-card').count(),100));
  assert.equal(await page.locator('.filter-panel .catalog-facet summary').count(),4);
  check('Load more shows subsequent products and preserves the four filter groups');
  const overflowingImages=await page.locator('.product-art img').evaluateAll(images=>images.filter(img=>{
    const image=img.getBoundingClientRect(),box=img.parentElement.getBoundingClientRect();
    return image.height>box.height+1 || image.width>box.width+1;
  }).length);
  assert.equal(overflowingImages,0);check('Product images stay within their card image area');
  assert.deepEqual(errors,[]);
  fs.mkdirSync('web/tests/artifacts',{recursive:true});
  await page.screenshot({path:`web/tests/artifacts/catalog-${new URL(webUrl).port || 'default'}.png`,fullPage:false});
  check('No browser JavaScript errors');
} finally {await browser.close();}
