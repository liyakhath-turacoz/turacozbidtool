import csv, json, os, re, time
from collections import Counter
from datetime import date
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from openpyxl import load_workbook

ROOT=os.path.dirname(__file__)
EFILE=os.path.join(ROOT,'E-large-home-appliances.csv')
FIELDS=None
today=date(2026,10,13).isoformat()

def read(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))
def write(path,rows,fields=None):
    if fields is None: fields=list(rows[0]) if rows else []
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

rows=read(EFILE)
session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'})
cache={}
for r in rows:
    u=r['product_url']; image=''
    if u not in cache:
        try:
            resp=session.get(u,timeout=15)
            soup=BeautifulSoup(resp.text,'html.parser') if resp.ok else None
            if soup:
                for meta in soup.find_all('meta'):
                    prop=(meta.get('property') or meta.get('name') or '').lower()
                    content=(meta.get('content') or '').strip()
                    if prop=='og:image' and content and not any(x in content.lower() for x in ('logo','placeholder','default')):
                        image=urljoin(u,content)
                        break
            if soup and (not image or 'logo' in image.lower()):
                model=(r['model'] or '').lower().replace(' ','')
                # Samsung storefront pages expose real product gallery assets in embedded markup,
                # while their OpenGraph image is only the Samsung logo.
                matches=re.findall(r'(?:https?:)?//images\.samsung\.com/is/image/samsung/[^"\'<>\s]*',resp.text,re.I)
                for candidate in matches:
                    candidate=candidate.replace('\\/','/').replace('&amp;','&')
                    if model and model in candidate.lower() and 'gallery' in candidate.lower():
                        image=candidate if candidate.startswith('http') else 'https:'+candidate
                        break
            cache[u]=image
        except Exception:
            cache[u]=''
    image=cache[u]
    # Manufacturer image URLs found by opening the model gallery where server-side requests are blocked.
    manual={
      'HRF-5251BGK-N':'https://image.haier.com/in/refrigerators/W020251114528387345346_60.jpg',
      'HW120-DM14F9BKU1':'https://image.haier.com/in/washing-machines/W020250530564127162547_60.png',
      'GL-B257EPT3':'https://www.lg.com/content/dam/channel/wcms/in/images/refrigerators/gl-b257ept3/GL-B257EPT3-450x450-1-v.jpg',
      'SHX78CM5N':'https://media3.bsh-group.com/Product_Shots/27999487_Bosch_SHX78CM5N_CR_Badge_Front_def.webp'
    }
    if not image: image=manual.get(r['model'],'')
    r['image_url']=image
    if not image and 'image URL' not in r['notes']:
        r['notes']=(r['notes'].rstrip()+' ' if r['notes'] else '')+'Official image URL was not captured; use the manufacturer product gallery before import.'
    if not r['description']:
        r['description']=f"{r['brand']} {r['product_type']} model {r['model']}; see listed specifications and manufacturer source."
    if not r['release_year'] and 'release date' not in r['notes'].lower() and 'release year' not in r['notes'].lower():
        r['notes']=(r['notes'].rstrip()+' ' if r['notes'] else '')+'Manufacturer release date/year was not verified.'
    if not r['price_source_url'] and r['official_price']:
        r['price_source_url']=r['product_url']
    # Source for the announced MSRP differs from the live product page/MOP.
    if r['model']=='HW120-DM14F9BKU1' and r['price_type']=='launch_msrp':
        r['price_source_url']='https://www.haier.com/in/about-haier/news/haier-launches-f9-series-indias-only-ai-color-panel-with-onetouch-washing-machine.shtml'

write(EFILE,rows)
fields=list(rows[0])

# Rebuild combined export from populated category CSVs; all category source files remain independent.
all_rows=[]
for code,filename in [('A','A-mobile-phones-tablets.csv'),('B','B-computers-laptops-it-equipment.csv'),('C','C-tvs-video-home-entertainment.csv'),('D','D-audio-headphones-speakers.csv'),('E','E-large-home-appliances.csv')]:
    all_rows.extend(read(os.path.join(ROOT,filename)))
write(os.path.join(ROOT,'all_products.csv'),all_rows,fields)

plan=read(os.path.join(ROOT,'category_plan.csv'))
for p in plan:
    if p['department_code']=='E': p['status']='COMPLETE' if p['product_types']=='ALL' else 'COMPLETE'
    elif p['department_code']=='F': p['status']='IN_PROGRESS' if p['product_types']=='ALL' else 'QUEUED'
write(os.path.join(ROOT,'category_plan.csv'),plan)

summary=read(os.path.join(ROOT,'master_summary.csv'))
summary=[r for r in summary if r['category_code']!='E']
dept='Large Home Appliances'; fname='E-large-home-appliances.csv'
summary.append(dict(category_code='E',department=dept,subcategory='ALL',products_count=str(len(rows)),processing_status='COMPLETE',csv_file=fname))
for sub,n in sorted(Counter(r['subcategory'] for r in rows).items()):
    summary.append(dict(category_code='E',department=dept,subcategory=sub,products_count=str(n),processing_status='COMPLETE',csv_file=fname))
write(os.path.join(ROOT,'master_summary.csv'),summary)

# Update the resumable category collection log, with source hosts and explicit data gaps.
log=read(os.path.join(ROOT,'collection_log.csv'))
log=[r for r in log if r['category_code']!='E']
domains=Counter(re.sub(r'^www\.','',__import__('urllib.parse').parse.urlparse(r['product_source_url']).hostname or '') for r in rows)
e_counts=Counter(r['subcategory'] for r in rows)
gap_year=sum(not r['release_year'] for r in rows);gap_price=sum(not r['official_price'] for r in rows);gap_img=sum(not r['image_url'] for r in rows)
log.append({'category_code':'E','product_type':'ALL','status':'COMPLETE','product_count':str(len(rows)),'brand_count':str(len(set(r['brand'] for r in rows))),'source_domain':'|'.join(sorted(domains)),'rows_attributed_to_domain':json.dumps(dict(sorted(domains.items())),separators=(',',':')),'last_updated':today,'notes':f"All 9 supplied subtypes represented; subtype counts {dict(sorted(e_counts.items()))}. Release year missing {gap_year}; official price missing {gap_price}; image URL missing {gap_img}. Manufacturer dates/prices/images left blank and noted where unavailable."})
for sub,n in sorted(e_counts.items()):
    log.append({'category_code':'E','product_type':sub,'status':'COMPLETE','product_count':str(n),'brand_count':str(len(set(r['brand'] for r in rows if r['subcategory']==sub))),'source_domain':'','rows_attributed_to_domain':'','last_updated':today,'notes':'Subtype coverage recorded from official manufacturer product pages/listings.'})
write(os.path.join(ROOT,'collection_log.csv'),log)

# Rebuild workbook sheets without changing project/database files.
book=os.path.join(ROOT,'master_catalogue.xlsx')
wb=load_workbook(book)
for i,name in enumerate(['Category Summary','A','B','C','D','E','E - Stats']):
    if name not in wb.sheetnames: wb.create_sheet(name)
sheet=wb['E']; sheet.delete_rows(1,sheet.max_row)
sheet.append(fields)
for row in rows: sheet.append([row.get(k,'') for k in fields])
stats=wb['E - Stats'];stats.delete_rows(1,stats.max_row)
stats.append(('E Product Statistics',None));stats.append(('Metric','Count'))
metrics=[('Total products',len(rows)),('Distinct brands',len(set(r['brand'] for r in rows))),('Verified release year',sum(bool(r['release_year']) for r in rows)),('Price listed',sum(bool(r['official_price']) for r in rows)),('Image URL present',sum(bool(r['image_url']) for r in rows)),('Release year unknown',gap_year),('Price unavailable',gap_price),('Image URL missing',gap_img)]
for item in metrics: stats.append(item)
stats.append((None,None));stats.append(('Subtype','Products'))
for sub,n in sorted(e_counts.items()): stats.append((sub,n))
cs=wb['Category Summary'];cs.delete_rows(1,cs.max_row);cs.append(['Category','Department','Subtype','Products','Status','CSV file'])
for r in sorted(summary,key=lambda x:(x['category_code'],x['subcategory'])):
    cs.append([r['category_code'],r['department'],r['subcategory'],int(r['products_count']),r['processing_status'],r['csv_file']])
wb.save(book)
print('E rows',len(rows),'brands',len(set(r['brand'] for r in rows)),'subtypes',dict(sorted(e_counts.items())))
print('E gaps: release year',gap_year,'price',gap_price,'image',gap_img,'images found',len(rows)-gap_img)
print('All export rows',len(all_rows),'Workbook updated')
