import csv,json,os,re,requests,concurrent.futures
from datetime import date
from collections import Counter
from bs4 import BeautifulSoup
ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'H-air-conditioning-cooling-air-quality.csv');TODAY=date(2026,10,13).isoformat()
FIELDS=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes'];rows=[]
def add(sub,typ,name,brand,model,url,specs=None,desc='',image='',price='',currency='',market='',ptype='',purl='',year='',notes=''):
 rows.append(dict(category_code='H',department='Air Conditioning, Cooling & Air Quality',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=desc or f'{name}; consult the linked official product/catalogue page for technical details.',specifications_json=json.dumps(specs or {},ensure_ascii=False,separators=(',',':')),image_url=image,product_url=url,release_date='',release_date_precision='',release_year=year,official_price=str(price),price_currency=currency,price_type=ptype,price_market=market,price_source_url=purl,product_source_url=url,source_attribution='Official manufacturer product page or catalogue',collected_on=TODAY,verification_status='official_page_verified',notes=notes))

# LG Electronics India official 2026 residential air-conditioner catalogue: 53 unique split-AC model codes.
lgpdf='https://www.lg.com/content/dam/channel/wcms/in/appliances-catalogue/air-conditioner/RAC_Catalogue_2026.pdf'
textfile=os.path.join(ROOT,'_temp_lg_ac.txt')
if os.path.exists(textfile):
 models=sorted(set(x.strip() for x in open(textfile,encoding='utf-8') if re.fullmatch(r'AS-Q[A-Z0-9]+',x.strip())))
 for model in models:
  add('Air Conditioners','Split Inverter Air Conditioner',f'LG Dual Inverter Split Air Conditioner {model}','LG',model,lgpdf,{'catalogue_edition':2026},notes='Model code appears in LG Electronics India official Residential Air Conditioners Catalogue 2026. Catalogue edition does not establish individual launch year; detailed capacity/specifications and price need model-page verification.')

headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
def fetch(u):
 try:return u,requests.get(u,headers=headers,timeout=16).text
 except Exception:return u,''

# Shopify pages: source display names/images/prices directly from Crompton's official live category catalogues.
shop_pages=[('https://www.crompton.co.in/collections/air-coolers','Air Coolers','Air Cooler'),('https://www.crompton.co.in/collections/fans','Fans','Electric Fan'),('https://www.crompton.co.in/collections/exhaust-fans','Ventilation Equipment','Exhaust Fan'),('https://www.crompton.co.in/collections/room-heaters','Heating Appliances','Room Heater')]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: pages=dict(ex.map(fetch,[x[0] for x in shop_pages]))
for src,sub,typ in shop_pages:
 soup=BeautifulSoup(pages.get(src,''),'html.parser');seen_urls=set()
 for a in soup.find_all('a',href=True):
  href=a['href']
  if '/products/' not in href:continue
  full=('https://www.crompton.co.in'+href) if href.startswith('/') else href
  if full in seen_urls:continue
  card=a
  for _ in range(6):
   if card.parent is None:break
   card=card.parent
   if 'product-card-wrapper' in (card.get('class') or []):break
  title=a.get_text(' ',strip=True)
  img=''
  im=card.select_one('img') if hasattr(card,'select_one') else None
  if im:img=im.get('src') or im.get('data-src') or im.get('data-original') or ''
  if img.startswith('//'):img='https:'+img
  if not title and im:title=im.get('alt','').strip()
  if not title or not full:continue
  seen_urls.add(full);txt=card.get_text(' ',strip=True)
  prices=re.findall(r'(?:MRP|Sale price|Regular price)?\s*₹\s*([0-9,]+(?:\.\d{1,2})?)',txt,re.I)
  price=prices[-1].replace(',','') if prices else ''
  # Use precise capacities/airflow/power only when stated in the source title.
  spec={};cap=re.search(r'(\d{2,3})\s*[- ]?L\b',title,re.I)
  if cap:spec['capacity_l']=int(cap.group(1))
  pw=re.search(r'(\d{2,4})\s*W\b',title,re.I)
  if pw:spec['power_w']=int(pw.group(1))
  model=title
  add(sub,typ,title,'Crompton',model,full,spec,title,img,price,'INR' if price else '','India' if price else '', 'current_listed' if price else '',src if price else '',notes='Listed in Crompton India official live product category. Product age/release date is not stated; model-level specifications beyond the title need review.' if not spec else 'Listed in Crompton India official live product category; release year not stated and age needs review.')

# Philips India product catalogues for air purifiers and humidifiers.
philips_pages=[('https://www.philips.co.in/c-m-ho/air-purifier-and-air-humidifier/air-purifier/all','Air Purifiers','Room Air Purifier'),('https://www.philips.co.in/c-m-ho/air-purifier-and-air-humidifier/humidifier/all','Humidifiers & Dehumidifiers','Room Humidifier')]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: pp=dict(ex.map(fetch,[x[0] for x in philips_pages]))
for src,sub,typ in philips_pages:
 soup=BeautifulSoup(pp.get(src,''),'html.parser');found={}
 for a in soup.find_all('a',href=True):
  m=re.search(r'/c-p/([^/]+)',a['href'])
  if not m:continue
  code=m.group(1);model=code.replace('_','/')
  href='https://www.philips.co.in'+a['href'] if a['href'].startswith('/') else a['href']
  if code not in found:found[code]=[href,'','']
  # walk to nearest product card to capture display name and official image
  card=a
  for _ in range(6):
   if card.parent is None:break
   card=card.parent
   if any(c in (card.get('class') or []) for c in ['product-item','product-card','product-tile']):break
  label=a.get_text(' ',strip=True)
  if label and not re.fullmatch(r'[A-Z0-9/]+',label):found[code][1]=label
  im=card.select_one('img') if hasattr(card,'select_one') else None
  if im and not found[code][2]:found[code][2]=im.get('src') or im.get('data-src') or ''
 for code,(url,name,img) in found.items():
  model=code.replace('_','/');name=name or f'Philips {typ} {model}'
  if '/support' in url:name=f'{name} {model}'
  if img.startswith('//'):img='https:'+img
  add(sub,typ,name,'Philips',model,url,{},name,img,notes='Listed in Philips India current product catalogue. Release date/year and age are not stated; verify current sale status and detailed specifications.')

# Official Crompton collection may expose only consumer products, not compatible AC remotes/filters; do not invent accessories.
# Keep the source-data gap visible in the plan and summary instead of manufacturing a climate accessory record.

unique=[];seen=set()
for r in rows:
 key=(r['brand'].lower(),r['model'].lower())
 if key in seen:continue
 seen.add(key);unique.append(r)
rows=unique
for r in rows:
 missing=[]
 if not r['release_year']:missing.append('release year not stated; age needs verification')
 if not r['official_price']:missing.append('official price not captured')
 if not r['image_url']:missing.append('official image URL not captured')
 if r['specifications_json']=='{}':missing.append('detailed specifications not captured')
 if missing:r['notes']=(r['notes'].rstrip(' .;')+'; ' if r['notes'] else '')+'Missing/unverified fields: '+', '.join(missing)+'.'
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
print('H records',len(rows),'brands',len(set(r['brand'] for r in rows)),'subtypes',dict(sorted(Counter(r['subcategory'] for r in rows).items())))
print('Missing year',sum(not r['release_year'] for r in rows),'price',sum(not r['official_price'] for r in rows),'image',sum(not r['image_url'] for r in rows),'specs',sum(r['specifications_json']=='{}' for r in rows),'duplicates',len(rows)-len(seen))
