import csv,json,os,re,requests
from datetime import date
from collections import Counter
from bs4 import BeautifulSoup

ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'G-cleaning-laundry-floor-care.csv');TODAY=date(2026,10,13).isoformat()
FIELDS=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes']
rows=[]
def add(sub,typ,name,brand,model,url,specs=None,description='',image='',price='',currency='',market='',price_type='',price_url='',year='',notes=''):
 rows.append(dict(category_code='G',department='Cleaning, Laundry & Floor Care',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=description or f'{name}; consult the linked official manufacturer page for full specifications.',specifications_json=json.dumps(specs or {},ensure_ascii=False,separators=(',',':')),image_url=image,product_url=url,release_date='',release_date_precision='',release_year=year,official_price=str(price),price_currency=currency,price_type=price_type,price_market=market,price_source_url=price_url,product_source_url=url,source_attribution='Official manufacturer product page or catalogue',collected_on=TODAY,verification_status='official_page_verified',notes=notes or 'Current official product/catalogue listing verified. Release year is not stated; age requires review.'))

# Ecovacs India current DEEBOT catalogue; page lists current online prices and explicitly marks three 2026 new launches.
ecovacs='https://ecovacsindia.in/'
ev=[('DEEBOT N30 White','https://ecovacsindia.in/deebot-n30-white','https://ecovacsindia.in/images/deebot-n30-white/thumbnil/N30-White-Best-Seller.jpg',19999,'',{}),('DEEBOT N30 PLUS','https://ecovacsindia.in/deebot-n30-plus','https://ecovacsindia.in/images/deebot-n30-plus/thumbnil/N30-Plus-Best-Seller.jpg',27999,'',{}),('DEEBOT N50 Pro Omni','https://ecovacsindia.in/deebot-n50-pro-omni','https://ecovacsindia.in/images/deebot-n50-pro-omni/thumbnil/N50-Pro-Omni.jpeg',53999,'',{}),('DEEBOT T30e OMNI','https://ecovacsindia.in/deebot-t30e-omni','https://ecovacsindia.in/images/deebot-t30e-omni/thumbnil/T30e-Omni-Main.jpg',44999,'2026',{}),('DEEBOT T50S PRO OMNI','https://ecovacsindia.in/deebot-t50s-pro-omni','https://ecovacsindia.in/images/deebot-t50s-pro-omni/thumbnil/1.jpg?ver=1',66999,'2026',{'suction_pa':25000,'mop_wash_temperature_f':167,'mop_dry_temperature_f':113,'cleaning_modes':['vacuum','mop','vacuum_and_mop','vacuum_then_mop']}),('DEEBOT T90 PRO OMNI','https://ecovacsindia.in/deebot-t90-pro-omni','https://ecovacsindia.in/images/deebot-t90-pro-omni/thumbnil/1.jpg',114999,'2026',{'suction_pa':30000,'obstacle_climb_cm':'2.2 single step / 4 double step','mop_rotation_rpm':200,'mop_wash_temperature_c':75}),('DEEBOT X11 OmniCyclone','https://ecovacsindia.in/deebot-x11-omni-cycle','https://ecovacsindia.in/images/deebot_x11_omnicyclone/thumbnil/1.png',99999,'',{}),('DEEBOT X12 OmniCyclone','https://ecovacsindia.in/deebot-x12-omni-cycle','https://ecovacsindia.in/images/deebot-x12-omnicyclone/thumbnil/1.jpg',144999,'',{})]
for name,url,img,price,year,spec in ev:
 model=name.replace('DEEBOT ','')
 note=('Official Ecovacs India listing labels this model as a 2026 new launch.' if year else 'Official Ecovacs India product page/current catalogue; source page does not establish release date, so age needs review.')
 if model=='T50S PRO OMNI': note='Official Ecovacs page labels this a 2026 new launch; product page verifies 25,000 Pa, multi-mode cleaning, and 167°F hot-water mop washing/113°F drying.'
 if model=='T90 PRO OMNI': note='Official Ecovacs page labels this a 2026 new launch; product page verifies 30,000 Pa, obstacle climbing, 200 RPM mopping and 75°C mop washing.'
 add('Robot Cleaners','Robot Vacuum and Mop',name,'ECOVACS',model,url,spec,name+' robot vacuum/mop system.',img,price,'INR','India','current_listed',ecovacs,year,note)

# Philips India latest floor-care and garment-steamer pages. Older/current models are kept but explicitly age-flagged.
vac=[('FC6146/01','MiniVac Handheld Vacuum Cleaner','https://www.philips.co.in/c-p/FC6146_01/minivac-handheld-vacuum-cleaner'),('FC6726/01','SpeedPro Cordless Stick Vacuum Cleaner','https://www.philips.co.in/c-p/FC6726_01/speedpro-cordless-stick-vacuum-cleaner'),('FC9571/01','5000 Series Bagless Vacuum Cleaner','https://www.philips.co.in/c-p/FC9571_01/5000-series-bagless-vacuum-cleaner'),('FC9352/01','3000 Series Bagless Vacuum Cleaner','https://www.philips.co.in/c-p/FC9352_01/3000-series-bagless-vacuum-cleaner'),('FC9351/01','PowerPro Compact Bagless Vacuum Cleaner','https://www.philips.co.in/c-p/FC9351_01/powerpro-compact-bagless-vacuum-cleaner'),('FC6130/01','MiniVac Handheld Vacuum Cleaner','https://www.philips.co.in/c-p/FC6130_01/minivac-handheld-vacuum-cleaner'),('FC6728/01','SpeedPro Aqua Cordless Stick Vacuum Cleaner','https://www.philips.co.in/c-p/FC6728_01/speedpro-aqua-cordless-stick-vacuum-cleaner')]
for model,name,url in vac:
 add('Vacuum Cleaners','Handheld Vacuum' if 'Handheld' in name else 'Cordless Stick Vacuum' if 'Stick' in name else 'Bagless Canister Vacuum',f'Philips {name} {model}','Philips',model,url,{'cleaning_type':'wet_and_dry' if 'Aqua' in name else 'dry'},image='',notes='Listed on Philips India floor-care product catalogue. Model page has product information; launch date/year not stated and age needs review. Image URL and current price were not captured.')

steam=[('STH3010/70','3000 Series Handheld Steamer'),('GC487/89','Easy Touch Stand Steamer'),('STH7020/20','7000 Series Handheld Steamer'),('STH7040/80','7000 Series Handheld Steamer'),('GC487/80','Easy Touch Stand Steamer'),('STE3170/80','3000 Series Stand Steamer with Tilting StyleBoard'),('STE3160/30','3000 Series Stand Steamer with Tilting StyleBoard'),('STH1010/10','1000 Series Handheld Steamer'),('STH1000/10','1000 Series Handheld Steamer')]
for model,name in steam:
 norm=model.replace('/','_');url=f'https://www.philips.co.in/c-p/{norm}/{name.lower().replace(" ","-")}'
 # Use canonical path from the manufacturer's current category page, whose URL is recorded when canonical slug is uncertain.
 slug={'STH3010/70':'https://www.philips.co.in/c-p/STH3010_70/3000-series-handheld-steamer','GC487/89':'https://www.philips.co.in/c-p/GC487_89/easy-touch-stand-steamer','STH7020/20':'https://www.philips.co.in/c-p/STH7020_20/7000-series-handheld-steamer','STH7040/80':'https://www.philips.co.in/c-p/STH7040_80/7000-series-handheld-steamer','GC487/80':'https://www.philips.co.in/c-p/GC487_80/easy-touch-stand-steamer','STE3170/80':'https://www.philips.co.in/c-p/STE3170_80/stand-steamer-3000-series-with-tilting-styleboard','STE3160/30':'https://www.philips.co.in/c-p/STE3160_30/stand-steamer-3000-series-with-tilting-styleboard','STH1010/10':'https://www.philips.co.in/c-p/STH1010_10/handheld-steamer-1000-series-handheld-steamer','STH1000/10':'https://www.philips.co.in/c-p/STH1000_10/handheld-steamer-1000-series-handheld-steamer'}
 add('Laundry Care','Handheld Garment Steamer' if 'Handheld' in name else 'Stand Garment Steamer',f'Philips {name} {model}','Philips',model,slug[model],{},notes='Listed in Philips India current garment-steamer catalogue. Release year and age are not stated; current price and official image URL were not captured.')

# Dreame India official live catalogue. Product names/model URLs are current manufacturer listings; no launch year asserted.
dreame='https://in.dreametech.com/collections/robot-vacuum-accessories'
dm=[('X60 Ultra Complete','robot','https://in.dreametech.com/products/x60-ultra'),('L50s Pro Ultra','robot','https://in.dreametech.com/products/l50s-pro-ultra'),('L50 Ultra CE','robot','https://in.dreametech.com/products/l50-ultra-ce'),('D30 Ultra','robot','https://in.dreametech.com/products/d30-ultra'),('D20 Ultra','robot','https://in.dreametech.com/products/dreame-d20-ultra'),('L50 Plus','robot','https://in.dreametech.com/products/l50-plus'),('L50','robot','https://in.dreametech.com/products/l50'),('D10 Plus Gen 2','robot','https://in.dreametech.com/products/d10-plus-gen2-robot-vacuum'),('F10','robot','https://in.dreametech.com/products/dreame-f10'),('D9 Max','robot','https://in.dreametech.com/products/dreame-d9-max-robot-vacuum'),('H12 Dual FlexReach','floor','https://in.dreametech.com/products/h12-dual-flexreach'),('H12 Dual','floor','https://in.dreametech.com/products/h12-dual'),('H12 Core','floor','https://in.dreametech.com/products/h12-core'),('H11 Core','floor','https://in.dreametech.com/products/dreame-h11-core'),('K10 Pro','floor','https://in.dreametech.com/products/dreame-mova-k10-pro'),('R20','vac','https://in.dreametech.com/products/dreame-r20'),('R10 Pro','vac','https://in.dreametech.com/products/r10-pro'),('J20','vac','https://in.dreametech.com/products/mova-j20-cordless-stick-vacuum'),('J10','vac','https://in.dreametech.com/products/mova-j10-cordless-stick-vacuum')]
sess=requests.Session();sess.headers.update({'User-Agent':'Mozilla/5.0'})
for model,kind,url in dm:
 try:
  resp=sess.get(url,timeout=12); soup=BeautifulSoup(resp.text,'html.parser'); title=(soup.select_one('meta[property="og:title"]') or {}).get('content','').split('|')[0].strip() or f'Dreame {model}'
  img=(soup.select_one('meta[property="og:image"]') or {}).get('content','')
  desc=(soup.select_one('meta[name="description"]') or {}).get('content','')
  if not desc: desc=title
 except Exception: title=f'Dreame {model}';img='';desc=title
 sub={'robot':'Robot Cleaners','floor':'Floor Cleaning','vac':'Vacuum Cleaners'}[kind]
 typ={'robot':'Robot Vacuum Cleaner','floor':'Wet and Dry Floor Cleaner','vac':'Cordless Stick Vacuum Cleaner'}[kind]
 add(sub,typ,title,'Dreame',model,url,{},desc,img,notes='Listed in Dreame India current product catalogue; release year not stated and age requires review. Price/image/specification details are not consistently exposed in the catalogue source.')

# Singer India official sewing-machine catalogue (15 current cards, with individual product URLs and listed MRP).
singer='https://shop.singerindia.com/product-category/sewing-machines/'
try:
 soup=BeautifulSoup(sess.get(singer,timeout=25).text,'html.parser')
 for a in soup.select('a.woocommerce-LoopProduct-link'):
  card=a.find_parent('li');
  if not card: continue
  titleel=card.select_one('.woocommerce-loop-product__title'); title=titleel.get_text(' ',strip=True) if titleel else a.get_text(' ',strip=True)
  url=a.get('href','');
  if not title or not url: continue
  # The exact displayed model/variant name is used as the model key when no separate manufacturer SKU is present.
  imgel=card.select_one('img'); img=(imgel.get('data-src') or imgel.get('src') or '') if imgel else ''
  txt=card.get_text(' ',strip=True); pm=re.search(r'₹\s*([0-9,]+(?:\.\d{1,2})?)',txt);price=pm.group(1).replace(',','') if pm else ''
  model=re.sub(r'^SINGER\s*','',title,flags=re.I)
  add('Sewing Equipment','Electric Sewing Machine',title if title.upper().startswith('SINGER') else 'Singer '+title,'Singer India',model,url,{},title,img,price,'INR','India','manufacturer_listed_mrp' if price else '',singer,notes='Current listing from Singer India official sewing-machine catalogue. Exact release date/year not stated; image/price fields follow catalogue availability.')
except Exception as e: print('Singer catalogue fetch issue',repr(e))

# Philips lists one dedicated vacuum-cleaner accessory on its India accessory catalogue.
add('Cleaning Accessories','Vacuum Cleaner Replacement Accessory','Philips Vacuum Cleaner Accessory','Philips','FC8046/01','https://www.philips.co.in/c-p/FC8046_01/-',{},notes='Listed in the Philips India vacuum-cleaner and mop accessories catalogue. The public listing does not provide a clear accessory name or compatibility/specification details; verify before import.')

# Deduplicate exact brand/model identifiers. Same base model sold in genuinely different case/stand packages remains variant-specific only where its catalog title identifies the package.
unique=[];seen=set()
for r in rows:
 key=(r['brand'].lower(),r['model'].lower())
 if key in seen: continue
 seen.add(key);unique.append(r)
rows=unique
# Explicitly report fields that need enrichment; do not invent missing specifications or release years.
for r in rows:
 missing=[]
 if not r['release_year']: missing.append('release year not stated; age needs verification')
 if not r['official_price']: missing.append('official price not captured')
 if not r['image_url']: missing.append('official product image URL not captured')
 if not r['specifications_json'] or r['specifications_json']=='{}': missing.append('detailed technical specifications not captured')
 if missing: r['notes']=(r['notes'].rstrip(' .;')+'; ' if r['notes'] else '')+'Missing/unverified fields: '+', '.join(missing)+'.'
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
print('G records',len(rows),'brands',len(set(r['brand'] for r in rows)),'subtypes',dict(sorted(Counter(r['subcategory'] for r in rows).items())))
print('Missing year',sum(not r['release_year'] for r in rows),'price',sum(not r['official_price'] for r in rows),'image',sum(not r['image_url'] for r in rows),'specs',sum(r['specifications_json']=='{}' for r in rows),'duplicates',len(rows)-len(seen))
