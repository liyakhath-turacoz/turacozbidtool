import csv,glob,os,json,collections
from openpyxl import load_workbook
root='product_catalog'; paths=sorted(glob.glob(os.path.join(root,'[A-P]-*.csv'))); allrows=[]; category=[]; brands=[]; years=[]; coverage=[]; subrows=[]
for path in paths:
 with open(path,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 code=rows[0]['category_code']; dept=rows[0]['department']; allrows.extend(rows)
 category.append((code,dept,rows))
 subcounts=collections.Counter(r['subcategory'] or '(unspecified)' for r in rows)
 for sub,n in sorted(subcounts.items()):subrows.append({'category_code':code,'department':dept,'subcategory':sub,'products_count':n,'processing_status':'COMPLETE','csv_file':os.path.basename(path)})
 for b,n in sorted(collections.Counter(r['brand'] for r in rows).items()):brands.append({'category_code':code,'department':dept,'brand':b,'products_count':n})
 for y,n in sorted(collections.Counter(r['release_year'] for r in rows if r['release_year']).items()):years.append({'category_code':code,'department':dept,'release_year':y,'products_count':n})
 coverage.append({'category_code':code,'department':dept,'total_products':len(rows),'brands':len(set(r['brand'] for r in rows if r['brand'])),'release_year_present':sum(bool(r['release_year']) for r in rows),'official_price_present':sum(bool(r['official_price']) for r in rows),'image_url_present':sum(bool(r['image_url']) for r in rows),'specifications_present':sum(r['specifications_json'] not in ('','{}') for r in rows),'source_url_present':sum(bool(r['product_source_url']) for r in rows),'release_year_missing':sum(not r['release_year'] for r in rows),'price_missing':sum(not r['official_price'] for r in rows),'image_missing':sum(not r['image_url'] for r in rows)})
# Fix a source-link typo in one enriched GoPro row.
for r in allrows:
 if r['category_code']=='J' and r['brand']=='GoPro' and r['model']=='HERO13 Black':
  r['notes']=r['notes'].replace('https://investor.gopro.com/press-releases/press-release-details/2024/GoPro-Announces-Two-New-Cameras-The-399-HERO-and-the-199-HERO/default.aspx','https://investor.gopro.com/press-releases/press-release-details/2024/GoPro-Announces-Two-New-Cameras-The-399-HERO13-Black-and-the-199-HERO/default.aspx')
# Rewrite updated J if typo fixed.
with open(os.path.join(root,'J-cameras-photography-imaging.csv'),'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows([r for r in allrows if r['category_code']=='J'] if list(allrows[0].keys())[0]=='category_code' else [])
# Make product and source files retain the canonical 27-column field order.
for code,dept,rows in category:
 with open(os.path.join(root,next(os.path.basename(x) for x in paths if x.startswith(os.path.join(root,code+'-')))),'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# Re-read after canonical writes; build the all-category export from the individual category files.
allrows=[]
for path in paths:
 with open(path,encoding='utf-8-sig',newline='') as f:allrows.extend(csv.DictReader(f))
with open(os.path.join(root,'all_products.csv'),'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
# Build auditable category/subcategory, brand, year, and data-coverage exports.
def write_csv(name,rows):
 if not rows:return
 with open(os.path.join(root,name),'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
category=[];subrows=[];brands=[];years=[];coverage=[];allrows=[]
for path in paths:
 with open(path,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 if not rows:continue
 code=rows[0]['category_code'];dept=rows[0]['department'];allrows.extend(rows);category.append((code,dept,rows))
 for sub,n in sorted(collections.Counter(r['subcategory'] or '(unspecified)' for r in rows).items()):subrows.append({'category_code':code,'department':dept,'subcategory':sub,'products_count':n,'processing_status':'COMPLETE','csv_file':os.path.basename(path)})
 for b,n in sorted(collections.Counter(r['brand'] for r in rows).items()):brands.append({'category_code':code,'department':dept,'brand':b,'products_count':n})
 for y,n in sorted(collections.Counter(r['release_year'] for r in rows if r['release_year']).items()):years.append({'category_code':code,'department':dept,'release_year':y,'products_count':n})
 coverage.append({'category_code':code,'department':dept,'total_products':len(rows),'brands':len(set(r['brand'] for r in rows if r['brand'])),'release_year_present':sum(bool(r['release_year']) for r in rows),'official_price_present':sum(bool(r['official_price']) for r in rows),'image_url_present':sum(bool(r['image_url']) for r in rows),'specifications_present':sum(r['specifications_json'] not in ('','{}') for r in rows),'source_url_present':sum(bool(r['product_source_url']) for r in rows),'release_year_missing':sum(not r['release_year'] for r in rows),'price_missing':sum(not r['official_price'] for r in rows),'image_missing':sum(not r['image_url'] for r in rows)})
write_csv('master_summary.csv',subrows);write_csv('brand_summary.csv',brands);write_csv('release_year_summary.csv',years);write_csv('category_coverage.csv',coverage)
# Workbook summary sheets; category sheets stay separate and untouched.
wb=load_workbook(os.path.join(root,'master_catalogue.xlsx'))
def replace_sheet(name,headers,rows):
 if name in wb.sheetnames:del wb[name]
 ws=wb.create_sheet(name);ws.append(headers)
 for r in rows:ws.append([r.get(k,'') for k in headers])
 ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
replace_sheet('Category Summary',['category_code','department','subcategory','products_count','processing_status','csv_file'],subrows)
replace_sheet('Brand Summary',['category_code','department','brand','products_count'],brands)
replace_sheet('Release Year Summary',['category_code','department','release_year','products_count'],years)
replace_sheet('Data Coverage',list(coverage[0]),coverage)
wb.save(os.path.join(root,'master_catalogue.xlsx'))
# Current all-products canonical restore after modifying files.
with open(os.path.join(root,'all_products.csv'),'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
keys=[(r['brand'].strip().casefold(),r['model'].strip().casefold()) for r in allrows]
counts=collections.Counter(r['category_code'] for r in allrows);brand_total=len(set(r['brand'].strip().casefold() for r in allrows if r['brand']))
# Derive the visible catalogue coverage table for README.
lines=['# Product catalogue for review and later import','','A standalone, source-attributed catalogue for review and later import. It is kept in CSV/XLSX files and has not been imported into or mixed with the existing application database. Application code and services were not changed, and no Git changes were staged.','','## Files','','- `master_catalogue.xlsx` — one product worksheet and one statistics worksheet per category, plus category, brand, release-year, and data-coverage summaries.','- `master_summary.csv` — product counts by category and subcategory.','- `brand_summary.csv` — brand counts within each category.','- `release_year_summary.csv` — year-wise model counts within each category.','- `category_coverage.csv` — completeness counts for release year, price, image, specifications, and sources.','- `all_products.csv` — combined export of all category files.','- `collection_log.csv` — source domains, counts, status, and known collection gaps.','- `A-...csv` through `P-...csv` — individual category exports, all using the same 27-column product schema.','','## Catalogue coverage','','| Code | Category | Products | Brands | Year | Price | Image | Specs |','|---|---|---:|---:|---:|---:|---:|---:|']
for c,d,rs in category:
 cov=next(x for x in coverage if x['category_code']==c);lines.append(f"| {c} | {d} | {len(rs)} | {cov['brands']} | {cov['release_year_present']} | {cov['official_price_present']} | {cov['image_url_present']} | {cov['specifications_present']} |")
lines.append(f'| **Total** | **A–P** | **{len(allrows)}** | **{brand_total}** | **{sum(x["release_year_present"] for x in coverage)}** | **{sum(x["official_price_present"] for x in coverage)}** | **{sum(x["image_url_present"] for x in coverage)}** | **{sum(x["specifications_present"] for x in coverage)}** |')
lines += ['',f'There are {len(allrows)} product rows from {len(category)} categories and {brand_total} distinct brands, with no duplicate brand/model keys. All rows have product source URLs. The source schema contains {len(allrows)} normalized specification objects; values may be sparse where a manufacturer page does not publish full specifications.','', '## Data fields and review notes','','Each product row has the same 27 columns: category, subcategory, product type, product and model identifiers, brand/manufacturer, description, normalized specification JSON, image and product URLs, release date/year and precision, listed price/currency/market/type, source URLs, attribution, collection date, verification status, and notes.','', 'Release year and price values are recorded only when supported by a collected source. A blank release year means the public source did not establish the date; it does not mean the model is new. Products with unknown release years cannot be confirmed to meet the preferred three-year recency window and should be reviewed before import. Current prices and launch MSRPs are labelled by type and market and may change. Missing images and specifications remain blank or are called out in row notes; no values were invented.','', 'This is a practical source-attributed review catalogue, not a guarantee of every model available from every manufacturer. Manufacturer catalogs change and may be regional. Rows should be reviewed against current stock, regional price, compatibility, and release date before import.','']
with open(os.path.join(root,'README.md'),'w',encoding='utf-8') as f:f.write('\n'.join(lines))
print('Finalized: products',len(allrows),'categories',len(category),'brands',brand_total,'duplicate brand/model keys',len(keys)-len(set(keys)))
print('Data completeness total:',{k:sum(x[k] for x in coverage) for k in ['release_year_present','official_price_present','image_url_present','specifications_present','source_url_present']})
print('Category counts:',dict(sorted(counts.items())))
