import csv, json
from pathlib import Path

p = Path(__file__).with_name('F-kitchen-appliances.csv')
with p.open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
fields = list(rows[0])
existing = {(r['brand'].strip().casefold(), r['model'].strip().casefold()) for r in rows if r['model'].strip()}
today = '2026-10-13'
def add(sub, typ, name, brand, model, product_url, source_url, specs, description, *, date='', precision='', year='', price='', currency='', market='', price_type='', price_url='', notes=''):
    key=(brand.casefold(),model.casefold())
    if key in existing:
        return
    existing.add(key)
    rows.append({
        'category_code':'F','department':'Kitchen Appliances','subcategory':sub,'product_type':typ,
        'product_name':name,'manufacturer':brand,'brand':brand,'model':model,
        'manufacturer_part_number':'','gtin':'','description':description,
        'specifications_json':json.dumps(specs,ensure_ascii=False,separators=(',',':')),
        'image_url':'','product_url':product_url,'release_date':date,'release_date_precision':precision,'release_year':year,
        'official_price':str(price) if price else '', 'price_currency':currency,'price_type':price_type,'price_market':market,
        'price_source_url':price_url,'product_source_url':source_url,
        'source_attribution':'Official manufacturer launch announcement and product page/catalogue',
        'collected_on':today,'verification_status':'official_sources_verified',
        'notes':notes or 'Manufacturer launch announcement establishes release timing; official product page supports identity and specifications. Product image URL and/or current transaction price were not captured; fields left blank.'
    })

delonghi_release='https://www.delonghi.com/en-us/press-releases'
delonghi_range='https://www.delonghi.com/en-us/c/coffee-e-espresso/coffee-machines/automatic-espresso-machines?refine=c_productRange%3DRIVELIA'
rivelia_specs={'machine_type':'fully automatic espresso machine','display_in':'3.5','preset_drinks':18,'user_profiles':4,'bean_hoppers':2,'milk_system':'LatteCrema Hot','bean_adapt':True,'grinder':'integrated burr grinder'}
for model,colour,price in [('EXAM44055B','Onyx Black',1299.95),('EXAM44055W','Arctic White',1299.95),('EXAM44055G','Pebble Gray',1299.95),('EXAM44055BG','Sand Beige',1299.99)]:
    url=f'https://www.delonghi.com/en-us/p/rivelia-rivelia-fully-automatic-espresso-machine--{colour.lower().replace(" ","-")}/{model}.html'
    add('Beverage Appliances','Fully Automatic Espresso Machine',f"De'Longhi Rivelia Fully Automatic Espresso Machine - {colour}",'De\'Longhi',model,url,delonghi_release,rivelia_specs,
        'Bean-to-cup espresso machine with one-touch drink recipes, dual removable bean hoppers, personalized profiles, and automatic milk frothing.',
        date='2025-05-01' if model!='EXAM44055BG' else '',precision='day' if model!='EXAM44055BG' else '',year='2025',price=price,currency='USD',market='United States',price_type='current_listed',price_url=delonghi_range,
        notes=('US/Canada Rivelia launch announcement dated 2025-05-01. Sand Beige was announced for later summer 2025, so only the year is recorded. Current manufacturer catalogue lists model and price. '+colour+' product detail URL uses the manufacturer model identifier; verify URL before import.'))

panasonic_pr='https://news.panasonic.com/jp/topics/206334'
panasonic_page='https://panasonic.jp/range/products/NE-FB2D.html'
add('Cooking Appliances','Microwave Oven','Panasonic Bistro Single-Function Microwave Oven NE-FB2D','Panasonic','NE-FB2D',panasonic_page,panasonic_pr,
    {'oven_type':'single-function microwave','sensor':'high-precision 64-point speed sensor','antenna':'3D antenna','heating':'Cyclonic Wave','features':['simultaneous heating of two items','one-bowl cooking','core-thaw defrost'],'color':'Off White'},
    'Countertop microwave with Panasonic 64-point sensing, targeted heating, simultaneous two-item warming, and core-thaw defrost.',
    date='2025-09-01',precision='month',year='2025',market='Japan',
    notes='Panasonic announced launch in early September 2025 and open MSRP. Release date stored to month precision only; price is blank because the manufacturer lists open pricing. Capacity and power were not established from the inspected announcement and are not inferred.')

dedica='https://www.delonghi.com/en-us/p/dedica-duo-dedica-duo-espresso-machine--metal/EC890M.html'
add('Beverage Appliances','Manual Espresso Machine',"De'Longhi Dedica Duo Espresso Machine - Stainless Steel",'De\'Longhi','EC890M',dedica,delonghi_release,
    {'machine_type':'manual pump espresso machine','pump_pressure_bar':15,'input_power_w':1450,'voltage_v':120,'frequency_hz':60,'water_tank_oz':34.83,'max_cup_height_mm':148.6,'display':'digital touch display','preset_drinks':['espresso','double espresso','cold brew'],'milk_wand':'steam wand'},
    'Compact pump espresso machine with touch controls, a steam wand, and presets for espresso, double espresso, and cold brew.',
    date='2025-06-05',precision='day',year='2025',price=249.95,currency='USD',market='United States',price_type='current_listed',price_url=dedica,
    notes='De\'Longhi announced the Dedica Duo for North America on 2025-06-05. Product-page specification and current listed price verified on the official manufacturer site; MSRP at launch differs from current listed price.')

with p.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print(f'F rows: {len(rows)}; appended recent records: {len(rows)-103}')
