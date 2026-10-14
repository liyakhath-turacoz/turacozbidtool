import csv,json,os
from datetime import date
from collections import Counter
ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'L-wearables-smart-devices.csv');TODAY=date(2026,10,13).isoformat()
FIELDS=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes'];rows=[]
def add(sub,typ,name,brand,model,url,specs=None,year='',price='',currency='',market='',price_type='',price_url='',notes=''):
 rows.append(dict(category_code='L',department='Wearables & Smart Devices',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=f'{name}; details are limited to manufacturer-published information linked here.',specifications_json=json.dumps(specs or {},ensure_ascii=False,separators=(',',':')),image_url='',product_url=url,release_date='',release_date_precision='',release_year=year,official_price=str(price),price_currency=currency,price_type=price_type,price_market=market,price_source_url=price_url,product_source_url=url,source_attribution='Official manufacturer product page or catalogue',collected_on=TODAY,verification_status='official_source_linked',notes=notes))

# Smartwatches.
add('Smartwatches','Cellular smartwatch','Apple Watch Series 11 GPS + Cellular 42mm','Apple','Series 11 42mm Cellular','https://www.apple.com/us/shop/goto/buy_watch',{'case_size_mm':42,'connectivity':'GPS + Cellular','display':'Always-On Retina OLED'},'2025')
add('Smartwatches','Smartwatch','Apple Watch Series 11 GPS 46mm','Apple','Series 11 46mm GPS','https://www.apple.com/us/shop/goto/buy_watch',{'case_size_mm':46,'connectivity':'GPS','display':'Always-On Retina OLED'},'2025')
add('Smartwatches','Rugged cellular smartwatch','Apple Watch Ultra 3','Apple','Ultra 3','https://www.apple.com/us/shop/goto/buy_watch',{'case_size_mm':49,'connectivity':'GPS + Cellular','case_material':'titanium'},'2025')
add('Smartwatches','Entry smartwatch','Apple Watch SE 3','Apple','SE 3','https://www.apple.com/us/shop/goto/buy_watch',{'case_sizes_mm':[40,44],'connectivity':'GPS / GPS + Cellular'},'2025')
add('Smartwatches','Smartwatch','Samsung Galaxy Watch8 40mm Bluetooth','Samsung','SM-L320','https://www.samsung.com/us/watches/galaxy-watch8/buy/galaxy-watch8-40mm-silver-wi-fi-bluetooth-sku-sm-l320nzsaxaa/',{'case_size_mm':40,'connectivity':'Bluetooth / Wi-Fi','OS':'Wear OS'},'2025',299.99,'USD','US','current listed price','https://www.samsung.com/us/watches/galaxy-watch8/buy/')
add('Smartwatches','Smartwatch','Samsung Galaxy Watch8 44mm Bluetooth','Samsung','SM-L330','https://www.samsung.com/us/watches/galaxy-watch8/buy/',{'case_size_mm':44,'connectivity':'Bluetooth / Wi-Fi','OS':'Wear OS'},'2025',329.99,'USD','US','current listed price','https://www.samsung.com/us/watches/galaxy-watch8/buy/')
add('Smartwatches','Classic smartwatch','Samsung Galaxy Watch8 Classic 46mm','Samsung','SM-L500','https://www.samsung.com/us/watches/galaxy-watch8-classic/buy/',{'case_size_mm':46,'rotating_bezel':True,'OS':'Wear OS'},'2025')
add('Smartwatches','Rugged LTE smartwatch','Samsung Galaxy Watch Ultra 2025 47mm LTE','Samsung','SM-L705','https://www.samsung.com/us/watches/galaxy-watch-ultra-2025/buy/',{'case_size_mm':47,'connectivity':'LTE / Wi-Fi','case_material':'titanium'},'2025',649.99,'USD','US','current listed price','https://www.samsung.com/us/watches/galaxy-watch-ultra-2025/buy/')
add('Smartwatches','Smartwatch','Google Pixel Watch 4 41mm Bluetooth/Wi-Fi','Google','Pixel Watch 4 41mm','https://store.google.com/us/product/pixel_watch_4_specs?hl=en-US',{'case_size_mm':41,'display':'AMOLED LTPO','peak_brightness_nits':3000,'battery_mah':325,'storage_gb':32,'OS':'Wear OS 6'},'2025',399.99,'USD','US','current listed price','https://store.google.com/us/config/pixel_watch_4?hl=en-US')
add('Smartwatches','LTE smartwatch','Google Pixel Watch 4 45mm LTE','Google','Pixel Watch 4 45mm LTE','https://store.google.com/us/product/pixel_watch_4_specs?hl=en-US',{'case_size_mm':45,'connectivity':'LTE','display':'AMOLED LTPO','battery_mah':455,'storage_gb':32},'2025',449.99,'USD','US','current listed price','https://store.google.com/us/config/pixel_watch_4?hl=en-US')
add('Smartwatches','GPS running smartwatch','Garmin Forerunner 970','Garmin','010-02969-01','https://www.garmin.com/en-US/p/1462801/',{'display':'AMOLED','materials':'titanium bezel','GPS':'multiband','LED_flashlight':True},'2025')
add('Smartwatches','GPS running smartwatch','Garmin Forerunner 570','Garmin','Forerunner 570','https://www.garmin.com/en-US/p/1464001/',{'display':'AMOLED','GPS':'multiband'},'2025')
add('Smartwatches','Multisport smartwatch','Garmin fēnix 8 Pro 47mm AMOLED','Garmin','fēnix 8 Pro 47mm','https://www.garmin.com/en-US/p/1701921/',{'display':'AMOLED','satellite_communication':'inReach','GPS':'multiband'},'2025')
add('Smartwatches','GPS multisport smartwatch','Garmin Venu 4','Garmin','Venu 4','https://www.garmin.com/en-US/p/1613801/',{'type':'GPS health and fitness smartwatch'},'2025')
add('Smartwatches','Rugged GPS smartwatch','Garmin Instinct 3 AMOLED 45mm','Garmin','Instinct 3 AMOLED 45mm','https://www.garmin.com/en-US/p/1316397/',{'display':'AMOLED','case_size_mm':45,'GPS':'multiband'},'2025')
add('Smartwatches','GPS smartwatch','Garmin vívoactive 6','Garmin','vívoactive 6','https://www.garmin.com/en-US/p/1555457/',{'type':'GPS health and fitness smartwatch'},'2025')
add('Smartwatches','Fitness smartwatch','Garmin Lily 2 Active','Garmin','Lily 2 Active','https://www.garmin.com/en-US/p/1196650/',{'built_in_gps':True,'display':'colour touchscreen'},'2024')
add('Smartwatches','Multisport smartwatch','HUAWEI WATCH 5','Huawei','WATCH 5','https://consumer.huawei.com/en/wearables/watch-5/',{'type':'smartwatch','health_sensor':'X-TAP'},'2025')
add('Smartwatches','Fitness smartwatch','HUAWEI WATCH FIT 4 Pro','Huawei','WATCH FIT 4 Pro','https://consumer.huawei.com/en/wearables/watch-fit4-pro/',{'display':'AMOLED','case_material':'aluminium alloy'},'2025')
add('Smartwatches','GPS smartwatch','HUAWEI WATCH GT 5 Pro 46mm','Huawei','WATCH GT 5 Pro 46mm','https://consumer.huawei.com/en/wearables/watch-gt5-pro/',{'case_size_mm':46,'battery_life_days_typical':9,'water_resistance':'IP69K'},'2024')
add('Smartwatches','GPS smartwatch','OnePlus Watch 3 43mm','OnePlus','Watch 3 43mm','https://www.oneplus.com/us/oneplus-watch-3-43mm',{'case_size_mm':43,'OS':'Wear OS','sports_modes':100},'2025')
add('Smartwatches','Smartwatch','OnePlus Watch 4','OnePlus','Watch 4','https://www.oneplus.com/global/oneplus-watch-4',{'battery_life_days_smart_mode':5,'type':'smartwatch'},'2026')
add('Smartwatches','GPS smartwatch','Amazfit Balance 2','Amazfit','Balance 2','https://us.amazfit.com/products/balance-2',{'display_inches':1.5,'display_resolution':'480x480','water_resistance_atm':10,'battery_life_days':21},'2025',299.99,'USD','US','current listed price','https://us.amazfit.com/pages/fitness-health-tracking')
add('Smartwatches','Rugged GPS smartwatch','Amazfit T-Rex 3 Pro 48mm','Amazfit','T-Rex 3 Pro 48mm','https://us.amazfit.com/products/t-rex-3-pro',{'display_inches':1.5,'display':'AMOLED','battery_life_days':25,'water_resistance_atm':10,'bezel':'Grade 5 titanium'},'2025',399.99,'USD','US','current listed price','https://us.amazfit.com/products/t-rex-3-pro')
add('Smartwatches','GPS smartwatch','Amazfit Active 2 Round','Amazfit','Active 2 Round','https://us.amazfit.com/products/active-2-round',{'type':'GPS smartwatch','water_resistance_atm':5},'2025',99.99,'USD','US','current listed price','https://us.amazfit.com/pages/fitness-health-tracking')
add('Smartwatches','GPS smartwatch','Amazfit Bip 6','Amazfit','Bip 6','https://us.amazfit.com/products/bip-6',{'display_inches':1.97,'display':'AMOLED','water_resistance_atm':5},'2025',79.99,'USD','US','current listed price','https://us.amazfit.com/pages/fitness-health-tracking')
add('Smartwatches','GPS smartwatch','Xiaomi Watch S4','Xiaomi','Watch S4','https://www.mi.com/global/product/xiaomi-watch-s4/',{'type':'GPS smartwatch'},'2024')
add('Smartwatches','Smartwatch','CMF Watch 3 Pro','CMF by Nothing','Watch 3 Pro','https://cmf.tech/pages/watch-3-pro',{'display':'AMOLED','GPS':'dual-band'},'2025')

# Activity bands.
add('Fitness Bands','Fitness tracker band','Google Fitbit Charge 6','Google Fitbit','Charge 6','https://store.google.com/us/product/fitbit_charge_6_specs?hl=en-US',{'battery_life_days':7,'water_resistance_m':50,'built_in_gps':True,'exercise_modes':40},'2023',159.95,'USD','US','current listed price','https://store.google.com/us/product/fitbit_charge_6?hl=en-US')
add('Fitness Bands','Fitness tracker band','HUAWEI Band 10','Huawei','Band 10','https://consumer.huawei.com/uk/wearables/band10/',{'workout_modes':100,'battery_life_days_aod':3},'2025')
add('Fitness Bands','Fitness tracker band','Xiaomi Smart Band 10','Xiaomi','Smart Band 10','https://www.mi.com/global/product/xiaomi-smart-band-10/',{'type':'fitness band'},'2025')
add('Fitness Bands','Fitness tracker band','Samsung Galaxy Fit3','Samsung','Galaxy Fit3','https://www.samsung.com/us/mobile/wearables/galaxy-fit3/',{'display':'AMOLED','type':'fitness band'},'2024')
add('Fitness Bands','Screenless fitness band','Amazfit Helio Strap','Amazfit','Helio Strap','https://us.amazfit.com/products/helio-strap',{'type':'screenless activity and recovery tracker'},'2025')

# Smart rings.
add('Smart Rings','Health tracking ring','Oura Ring 4','Oura','Ring 4','https://ouraring.com/store/rings/oura-ring-4',{'battery_life_days':[5,8],'weight_g':[3.3,5.2],'sensor_type':'inward-facing sensor array'},'2024')
add('Smart Rings','Health tracking ring','Samsung Galaxy Ring','Samsung','Galaxy Ring','https://www.samsung.com/us/rings/galaxy-ring/',{'connectivity':'Bluetooth','form_factor':'titanium smart ring'},'2024')
add('Smart Rings','Health tracking ring','Ultrahuman Ring AIR','Ultrahuman','Ring AIR','https://www.ultrahuman.com/ring/buy/',{'connectivity':'Bluetooth Low Energy','platforms':['iOS','Android']},'2023')
add('Smart Rings','Health tracking ring','RingConn Gen 2','RingConn','Gen 2','https://ringconn.com/products/ringconn-gen-2',{'type':'sleep and health tracking ring'},'2024')
add('Smart Rings','Health tracking ring','RingConn Gen 2 Air','RingConn','Gen 2 Air','https://ringconn.com/products/ringconn-gen-2-air',{'type':'sleep and health tracking ring'},'2025')
add('Smart Rings','Health tracking ring','Amazfit Helio Ring','Amazfit','Helio Ring','https://us.amazfit.com/collections/helio-collection/products/amazfit-helio-ring',{'type':'health and recovery tracking ring'},'2024')
add('Wearable Accessories','charging case','Oura Ring 4 Charging Case','Oura','Ring 4 charging case','https://ouraring.com/store/accessories/oura-ring-4-charger/oura-ring-4-charging-case',{'compatibility':'Oura Ring 4','charges':5},'2024')

# Smart glasses / display glasses.
add('Smart Glasses','AI smart glasses','Ray-Ban Meta Gen 2','Ray-Ban / Meta','Ray-Ban Meta Gen 2','https://www.meta.com/smart-glasses/',{'camera':'12MP ultra-wide','video':'3K','connectivity':'Wi-Fi / Bluetooth'},'2025',notes='Official Meta smart-glasses range; storefront presents style and market variants.')
add('Smart Glasses','AI smart glasses','Oakley Meta HSTN','Oakley / Meta','HSTN','https://www.oakley.com/en-us/category/oakley-meta',{'type':'AI camera and audio glasses'},'2025')
add('Smart Glasses','AI smart glasses','Oakley Meta Vanguard','Oakley / Meta','Vanguard','https://www.oakley.com/en-us/category/oakley-meta',{'type':'sport AI camera and audio glasses'},'2025')
add('Smart Glasses','AR display glasses','XREAL One','XREAL','One','https://us.shop.xreal.com/products/xreal-one',{'display':'micro-OLED','virtual_screen_inches':147,'refresh_rate_hz':120},'2024')
add('Smart Glasses','AR display glasses','XREAL One Pro','XREAL','One Pro','https://www.xreal.com/one-pro',{'display':'micro-OLED','refresh_rate_hz':120},'2025')
add('Smart Glasses','AR display glasses','Vuzix Z100 Smart Glasses','Vuzix','Z100','https://www.vuzix.com/products/z100-smart-glasses',{'type':'monocular waveguide smart glasses'},'2024')
add('Smart Glasses','Display smart glasses','Even Realities G1','Even Realities','G1','https://www.evenrealities.com/g1',{'type':'display smart glasses'},'2024')
add('Smart Glasses','AI smart glasses','Amazon Echo Frames (3rd Gen)','Amazon','Echo Frames 3rd Gen','https://www.amazon.com/echo-frames/',{'type':'audio smart glasses'},'2023',notes='Amazon storefront availability is region-dependent; verify current model/stock before import.')

# Bluetooth and GPS tracking products.
add('Tracking Devices','Bluetooth item tracker','Samsung Galaxy SmartTag2','Samsung','EI-T5600','https://www.samsung.com/us/mobile/mobile-accessories/phones/galaxy-smarttag2-black-ei-t5600bbegus/',{'connectivity':'Bluetooth LE / UWB','battery_replaceable':True},'2023')
add('Tracking Devices','Bluetooth item tracker','Chipolo POP','Chipolo','POP','https://chipolo.net/en/products/chipolo-pop',{'sound_db':120,'bluetooth_range_m':90,'water_resistance':'IP55','battery':'CR2032 replaceable','battery_life_years':1},'2025',29,'USD','US','current listed price','https://chipolo.net/en-us/pages/chipolo-collection')
add('Tracking Devices','Bluetooth item tracker','Chipolo LOOP','Chipolo','LOOP','https://chipolo.net/en/products/chipolo-loop',{'bluetooth_range_m':120,'water_resistance':'IP67','charging':'USB-C'},'2025')
add('Tracking Devices','Bluetooth wallet tracker','Chipolo CARD','Chipolo','CARD','https://chipolo.net/en/products/chipolo-card',{'bluetooth_range_m':120,'water_resistance':'IP67','charging':'Qi wireless'},'2025')
add('Tracking Devices','Bluetooth item tracker','Tile Pro (2024)','Tile','Pro 2024','https://www.tile.com/product/black-pro',{'type':'Bluetooth item tracker','replaceable_battery':True},'2024')
add('Tracking Devices','Bluetooth item tracker','Tile Mate (2024)','Tile','Mate 2024','https://www.tile.com/product/black-mate',{'type':'Bluetooth item tracker'},'2024')
add('Tracking Devices','Bluetooth item tracker','Pebblebee Clip 5','Pebblebee','Clip 5','https://pebblebee.com/products/clip-5',{'network_compatibility':['Apple Find My','Google Find Hub'],'charging':'USB-C rechargeable'},'2025')
add('Tracking Devices','Bluetooth wallet tracker','Pebblebee Card 5','Pebblebee','Card 5','https://pebblebee.com/products/card-5',{'network_compatibility':['Apple Find My','Google Find Hub'],'form_factor':'rechargeable wallet card'},'2025')
add('Tracking Devices','Bluetooth item tracker','Motorola Moto Tag 2','Motorola','Moto Tag 2','https://www.motorola.com/us/moto-tag-2/p',{'connectivity':'Bluetooth / UWB'},'2026')
add('Tracking Devices','Satellite GPS communicator / tracker','Garmin inReach Messenger Plus','Garmin','inReach Messenger Plus','https://www.garmin.com/en-US/p/890109/',{'connectivity':'Iridium satellite','features':['two-way messaging','SOS','location sharing']},'2024')
add('Tracking Devices','Satellite GPS tracker','SPOT X 2-Way Satellite Messenger','SPOT','SPOT X','https://www.findmespot.com/en-us/products-services/spot-x',{'connectivity':'Globalstar satellite','features':['two-way messaging','SOS','GPS tracking']},'2023')

# Wearable accessories (compatible bands, chargers and docks).
accessories=[
('Apple','49mm Titanium Milanese Loop','Apple Watch Ultra band','https://www.apple.com/shop/watch/bands/','watch band'),
('Apple','46mm Sport Band','Apple Watch band','https://www.apple.com/shop/watch/bands/','watch band'),
('Samsung','Galaxy Watch8 Sport Band','Galaxy Watch8 band','https://www.samsung.com/us/mobile/mobile-accessories/bands/','watch band'),
('Samsung','Galaxy Watch8 Trail Band','Galaxy Watch8 trail band','https://www.samsung.com/us/mobile/mobile-accessories/bands/','watch band'),
('Garmin','Lily 2 Bands 14mm','Lily 2 quick-release band','https://www.garmin.com/en-US/p/993337/pn/010-13302-10/','replacement watch band'),
('Google','Pixel Watch 4 Active Sport Band','Pixel Watch 4 band','https://store.google.com/category/watches_bands','replacement watch band'),
('Google','Pixel Watch 4 Quick Charge Dock','Pixel Watch 4 dock','https://store.google.com/category/watches_accessories','charging dock'),
('Oura','Oura Ring 4 Charging Dock','Ring 4 charger','https://ouraring.com/store/accessories/oura-ring-4-charger/oura-ring-4-charger','charging dock'),
('Samsung','Galaxy Ring Charging Case','Galaxy Ring case','https://www.samsung.com/us/rings/galaxy-ring/','charging case'),
('Fitbit','Charge 6 Woven Band','Charge 6 band','https://store.google.com/category/fitbit_accessories','replacement fitness band'),
('Amazfit','T-Rex 3 Pro Strap 22mm','T-Rex 3 Pro Strap','https://us.amazfit.com/products/t-rex-3-pro','replacement watch band'),
]
for b,n,m,u,t in accessories:add('Wearable Accessories',t,n,b,m,u,{'compatibility':m.split()[0]+' series'},notes='Official accessory category/product listing; verify model, lug/connector size and regional SKU before purchase.')

# Deduplicate by manufacturer and model and explicitly flag gaps.
unique=[];seen=set()
for r in rows:
 k=(r['brand'].lower(),r['model'].lower())
 if k in seen:continue
 seen.add(k);unique.append(r)
rows=unique
for r in rows:
 missing=[]
 if not r['release_year']:missing.append('release year not verified')
 if not r['official_price']:missing.append('official listed price not captured')
 if not r['image_url']:missing.append('official image URL not captured')
 if r['specifications_json']=='{}':missing.append('detailed specifications not captured')
 if missing:r['notes']=(r['notes'].rstrip(' .;')+'; ' if r['notes'] else '')+'Missing/unverified fields: '+', '.join(missing)+'.'
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
print('L records',len(rows),'brands',len(set(r['brand'] for r in rows)),'subtypes',dict(sorted(Counter(r['subcategory'] for r in rows).items())))
print('Missing year',sum(not r['release_year'] for r in rows),'price',sum(not r['official_price'] for r in rows),'image',sum(not r['image_url'] for r in rows),'specs',sum(r['specifications_json']=='{}' for r in rows),'duplicates',len(rows)-len(seen))
