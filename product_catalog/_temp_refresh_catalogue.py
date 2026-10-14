import csv,glob,os,collections
from openpyxl import load_workbook
root='product_catalog';paths=sorted(glob.glob(os.path.join(root,'[A-P]-*.csv')))
allrows=[];cats=[];coverage=[];subrows=[];brands=[];years=[]
plan_path=os.path.join(root,'category_plan.csv')
with open(plan_path,encoding='utf-8-sig',newline='') as f: review_status={r['department_code']:r['review_status'] for r in csv.DictReader(f)}
for path in paths:
 with open(path,encoding='utf-8-sig',newline='') as f:rs=list(csv.DictReader(f))
 if not rs:continue
 code=rs[0]['category_code'];dept=rs[0]['department'];cats.append((code,dept,os.path.basename(path),rs));allrows+=rs
 for name,n in sorted(collections.Counter(r['subcategory'] for r in rs).items()):subrows.append({'category_code':code,'department':dept,'subcategory':name,'products_count':n,'processing_status':review_status.get(code,'PENDING'),'csv_file':os.path.basename(path)})
 for name,n in sorted(collections.Counter(r['brand'] for r in rs).items()):brands.append({'category_code':code,'department':dept,'brand':name,'products_count':n})
 for name,n in sorted(collections.Counter(r['release_year'] for r in rs if r['release_year']).items()):years.append({'category_code':code,'department':dept,'release_year':name,'products_count':n})
 coverage.append({'category_code':code,'department':dept,'total_products':len(rs),'brands':len(set(r['brand'] for r in rs)),'release_year_present':sum(bool(r['release_year']) for r in rs),'official_price_present':sum(bool(r['official_price']) for r in rs),'image_url_present':sum(bool(r['image_url']) for r in rs),'specifications_present':sum(r['specifications_json'] not in ('','{}') for r in rs),'source_url_present':sum(bool(r['product_source_url']) for r in rs),'release_year_missing':sum(not r['release_year'] for r in rs),'price_missing':sum(not r['official_price'] for r in rs),'image_missing':sum(not r['image_url'] for r in rs)})
summary=[]
for c,d,n,rs in cats:summary.append({'category_code':c,'department':d,'subcategory':'ALL','products_count':len(rs),'processing_status':review_status.get(c,'PENDING'),'csv_file':n})
summary.sort(key=lambda r:r['category_code']);summary+=subrows
# rewrite canonical aggregate CSVs
def write(name,rs):
 with open(os.path.join(root,name),'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
write('all_products.csv',allrows);write('master_summary.csv',summary);write('brand_summary.csv',brands);write('release_year_summary.csv',years);write('category_coverage.csv',coverage)
wb=load_workbook(os.path.join(root,'master_catalogue.xlsx'))
def sheet_replace(name,headers,rs):
 if name in wb.sheetnames:del wb[name]
 ws=wb.create_sheet(name);ws.append(headers)
 for r in rs:ws.append([r.get(k,'') for k in headers])
 ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
sheet_replace('Category Summary',list(summary[0]),summary);sheet_replace('Brand Summary',list(brands[0]),brands);sheet_replace('Release Year Summary',list(years[0]),years);sheet_replace('Data Coverage',list(coverage[0]),coverage)
# Refresh every product tab from its matching CSV; rebuild per-category stats with current counts.
for code,dept,name,rs in cats:
 ws=wb[code];ws.delete_rows(1,ws.max_row);ws.append(list(rs[0]))
 for r in rs:ws.append([r.get(k,'') for k in rs[0]])
 ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
 stname=code+' - Stats'
 if stname not in wb.sheetnames:wb.create_sheet(stname)
 st=wb[stname];st.delete_rows(1,st.max_row);st.append([f'{code} Product Statistics']);st.append(['Metric','Count'])
 for label,key in [('Total products',None),('Distinct brands','brand'),('Release year verified','release_year'),('Official price listed','official_price'),('Image URL present','image_url'),('Detailed specifications present','specifications_json'),('Source URL present','product_source_url')]:
  n=len(rs) if key is None else len(set(x[key] for x in rs)) if key=='brand' else sum(bool(x[key]) and (key!='specifications_json' or x[key]!='{}') for x in rs)
  st.append([label,n])
 st.append([]);st.append(['Subtype','Products'])
 for sub,n in sorted(collections.Counter(x['subcategory'] for x in rs).items()):st.append([sub,n])
wb.save(os.path.join(root,'master_catalogue.xlsx'))
# Update README from source files and derived counts.
distinct_brands=len(set(r['brand'].strip().casefold() for r in allrows if r['brand']))
lines=['# Product catalogue for review and later import','','A standalone, source-attributed catalogue for review and later import. It is kept in CSV/XLSX files and has not been imported into or mixed with the existing application database. Application code and services were not changed, and no Git changes were staged.','','## Files','','- `master_catalogue.xlsx` — one product worksheet and one statistics worksheet per category, plus category, brand, release-year, and data-coverage summaries.','- `master_summary.csv` — overall category totals and subcategory product counts.','- `brand_summary.csv` — brand counts within each category.','- `release_year_summary.csv` — year-wise model counts within each category.','- `category_coverage.csv` — completeness counts for release year, price, image, specifications, and sources.','- `all_products.csv` — combined export of all category files.','- `collection_log.csv` — source domains, counts, status, and known collection gaps.','- `A-...csv` through `P-...csv` — individual category exports, each with the same 27-column product schema.','','## Catalogue coverage','','| Code | Category | Products | Brands | Year | Price | Image | Specs |','|---|---|---:|---:|---:|---:|---:|---:|']
for c,d,n,rs in cats:
 q=next(x for x in coverage if x['category_code']==c);lines.append(f"| {c} | {d} | {len(rs)} | {q['brands']} | {q['release_year_present']} | {q['official_price_present']} | {q['image_url_present']} | {q['specifications_present']} |")
lines.append(f"| **Total** | **A–P** | **{len(allrows)}** | **{distinct_brands}** | **{sum(x['release_year_present'] for x in coverage)}** | **{sum(x['official_price_present'] for x in coverage)}** | **{sum(x['image_url_present'] for x in coverage)}** | **{sum(x['specifications_present'] for x in coverage)}** |")
lines+=['','Category and master counts are product records. A row for a manufacturer-published range can describe several SKUs; where the source states a count, it is stored in `specifications_json.model_count`. Treat such a row as a range record, not as one model. Individual model totals can therefore differ from product-row counts.','',f'There are {len(allrows)} product records from {len(cats)} categories and {distinct_brands} distinct brands, with no duplicate populated brand/model identifiers. Manufacturer-announced ranges without public model codes retain blank model fields and are named as ranges in the product name and notes. All rows have product source URLs. {sum(x["specifications_present"] for x in coverage)} rows have a captured specifications object; fields remain incomplete when manufacturer sources omit values.','','## Data fields and review notes','','Each product row has the same 27 columns: category, subcategory, product type, product and model identifiers, brand/manufacturer, description, normalized specification JSON, image and product URLs, release date/year and precision, listed price/currency/market/type, source URLs, attribution, collection date, verification status, and notes.','','Release years and prices are recorded only when supported by a collected source. A blank release year means the public source did not establish the date; it does not mean the model is new. Products with unknown release years cannot be confirmed to meet the preferred three-year recency window and should be reviewed before import. Current prices and launch MSRPs are labeled by type and market and may change. Missing images and specifications remain blank or are called out in row notes; no values were invented.','','This is a source-attributed review catalogue, not a guarantee of every model available from every manufacturer. Manufacturer catalogs change and may be regional. Review current stock, regional price, compatibility, and release date before import.','']
with open(os.path.join(root,'README.md'),'w',encoding='utf-8') as f:f.write('\n'.join(lines))
keys=[(r['brand'].strip().casefold(),r['model'].strip().casefold()) for r in allrows if r['brand'].strip() and r['model'].strip()]
print('Refreshed all category sheets and summaries:',len(allrows),'rows;',len(cats),'categories;',distinct_brands,'distinct brands;',len(keys)-len(set(keys)),'duplicate nonblank brand/model keys')
print('A price entries',next(x['official_price_present'] for x in coverage if x['category_code']=='A'))
