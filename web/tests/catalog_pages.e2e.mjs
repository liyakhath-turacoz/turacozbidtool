import assert from 'node:assert/strict';

// Validate every catalog page without rendering thousands of cards at once.
const base=process.env.E2E_API_URL || 'http://localhost:8000';
const login=await fetch(base+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:process.env.E2E_BUYER || 'buyer1',password:process.env.E2E_BUYER_PASSWORD || 'buyer1'})});
assert.equal(login.status,200);const session=await login.json();
const headers={Accept:'application/json',Authorization:`Bearer ${session.access_token}`};
const read=async path=>{const response=await fetch(base+path,{headers});assert.equal(response.status,200);return response.json();};
const first=await read('/catalog/search?limit=250&include_facets=false');
const ids=new Set();let pages=0;
for(let offset=0;offset<first.total;offset+=250){
  const result=offset===0?first:await read(`/catalog/search?limit=250&offset=${offset}&include_facets=false`);
  assert.equal(result.total,first.total,'Catalog changed during the check; retry after imports finish.');
  assert.equal(result.items.length,Math.min(250,first.total-offset));
  for(const item of result.items){assert(!ids.has(item.id),'Duplicate product across pages');assert.equal(item.status,'active');ids.add(item.id);}
  pages++;
}
assert.equal(ids.size,first.total);
const facets=await read('/catalog/search?limit=1');
assert.deepEqual(Object.keys(facets.facets).sort(),['brands','categories','product_types','years']);
assert.equal(facets.facets.categories.reduce((sum,row)=>sum+row.count,0),first.total);
assert.equal(facets.facets.product_types.reduce((sum,row)=>sum+row.count,0),first.total);
console.log(`PASS: ${ids.size.toLocaleString('en-US')} available products across ${pages} complete pages, with no missing or duplicate IDs`);
console.log('PASS: Category and product-type totals match the complete available catalog; only four facet groups are returned');
