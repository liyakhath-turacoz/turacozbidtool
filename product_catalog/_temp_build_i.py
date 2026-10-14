import csv,json,os,re,requests,concurrent.futures
from datetime import date
from collections import Counter
from bs4 import BeautifulSoup
ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'I-personal-care-grooming-appliances.csv');TODAY=date(2026,10,13).isoformat()
FIELDS=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes'];rows=[]
def add(sub,typ,name,brand,model,url,specs=None,desc='',image='',price='',currency='',market='',ptype='',purl='',year='',notes=''):
 rows.append(dict(category_code='I',department='Personal Care & Grooming Appliances',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=desc or f'{name}; consult the linked official manufacturer product page for technical details.',specifications_json=json.dumps(specs or {},ensure_ascii=False,separators=(',',':')),image_url=image,product_url=url,release_date='',release_date_precision='',release_year=year,official_price=str(price),price_currency=currency,price_type=ptype,price_market=market,price_source_url=purl,product_source_url=url,source_attribution='Official manufacturer product page or catalogue',collected_on=TODAY,verification_status='official_page_verified',notes=notes))

headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
session=requests.Session();session.headers.update(headers)
philips=[('https://www.philips.co.in/c-m-pe/haircare/hair-dryers/all','Hair Care','Hair Dryer'),('https://www.philips.co.in/c-m-pe/haircare/straighteners/latest','Hair Care','Hair Straightener / Curler'),('https://www.philips.co.in/c-m-pe/haircare/hairbrush/latest','Hair Care','Heated Styling Brush'),('https://www.philips.co.in/c-m-pe/face-stylers-and-grooming-kits/beard-trimmers/latest','Shaving & Grooming','Beard Trimmer'),('https://www.philips.co.in/c-m-pe/face-stylers-and-grooming-kits/multigroomers/latest','Shaving & Grooming','Multi-Grooming Trimmer'),('https://www.philips.co.in/c-m-pe/face-shavers/latest','Shaving & Grooming','Electric Shaver'),('https://www.philips.co.in/c-m-pe/electric-toothbrushes','Oral Care','Electric Toothbrush')]
def get(u):
 try:return u,session.get(u,timeout=25).text
 except Exception:return u,''
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex: pages=dict(ex.map(get,[x[0] for x in philips]))
for src,sub,typ in philips:
 soup=BeautifulSoup(pages.get(src,''),'html.parser');groups={}
 for a in soup.find_all('a',href=True):
  m=re.search(r'/c-p/([^/]+)',a['href'])
  if not m:continue
  code=m.group(1);url=('https://www.philips.co.in'+a['href']) if a['href'].startswith('/') else a['href']
  if code not in groups:groups[code]={'url':url,'texts':[],'image':''}
  text=a.get_text(' ',strip=True)
  if text:groups[code]['texts'].append(text)
  card=a
  for _ in range(7):
   if card.parent is None:break
   card=card.parent
   if any(c in (card.get('class') or []) for c in ['product-item','product-card','product-tile']):break
  if hasattr(card,'select_one'):
   im=card.select_one('img')
   if im and not groups[code]['image']:groups[code]['image']=im.get('src') or im.get('data-src') or im.get('data-original') or ''
 for code,g in groups.items():
  model=code.replace('_','/');texts=g['texts'];name=next((t for t in texts if not re.fullmatch(r'[A-Z0-9/\s-]+',t) and 'view product' not in t.lower()),'')
  if not name:name=f'Philips {typ} {model}'
  img=g['image'];
  if img.startswith('//'):img='https:'+img
  if img.startswith('/'):img='https://www.philips.co.in'+img
  add(sub,typ,name,'Philips',model,g['url'],{},name,img,notes='Listed in Philips India current category catalogue. Release date/year is not stated and product age requires review; exact specifications/price need the individual page before import.')

# Official Beurer product categories: massage guns, scales, and wellness catalogue products.
beurer=[('https://www.beurer.com/uk/c/0020202/','Personal Wellness Devices','Massage Gun'),('https://www.beurer.com/uk/c/00501/','Personal Measurement Devices','Digital / Body Composition Scale'),('https://www.beurer.com/uk/c/002/','Personal Wellness Devices','Personal Wellness Device')]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex: pages=dict(ex.map(get,[x[0] for x in beurer]))
seen_beurer=set()
for src,sub,typ in beurer:
 soup=BeautifulSoup(pages.get(src,''),'html.parser')
 for a in soup.find_all('a',href=True):
  href=a['href']
  if '/uk/p/' not in href:continue
  url=('https://www.beurer.com'+href) if href.startswith('/') else href
  if url in seen_beurer:continue
  title=a.get_text(' ',strip=True)
  if not title:continue
  lower=title.lower()
  if sub=='Personal Wellness Devices' and src.endswith('/002/') and not any(k in lower for k in ('massage','foot massager','foot spa')):continue
  if sub=='Personal Measurement Devices' and not any(k in lower for k in ('scale','bathroom scale')):continue
  if sub=='Personal Wellness Devices' and src.endswith('/0020202/') and 'massage' not in lower:continue
  seen_beurer.add(url)
  # Titles are from the official manufacturer product card and include its model family.
  plain=re.sub(r'\s+(?:RRP|In stock|Few in stock|Not available online|Back in stock shortly).*$','',title,flags=re.I).strip()
  modelmatch=re.match(r'^(?:\d+ Colors?\s+)?([A-Z]{1,4}\s*\d{2,4}(?:\s+[A-Z]{1,3})?)\b',plain)
  model=modelmatch.group(1).strip() if modelmatch else plain
  if sub=='Personal Wellness Devices' and 'foot' in lower:ptype='Foot Massager / Foot Spa'
  elif sub=='Personal Wellness Devices':ptype='Electric Massage Device'
  elif 'body composition' in lower or 'diagnostic' in lower:ptype='Body Composition Scale'
  else:ptype='Digital Weighing Scale'
  product_name='Beurer '+plain
  add(sub,ptype,product_name,'Beurer',model,url,{},product_name,notes='Listed in Beurer official current product catalogue. Release date/year is not stated; age and detailed specifications need review before import.')

# Verified Philips accessories/flosser model pages.
add('Oral Care','Cordless Water Flosser','Philips Sonicare Cordless Power Flosser 3000','Philips','HX3826/31','https://www.philips.co.in/c-p/HX3826_31/cordless-power-flosser-3000',{},notes='Philips India product page for the Sonicare cordless water flosser; detailed specs/release year/price need review.')
add('Personal Care Accessories','Sonic Toothbrush Replacement Heads','Philips Sonicare ProResults Standard Brush Heads 4-pack','Philips','HX6014/07','https://www.philips.co.in/c-p/HX6014_07/sonicare-proresults-standard-sonic-toothbrush-heads',{'pack_quantity':4,'compatible_with':'Philips Sonicare click-on handles'},notes='Philips model/official page; verify availability and complete compatibility list before import.')
add('Personal Care Accessories','Electric Shaver Replacement Head','Philips Shaver Replacement Head','Philips','SH50/50','https://www.philips.co.in/c-p/SH50_50/shaver-series-5000-replacement-heads',{},notes='Official Philips replacement-head model listing; compatible shaver models and release year need review.')
add('Personal Care Accessories','OneBlade Replacement Blade','Philips OneBlade Replacement Blade 2-pack','Philips','QP230/50','https://www.philips.co.in/c-p/QP230_50/oneblade-replacement-blade',{'pack_quantity':2},notes='Official Philips OneBlade accessory model; product family compatibility needs review.')

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
print('I records',len(rows),'brands',len(set(r['brand'] for r in rows)),'subtypes',dict(sorted(Counter(r['subcategory'] for r in rows).items())))
print('Missing year',sum(not r['release_year'] for r in rows),'price',sum(not r['official_price'] for r in rows),'image',sum(not r['image_url'] for r in rows),'specs',sum(r['specifications_json']=='{}' for r in rows),'duplicates',len(rows)-len(seen))
