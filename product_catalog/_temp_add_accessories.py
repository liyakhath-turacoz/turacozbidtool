import csv,json
from pathlib import Path
p=Path('product_catalog/C-tvs-video-home-entertainment.csv')
with p.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);cols=r.fieldnames;rows=list(r)
keys={(x['brand'].lower(),x['model'].lower()) for x in rows}
items=[
('Sony','SU-WL905','Sony SU-WL905 Low-Profile TV Wall-Mount Bracket','Wall-mount bracket','Wall mount for selected compatible Sony BRAVIA televisions; check the official compatibility list before purchase.',{'accessory':'TV wall mount','release_year':2024,'compatibility':'Sony compatibility list; includes selected 2025 BRAVIA TVs','mount':'Low profile'},'https://www.sony.com/electronics/support/television-projector-accessories-wall-mount-bracket/su-wl905','2024-03-31','Operating instructions dated 2024-03-31; compatible with selected current BRAVIA models.'),
('LG','ST-G4WR8377','LG OLED G Series 77/83-inch Stand and Back Cover','TV stand','Center-mounted stand and back cover compatible with specified LG OLED G television sizes.',{'accessory':'Center-mounted TV stand and back cover','compatible_2025_models':['OLED83G5WUA','OLED77G5WUA'],'compatible_2024_models':['OLED83G4WUA','OLED77G4WUA']},'https://www.lg.com/us/tv-audio-video-accessories/lg-st-g4wr8377-oled-g4-stand','2024','Official listing confirms compatible 2025 television models; current official price not captured.')]
for brand,model,name,typ,desc,spec,url,year,note in items:
 if (brand.lower(),model.lower()) in keys:continue
 rows.append(dict(category_code='C',department='TVs, Video & Home Entertainment',subcategory='TV Accessories',product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number=model,gtin='',description=desc,specifications_json=json.dumps(spec,separators=(',',':')),image_url='',product_url=url,release_date=year if len(year)==10 else '',release_date_precision='day' if len(year)==10 else 'year',release_year=year[:4],official_price='',price_currency='',price_type='',price_market='',price_source_url='',product_source_url=url,source_attribution='Official manufacturer accessory page/support page',collected_on='2026-10-13',verification_status='official_manufacturer_source_verified',notes=note+' Confirm size/model compatibility before purchase. Image URL and price not captured.'))
with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
print('C rows',len(rows))
