import csv,json,os
from datetime import date
from collections import Counter
ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'K-gaming-virtual-reality.csv');TODAY=date(2026,10,13).isoformat()
FIELDS=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes']
rows=[]
def add(sub,typ,name,brand,model,url,specs=None,year='',price='',currency='',market='',price_type='',price_url='',notes=''):
 rows.append(dict(category_code='K',department='Gaming & Virtual Reality',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=f'{name}; product details are limited to manufacturer-published information linked here.',specifications_json=json.dumps(specs or {},ensure_ascii=False,separators=(',',':')),image_url='',product_url=url,release_date='',release_date_precision='',release_year=year,official_price=str(price),price_currency=currency,price_type=price_type,price_market=market,price_source_url=price_url,product_source_url=url,source_attribution='Official manufacturer/product catalogue or publisher product listing',collected_on=TODAY,verification_status='official_source_linked',notes=notes))

# Consoles and dedicated handheld gaming systems.
add('Gaming Consoles','Hybrid console','Nintendo Switch 2','Nintendo','BEE-001','https://www.nintendo.com/us/gaming-systems/switch-2/features/',{'display_inches':7.9,'display_resolution':'1920x1080','internal_storage_gb':256,'max_supported_tv_resolution':'4K','max_frame_rate_fps':120},'2025',449.99,'USD','US','MSRP','https://www.nintendo.com/us/whatsnew/nintendo-maintains-nintendo-switch-2-pricing-retail-pre-orders-to-begin-april-24-in-u-s/')
add('Gaming Consoles','Home console','PlayStation 5 Pro','Sony','CFI-7000 series','https://blog.playstation.com/2024/09/10/welcome-playstation-5-pro-the-most-visually-impressive-way-to-play-games-on-playstation/',{'ssd_storage_tb':2,'optical_drive':'sold separately'},'2024',699.99,'USD','US','announced MSRP','https://blog.playstation.com/2024/09/10/welcome-playstation-5-pro-the-most-visually-impressive-way-to-play-games-on-playstation/')
add('Gaming Consoles','Home console','Xbox Series X 2TB Galaxy Black Special Edition','Microsoft Xbox','2TB Galaxy Black','https://news.xbox.com/en-us/2024/06/09/xbox-series-x-s-new-console-options/',{'storage_tb':2,'edition':'Galaxy Black Special Edition'},'2024','','','','','',notes='Official Xbox announcement identifies edition; region price not captured.')
add('Gaming Consoles','Home console','Xbox Series X 1TB Digital Edition Robot White','Microsoft Xbox','1TB Digital Edition','https://news.xbox.com/en-us/2024/06/09/xbox-series-x-s-new-console-options/',{'storage_tb':1,'disc_drive':False,'colour':'Robot White'},'2024')
add('Gaming Consoles','Home console','Xbox Series S 1TB Robot White','Microsoft Xbox','1TB Robot White','https://news.xbox.com/en-us/2024/06/09/xbox-series-x-s-new-console-options/',{'storage_tb':1,'colour':'Robot White'},'2024')
add('Gaming Consoles','Console accessory','Nintendo Switch 2 Dock Set','Nintendo','BEE-005','https://www.nintendo.com/us/store/products/nintendo-switch-2-dock-set-123791/',{'compatibility':'Nintendo Switch 2'},'2025',124.99,'USD','US','current listed price','https://www.nintendo.com/us/store/hardware/')

add('Handheld Gaming','Windows gaming handheld','ASUS ROG Ally X (2024)','ASUS','RC72LA','https://rog.asus.com/ca-en/gaming-handhelds/rog-ally/rog-ally-x-2024/spec/',{'display_inches':7,'display_resolution':'1920x1080','refresh_rate_hz':120,'processor':'AMD Ryzen Z1 Extreme','memory_gb':24,'storage_gb':1024,'battery_wh':80,'os':'Windows 11 Home'},'2024')
add('Handheld Gaming','Windows gaming handheld','MSI Claw 8 AI+ A2VM','MSI','A2VM','https://www.msi.com/Handheld/Claw-8-AI-Plus-A2VMX/Specification',{'display_inches':8,'display_resolution':'1920x1200','refresh_rate_hz':120,'processor':'Intel Core Ultra 7 258V','memory_gb':32,'battery_wh':80,'wireless':'Wi-Fi 7, Bluetooth 5.4'},'2024')
add('Handheld Gaming','Windows gaming handheld','MSI Claw 7 AI+ A2VM','MSI','A2VM 7-inch','https://www.msi.com/news/detail/MSI-s-New-Claw-8-AI----Claw-7-AI--Handheld-with-Powerful-Performance-and-Low-Power-Consumption--Available-Now--145096',{'display_inches':7,'display_resolution':'1920x1080','refresh_rate_hz':120,'processor':'Intel Core Ultra 7 258V','memory_gb':32,'battery_wh':54.5},'2024')
add('Handheld Gaming','Windows gaming handheld','MSI Claw A8 BZ2EM','MSI','BZ2EM','https://www.msi.com/Handheld/Claw-A8-BZ2EMXXX',{'display_inches':8,'display_resolution':'1920x1200','refresh_rate_hz':120,'processor':'AMD Ryzen Z2 Extreme','memory_gb':24,'battery_wh':80,'wireless':'Wi-Fi 7, Bluetooth 5.4'},'2025',notes='Official product and specification pages; exact regional price/SKU should be checked.')
add('Handheld Gaming','Windows gaming handheld','Lenovo Legion Go S','Lenovo','Legion Go S','https://www.lenovo.com/us/en/p/handheld/legion-go-s/83l3001vus',{'type':'Windows/SteamOS handheld gaming PC'},'2025')
add('Handheld Gaming','Windows gaming handheld','Lenovo Legion Go Gen 2','Lenovo','83N10009US','https://www.lenovo.com/us/en/p/handheld/legion-go-gen-2/83n10009us',{'display_inches':8.8,'display_resolution':'1920x1200','panel':'OLED','refresh_rate_hz':144,'processor':'AMD Ryzen Z2','memory_gb':16,'storage_gb':1024},'2025',notes='Lenovo product listing; configuration can vary by regional SKU.')
add('Handheld Gaming','Windows gaming handheld','ASUS ROG Ally (2023)','ASUS','RC71L','https://rog.asus.com/gaming-handhelds/rog-ally/rog-ally-2023/',{'display_inches':7,'display_resolution':'1920x1080','refresh_rate_hz':120,'processor':'AMD Ryzen Z1 / Z1 Extreme','os':'Windows 11 Home'},'2023',notes='Retained as recent-generation catalogue reference; release age should be reviewed against the requested import window.')
add('Handheld Gaming','Handheld console','Steam Deck OLED','Valve','Steam Deck OLED','https://www.steamdeck.com/en/oled',{'display':'7.4-inch HDR OLED','refresh_rate_hz':90,'battery_wh':50,'storage_gb_options':[512,1024]},'2023',notes='Official model page; product was announced in late 2023. Age is near the requested horizon.')
add('Handheld Gaming','Handheld gaming PC','GPD WIN 4 (2025)','GPD','WIN 4 2025','https://www.gpd.hk/gpdwin42025',{'type':'sliding-screen handheld gaming PC'},'2025',notes='Official GPD model catalogue; current configuration and revision details need review.')
add('Handheld Gaming','Handheld gaming PC','AYANEO 3','AYANEO','AYANEO 3','https://ayaneo.com/product/AYANEO-3',{'display_inches':7,'resolution':'1920x1080','refresh_rate_hz':144,'processor_options':['AMD Ryzen AI 9 HX 370','AMD Ryzen 7 8840U'],'battery_wh':49},'2025',notes='Official AYANEO product page; specifications vary by screen and configuration.')
add('Handheld Gaming','Handheld gaming PC','ONEXPLAYER X1 PRO AMD Ryzen AI 9 HX 470','One-Netbook','X1 Pro HX 470','https://onexplayerstore.com/products/onexplayer-x1-pro-amd-ryzen%E2%84%A2-ai-9-hx-370-8840u-10-95-3-in-1-gaming-handheld-pc-bundle-onexgpu2',{'display_inches':10.95,'processor':'AMD Ryzen AI 9 HX 470','type':'3-in-1 handheld gaming PC'},'2026',notes='Official ONEXPLAYER storefront lists current HX 470 configuration; the product slug also references earlier HX 370/8840U variants.')

# Controllers and other console gaming accessories.
controllers=[
('Nintendo','Nintendo Switch 2 Pro Controller','BEE-008','https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/','2025',{'wireless':'Bluetooth','compatibility':'Nintendo Switch 2'}),
('Nintendo','Joy-Con 2 Pair','BEE-012','https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/','2025',{'compatibility':'Nintendo Switch 2','pair':'left and right'}),
('Nintendo','Joy-Con 2 Charging Grip','BEE-013','https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/','2025',{'compatibility':'Nintendo Switch 2','charging':'USB-C'}),
('Nintendo','Joy-Con 2 Wheel Set','BEE-014','https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/','2025',{'compatibility':'Joy-Con 2'}),
('Nintendo','Nintendo Switch 2 Camera','BEE-015','https://www.nintendo.com/us/store/products/nintendo-switch-2-camera-123682/','2025',{'interface':'USB-C','compatibility':'Nintendo Switch 2'}),
('Sony','DualSense Edge Wireless Controller','CFI-ZCP1','https://www.playstation.com/en-us/accessories/dualsense-edge-wireless-controller/','2023',{'connection':'Bluetooth / USB','features':['replaceable stick modules','rear buttons','profiles']}),
('Sony','Access Controller','CFI-ZAC1','https://www.playstation.com/en-us/accessories/access-controller/','2023',{'compatibility':'PS5','features':['customizable button mapping','multiple expansion ports']}),
('Sony','DualSense Wireless Controller - Chroma Indigo','CFI-ZCT1W','https://www.playstation.com/en-us/accessories/dualsense-wireless-controller/','2025',{'connection':'Bluetooth / USB-C'}),
('Sony','DualSense Wireless Controller - Chroma Pearl','CFI-ZCT1W','https://www.playstation.com/en-us/accessories/dualsense-wireless-controller/','2025',{'connection':'Bluetooth / USB-C'}),
('Microsoft Xbox','Xbox Wireless Controller - Sky Cipher Special Edition','QAU-00001','https://www.xbox.com/en-US/accessories/controllers/sky-cipher-special-edition','2024',{'connection':'Xbox Wireless / Bluetooth'}),
('Microsoft Xbox','Xbox Wireless Controller - Ghost Cipher Special Edition','QAU-00101','https://www.xbox.com/en-US/accessories/controllers/ghost-cipher-special-edition','2024',{'connection':'Xbox Wireless / Bluetooth'}),
('Microsoft Xbox','Xbox Elite Wireless Controller Series 2 - Core','FST-00001','https://www.xbox.com/en-US/accessories/controllers/xbox-elite-wireless-controller-series-2-core','',{'connection':'Xbox Wireless / Bluetooth','adjustable_thumbsticks':True}),
('PowerA','Advantage Wired Controller for Nintendo Switch 2','NSGP0300','https://www.powera.com/p/nintendo/nintendo-switch-2/controllers/wired/','2025',{'connection':'wired USB','compatibility':'Nintendo Switch 2'}),
('PDP','Afterglow Wave Wireless Controller for Nintendo Switch 2','PDP Afterglow Wave','https://pdp.com/collections/nintendo-switch-2','2025',{'connection':'wireless','compatibility':'Nintendo Switch 2'}),
('Turtle Beach','Stealth Ultra Wireless Controller','Stealth Ultra','https://www.turtlebeach.com/products/stealth-ultra-controller','2023',{'connection':'wireless','display':'built-in command screen'}),
('Victrix','Pro BFG Wireless Modular Controller','Pro BFG','https://pdp.com/collections/victrix','',{'connection':'wireless / wired','platforms':['PlayStation','PC']}),
('8BitDo','Ultimate 2 Wireless Controller','Ultimate 2','https://www.8bitdo.com/ultimate-2-wireless-controller/','2025',{'connection':'2.4G / Bluetooth / wired'}),
('8BitDo','Pro 2 Bluetooth Controller','Pro 2','https://www.8bitdo.com/pro2/','',{'connection':'Bluetooth / wired','platforms':['Switch','Windows','Android','macOS']}),

]
for b,n,m,u,y,sp in controllers:
 price,currency,market,ptype,purl=('','','','','')
 if b=='Nintendo':
  price_map={'Nintendo Switch 2 Pro Controller':89.99,'Joy-Con 2 Pair':99.99,'Joy-Con 2 Charging Grip':39.99,'Joy-Con 2 Wheel Set':24.99,'Nintendo Switch 2 Camera':54.99}
  if n in price_map:price=price_map[n];currency='USD';market='US';ptype='current listed price';purl='https://www.nintendo.com/us/store/hardware/'
 if b=='PowerA':price=69.99;currency='USD';market='US';ptype='current listed price';purl='https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/'
 if b=='PDP':price=64.99;currency='USD';market='US';ptype='current listed price';purl='https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/'
 add('Gaming Accessories','Controller / console accessory',n,b,m,u,sp,y,price,currency,market,ptype,purl,notes='Manufacturer catalogue source; check regional colour/SKU and current availability.')
 if b=='Nintendo':rows[-1]['release_date']='2025-06-05';rows[-1]['release_date_precision']='day'

# Gaming keyboards and mice/mousepads from official brands.
peripherals=[
('Razer','Gaming Keyboard','BlackWidow V4 75% Mechanical Gaming Keyboard','RZ03-0500','https://www.razer.com/gaming-keyboards/Razer-BlackWidow-V4-75/RZ03-05000200-R3U1',{'layout':'75%','switches':'hot-swappable mechanical'}),
('Razer','Gaming Keyboard','BlackWidow V4 Pro 75 Wireless Gaming Keyboard','BlackWidow V4 Pro 75','https://www.razer.com/gaming-keyboards/razer-blackwidow-v4-pro-75',{'layout':'75%','connection':'wireless'}),
('Razer','Gaming Keyboard','BlackWidow V4 Low-Profile Tenkeyless HyperSpeed','BlackWidow V4 LP TKL HyperSpeed','https://www.razer.com/pc/gaming-keyboards/blackwidow-line',{'layout':'tenkeyless','connection':'HyperSpeed wireless'}),
('Razer','Gaming Keyboard','BlackWidow V4 Tenkeyless HyperSpeed','BlackWidow V4 TKL HyperSpeed','https://www.razer.com/pc/gaming-keyboards/blackwidow-line',{'layout':'tenkeyless','connection':'wireless'}),
('Razer','Gaming Mouse','DeathAdder V3 HyperSpeed','RZ01-0514','https://www.razer.com/gaming-mice/razer-deathadder-v3-hyperspeed',{'sensor':'Focus X 26K','connection':'HyperSpeed wireless'}),
('Razer','Gaming Mouse','Viper V3 Pro','RZ01-0512','https://www.razer.com/gaming-mice/razer-viper-v3-pro',{'sensor':'Focus Pro 35K','connection':'wireless'}),
('Razer','Gaming Mouse','Cobra Pro Wireless Gaming Mouse','RZ01-0466','https://www.razer.com/gaming-mice/razer-cobra-pro',{'connection':'wireless','lighting':'Chroma RGB'}),
('Logitech G','Gaming Keyboard','PRO X TKL RAPID Gaming Keyboard','PRO X TKL RAPID','https://www.logitechg.com/en-us/products/gaming-keyboards/pro-x-tkl-rapid.html',{'layout':'tenkeyless','switches':'magnetic analog'}),
('Logitech G','Gaming Mouse','PRO 2 LIGHTSPEED Gaming Mouse','PRO 2 LIGHTSPEED','https://www.logitechg.com/en-us/products/gaming-mice/pro-2-lightspeed.html',{'connection':'LIGHTSPEED wireless'}),
('Logitech G','Gaming Mouse','G PRO X SUPERLIGHT 2 DEX','PRO X SUPERLIGHT 2 DEX','https://www.logitechg.com/en-us/products/gaming-mice/pro-x-superlight-2-dex.html',{'sensor':'HERO 2','connection':'LIGHTSPEED wireless'}),
('Corsair','Gaming Keyboard','K70 MAX RGB Magnetic-Mechanical Gaming Keyboard','K70 MAX','https://www.corsair.com/us/en/p/keyboards/ch-910961g-na/k70-max-magnetic-mechanical-gaming-keyboard',{'switches':'MGX magnetic-mechanical'}),
('Corsair','Gaming Mouse','M75 AIR Wireless Gaming Mouse','M75 AIR','https://www.corsair.com/us/en/p/gaming-mouse/ch-931d100-na/m75-air-wireless-gaming-mouse',{'connection':'wireless'}),
('SteelSeries','Gaming Keyboard','Apex Pro Gen 3 Gaming Keyboard','Apex Pro Gen 3','https://steelseries.com/gaming-keyboards/apex-pro-gen-3',{'switches':'OmniPoint adjustable actuation'}),
('SteelSeries','Gaming Mouse','Aerox 5 Wireless','Aerox 5 Wireless','https://steelseries.com/gaming-mice/aerox-5-wireless',{'connection':'2.4GHz / Bluetooth'}),
('HyperX','Gaming Keyboard','Alloy Rise Gaming Keyboard','Alloy Rise','https://hyperx.com/collections/gaming-keyboards/products/hyperx-alloy-rise-mechanical-gaming-keyboard/products/hyperx-alloy-rise-mechanical-gaming-keyboard',{'layout':'full size','switches':'hot-swappable'}),
('HyperX','Gaming Mouse','Pulsefire Haste 2 Pro 4K Wireless Gaming Mouse','Pulsefire Haste 2 Pro 4K','https://hyperx.com/products/hyperx-pulsefire-haste-2-pro-4k-wireless-gaming-mouse',{'connection':'wireless','polling_rate_hz':4000}),
('Logitech G','Gaming Mousepad','G840 XL Gaming Mouse Pad','G840 XL','https://www.logitechg.com/en-us/shop/p/g840-cloth-xl-gaming-mouse-pad.943-000117',{'type':'extended cloth mouse pad'}),
('Razer','Gaming Mousepad','Atlas Tempered Glass Gaming Mouse Mat','RZ02-0489','https://www.razer.com/gaming-mouse-mats/razer-atlas',{'surface':'tempered glass'}),
]
for b,typ,n,m,u,sp in peripherals:add('Gaming Peripherals',typ,n,b,m,u,sp,notes='Official brand product/catalogue page; verify region/SKU and current price before import.')

# VR and mixed-reality headsets.
vr=[
('Meta','Quest 3S','SK-1000207','https://www.meta.com/quest/quest-3s/','2024',{'storage_gb_options':[128,256],'tracking':'inside-out','controllers':'Touch Plus'},349.99),
('Meta','Quest 3','SK-1000204','https://www.meta.com/quest/quest-3/','2023',{'display':'4K+ Infinite Display','tracking':'inside-out','mixed_reality':'full-colour passthrough'},499.99),
('Sony','PlayStation VR2','CFI-ZVR1','https://www.playstation.com/en-us/ps-vr2/','2023',{'display':'OLED','resolution_per_eye':'2000x2040','refresh_rate_hz':[90,120],'tracking':'inside-out'},549.99),
('HTC VIVE','VIVE Focus Vision','99HAUM003-00','https://www.vive.com/us/product/vive-focus-vision/overview/','2024',{'type':'standalone PC VR/MR headset','display_resolution_per_eye':'2448x2448'},999),
('PICO','PICO 4 Ultra','PICO 4 Ultra','https://www.picoxr.com/global/products/pico4-ultra','2024',{'type':'standalone mixed-reality headset'},599),
('Bigscreen','Beyond 2','Beyond 2','https://www.bigscreenvr.com/','2025',{'type':'PC VR headset','display':'micro-OLED'},''),
('Apple','Apple Vision Pro (M5)','Vision Pro M5','https://www.apple.com/apple-vision-pro/','2025',{'chip':'Apple M5','type':'spatial computing headset'},3499),
]
for b,n,m,u,y,sp,price in vr:add('VR & AR Devices','VR / mixed-reality headset',n,b,m,u,sp,y,price,'USD','US','manufacturer listed price' if b in ('Meta','HTC VIVE','Apple') else 'launch/configuration price',u,notes='Price reflects the linked US manufacturer page/announcement where present; local market and bundle may differ.')

# Gaming chairs and desks. Current brand range pages may represent configurable size/material options.
furniture=[
('Secretlab','TITAN Evo Gaming Chair','TITAN Evo','https://secretlab.co/products/titan-evo-2022-series',{'sizes':['Small','Regular','XL'],'recline':'165 degrees'}),
('Razer','Iskur V2 Gaming Chair','Iskur V2','https://www.razer.com/gaming-chairs/razer-iskur-v2',{'type':'gaming chair','lumbar_support':'adaptive'}),
('Corsair','TC500 LUXE Gaming Chair','TC500 LUXE','https://www.corsair.com/us/en/p/gaming-chairs/cf-9010068-ww/tc500-luxe-gaming-chair'),
('AndaSeat','Kaiser 4 Gaming Chair','Kaiser 4','https://www.andaseat.com/products/andaseat-kaiser-4-6d-armrest-gaming-chair'),
('Secretlab','MAGNUS Pro Sit-to-Stand Metal Desk','MAGNUS Pro','https://secretlab.co/products/magnus-pro'),
('Secretlab','MAGNUS Pro XL Sit-to-Stand Metal Desk','MAGNUS Pro XL','https://secretlab.co/products/magnus-pro'),
('Razer','Fujin Pro Mesh Gaming Chair','Fujin Pro','https://www.razer.com/gaming-chairs/razer-fujin-pro'),
]
for row in furniture:
 b,n,m,u,*rest=row;sp=rest[0] if rest else {};add('Gaming Furniture & Equipment','Gaming chair or desk',n,b,m,u,sp,notes='Official manufacturer product listing; dimensions, finish options and local price depend on configuration.')

# Recent console/PC game products from official publishers or console storefronts.
games=[
('Nintendo','Donkey Kong Bananza','Nintendo Switch 2','https://www.nintendo.com/us/store/products/nintendo-switch-2-donkey-kong-bananza-121485/','2025','2025-07-17',69.99,'USD','US',{'platform':'Nintendo Switch 2','players':'1-2'}),
('Nintendo','Pokémon Legends: Z-A','Nintendo Switch 2 Edition','https://www.nintendo.com/store/products/pokemon-legends-z-a-nintendo-switch-2-edition-switch-2/','2025','2025-10-16',69.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','Mario Kart World','Nintendo Switch 2','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2025','2025-06-05',79.99,'USD','US',{'platform':'Nintendo Switch 2','players':'1-24 online'}),
('Nintendo','Metroid Prime 4: Beyond','Nintendo Switch 2 Edition','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2025','2025-12-04',69.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','Super Mario Party Jamboree + Jamboree TV','Nintendo Switch 2 Edition','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2025','2025-07-24',79.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','Pokémon Pokopia','Nintendo Switch 2','https://www.nintendo.com/us/whatsnew/nintendo-switch-2-choose-your-game-bundle-launches-this-summer/','2026','',69.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','Mario Tennis Fever','Nintendo Switch 2','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2026','2026-02-12',69.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','Yakuza Kiwami 3 & Dark Ties','Nintendo Switch 2','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2026','2026-02-12',59.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','Hollow Knight: Silksong','Nintendo Switch 2 Edition','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2025','2025-09-04',19.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','EA SPORTS FC 26','Nintendo Switch 2','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2025','2025-09-26',69.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Nintendo','Little Nightmares III','Nintendo Switch 2','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2025','2025-10-10',39.99,'USD','US',{'platform':'Nintendo Switch 2'}),
('Sony Interactive Entertainment','ASTRO BOT','PS5 Standard Edition','https://www.playstation.com/en-us/games/astro-bot/','2024','',59.99,'USD','US',{'platform':'PlayStation 5','players':1}),
('Sony Interactive Entertainment','Ghost of Yōtei','PS5','https://www.playstation.com/en-us/games/ghost-of-yotei/most-wanted/','2025','',69.99,'USD','US',{'platform':'PlayStation 5'}),
('Sony Interactive Entertainment','Death Stranding 2: On the Beach','PS5','https://www.playstation.com/en-us/games/death-stranding-2-on-the-beach/','2025','',69.99,'USD','US',{'platform':'PlayStation 5'}),
('Sony Interactive Entertainment','LEGO Horizon Adventures','PS5','https://www.playstation.com/en-us/games/lego-horizon-adventures/','2024','',59.99,'USD','US',{'platform':'PlayStation 5'}),
('Sony Interactive Entertainment','Until Dawn','PS5','https://www.playstation.com/en-us/games/until-dawn/','2024','',59.99,'USD','US',{'platform':'PlayStation 5'}),
('Microsoft Xbox','Indiana Jones and the Great Circle','Xbox Series X|S','https://www.xbox.com/en-US/games/indiana-jones-and-the-great-circle','2024','',69.99,'USD','US',{'platform':'Xbox Series X|S'}),
('Microsoft Xbox','DOOM: The Dark Ages','Xbox Series X|S','https://www.xbox.com/en-US/games/doom-the-dark-ages','2025','',69.99,'USD','US',{'platform':'Xbox Series X|S'}),
('Microsoft Xbox','Avowed','Xbox Series X|S','https://www.xbox.com/en-US/games/avowed','2025','',69.99,'USD','US',{'platform':'Xbox Series X|S'}),
('Microsoft Xbox','South of Midnight','Xbox Series X|S','https://www.xbox.com/en-US/games/south-of-midnight','2025','',39.99,'USD','US',{'platform':'Xbox Series X|S'}),
('Microsoft Xbox','Forza Motorsport','Xbox Series X|S','https://www.xbox.com/en-US/games/forza-motorsport','2023','',69.99,'USD','US',{'platform':'Xbox Series X|S'}),
('Microsoft Xbox','Senua’s Saga: Hellblade II','Xbox Series X|S','https://www.xbox.com/en-us/play/games/senuas-saga-hellblade-ii/9pmbb7nghv95','2024','',49.99,'USD','US',{'platform':'Xbox Series X|S'}),
('Microsoft Xbox','Microsoft Flight Simulator 2024','Xbox Series X|S','https://www.xbox.com/en-US/games/microsoft-flight-simulator-2024','2024','',69.99,'USD','US',{'platform':'Xbox Series X|S'}),
('Nintendo','Tales of the Shire: A The Lord of the Rings Game','Nintendo Switch 2 Edition','https://www.nintendo.com/us/store/games/nintendo-switch-2-games/','2026','2026-03-25',34.99,'USD','US',{'platform':'Nintendo Switch 2'}),
]
for pub,name,edition,url,year,rdate,price,currency,market,specs in games:
 add('Physical Games & Software','Video game software',name,pub,name+' - '+edition,url,specs,year,price,currency,market,'manufacturer / publisher listed price',url,notes=('Official publisher or platform product listing; release date recorded only when stated in the source.' if rdate else 'Official publisher or platform catalogue listing; exact release date not captured from linked source.'))
 rows[-1]['release_date']=rdate
 rows[-1]['release_date_precision']='day' if rdate else ''
 if pub in ('Sony Interactive Entertainment','Microsoft Xbox') and name!='ASTRO BOT':
  rows[-1]['official_price']='';rows[-1]['price_currency']='';rows[-1]['price_type']='';rows[-1]['price_market']='';rows[-1]['price_source_url']=''
 if pub in ('Sony Interactive Entertainment','Microsoft Xbox') and not rdate:
  rows[-1]['release_year']=''

# Deduplicate exact maker/model entries and add field-gap notes.
unique=[];seen=set()
for r in rows:
 key=(r['brand'].strip().lower(),r['model'].strip().lower())
 if key in seen:continue
 seen.add(key);unique.append(r)
rows=unique
for r in rows:
 missing=[]
 for field,label in [('release_year','release year not verified'),('official_price','official listed price not captured'),('image_url','official image URL not captured')]:
  if not r[field]:missing.append(label)
 if r['specifications_json']=='{}':missing.append('detailed specifications not captured')
 if missing:r['notes']=(r['notes'].rstrip(' .;')+'; ' if r['notes'] else '')+'Missing/unverified fields: '+', '.join(missing)+'.'
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
print('K records',len(rows),'brands',len(set(r['brand'] for r in rows)),'subtypes',dict(sorted(Counter(r['subcategory'] for r in rows).items())))
print('Missing year',sum(not r['release_year'] for r in rows),'price',sum(not r['official_price'] for r in rows),'image',sum(not r['image_url'] for r in rows),'specs',sum(r['specifications_json']=='{}' for r in rows),'duplicates',len(rows)-len(seen))
