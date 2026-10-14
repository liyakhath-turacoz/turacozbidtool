import csv,json,os
from collections import Counter
ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'P-power-backup-batteries-electrical-equipment.csv');TODAY='2026-10-13'
data=[]
def add(sub,typ,name,brand,model,url,spec=None,year='',price='',currency='',market='',price_type='',source_note=''):
 gaps=[]
 if not year:gaps.append('Manufacturer source does not state release year; age needs review.')
 if not price:gaps.append('Official price not captured from source.')
 gaps.append('No official image URL captured.')
 if source_note:gaps.append(source_note)
 data.append(dict(category_code='P',department='Power Backup, Batteries & Electrical Equipment',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=f'{name}; normalized specifications contain only manufacturer-published details captured from the linked source.',specifications_json=json.dumps(spec or {},separators=(',',':'),ensure_ascii=False),image_url='',product_url=url,release_date='',release_date_precision='year' if year else '',release_year=str(year) if year else '',official_price=str(price) if price else '',price_currency=currency,price_type=price_type,price_market=market,price_source_url=url if price else '',product_source_url=url,source_attribution='Official manufacturer product page, catalogue, newsroom, or support source',collected_on=TODAY,verification_status='official_source_linked',notes=' '.join(gaps)))

# UPS, inverter and backup devices. Series pages are retained as sources if the
# manufacturer exposes SKU variants there; exact models remain separate rows.
ups='https://www.cyberpower.com/global/en/product/series/pfc_sinewave_gen._2'
for model,va,w,price in [('CP850PFCLCDa',850,510,''),('CP1000PFCLCDa',1000,600,''),('CP1500PFCLCDa',1500,1000,''),('CP1350PFCLCD',1350,810,''),('CP1500AVRLCD3',1500,900,''),('CP1500PFCLCD',1500,1000,'')]:
 add('Power Backup','Line-interactive UPS',f'CyberPower {model} PFC Sinewave UPS','CyberPower',model,ups,{'capacity_va':va,'output_w':w,'topology':'line-interactive','output_waveform':'pure sine wave'},2024,price,'USD' if price else '', 'US' if price else '', 'current official price' if price else '')
apc='https://www.apc.com/us/en/product-range/61888-apc-backups-pro/'
for model,va,w in [('BR1500MS2',1500,900),('BR1350MS',1350,810),('BR1000MS',1000,600),('BR1500G',1500,865),('BX1500M',1500,900),('BX1000M',1000,600)]:
 add('Power Backup','UPS battery backup',f'APC Back-UPS {model}','APC by Schneider Electric',model,apc,{'capacity_va':va,'output_w':w,'functions':'battery backup, surge protection','voltage_regulation':'model dependent'})
for model,va in [('5P1550GR',1550),('5PX1500RTG2',1500),('5PX2200RTG2',2200),('5PX3000RTG2',3000),('9PX1500RT',1500),('9PX3000RT',3000),('5P1550GR-L',1550)]:
 add('Power Backup','Enterprise UPS',f'Eaton {model} UPS','Eaton',model,'https://www.eaton.com/us/en-us/products/backup-power-ups-surge-it-power-distribution/backup-power-ups/eaton-5-series-ups-overview.html',{'capacity_va':va,'topology':'model dependent; line-interactive or online double-conversion','form_factor':'tower/rack options vary','battery_options':'lead-acid or lithium-ion varies by model'})
for model,va,w in [('GXT5-1000LVRT2UXL',1000,1000),('GXT5-1500LVRT2UXL',1500,1350),('GXT5-2000LVRT2UXL',2000,1800),('GXT5-3000LVRT2UXL',3000,2700)]:
 add('Power Backup','Online double-conversion UPS',f'Vertiv Liebert GXT5 {model}','Vertiv',model,'https://www.vertiv.com/en-us/products-catalog/critical-power/uninterruptible-power-supplies-ups/liebert-gxt5-ups-750-va-20-kva/',{'capacity_va':va,'output_w':w,'topology':'online double-conversion','form_factor':'2U rack/tower','transfer_time_ms':0})
for model,va,price in [('Zelio+ 1100',900,8699),('Zelio+ 1700',1500,8734.8),('Zelio M 1200',900,8099),('Zelio M 1300',1100,9299),('Zelio M 1600',1500,11299),('Zelio S 1150',900,8699),('Zelio S 1250',1100,9399),('Zelio S 1550',1400,12499),('Eco Volt Neo 750',650,5699),('Eco Volt Neo 1050',900,6199),('Eco Volt Neo 1250',1100,7099),('Eco Volt Neo 1650',1500,9999),('Eco Watt Neo 700',600,5099),('Eco Watt Neo 900',800,5699),('Eco Watt Neo 1650',1500,8799),('Power Sine M 900',700,5799),('Power Sine M 1100',900,6599),('EVO S 1050',900,6899),('EVO S 1250',1100,7999),('EVO D 1250',1100,7299)]:
 wave='pure sine wave' if any(x in model.lower() for x in ['zelio','eco volt','power sine','evo s']) else 'square wave'
 add('Power Backup','Home inverter / home UPS',f'Luminous {model} Home Inverter','Luminous',model,'https://www.luminousindia.com/home-inverters/all-products',{'capacity_va':va,'technology':wave,'battery_supported':'12V battery; exact supported type varies by model','warranty_months':36},'',price,'INR','India','current official price','Current product listing does not state model launch date; treat release year as unknown.')
microtek_ups='https://www.microtek.in/product/critical-power-backup-solution/online-ups/listing?product_series=24'
for model,sku,kva,dc,price in [('MAX+ 6KVA 1PH:1PH 192V','899-601-6001',6,192,71500),('MAX+ 10KVA 1PH:1PH 192V','899-601-1002',10,192,101990),('MAX+ 1KVA 1PH:1PH 36V-IB','899-711-1001',1,36,25490),('MAX+ 1KVA 1PH:1PH 36V','899-601-1001',1,36,22590),('MAX+ 2KVA 1PH:1PH 72V-IB','899-711-2001',2,72,39590),('MAX+ 2KVA 1PH:1PH 72V','899-601-2001',2,72,32490),('MAX+ 3KVA 1PH:1PH 72V-IB','899-711-3001',3,72,44500),('MAX+ 3KVA ISO Tx','899-621-3001',3,72,47500),('MAX+ 3KVA 1PH:1PH 72V','899-601-3001',3,72,36450),('MAX+ 2KVA ISO Tx','899-621-2001',2,72,40850)]:
 add('Power Backup','Online UPS',f'Microtek {model} Online UPS','Microtek',model,microtek_ups,{'capacity_kva':kva,'dc_bus_v':dc,'topology':'online UPS','battery_configuration':'model-specific'},'',price,'INR','India','current official price','Listing page gives price and manufacturer SKU; product release year is not stated.')
 data[-1]['manufacturer_part_number']=sku

# Voltage regulation and surge-protection devices. Do not use discontinued Line-R AVR SKUs.
for brand,model,name,url,spec in [
 ('Schneider Electric','Acti9 iPRF1','Acti9 iPRF1 Type 1 surge protection device','https://www.se.com/in/en/product-subcategory/1615-acti-9-surge-protection-devices-spds/',{'protection_type':'Type 1 SPD'}),
 ('Schneider Electric','Acti9 PRD1','Acti9 PRD1 Type 1+2 surge protection device','https://www.se.com/in/en/product-subcategory/1615-acti-9-surge-protection-devices-spds/',{'protection_type':'Type 1+2 SPD'}),
 ('Schneider Electric','Acti9 iPRD','Acti9 iPRD Type 2 surge protection device','https://www.se.com/in/en/product-subcategory/1615-acti-9-surge-protection-devices-spds/',{'protection_type':'Type 2 SPD'}),
 ('Microtek','EM 4150+','Microtek Smart EM 4150+ 1.5 Ton AC Stabilizer','https://www.microtek.in/product/voltage-stabilizers/ac-stabilizers/listing/15-ton-ac-stabilizer-smart-em-4150?product_id=86&title=15-ton-ac-stabilizer-smart-em-4150',{'capacity':'AC up to 1.5 ton','input_range_v':'150-280','output_range_v':'150-280','display':'digital','warranty_years':3}),
 ('Microtek','Pearl EM 5170+','Microtek Pearl EM 5170+ 2 Ton AC Stabilizer','https://www.microtek.in/product/voltage-stabilizers/ac-stabilizers/listing/20-ton-ac-stabilizer-pearl-em-5170?category=&product_id=103&title=automatic-voltage-stabilizer-em-5170',{'capacity':'AC up to 2 ton','input_range_v':'170-270','display':'LED'}),
 ('Microtek','Smart EMR 4013','Microtek Smart EMR 4013 Refrigerator Stabilizer','https://www.microtek.in/product/voltage-stabilizers/refrigeratordeep-freezer-stabilizers/listing/automatic-voltage-stabilizer-smart-emr-4013-130v-295v',{'capacity_kva':0.5,'input_range_v':'130-295','display':'digital'}),
 ('Microtek','EML 8090','Microtek Automatic Voltage Stabilizer EML 8090','https://www.microtek.in/product/voltage-stabilizers/mainline-stabilizers-for-mains/listing/automatic-voltage-stabilizer-eml-8090?category=&product_id=1358&title=automatic-voltage-stabilizer-eml-8090',{'input_range_v':'100-290','output_range_v':'100-290','display':'digital','mount':'wall/floor','weight_kg':34.8}),
 ('APC by Schneider Electric','P11VT3','SurgeArrest Performance 11-Outlet Surge Protector','https://www.se.com/us/en/product-range/61876-surgearrest-performance-surge-protectors/',{'outlets':11,'protection_type':'point-of-use surge protector'}),
 ('APC by Schneider Electric','P8U2','SurgeArrest 8-Outlet Surge Protector with USB','https://www.se.com/us/en/product-range/61875-surgearrest-home-surge-protectors/',{'outlets':8,'usb_charging':True,'protection_type':'surge protector'}),
 ('Belkin','BV112230','Belkin 12-Outlet Surge Protector with 8 ft Cord','https://www.belkin.com/support-article/?articleNum=317736',{'outlets':12,'cord_length_ft':8,'protection_type':'surge protector'}),
 ('Eaton','TLP1208TEL','Protect It! 12-Outlet Surge Protector','https://tripplite.eaton.com/products/surge-protectors~24',{'outlets':12,'protection_type':'surge protection'}),
 ('Eaton','TLP1008TEL','Protect It! 10-Outlet Surge Protector','https://tripplite.eaton.com/products/surge-protectors~24',{'outlets':10,'protection_type':'surge protection'}),
 ('CyberPower','CSP600WSURC2','6-Outlet Surge Protector Wall Tap','https://www.cyberpowersystems.com/products/surge/',{'outlets':6,'protection_type':'surge protector'}),
 ('CyberPower','P705G','7-Outlet Surge Protector','https://www.cyberpowersystems.com/products/surge/',{'outlets':7,'protection_type':'surge protector'})]:
 p={'EM 4150+':4800,'Pearl EM 5170+':2570,'Smart EMR 4013':2350,'EML 8090':19900}.get(model,'')
 add('Voltage Protection','Voltage regulator / surge protection',name,brand,model,url,spec,'',p,'INR' if p else '','India' if p else '', 'current official price' if p else '',source_note='Release year is not stated by the official source; check current sale status and region before import.')

# Batteries: only named rechargeable, inverter, and power-station replacement batteries.
for model,name,spec,url in [
 ('IT500','Exide Home InvaTubular IT500',{'capacity_ah':150,'cycle_life':'1200 cycles at 80% DOD','warranty_months':66},'https://www.exidecare.com/brand/exide-home/exide-invatubular-it500-gqp12v1125'),
 ('IT750','Exide Home InvaTubular IT750',{'capacity_ah':200,'weight_kg':68,'warranty_months':66},'https://www.exidecare.com/find-exide/products/exide-inva-tubular/it750'),
 ('IT850','Exide Home InvaTubular IT850',{'capacity_ah':230,'warranty_months':66},'https://www.exidecare.com/brand/exide-home-invatubular-inverter-battery'),
 ('IT900','Exide Home InvaTubular IT900',{'capacity_ah':240,'warranty_months':66},'https://www.exidecare.com/brand/exide-home-invatubular-inverter-battery'),
 ('IT950','Exide Home InvaTubular IT950',{'capacity_ah':260,'warranty_months':66},'https://www.exidecare.com/brand/exide-home-invatubular-inverter-battery'),
 ('ILTT18060','Luminous Inverlast ILTT 18060 PRO',{'battery_type':'tubular inverter battery'},'https://www.luminousindia.com/product-listing/shop-now/inverter-battery-combo'),
 ('RC25000','Luminous RC 25000 Pro',{'battery_type':'inverter battery'},'https://www.luminousindia.com/catalogue'),
 ('AA Recharge Universal','Energizer Recharge Universal AA',{'chemistry':'NiMH','size':'AA','charge_cycles_up_to':1000},'https://energizer.com/batteries/energizer-rechargeable-batteries/'),
 ('AAA Recharge Universal','Energizer Recharge Universal AAA',{'chemistry':'NiMH','size':'AAA','charge_cycles_up_to':1000},'https://energizer.com/batteries/energizer-rechargeable-batteries/'),
 ('C Recharge Universal','Energizer Recharge Universal C',{'chemistry':'NiMH','size':'C'},'https://energizer.com/batteries/energizer-rechargeable-batteries/'),
 ('D Recharge Universal','Energizer Recharge Universal D',{'chemistry':'NiMH','size':'D'},'https://energizer.com/batteries/energizer-rechargeable-batteries/'),
 ('9V Recharge Universal','Energizer Recharge Universal 9V',{'chemistry':'NiMH','size':'9V'},'https://energizer.com/batteries/energizer-rechargeable-batteries/'),
 ('AA Ultimate Lithium','Energizer Ultimate Lithium AA',{'chemistry':'lithium primary','size':'AA'},'https://energizer.com/batteries/aa-batteries/'),
 ('AA MAX','Energizer MAX AA',{'chemistry':'alkaline','size':'AA'},'https://energizer.com/batteries/aa-batteries/'),
]:
 if len((model,name,spec,url))==4: brand='Energizer' if model not in ('IT500','IT750','IT850','IT900','IT950','ILTT18060','RC25000') else ('Exide' if model.startswith('IT') else 'Luminous'); add('Batteries','Rechargeable / inverter battery',name,brand,model,url,spec)

# Charger products: consumer battery chargers, device charging stations, UPS charging and power-station ecosystem units.
chargers=[
('Anker Prime Charger 250W 6-Port','A2345','Anker','https://www.anker.com/products/a2345-anker-prime-charger-250w-6-ports-ganprime',{'max_output_w':250,'ports':6,'gan':True},2024,169.99,'USD','US'),
('Anker Prime Charger 160W 3-Port','A2687','Anker','https://release.anker.com/products/a2687-anker-prime-charger-160w-3-ports-gan',{'max_output_w':160,'ports':3,'gan':True},2026,'' ,'',''),
('Anker Charger 200W 6-Port','A2683','Anker','https://www.anker.com/uk/products/a2683-anker-prime-charger-200w-6-ports-gan',{'max_output_w':200,'ports':6,'gan':True},2024,'' ,'',''),
('Anker Prime Charging Station 240W 8-in-1','A91B2','Anker','https://www.anker.com/products/a91b2-anker-prime-charging-station-240w-8-in-1',{'max_output_w':240,'ports':8,'ac_outlets':2,'usb_c_ports':4,'usb_a_ports':2},2024,129.99,'USD','US'),
('Energizer Recharge 1-Hour Charger','CH1HR','Energizer','https://energizer.com/batteries/battery-charger/',{'battery_chemistry':'NiMH','supported_sizes':'AA, AAA','charge_time_hours':1},'' ,'' ,'',''),
('Energizer Recharge Pro Charger','CHPRO','Energizer','https://energizer.com/batteries/battery-charger/',{'battery_chemistry':'NiMH','supported_sizes':'AA, AAA'},'' ,'' ,'',''),
('Energizer Recharge Universal Charger','CHVCM4','Energizer','https://energizer.com/canada/product/power/battery-chargers/universal-battery-charger/',{'battery_chemistry':'NiMH','supported_sizes':'AA, AAA, C, D, 9V','positions':4},'' ,'' ,'',''),
('Energizer Recharge Value Charger','CHVCM','Energizer','https://energizer.com/batteries/battery-charger/',{'battery_chemistry':'NiMH','supported_sizes':'AA, AAA'},'' ,'' ,'',''),
('EcoFlow Alternator Charger 800W','800W Alternator Charger','EcoFlow','https://us.ecoflow.com/products/800w-alternator-charger',{'max_charging_w':800,'input':'vehicle alternator','app_control':True},2024,919,'USD','US'),
('EcoFlow Alternator Charger 500W','500W Alternator Charger','EcoFlow','https://www.ecoflow.com/us/on-the-road-power-solution',{'max_charging_w':500,'input':'vehicle alternator'},2024,'' ,'',''),
('Jackery DC-DC Alternator Charger','DC-DC Charger','Jackery','https://www.jackery.com/products/dc-dc-alternator-charger',{'charger_type':'vehicle alternator to power station'},2024,269,'USD','US'),
('BLUETTI Charger 1 Alternator Charger','Charger 1','BLUETTI','https://support.bluettipower.com/en-ca/products/charger-1',{'charger_type':'vehicle alternator charger'},2024,'' ,'',''),
('Victron Blue Smart IP22 Charger 12/30','BPC123047006','Victron Energy','https://www.victronenergy.com/chargers/blue-smart-ip22-charger',{'output_voltage_v':12,'output_current_a':30,'battery_profiles':'lead-acid, lithium'},'' ,'' ,'',''),
('NOCO GENIUS10 Smart Battery Charger','GENIUS10','NOCO','https://no.co/genius10',{'output_voltage_v':6,'max_output_current_a':10,'battery_chemistry':'lead-acid, lithium'},'' ,'' ,'',''),
('NOCO GENIUS5 Smart Battery Charger','GENIUS5','NOCO','https://no.co/genius5',{'output_voltage_v':6,'max_output_current_a':5,'battery_chemistry':'lead-acid, lithium'},'' ,'' ,'',''),
('NOCO GENIUS2 Smart Battery Charger','GENIUS2','NOCO','https://no.co/genius2',{'max_output_current_a':2,'battery_chemistry':'lead-acid, lithium'},'' ,'' ,'',''),
('NOCO GENIUS1 Smart Battery Charger','GENIUS1','NOCO','https://no.co/genius1',{'max_output_current_a':1,'battery_chemistry':'lead-acid, lithium'},'' ,'' ,'',''),
('CTEK MXS 5.0 Battery Charger','MXS 5.0','CTEK','https://ctek.com/en-us/collections/battery-chargers-12v-24v',{'output_voltage_v':12,'max_output_current_a':5,'battery_chemistry':'lead-acid'},'' ,'' ,'',''),
('CTEK CS ONE Gen 2 Smart Battery Charger','CS ONE Gen 2 NA','CTEK','https://ctek.com/en-us/collections/battery-chargers-12v-24v',{'charger_type':'adaptive smart battery charger','voltage':'12V','wifi':True},2025,314.99,'USD','US'),
('Battery Tender 4 AMP Selectable Charger','022-0209-WAL','Battery Tender','https://www.batterytender.com/products/walmart-4-amp-battery-charger',{'max_output_current_a':4,'voltage':'6V/12V selectable','battery_chemistry':'lead-acid, lithium'},'' ,104.95,'USD','US'),
('Battery Tender Plus 12V 1.25A','021-0128','Battery Tender','https://www.batterytender.com/products/battery-tender-plus',{'output_voltage_v':12,'max_output_current_a':1.25},'' ,'' ,'',''),
]
for n,m,b,u,s,y,p,c,market in chargers:add('Charging Equipment','Battery charger / charging station',n,b,m,u,s,y,p,c,market,'current official price' if p else '')

# Portable power stations, battery systems and solar-ready backup units.
stations=[
('EcoFlow DELTA 3','DELTA 3','EcoFlow','https://us.ecoflow.com/products/delta-3-portable-power-station',{'capacity_wh':1024,'ac_output_w':1800,'surge_w':3600,'solar_input_w':500,'battery_chemistry':'LFP','outlets':13},2024),
('EcoFlow DELTA 3 Plus','DELTA 3 Plus','EcoFlow','https://us.ecoflow.com/products/delta-3-portable-power-station',{'capacity_wh':1024,'ac_output_w':1800,'solar_input_w':1000,'battery_chemistry':'LFP','expandable_capacity_kwh':'up to 5'},2024),
('EcoFlow DELTA 3 Classic','DELTA 3 Classic','EcoFlow','https://www.ecoflow.com/us/delta-3-classic-portable-power-station/specs',{'capacity_wh':1024,'ac_output_w':1800,'surge_w':3600,'solar_input_w':500,'battery_chemistry':'LFP'},2025),
('EcoFlow DELTA 3 Ultra','DELTA 3 Ultra','EcoFlow','https://us.ecoflow.com/collections/olddelta-series/products/ecoflow-delta-3-ultra-portable-power-station-3072wh',{'capacity_wh':3072,'ac_output_w':3600,'surge_w':7200},2025),
('EcoFlow RIVER 3','RIVER 3','EcoFlow','https://www.ecoflow.com/us/river-3-series-portable-power-station',{'capacity_wh':245,'ac_output_w':300,'battery_chemistry':'LFP','ups_transfer_ms':10},2024),
('EcoFlow RIVER 3 Plus','RIVER 3 Plus','EcoFlow','https://www.ecoflow.com/us/river-3-series-portable-power-station',{'capacity_wh':286,'ac_output_w':600,'battery_chemistry':'LFP','expandable':True},2024),
('Jackery Explorer 1000 v2','JE-1000C','Jackery','https://www.jackery.com/products/jackery-explorer-1000-v2',{'capacity_wh':1070,'ac_output_w':1500,'surge_w':3000,'battery_chemistry':'LiFePO4','cycle_life':4000,'usb_c_w':100},2024,519,'USD','US'),
('Jackery Explorer 2000 v2','JE-2000B','Jackery','https://www.jackery.com/collections/portable-power-stations',{'capacity_wh':2042,'ac_output_w':2200,'battery_chemistry':'LiFePO4'},2024),
('Jackery HomePower 1000 v2','HomePower 1000 v2','Jackery','https://www.jackery.com/collections/portable-power-stations',{'capacity_wh':1070,'ac_output_w':1500,'battery_chemistry':'LiFePO4'},2025),
('BLUETTI AC70','AC70','BLUETTI','https://www.bluettipower.com/products/ac70',{'capacity_wh':768,'ac_output_w':1000,'surge_w':1500,'battery_chemistry':'LiFePO4','cycle_life':3000,'solar_input_w':500},2023),
('BLUETTI AC180','AC180','BLUETTI','https://www.bluettipower.com/products/ac180',{'capacity_wh':1152,'ac_output_w':1800,'battery_chemistry':'LiFePO4','solar_input_w':500},2023),
('BLUETTI Elite 100 V2','Elite 100 V2','BLUETTI','https://www.bluettipower.com/products/elite-100-v2-portable-power-station/',{'capacity_wh':1024,'ac_output_w':1800,'battery_chemistry':'LiFePO4'},2025),
('BLUETTI Elite 200 V2','Elite 200 V2','BLUETTI','https://www.bluettipower.com/products/elite-200-v2-portable-power-station',{'capacity_wh':2073.6,'ac_output_w':2600,'battery_chemistry':'LiFePO4'},2024),
('BLUETTI Elite 400','Elite 400','BLUETTI','https://www.bluettipower.com/products/elite-400-portable-power-station',{'capacity_wh':3840,'ac_output_w':2600,'battery_chemistry':'LiFePO4'},2025),
('Anker SOLIX C1000','A1761','Anker SOLIX','https://service.anker.com/article-description/Introduction-to-Anker-SOLIX-C1000',{'capacity_wh':1056,'ac_output_w':1800,'solar_input_w':600,'battery_chemistry':'LiFePO4','ups_transfer_ms':20,'ports':11},2023),
('Anker SOLIX F2000 PowerHouse','A1780','Anker SOLIX','https://beta.au.anker.com/uk/products/a1780',{'capacity_wh':2048,'ac_output_w':2300,'battery_chemistry':'LiFePO4','expandable':True},2023),
('Anker SOLIX F3800','A1790','Anker SOLIX','https://www.anker.com/eu-en/a1790-pps',{'capacity_wh':3840,'ac_output_w':6000,'battery_chemistry':'LiFePO4','expandable':True},2023),
('Zendure SuperBase V4600','ZDSBV4600','Zendure','https://us.zendure.com/products/zendure-superbase-v',{'capacity_wh':4608,'ac_output_w':3800,'surge_w':5000,'battery_chemistry':'LiFePO4','ups_transfer_ms':0,'expandable_kwh':23},2023),
('Zendure SuperBase V6400','ZDSBV6400','Zendure','https://us.zendure.com/products/zendure-superbase-v',{'capacity_wh':6438,'ac_output_w':3800,'surge_w':5000,'battery_chemistry':'semi-solid state','expandable_kwh':64,'ups_transfer_ms':0},2023),
('Goal Zero Yeti 700','Yeti 700','Goal Zero','https://goalzero.com/pages/yeti-power-stations-6th-gen-family-lifepo4',{'capacity_wh':677,'battery_chemistry':'LiFePO4','cycle_life':4000,'ip_rating':'IPX4'},2025),
('Goal Zero Yeti 1000','Yeti 1000','Goal Zero','https://goalzero.com/pages/yeti-power-stations-6th-gen-family-lifepo4',{'capacity_wh':997,'ac_output_w':2000,'surge_w':3600,'solar_input_w':900,'battery_chemistry':'LiFePO4'},2025,1199.95,'USD','US'),
('Goal Zero Yeti 1500','Yeti 1500','Goal Zero','https://goalzero.com/pages/yeti-power-stations-6th-gen-family-lifepo4',{'capacity_wh':1505,'ac_output_w':2000,'surge_w':3600,'solar_input_w':900,'battery_chemistry':'LiFePO4'},2025,1499.95,'USD','US'),
('Goal Zero Yeti PRO 4000','Yeti PRO 4000','Goal Zero','https://goalzero.com/pages/yeti-power-stations-6th-gen-family-lifepo4',{'capacity_wh':3993.6,'ac_output_w':3600,'surge_w':7200,'solar_input_w':3000,'battery_chemistry':'LFP'},2025,3999.95,'USD','US'),
('EcoFlow DELTA Pro 3','DELTA Pro 3','EcoFlow','https://www.ecoflow.com/us/delta-pro-3-portable-power-station',{'capacity_wh':4096,'ac_output_w':4000,'battery_chemistry':'LFP','expandable_kwh':12},2024),
]
for n,m,b,u,s,y,*p in stations:
 price=p[0] if p else ''; cur=p[1] if p else ''; market=p[2] if p else ''
 add('Portable Power','Portable power station / expandable battery',n,b,m,u,s,y,price,cur,market,'current official price' if price else '')

# Electrical test and measurement instruments. Model-level specifications only.
meters=[
('Fluke 117 Electrician Multimeter','117','Fluke','https://www.fluke.com/en-us/product/electrical-testing/digital-multimeters/fluke-117',{'measurement':'AC/DC voltage, current, resistance, continuity, frequency, capacitance','max_voltage_v':600,'max_current_a':10,'safety_rating':'CAT III 600 V','true_rms':True},2024,304.99,'USD','US'),
('Fluke 115 Field Technicians Multimeter','115','Fluke','https://www.fluke.com/en-us/product/electrical-testing/digital-multimeters/fluke-115',{'measurement':'AC/DC voltage, current, resistance, continuity, frequency, capacitance','max_voltage_v':600,'max_current_a':10,'true_rms':True},''),
('Fluke 177 True-RMS Multimeter','177','Fluke','https://www.fluke.com/en-us/product/electrical-testing/digital-multimeters/fluke-177',{'max_voltage_v':1000,'max_current_a':10,'safety_rating':'CAT III 1000 V / CAT IV 600 V','true_rms':True},''),
('Fluke 179 True-RMS Multimeter','179','Fluke','https://www.fluke.com/en-us/product/electrical-testing/digital-multimeters/fluke-179',{'max_voltage_v':1000,'max_current_a':10,'temperature_measurement':True,'true_rms':True},''),
('Fluke 289 Logging Multimeter','289','Fluke','https://www.fluke.com/en-us/product/electrical-testing/digital-multimeters/fluke-289',{'data_logging':True,'trend_capture':True,'max_voltage_v':1000,'true_rms':True},''),
('Fluke 376 FC Clamp Meter with iFlex','376 FC','Fluke','https://www.fluke.com/en-us/product/electrical-testing/clamp-meters/fluke-376-fc',{'max_current_a':2500,'max_voltage_v':1000,'bluetooth':True,'true_rms':True},2024,699.99,'USD','US'),
('Fluke 323 Clamp Meter','323','Fluke','https://www.fluke.com/en-us/product/electrical-testing/clamp-meters/fluke-323',{'max_current_a':400,'max_voltage_v':600,'true_rms':True},''),
('Fluke T6-1000 Electrical Tester','T6-1000','Fluke','https://www.fluke.com/en-us/product/electrical-testing/electrical-testers/fluke-t6-1000',{'max_voltage_v':1000,'measurement':'voltage, current, frequency','field_sense':True},''),
('Fluke 117/323 Kit','117/323 KIT','Fluke','https://www.fluke.com/en-us/product/electrical-testing/digital-multimeters/fluke-117',{'kit_contents':'117 multimeter, 323 clamp meter'},''),
('Klein MM460S Smart Digital Multimeter','MM460S','Klein Tools','https://www.kleintools.com/catalog/test-measurement/multimeters',{'max_voltage_v':600,'measurement':'AC/DC voltage, current, resistance','auto_ranging':True},2025),
('Klein CL460S Smart Clamp Meter','CL460S','Klein Tools','https://www.kleintools.com/catalog/test-measurement',{'max_current_a':400,'measurement':'AC/DC current, voltage','auto_ranging':True},2025),
('Klein CL900 Clamp Meter','CL900','Klein Tools','https://www.kleintools.com/catalog/clamp-meters/digital-clamp-meter-ac-auto-range-trms-low-impedance-loz-2000-amp',{'max_current_a':2000,'true_rms':True,'low_impedance':True},''),
('Klein ET350 Circuit Breaker Finder','ET350','Klein Tools','https://www.kleintools.com/catalog/test-measurement',{'functions':'circuit breaker finding and electrical testing'},2025),
('Klein MM450 Slim Digital Multimeter','MM450','Klein Tools','https://www.kleintools.com/catalog/test-measurement/multimeters',{'max_voltage_v':600,'true_rms':True,'auto_ranging':True},2025),
('Megger AVO850 True-RMS Multimeter','AVO850','Megger','https://www.megger.com/en-us/type/low-voltage-installation-testing/multimeters-and-clampmeters',{'measurement':'AC/DC V/A, resistance, continuity','true_rms':True,'display':'colour'},''),
('Megger AVO840 Multimeter','AVO840','Megger','https://www.megger.com/en-us/type/low-voltage-installation-testing/multimeters-and-clampmeters',{'max_voltage_v':1000,'low_impedance':True,'true_rms':True},''),
('Megger AVO215 Multimeter','AVO215','Megger','https://www.megger.com/en-us/type/low-voltage-installation-testing/multimeters-and-clampmeters',{'true_rms':True,'safety_rating':'CAT III'},''),
('Megger DCM1500 Clamp Meter','DCM1500','Megger','https://www.megger.com/en-us/type/low-voltage-installation-testing/multimeters-and-clampmeters',{'max_current_a':1500,'true_rms':True,'clamp_meter':True},''),
('Megger MET1000 Electrical Tester','MET1000','Megger','https://www.megger.com/en-us/products/met1000',{'max_voltage_v':1000,'max_current_a':200,'safety_rating':'CAT IV 600 V / CAT III 1000 V','true_rms':True,'ip_rating':'IP65'},''),
('Fluke 1AC II VoltAlert','1AC II','Fluke','https://www.fluke.com/en-us/product/electrical-testing/basic-testers/fluke-1ac-ii',{'tester_type':'non-contact voltage detector'},''),
('Klein NCVT-4IR Non-Contact Voltage Tester','NCVT-4IR','Klein Tools','https://www.kleintools.com/catalog/electrical-testers/non-contact-voltage-tester-pen-infrared-thermometer-12-1000v-ac',{'tester_type':'non-contact voltage tester with IR thermometer','voltage_ac_v':'12-1000','ip_rating':'IP54'},''),
('Klein ET45 Voltage Tester','ET45','Klein Tools','https://www.kleintools.com/catalog/electrical-testers/acdc-voltage-tester',{'tester_type':'voltage tester','voltage_ac_v':'24, 48, 120, 240','voltage_dc_v':'32, 64, 160, 330'},''),
('Fluke 1507 Insulation Resistance Tester','1507','Fluke','https://www.fluke.com/en-us/product/electrical-testing/insulation-testers/fluke-1507',{'tester_type':'insulation resistance tester','test_voltage_v':'50, 100, 250, 500, 1000'},''),
('Fluke 1664 FC Installation Tester','1664 FC','Fluke','https://www.fluke.com/en-us/product/electrical-testing/installation-testers/fluke-1664-fc',{'tester_type':'multifunction installation tester','bluetooth':True},''),
('Megger MIT420/2 Insulation Tester','MIT420/2','Megger','https://www.megger.com/en/products/mit420-2',{'tester_type':'insulation resistance tester'},''),
]
for row in meters:
 n,m,b,u,s,*tail=row; y=tail[0] if tail else ''; price=tail[1] if len(tail)>1 else ''; cur=tail[2] if len(tail)>2 else ''; market=tail[3] if len(tail)>3 else ''
 add('Electrical Test Equipment','Multimeter / clamp meter / electrical tester',n,b,m,u,s,y,price,cur,market,'current official price' if price else '')

# Power accessories: outlet strips, extension devices and manufacturer-compatible expansion packs.
accessories=[
('APC Essential SurgeArrest 5 Outlet','P5B','APC by Schneider Electric','https://www.se.com/in/en/product-subcategory/8012-power-strips/',{'outlets':5,'protection_type':'surge protector'}),
('APC Essential SurgeArrest 6 Outlet','P6B','APC by Schneider Electric','https://www.se.com/in/en/product-subcategory/8012-power-strips/',{'outlets':6,'protection_type':'surge protector'}),
('APC Performance SurgeArrest 8 Outlet','P8GT','APC by Schneider Electric','https://www.se.com/in/en/product-range/61876-surgearrest-performance-surge-protectors/',{'outlets':8,'protection_type':'surge protector'}),
('APC Rack PDU Basic 1U','AP9562','APC by Schneider Electric','https://www.apc.com/us/en/product-range/61878-rack-pdu/',{'form_factor':'1U rack','outlets':'model-dependent'}),
('Eaton Tripp Lite 12-Outlet Power Strip','TLP1208TEL','Eaton','https://tripplite.eaton.com/products/power-strips~23',{'outlets':12,'cord_length_ft':8}),
('Eaton Tripp Lite 6-Outlet Power Strip','TLP606','Eaton','https://tripplite.eaton.com/products/power-strips~23',{'outlets':6}),
('Eaton Tripp Lite 8-Outlet Rack PDU','PDUMH20','Eaton','https://tripplite.eaton.com/products/rack-pdus~25',{'outlets':8,'form_factor':'rack PDU'}),
('Belkin 12-Outlet Surge Protector with USB Charging','BV112050-06','Belkin','https://www.belkin.com/p/12-outlet-surge-protector-with-usb-charging/BV112050-06.html',{'outlets':12,'surge_protection_joules':3940,'usb_charging':True}),
('Anker USB Power Strip 10-in-1, 20W','A91F2','Anker','https://www.anker.com/ca/products/a91f2',{'outlets':10,'ac_outlets':6,'usb_c_ports':2,'usb_a_ports':2,'usb_output_w':20}),
('EcoFlow DELTA 3 Extra Battery','DELTA 3 EB','EcoFlow','https://www.ecoflow.com/us/delta-3-classic-portable-power-station/specs',{'capacity_wh':1024,'compatible_device':'DELTA 3 family','battery_chemistry':'LFP'}),
('Jackery SolarSaga 100W Solar Panel','SolarSaga 100','Jackery','https://www.jackery.com/collections/solar-panels',{'max_output_w':100,'accessory_type':'portable solar panel'}),
('Jackery SolarSaga 200W Solar Panel','SolarSaga 200','Jackery','https://www.jackery.com/products/solarsaga-200w-solar-panel',{'max_output_w':200,'accessory_type':'portable solar panel'}),
('BLUETTI B80 Expansion Battery','B80','BLUETTI','https://www.bluettipower.com/products/b80',{'capacity_wh':806,'compatible_device':'AC60/AC70 family'}),
('BLUETTI B300K Expansion Battery','B300K','BLUETTI','https://www.bluettipower.com/products/apex-300-b300k-expansion-battery',{'capacity_wh':2764.8,'battery_chemistry':'LiFePO4','accessory_type':'expansion battery'}),
('Anker SOLIX BP1000 Expansion Battery','BP1000','Anker SOLIX','https://beta.au.anker.com/uk/products/a17611a1-85',{'capacity_wh':1056,'compatible_device':'SOLIX C1000','battery_chemistry':'LFP'}),
('Anker SOLIX BP3800 Expansion Battery','BP3800','Anker SOLIX','https://beta.au.anker.com/uk/products/a1790111-85',{'capacity_wh':3840,'compatible_device':'SOLIX F3800','battery_chemistry':'LFP'}),
('Vertiv Liebert GXT5 External Battery Cabinet','VEBCLI-48VRT1U','Vertiv','https://www.vertiv.com/en-us/products-catalog/critical-power/uninterruptible-power-supplies-ups/liebert-gxt5-ups-750-va-20-kva/',{'accessory_type':'UPS external battery cabinet','compatible_device':'GXT5 lithium-ion UPS'}),
('Eaton 5PX G2 External Battery Module','EBM 5PX G2','Eaton','https://www.eaton.com/us/en-us/products/backup-power-ups-surge-it-power-distribution/backup-power-ups/eaton-5-series-ups-overview.html',{'accessory_type':'UPS external battery module','compatible_device':'5PX G2 UPS'}),
('Eaton 9PX Lithium-ion External Battery Module','EBM 9PX Li-ion','Eaton','https://www.eaton.com/us/en-us/products/backup-power-ups-surge-it-power-distribution/backup-power-ups/lithium-ion-batteries-/eaton-9-series-lithium-ion-batteries.html',{'accessory_type':'UPS external battery module','compatible_device':'9PX lithium-ion UPS'}),
('CyberPower CP1500PFCLCD Replacement Battery Cartridge','RB1290X2','CyberPower','https://www.cyberpowersystems.com/products/replacement-batteries/',{'accessory_type':'UPS replacement battery cartridge','compatible_device':'selected CyberPower UPS'}),
('APC Replacement Battery Cartridge RBC55','RBC55','APC by Schneider Electric','https://www.apc.com/us/en/product-range/61922-backups-accessories/',{'accessory_type':'UPS replacement battery cartridge'}),
]
for n,m,b,u,s in accessories:add('Power Accessories','Power strip / extension / compatible backup accessory',n,b,m,u,s)

# Keep release dates only where a manufacturer source explicitly supplies a
# launch date. The EcoFlow launch announcement gives an exact May 15, 2024 date.
for r in data:
 if r['brand']=='EcoFlow' and r['model']=='800W Alternator Charger':
  r['release_date']='2024-05-15';r['release_date_precision']='day';r['release_year']='2024'
  r['product_source_url']='https://www.ecoflow.com/us/blog/ecoflow-offers-more-on-the-road-power-for-adventurers-with-launch-of-new-alternator-charger'
  r['source_attribution']='Official EcoFlow launch announcement; product details link retained separately'
  r['notes'] += ' Product release date is from the official launch announcement; specifications and current price link to the official product page.'
 else:
  r['release_date']='';r['release_date_precision']='';r['release_year']=''
  if 'release year' not in r['notes'].lower():r['notes'] += ' Official source does not provide a verifiable product release date/year; age needs review.'

# Remove duplicate manufacturer/model pairs before writing, keeping first sourced listing.
seen=set();unique=[]
for r in data:
 k=(r['brand'].casefold(),r['model'].casefold())
 if k in seen:continue
 seen.add(k);unique.append(r)
data=unique
fields=list(data[0])
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
print('P products',len(data),'brands',len(set(r['brand'] for r in data)),'subtypes',dict(Counter(r['subcategory'] for r in data)))
