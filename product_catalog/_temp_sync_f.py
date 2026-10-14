import csv, json, os, re
from collections import Counter
from urllib.parse import urlparse
from openpyxl import load_workbook

ROOT=os.path.dirname(__file__); TODAY='2026-10-13'
F='F-kitchen-appliances.csv'; PLAN='category_plan.csv'; SUMMARY='master_summary.csv'; LOG='collection_log.csv'; ALL='all_products.csv'; BOOK='master_catalogue.xlsx'
fields=list(next(csv.DictReader(open(os.path.join(ROOT,F),encoding='utf-8-sig'))).keys())
def read(name):
    with open(os.path.join(ROOT,name),encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write(name,rows,cols=None):
    with open(os.path.join(ROOT,name),'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols or (list(rows[0]) if rows else []),extrasaction='ignore');w.writeheader();w.writerows(rows)

rows=read(F)
# First use official images captured by Firecrawl; require model context and a real image URL.
md=[]
for root,_,files in os.walk(os.path.join(ROOT,'.firecrawl')):
    for fn in files:
        if fn.endswith('.md'):
            try: md.append(open(os.path.join(root,fn),encoding='utf-8').read())
            except Exception: pass
for r in rows:
    model=r['model'].replace('/','_')
    if not r['image_url'] or 'placeholder' in r['image_url'].lower():
        for s in md:
            ix=s.lower().find(model.lower())
            if ix<0: ix=s.lower().find(r['model'].lower())
            if ix<0: continue
            chunk=s[max(0,ix-1400):ix+1400]
            urls=re.findall(r'!\[[^]]*\]\((https?://[^)]+)\)',chunk)
            urls=[u for u in urls if not any(t in u.lower() for t in ('logo','icon','placeholder','flag','youtube','facebook','.svg'))]
            good=[u for u in urls if r['model'].replace('/','').lower() in u.lower().replace('/','')]
            if good or urls:
                r['image_url']=(good or urls)[0]; break
    if not r['image_url'] or 'placeholder' in r['image_url'].lower():
        r['image_url']=''
    missing=[]
    if not r['release_year']: missing.append('release year not stated; age requires verification')
    if not r['official_price']: missing.append('official price not captured')
    if not r['image_url']: missing.append('official product image URL not captured')
    if not r['description'] or r['description'].strip()==r['product_name'].strip(): missing.append('full product description/specifications require review')
    if missing:
        r['notes']=(r['notes'].rstrip(' .;')+'; ' if r['notes'] else '')+'Missing/unverified fields: '+', '.join(missing)+'.'
    # The model page is the product source; category pages are retained as price source where applicable.
write(F,rows,fields)

allrows=[]
for file in ['A-mobile-phones-tablets.csv','B-computers-laptops-it-equipment.csv','C-tvs-video-home-entertainment.csv','D-audio-headphones-speakers.csv','E-large-home-appliances.csv',F]: allrows += read(file)
write(ALL,allrows,fields)

plan=read(PLAN)
for p in plan:
    if p['department_code']=='F': p['status']='COMPLETE'
    elif p['department_code']=='G': p['status']='IN_PROGRESS' if p['product_types'].startswith('ALL') else 'IN_PROGRESS'
write(PLAN,plan)

summary=read(SUMMARY)
for sr in summary:
    if sr['category_code']=='G': sr['processing_status']='IN_PROGRESS'
summary=[r for r in summary if r['category_code']!='F']
counts=Counter(r['subcategory'] for r in rows)
summary.append(dict(category_code='F',department='Kitchen Appliances',subcategory='ALL',products_count=str(len(rows)),processing_status='COMPLETE',csv_file=F))
for sub,n in sorted(counts.items()): summary.append(dict(category_code='F',department='Kitchen Appliances',subcategory=sub,products_count=str(n),processing_status='COMPLETE',csv_file=F))
write(SUMMARY,summary)

domains=Counter(re.sub(r'^www\.','',urlparse(r['product_source_url']).hostname or '') for r in rows)
log=[r for r in read(LOG) if r['category_code']!='F']
log.append({'category_code':'F','product_type':'ALL','status':'COMPLETE','product_count':str(len(rows)),'brand_count':str(len(set(r['brand'] for r in rows))),'source_domain':'|'.join(sorted(domains)),'rows_attributed_to_domain':json.dumps(dict(sorted(domains.items())),separators=(',',':')),'last_updated':TODAY,'notes':f'All 8 supplied subtypes represented; subtype counts {dict(sorted(counts.items()))}. Release year missing {sum(not r["release_year"] for r in rows)}; official price missing {sum(not r["official_price"] for r in rows)}; image URL missing {sum(not r["image_url"] for r in rows)}. Missing values left blank and flagged in each row.'})
for sub,n in sorted(counts.items()): log.append({'category_code':'F','product_type':sub,'status':'COMPLETE','product_count':str(n),'brand_count':str(len(set(r['brand'] for r in rows if r['subcategory']==sub))),'source_domain':'','rows_attributed_to_domain':'','last_updated':TODAY,'notes':'Official manufacturer product pages or catalogues recorded in each product row.'})
log=[r for r in log if not (r['category_code']=='G' and r['product_type']=='ALL')]
log.append({'category_code':'G','product_type':'ALL','status':'IN_PROGRESS','product_count':'0','brand_count':'0','source_domain':'','rows_attributed_to_domain':'','last_updated':TODAY,'notes':'Current category; begin subtype-by-subtype collection only after F is complete.'})
write(LOG,log)

wb=load_workbook(os.path.join(ROOT,BOOK))
for name in ['F','F - Stats','Category Summary']:
    if name not in wb.sheetnames: wb.create_sheet(name)
ws=wb['F']; ws.delete_rows(1,ws.max_row); ws.append(fields)
for r in rows: ws.append([r.get(k,'') for k in fields])
stats=wb['F - Stats']; stats.delete_rows(1,stats.max_row); stats.append(['F Product Statistics',None]);stats.append(['Metric','Count'])
for key,val in [('Total products',len(rows)),('Distinct brands',len(set(r['brand'] for r in rows))),('Verified release year',sum(bool(r['release_year']) for r in rows)),('Official price listed',sum(bool(r['official_price']) for r in rows)),('Image URL present',sum(bool(r['image_url']) for r in rows)),('Release year unknown',sum(not r['release_year'] for r in rows)),('Price unavailable',sum(not r['official_price'] for r in rows)),('Image URL missing',sum(not r['image_url'] for r in rows))]: stats.append([key,val])
stats.append([None,None]);stats.append(['Subtype','Products'])
for sub,n in sorted(counts.items()): stats.append([sub,n])
cs=wb['Category Summary'];cs.delete_rows(1,cs.max_row);cs.append(['Category','Department','Subtype','Products','Status','CSV file'])
for r in sorted(summary,key=lambda x:(x['category_code'],x['subcategory'])): cs.append([r['category_code'],r['department'],r['subcategory'],int(r['products_count']),r['processing_status'],r['csv_file']])
wb.save(os.path.join(ROOT,BOOK))
keys=[(r['brand'].lower(),r['model'].lower()) for r in rows]
print('F validation:',len(rows),'products;',len(set(r['brand'] for r in rows)),'brands;',len(counts),'subtypes; duplicates',len(keys)-len(set(keys)))
print('F gaps: year',sum(not r['release_year'] for r in rows),'price',sum(not r['official_price'] for r in rows),'image',sum(not r['image_url'] for r in rows),'blank source URL',sum(not r['product_source_url'] for r in rows))
print('All products:',len(allrows),'rows; G is now the only active category.')
