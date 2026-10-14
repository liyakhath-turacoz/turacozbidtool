import csv,json,os,requests
from datetime import date
from urllib.parse import urljoin
root=os.path.dirname(__file__);path=os.path.join(root,'H-air-conditioning-cooling-air-quality.csv')
with open(path,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f)); fields=list(rows[0])
# Values were transcribed from the linked Blue Star 2026 BEE-label technical specifications.
items=[
('inverter-ac-v-smart-wi-fi-series-1-ton-3-star-2026-bee-label','IA312VXU','1.02','3','3600','1046~3693','4.38','1080','52','Wi-Fi-ready V series'),
('inverter-ac-d-series-1-5-ton-5-star-2026-bee-label','IA518DXU','1.46','5','5150','2830~5522','5.70','1210','54','D series'),
('inverter-ac-t-series-1-ton-5-star-2026-bee-label','IA512TXU','1.02','5','3600','1754~3606','5.63','815','54','T series'),
('inverter-ac-z-smart-wi-fi-series-1-5-ton-5-star-2026-bee-label','IA518ZXUS','1.45','5','5100','2175~5468','5.63','1227','54','Z Smart Wi-Fi series'),
('inverter-ac-v-smart-wi-fi-series-1-5-ton-5-star-2026-bee-label','IA518VXUS','1.46','5','5150','2830~5522','5.70','1210','54','V Smart Wi-Fi series'),
('inverter-ac-u-smart-wi-fi-series-1-ton-5-star-2026-bee-label','IA512UXUS','1.02','5','3600','1754~3606','5.63','815','54','U Smart Wi-Fi series'),
('inverter-ac-u-smart-wi-fi-series-1-5-ton-5-star-2026-bee-label-1','IA518UXUS','1.45','5','5100','2175~5468','5.63','1227','54','U Smart Wi-Fi series'),
('inverter-ac-z-series-1-ton-3-star-2026-bee-label','IA312ZXU','1.00','3','3517','1600~3618','4.38','1060','52','Z series'),
('inverter-ac-q-smart-wi-fi-series-1-5-ton-5-star-2026-bee-label','IA518QXUS','1.45','5','5100','2175~5468','5.63','1227','54','Q Smart Wi-Fi series'),
]
existing={(r['brand'].strip().lower(),r['model'].strip().lower()) for r in rows}
headers={'User-Agent':'Mozilla/5.0'}; added=[]
for slug,model,ton,star,cool,range_w,iseer,input_w,ambient,family in items:
 if ('blue star',model.lower()) in existing: continue
 page='https://consumer.bluestarindia.com/products/'+slug
 resp=requests.get(page+'.js',headers=headers,timeout=20);resp.raise_for_status();j=resp.json()
 variants=j.get('variants') or [];price=str(variants[0].get('price','')/100) if variants and variants[0].get('price') is not None else ''
 if price.endswith('.0'):price=price[:-2]
 img=(j.get('images') or [''])[0];img=urljoin('https:',img) if img.startswith('//') else img
 title=j.get('title','')
 specs={'air_conditioner_type':'split inverter AC','series':family,'nominal_cooling_capacity_ton':float(ton),'bee_star_rating':int(star),'cooling_capacity_w':int(cool),'cooling_capacity_range_w':range_w,'rated_voltage_frequency_phase':'230V/50Hz/1Ph','iseer':float(iseer),'cooling_rated_power_input_w':int(input_w),'maximum_ambient_cooling_temperature_c':int(ambient),'refrigerant':'R32','condenser_coil':'100% copper','compressor_type':'inverter rotary','country_of_origin':'India'}
 if 'Wi-Fi' in family:specs['connectivity']='Wi-Fi / smart app (series listing)'
 pub=j.get('published_at','');note='Official Blue Star India product page and 2026 BEE-label specification. Page publication timestamp: '+pub+'. Current price is the manufacturer Shopify listing price as collected on 2026-10-13; regional availability and price may vary.'
 added.append(dict(category_code='H',department='Air Conditioning, Cooling & Air Quality',subcategory='Air Conditioners',product_type='Split Inverter Air Conditioner',product_name=f'Blue Star {family} Split Inverter AC {model}',manufacturer='Blue Star Limited',brand='Blue Star',model=model,manufacturer_part_number=model,gtin='',description=title, specifications_json=json.dumps(specs,ensure_ascii=False,separators=(',',':')),image_url=img,product_url=page,release_date='',release_date_precision='year',release_year='2026',official_price=price,price_currency='INR',price_type='current_listed',price_market='India',price_source_url=page,product_source_url=page,source_attribution='Official Blue Star India product page; 2026 BEE label',collected_on='2026-10-13',verification_status='official_page_verified',notes=note))
with open(path,'a',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writerows(added)
print('Blue Star records added:',len(added));print('Models:',', '.join(r['model'] for r in added));print('Official listing prices:',', '.join(r['model']+' ₹'+r['official_price'] for r in added))
