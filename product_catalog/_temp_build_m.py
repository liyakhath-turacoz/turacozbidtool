import csv, json, os
from datetime import date
ROOT=os.path.dirname(__file__)
OUT=os.path.join(ROOT,'M-smart-home-security-surveillance.csv')
TODAY='2026-10-13'
catalogs={
 'Aqara':'https://www.aqara.com/us/product',
 'Philips Hue':'https://www.philips-hue.com/en-us/products/all-products',
 'TP-Link Tapo':'https://www.tp-link.com/us/smart-home/',
 'Ring':'https://ring.com/collections/all-products',
 'Google Nest':'https://store.google.com/category/nest_cameras',
 'Reolink':'https://reolink.com/us/product/',
 'Amazon':'https://www.aboutamazon.com/news/devices/amazon-new-echo-devices-alexa-plus',
 'Eve Systems':'https://www.evehome.com/en',
 'Yale':'https://shopyalehome.com/collections/smart-locks',
 'Arlo':'https://www.arlo.com/en-us/cameras',
 'Sonos':'https://www.sonos.com/en-us/shop',
 'Apple':'https://www.apple.com/homepod/',
}
# Rows use the manufacturer's product page where known, otherwise the official
# catalogue page that lists the model. Unknown publication dates/prices stay blank.
data=[]
def add(sub,typ,name,brand,model,url,spec=None,year='',price='',currency='',market='',price_type='',description=''):
 source=url or catalogs.get(brand,'')
 if not source: source=catalogs['Aqara']
 spec=spec or {}
 note=[]
 if not year: note.append('Official product listing found; release year not stated by the source and needs age review.')
 if not price: note.append('Official listed price not captured.')
 note.append('No official image URL captured.')
 data.append(dict(category_code='M',department='Smart Home, Security & Surveillance',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=description or f'{name}; normalized product details include only manufacturer-published information captured from the linked source.',specifications_json=json.dumps(spec,separators=(',',':'),ensure_ascii=False),image_url='',product_url=source,release_date='',release_date_precision='',release_year=str(year) if year else '',official_price=str(price) if price else '',price_currency=currency,price_type=price_type,price_market=market,price_source_url=source if price else '',product_source_url=source,source_attribution='Official manufacturer product page or catalogue',collected_on=TODAY,verification_status='official_source_linked',notes=' '.join(note)))

# Smart home control and hubs
for n,m,url,s,y in [
 ('Hub M100','HM-G02E','https://www.aqara.com/us/product/hub-m100/','Zigbee, Thread, 2.4GHz Wi-Fi, BLE 5.2, USB-A',2025),
 ('Hub M200','HM-G03D','https://www.aqara.com/us/product/hub-m200/','Matter controller, IR control, smart home hub',2025),
 ('Hub M3','HM-G01D','https://www.aqara.com/us/product/hub-m3/','Matter controller, Thread border router, Zigbee, Wi-Fi, Ethernet',2024),
 ('Echo Hub','Echo Hub','https://www.aboutamazon.com/news/devices/amazon-echo-hub-best-features','Alexa smart home control panel, Zigbee, Matter, Thread, Bluetooth LE, Wi-Fi/Ethernet',2023),
 ('Hue Bridge Pro','Bridge Pro','https://www.philips-hue.com/en-us/p/hue-bridge-pro/','Zigbee, Matter, supports 150+ lights and 50+ accessories',2025),
 ('Tapo H500 Smart HomeBase','H500','https://www.tp-link.com/us/smart-home/smart-hub/tapo-h500/','Smart home hub, local storage, camera/doorbell connections',2025),
 ('Tapo H200 Smart Hub','H200','https://www.tp-link.com/us/smart-home/smart-hub/tapo-h200/','Smart hub, microSD storage, sub-GHz accessories',2024),
]: add('Smart Home Control','Smart home hub/controller',n,'Aqara' if n.startswith('Hub') else 'Philips Hue' if n.startswith('Hue') else 'TP-Link Tapo' if n.startswith('Tapo') else 'Amazon',m,url,{'published_features':s},y)

# Smart lighting, selected recent models and current catalog SKUs
for n,m,url,s,y,p in [
 ('Hue Play screen sync','Play screen sync','https://www.philips-hue.com/en-us/p/hue-play-screen-sync/','App-based screen color sync',2025,119.99),
 ('Hue Play HDMI sync box 8K','Play HDMI sync box 8K','https://www.philips-hue.com/en-us/p/hue-play-hdmi-sync-box-8k/','HDMI 2.1, 8K 60Hz, 4K 120Hz',2025,349.99),
 ('Hue Tento round ceiling panel small','Tento small','https://www.philips-hue.com/en-us/products/all-products','Tunable white and color, up to 2250 lm',2025,119.99),
 ('Hue Tento round ceiling panel medium','Tento medium','https://www.philips-hue.com/en-us/products/all-products','Tunable white and color, up to 2250 lm',2025,149.99),
 ('Hue Tento round ceiling panel extra large','Tento XL','https://www.philips-hue.com/en-us/products/all-products','Tunable white and color, up to 2250 lm',2025,199.99),
 ('Hue Festavia curtain lights 250 LEDs','Festavia curtain 250','https://www.philips-hue.com/en-us/products/all-products','White and color gradients, dynamic effects',2025,249.99),
 ('Hue Festavia icicle lights 250 LEDs','Festavia icicle 250','https://www.philips-hue.com/en-us/products/all-products','White and color gradients, weather resistant',2025,249.99),
 ('Hue OmniGlow outdoor strip light 10 ft','OmniGlow 10 ft','https://www.philips-hue.com/en-us/products/all-products','Outdoor smart strip light',2025,229.99),
 ('Hue Festavia Globe Outdoor String Lights 22 ft','Festavia globe 22 ft','https://www.philips-hue.com/en-us/products/all-products','Outdoor smart string lights, white and color gradient',2025,179.99),
 ('Tapo L535E Smart Wi-Fi Light Bulb','L535E','https://www.tp-link.com/us/home-networking/smart-bulb/tapo-l535e/v3%20%281-pack%29/','1100 lm, multicolor, Matter, 2500-6500K, Wi-Fi',2024,''),
 ('Tapo L930-5 Smart Wi-Fi Light Strip','L930-5','https://www.tp-link.com/us/home-networking/smart-lighting/tapo-l930-5/','RGBIC, Wi-Fi, app and voice control',2024,''),
 ('Aqara LED Strip T1','LED Strip T1','https://www.aqara.com/us/product/led-strip-t1/','RGB CCT, Zigbee, Matter bridge compatibility',2024,''),
 ('Nanoleaf Blocks Starter Kit','Blocks','https://nanoleaf.me/en-US/products/nanoleaf-blocks/','Modular smart lighting panels',2024,''),
]: add('Smart Lighting','Smart bulb / LED strip / smart lamp',n,'Philips Hue' if n.startswith('Hue') else 'TP-Link Tapo' if n.startswith('Tapo') else 'Aqara' if n.startswith('Aqara') else 'Nanoleaf',m,url,{'published_features':s},y,p,'USD' if p else '', 'US' if p else '', 'current listed price' if p else '')

# Smart switches and plugs
for n,m,b,url,s,y in [
 ('Tapo P125M Mini Smart Wi-Fi Plug','P125M','TP-Link Tapo','https://www.tp-link.com/us/home-networking/smart-plug/tapo-p125m/','Matter, energy monitoring, Wi-Fi',2024),
 ('Tapo P110M Mini Smart Wi-Fi Plug','P110M','TP-Link Tapo','https://www.tp-link.com/us/home-networking/smart-plug/tapo-p110m/','Matter, energy monitoring',2024),
 ('Tapo S505 Smart Wi-Fi Light Switch','S505','TP-Link Tapo','https://www.tp-link.com/us/home-networking/smart-switch/tapo-s505/','Matter, Wi-Fi, single pole',2024),
 ('Aqara Light Switch H2 EU','Light Switch H2 EU','Aqara','https://www.aqara.com/en/product/light-switch-h2-eu/','Matter over Thread, Zigbee',2025),
 ('Aqara Power Plug H2 EU','Power Plug H2 EU','Aqara','https://www.aqara.com/en/product/power-plug-h2-eu/','Matter over Thread, Zigbee, energy monitoring',2025),
]: add('Smart Switches & Plugs','Smart switch / connected plug',n,b,m,url,{'published_features':s},y)

# Smart locks
for n,m,b,url,s,y,p in [
 ('Aqara Smart Lock U400','U400','Aqara','https://www.aqara.com/us/product/smart-lock-u400/','Ultra Wideband, Apple home key, Matter over Thread',2025,''),
 ('Aqara Smart Lock U300','U300','Aqara','https://www.aqara.com/us/product/smart-lock-u300/','Fingerprint, keypad, Matter over Thread',2024,''),
 ('Aqara Smart Lock U200','U200','Aqara','https://www.aqara.com/us/product/smart-lock-u200/','Retrofit lock, fingerprint/keypad accessory, Matter over Thread',2024,''),
 ('Aqara Smart Lock U50','U50','Aqara','https://www.aqara.com/us/product/smart-lock-u50/','Deadbolt, Apple home key, Matter over Thread',2024,''),
 ('Yale Linus Smart Lock L2','Linus L2','Yale','https://shopyalehome.com/products/yale-linus-smart-lock-l2','Bluetooth, Wi-Fi bridge compatible, keyless access',2024,''),
 ('Ring Smart Lock','Ring Smart Lock','Ring','https://ring.com/products/smart-lock','Fingerprint, PIN, app and Alexa unlock; Amazon Sidewalk',2026,249.99),
]: add('Smart Locks','Electronic smart door lock',n,b,m,url,{'published_features':s},y,p,'USD' if p else '', 'US' if p else '', 'current listed price' if p else '')

# Video doorbells / intercoms
for n,m,b,url,s,y,p in [
 ('Aqara Doorbell Camera Hub G410','G410','Aqara','https://www.aqara.com/en/product/doorbell-camera-hub-g410/','2K, 175° field of view, mmWave, Matter controller, Zigbee hub',2025,''),
 ('Aqara Doorbell Camera G400 Wired','G400','Aqara','https://www.aqara.com/en/product/doorbell-camera-g400/','Wired video doorbell, smart home integration',2026,''),
 ('TP-Link Tapo D225 Smart Wi-Fi Video Doorbell','D225','TP-Link Tapo','https://www.tp-link.com/us/smart-home/smart-doorbell/tapo-d225/','2K, 180° field of view, battery or hardwire, 512GB local storage',2025,''),
 ('Google Nest Doorbell (wired, 3rd gen)','Nest Doorbell wired 3rd gen','Google Nest','https://store.google.com/product/nest_doorbell_wired_3rd_gen?hl=en-US','2K HDR, wired, 166° diagonal field of view',2026,''),
 ('Philips Hue Wired Video Doorbell','Wired video doorbell','Philips Hue','https://www.philips-hue.com/en-us/products/all-products','2K video, two-way audio, Hue lighting integration',2025,169.99),
 ('Ring Battery Doorbell Pro','Battery Doorbell Pro','Ring','https://ring.com/products/battery-doorbell-pro','2K video doorbell, battery power, two-way audio',2024,149.99),
]: add('Video Doorbells','Video doorbell / intercom',n,b,m,url,{'published_features':s},y,p,'USD' if p else '', 'US' if p else '', 'current listed price' if p else '')

# Security cameras
for n,m,b,url,s,y,p in [
 ('Ring Indoor Cam 4K Plug-In','Indoor Cam 4K','Ring','https://partners.ring.com/products/indoor-cam-4k','4K, Auto HDR, 10x enhanced zoom, plug-in',2026,99.99),
 ('Ring Indoor Cam 4K PoE','Indoor Cam 4K PoE','Ring','https://partners.ring.com/products/indoor-cam-4k','4K, Auto HDR, Power over Ethernet',2026,149.98),
 ('Ring Outdoor Cam 4K Plus','Outdoor Cam 4K Plus','Ring','https://partners.ring.com/products/outdoor-cam-4k-plus','Retinal 4K, battery/plug-in/wired/solar/PoE options',2026,149.99),
 ('Ring Spotlight Cam 4K Plus','Spotlight Cam 4K Plus','Ring','https://ring.com/collections/all-products','4K outdoor camera with spotlight',2026,199.99),
 ('Ring Floodlight Cam 4K Plus','Floodlight Cam 4K Plus','Ring','https://ring.com/collections/all-products','4K floodlight camera',2026,219.99),
 ('TP-Link Tapo C425 Wire-Free Security Camera','C425','TP-Link Tapo','https://www.tp-link.com/us/home-networking/cloud-camera/tapo-c425/','2K, wire-free, color night vision, IP66',2024,''),
 ('TP-Link Tapo C530WS Outdoor Pan/Tilt Camera','C530WS','TP-Link Tapo','https://www.tp-link.com/us/home-networking/cloud-camera/tapo-c530ws/','3K 5MP, pan/tilt, IP66, color night vision',2025,''),
 ('TP-Link Tapo C545D Dual-Lens Camera','C545D','TP-Link Tapo','https://www.tp-link.com/us/home-networking/cloud-camera/tapo-c545d/','Dual 2K lenses, outdoor pan/tilt',2025,''),
 ('Aqara Camera Hub G5 Pro Wi-Fi','G5 Pro Wi-Fi','Aqara','https://www.aqara.com/en/product/camera-hub-g5-pro/','Outdoor camera, Matter controller, Zigbee hub',2025,''),
 ('Aqara Camera Hub G5 Pro PoE','G5 Pro PoE','Aqara','https://www.aqara.com/en/product/camera-hub-g5-pro-poe/','PoE outdoor camera, Matter controller, Zigbee hub',2025,''),
 ('Aqara Camera G100','G100','Aqara','https://www.aqara.com/en/product/camera-g100/','Indoor/outdoor smart camera',2025,''),
 ('Aqara Camera Hub G350','G350','Aqara','https://www.aqara.com/en/product/camera-hub-g350/','Camera hub and smart home controller',2026,''),
 ('Google Nest Cam Indoor (wired, 3rd gen)','Nest Cam Indoor wired 3rd gen','Google Nest','https://store.google.com/category/nest_cameras','Indoor security camera, wired',2026,''),
 ('Google Nest Cam Outdoor (wired, 2nd gen)','Nest Cam Outdoor wired 2nd gen','Google Nest','https://store.google.com/category/nest_cameras','Outdoor security camera, wired',2026,''),
 ('Arlo Essential 3 2K Security Camera','Essential 3 2K','Arlo','https://www.arlo.com/en-us/cameras','2K home security camera',2025,''),
 ('Reolink TrackMix WiFi','TrackMix WiFi','Reolink','https://reolink.com/us/product/trackmix-wifi/','Dual-lens auto-tracking Wi-Fi camera',2024,''),
]: add('Security Cameras','Wi-Fi/IP security camera',n,b,m,url,{'published_features':s},y,p,'USD' if p else '', 'US' if p else '', 'current listed price' if p else '')

# Surveillance recorders and kits
for n,m,b,url,s,y in [
 ('Reolink RLN12W Wi-Fi NVR','RLN12W','Reolink','https://reolink.com/us/product/rln12w/','Wi-Fi NVR for Reolink cameras',2024),
 ('Reolink Home Hub Pro','Home Hub Pro','Reolink','https://reolink.com/us/product/home-hub-pro/','Local video storage and camera management hub',2025),
 ('TP-Link VIGI NVR1008H-8MP','NVR1008H-8MP','TP-Link VIGI','https://www.tp-link.com/us/business-networking/all-vigi-surveillance/','8-channel PoE+ NVR, 4K HDMI, 8 PoE ports',2025),
 ('TP-Link VIGI NVR2016H-16MP','NVR2016H-16MP','TP-Link VIGI','https://www.tp-link.com/us/business-networking/all-vigi-surveillance/','16-channel PoE+ NVR, 4K HDMI',2025),
 ('TP-Link VIGI NVR4064H','NVR4064H','TP-Link VIGI','https://www.tp-link.com/us/business-networking/all-vigi-surveillance/','64-channel network video recorder',2025),
]: add('Surveillance Systems','NVR / CCTV recording system',n,b,m,url,{'published_features':s},y)

# Alarm systems, modern sensors/accessory ecosystems
for n,m,b,url,s,y in [
 ('Aqara Presence Multi-Sensor FP300','FP300','Aqara','https://www.aqara.com/en/product/presence-multi-sensor-fp300/','Multi-protocol presence sensor with multiple sensing capabilities',2025),
 ('Aqara Presence Sensor FP2','FP2','Aqara','https://www.aqara.com/us/product/presence-sensor-fp2/','mmWave presence sensing, zone detection',2023),
 ('Aqara Door and Window Sensor P2','P2','Aqara','https://www.aqara.com/us/product/door-and-window-sensor-p2/','Matter over Thread contact sensor',2023),
 ('Aqara Motion and Light Sensor P2','P2 Motion and Light Sensor','Aqara','https://www.aqara.com/en/product/motion-and-light-sensor-p2/','Matter over Thread, motion and illuminance sensing',2024),
 ('Ring Alarm Glass Break Sensor','Glass Break Sensor','Ring','https://ring.com/products/glass-break-sensor','Glass-break detection, Ring Alarm ecosystem',2024),
 ('Philips Hue Secure Contact Sensor','Secure Contact Sensor','Philips Hue','https://www.philips-hue.com/en-us/p/hue-secure-contact-sensor/','Door/window contact sensor, Hue security automation',2023),
]: add('Alarm Systems','Motion / contact / alarm sensor',n,b,m,url,{'published_features':s},y)

# Smart speakers / displays
for n,m,b,url,s,y,p in [
 ('Amazon Echo Show 11 (2025 release)','Echo Show 11','Amazon','https://www.aboutamazon.com/news/devices/amazon-new-echo-devices-alexa-plus','11-inch smart display with Alexa',2025,''),
 ('Amazon Echo Show 8 (2025 release)','Echo Show 8','Amazon','https://www.aboutamazon.com/news/devices/amazon-new-echo-devices-alexa-plus','8-inch smart display with Alexa',2025,''),
 ('Amazon Echo Dot Max (2025 release)','Echo Dot Max','Amazon','https://www.aboutamazon.com/news/devices/amazon-new-echo-devices-alexa-plus','Smart speaker with Alexa',2025,''),
 ('Amazon Echo Studio (2025 release)','Echo Studio','Amazon','https://www.aboutamazon.com/news/devices/amazon-new-echo-devices-alexa-plus','Smart speaker with spatial audio and Alexa',2025,''),
 ('Google Home Speaker','Google Home Speaker','Google','https://store.google.com/us/product/google_home_speaker?hl=en-US','Smart speaker, Gemini, Thread border router, Matter hub, Wi-Fi 6',2026,99.99),
 ('Apple HomePod (2nd generation)','HomePod 2nd Gen','Apple','https://www.apple.com/homepod/','Smart speaker with Siri and Matter home hub support',2023,''),
]: add('Smart Speakers','Voice assistant smart speaker/display',n,b,m,url,{'published_features':s},y,p,'USD' if p else '', 'US' if p else '', 'current listed price' if p else '')

fields=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes']
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
print('M rows',len(data),'subtypes',len(set(r['subcategory'] for r in data)),'brands',len(set(r['brand'] for r in data)),'duplicate keys',len(data)-len(set((r['brand'].lower(),r['model'].lower()) for r in data)))
from collections import Counter
print(dict(Counter(r['subcategory'] for r in data)))
