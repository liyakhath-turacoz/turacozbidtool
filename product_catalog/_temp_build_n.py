import csv,json,os
from collections import Counter
ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'N-networking-gps-communication.csv');TODAY='2026-10-13'
data=[]
def add(sub,typ,name,brand,model,url,spec=None,year='',price='',currency='',market='',price_type='',desc=''):
 note=[]
 if not year: note.append('Official model/catalogue listing found; source did not establish release year, so age needs review.')
 if not price: note.append('Official listed price not captured.')
 note.append('No official image URL captured.')
 data.append(dict(category_code='N',department='Networking, GPS & Communication',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=desc or f'{name}; normalized specifications include only details published by the manufacturer at the linked source.',specifications_json=json.dumps(spec or {},separators=(',',':'),ensure_ascii=False),image_url='',product_url=url,release_date='',release_date_precision='year' if year else '',release_year=str(year) if year else '',official_price=str(price) if price else '',price_currency=currency,price_type=price_type,price_market=market,price_source_url=url if price else '',product_source_url=url,source_attribution='Official manufacturer product page, catalogue, newsroom, or support document',collected_on=TODAY,verification_status='official_source_linked',notes=' '.join(note)))

# NETWORKING EQUIPMENT — Wi-Fi routers, mesh kits, modems, range extenders
routers=[
('Archer BE9300 Tri-Band Wi-Fi 7 Router','TP-Link','Archer BE9300','https://www.tp-link.com/us/home-networking/wifi-router/archer-be9300/',{'wifi':'Wi-Fi 7','bands':'tri-band','aggregate_speed_mbps':9214,'ethernet':'2 x 2.5GbE'},2024,''),
('Archer BE800 Tri-Band Wi-Fi 7 Router','TP-Link','Archer BE800','https://www.tp-link.com/us/home-networking/wifi-router/archer-be800/',{'wifi':'Wi-Fi 7','bands':'tri-band','ethernet':'10GbE and 2.5GbE'},2023,''),
('Archer BE900 Quad-Band Wi-Fi 7 Router','TP-Link','Archer BE900','https://www.tp-link.com/us/home-networking/wifi-router/archer-be900/',{'wifi':'Wi-Fi 7','bands':'quad-band','ethernet':'10GbE'},2023,''),
('Archer BE19000 Tri-Band Wi-Fi 7 Router','TP-Link','Archer BE19000','https://www.tp-link.com/us/home-networking/all-router/',{'wifi':'Wi-Fi 7','bands':'tri-band','aggregate_speed_class':'BE19000'},2025,''),
('Archer BE15000 Tri-Band Wi-Fi 7 Router','TP-Link','Archer BE15000','https://www.tp-link.com/us/home-networking/all-router/',{'wifi':'Wi-Fi 7','bands':'tri-band','aggregate_speed_class':'BE15000'},2025,''),
('Archer BE400 Dual-Band Wi-Fi 7 Router','TP-Link','Archer BE400','https://www.tp-link.com/us/home-networking/all-router/',{'wifi':'Wi-Fi 7','bands':'dual-band','aggregate_speed_class':'BE6500','ports':'2.5GbE'},2025,''),
('Nighthawk RS600 Wi-Fi 7 Router','NETGEAR','RS600','https://www.netgear.com/home/wifi/routers/10-gig-routers/',{'wifi':'Wi-Fi 7','speed_gbps':18,'wan_lan':'10GbE'},2025,499.99),
('Nighthawk RS700S Wi-Fi 7 Router','NETGEAR','RS700S','https://www.netgear.com/home/wifi/routers/10-gig-routers/',{'wifi':'Wi-Fi 7','speed_gbps':19,'wan_lan':'10GbE'},2024,599.99),
('Orbi 970 Series Quad-Band Wi-Fi 7 Mesh System','NETGEAR','RBE973S','https://www.netgear.com/home/wifi/mesh/rbe973s/',{'wifi':'Wi-Fi 7','bands':'quad-band','speed_gbps':27,'coverage_sqft':10000,'device_capacity':200},2023,1999.99),
('Orbi 770 Series Tri-Band Wi-Fi 7 Mesh System','NETGEAR','RBE772','https://www.netgear.com/home/wifi/mesh/rbe772/',{'wifi':'Wi-Fi 7','bands':'tri-band','speed_gbps':11,'coverage_sqft':5500,'device_capacity':100},2025,449.99),
('RT-BE96U Wi-Fi 7 Router','ASUS','RT-BE96U','https://www.asus.com/networking-iot-servers/wifi-7/all-series/',{'wifi':'Wi-Fi 7','bands':'tri-band','aggregate_speed_class':'BE19000'},2024,''),
('RT-BE88U Wi-Fi 7 Router','ASUS','RT-BE88U','https://www.asus.com/networking-iot-servers/wifi-7/all-series/',{'wifi':'Wi-Fi 7','ports':'10GbE and 2.5GbE'},2024,''),
('GT-BE98 Pro ROG Rapture Wi-Fi 7 Router','ASUS','GT-BE98 Pro','https://www.asus.com/networking-iot-servers/wifi-7/all-series/',{'wifi':'Wi-Fi 7','bands':'quad-band','gaming_router':True},2024,''),
('ZenWiFi BQ16 Pro Quad-Band Wi-Fi 7 Mesh System','ASUS','ZenWiFi BQ16 Pro','https://www.asus.com/networking-iot-servers/whole-home-mesh-wifi-system/all-series/',{'wifi':'Wi-Fi 7','bands':'quad-band','mesh':True},2024,''),
('eero Max 7 Mesh Wi-Fi System','Amazon eero','eero Max 7','https://eero.com/shop/eero-max-7',{'wifi':'Wi-Fi 7','ethernet':'10GbE','mesh':True},2023,''),
('eero 7 Mesh Wi-Fi System','Amazon eero','eero 7','https://eero.com/shop/eero-7',{'wifi':'Wi-Fi 7','mesh':True},2024,''),
('eero Pro 7 Mesh Wi-Fi System','Amazon eero','eero Pro 7','https://eero.com/shop/eero-pro-7',{'wifi':'Wi-Fi 7','tri-band':True,'mesh':True},2025,''),
('Flint 3 BE9300 Wi-Fi 7 Router','GL.iNet','GL-BE9300','https://www.gl-inet.com/products/gl-be9300/',{'wifi':'Wi-Fi 7','bands':'tri-band','aggregate_speed_class':'BE9300'},2024,''),
('Deco BE95 Quad-Band Wi-Fi 7 Mesh System','TP-Link','Deco BE95','https://www.tp-link.com/us/deco-mesh-wifi/product-family/deco-be95/',{'wifi':'Wi-Fi 7','bands':'quad-band','mesh':True,'ports':'10GbE'},2023,''),
('Deco BE65 Tri-Band Wi-Fi 7 Mesh System','TP-Link','Deco BE65','https://www.tp-link.com/us/deco-mesh-wifi/product-family/deco-be65/',{'wifi':'Wi-Fi 7','bands':'tri-band','mesh':True},2024,''),
('RE655BE BE11000 Wi-Fi 7 Range Extender','TP-Link','RE655BE','https://www.tp-link.com/us/home-networking/range-extender/re655be/',{'wifi':'Wi-Fi 7','speed_gbps':10.8,'ethernet':'2.5GbE','mesh':'EasyMesh'},2025,''),
('RE405BE BE6500 Wi-Fi 7 Range Extender','TP-Link','RE405BE','https://www.tp-link.com/us/home-networking/range-extender/re405be/',{'wifi':'Wi-Fi 7','speed_gbps':6.5,'ethernet':'2.5GbE','mesh':'EasyMesh'},2025,''),
('RE225BE BE3600 Wi-Fi 7 Range Extender','TP-Link','RE225BE','https://www.tp-link.com/us/home-networking/range-extender/re225be/',{'wifi':'Wi-Fi 7','speed_gbps':3.6,'ethernet':'1GbE','mesh':'EasyMesh'},2025,''),
('Nighthawk CM3000 DOCSIS 3.1 Cable Modem','NETGEAR','CM3000','https://www.netgear.com/home/wifi/modems/cm3000/',{'docsis':'3.1','ethernet':'2.5GbE','internet_tier':'multi-gig'},2024,''),
('SURFboard S34 DOCSIS 3.1 Cable Modem','CommScope ARRIS','S34','https://www.surfboard.com/products/cable-modems/s34/',{'docsis':'3.1','ethernet':'2.5GbE'},2024,''),
('Nighthawk M6 Pro 5G Mobile Hotspot','NETGEAR','MR6550','https://www.netgear.com/home/mobile-wifi/hotspots/mr6550/',{'cellular':'5G','wifi':'Wi-Fi 6E','portable':True},2023,''),
]
for n,b,m,u,s,y,p in routers:add('Networking Equipment','Router / mesh / modem / range extender',n,b,m,u,s,y,p,'USD' if p else '', 'US' if p else '', 'current listed price' if p else '')

# NETWORK INFRASTRUCTURE — managed switches, access points, network adapters/cards
infra=[
('U7 Pro Wi-Fi 7 Access Point','Ubiquiti','U7-Pro','https://store.ui.com/us/en/products/u7-pro',{'wifi':'Wi-Fi 7','streams':6,'uplink':'2.5GbE PoE+'},2024,189),
('U7 Pro Max Wi-Fi 7 Access Point','Ubiquiti','U7-Pro-Max','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','streams':8,'uplink':'2.5GbE','spectrum_scan':True},2024,279),
('U7 Outdoor Wi-Fi 7 Access Point','Ubiquiti','U7-Outdoor','https://store.ui.com/us/en/category/all-wifi/products/u7-outdoor',{'wifi':'Wi-Fi 7','rating':'IPX6','uplink':'2.5GbE PoE+'},2025,199),
('U7 Mesh Wi-Fi 7 Access Point','Ubiquiti','U7-Mesh','https://store.ui.com/us/en/products/u7-mesh',{'wifi':'Wi-Fi 7','rating':'IPX6','uplink':'2.5GbE PoE'},2025,199),
('U7 Pro XGS Wi-Fi 7 Access Point','Ubiquiti','U7-Pro-XGS','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','streams':8,'uplink':'10GbE'},2026,299),
('U7 Pro XG Wi-Fi 7 Access Point','Ubiquiti','U7-Pro-XG','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','streams':6,'uplink':'10GbE'},2026,199),
('U7 Pro Wall Wi-Fi 7 Access Point','Ubiquiti','U7-Pro-Wall','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','form_factor':'wall'},2025,199),
('U7 In-Wall Wi-Fi 7 Access Point','Ubiquiti','U7-IW','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','form_factor':'wall','integrated_switch':'2.5GbE PoE'},2025,149),
('U7 Lite Wi-Fi 7 Access Point','Ubiquiti','U7-Lite','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','uplink':'2.5GbE'},2025,99),
('U7 Long-Range Wi-Fi 7 Access Point','Ubiquiti','U7-LR','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','form_factor':'ceiling, extended range'},2025,159),
('U7 Industrial Wi-Fi 7 Access Point','Ubiquiti','U7-Industrial','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','rating':'IP67','industrial':True},2026,349),
('Omada EAP787 BE15000 Wi-Fi 7 AP','TP-Link Omada','EAP787','https://www.tp-link.com/us/business-networking/omada/wifi/wifi-7/',{'wifi':'Wi-Fi 7','bands':'tri-band','speed_class':'BE15000','streams':8},2025,''),
('Omada EAP772 BE11000 Wi-Fi 7 AP','TP-Link Omada','EAP772','https://www.tp-link.com/us/business-networking/omada/wifi/wifi-7/',{'wifi':'Wi-Fi 7','bands':'tri-band','speed_class':'BE11000','uplink':'2.5GbE'},2024,''),
('Omada EAP773 BE11000 Wi-Fi 7 AP','TP-Link Omada','EAP773','https://www.tp-link.com/us/business-networking/omada/wifi/wifi-7/',{'wifi':'Wi-Fi 7','bands':'tri-band','speed_class':'BE11000','uplink':'10GbE'},2024,''),
('Omada EAP723 BE5000 Wi-Fi 7 AP','TP-Link Omada','EAP723','https://www.tp-link.com/us/business-networking/omada/wifi/wifi-7/',{'wifi':'Wi-Fi 7','bands':'dual-band','speed_class':'BE5000'},2025,''),
('Omada EAP775-Wall Wi-Fi 7 AP','TP-Link Omada','EAP775-Wall','https://www.tp-link.com/us/business-networking/omada/wifi/wifi-7/',{'wifi':'Wi-Fi 7','form_factor':'wall plate','bands':'tri-band'},2025,''),
('Omada EAP725-Wall Wi-Fi 7 AP','TP-Link Omada','EAP725-Wall','https://www.tp-link.com/us/business-networking/omada/wifi/wifi-7/',{'wifi':'Wi-Fi 7','form_factor':'wall plate','bands':'dual-band'},2025,''),
('Omada EAP772-Outdoor Wi-Fi 7 AP','TP-Link Omada','EAP772-Outdoor','https://www.tp-link.com/us/business-networking/omada-wifi-outdoor/eap772-outdoor/',{'wifi':'Wi-Fi 7','bands':'tri-band','speed_mbps':10777,'rating':'IP68'},2025,''),
('Omada EAP725-Outdoor Wi-Fi 7 AP','TP-Link Omada','EAP725-Outdoor','https://www.tp-link.com/us/business-networking/omada/wifi/wifi-7/',{'wifi':'Wi-Fi 7','form_factor':'outdoor','bands':'dual-band'},2025,''),
('Omada SG3428X-M2 24-Port 2.5G Managed Switch','TP-Link Omada','SG3428X-M2','https://www.tp-link.com/us/business-networking/omada-switch-l3-l2-managed/sg3428x-m2/',{'ports':'24 x 2.5GbE','uplinks':'4 x 10GbE SFP+'},2024,''),
('Omada TL-SX3206HPP 6-Port 10G PoE++ Switch','TP-Link Omada','TL-SX3206HPP','https://www.tp-link.com/us/business-networking/omada-switch-l3-l2-managed/tl-sx3206hpp/',{'ports':'4 x 10GbE PoE++','uplinks':'2 x 10GbE SFP+','managed':True},2024,''),
('UniFi Switch Pro Max 16 PoE','Ubiquiti','USW-Pro-Max-16-PoE','https://store.ui.com/us/en/category/all-switching/products/usw-pro-max-16-poe',{'ports':'16','multi-gig':True,'PoE':True},2024,''),
('UniFi Switch Pro Max 48 PoE','Ubiquiti','USW-Pro-Max-48-PoE','https://store.ui.com/us/en/category/all-switching/products/usw-pro-max-48-poe',{'ports':'48','multi-gig':True,'PoE':True},2024,''),
('UniFi EnterpriseXG 24 Switch','Ubiquiti','USW-EnterpriseXG-24','https://store.ui.com/us/en/category/all-switching/products/usw-enterprisexg-24',{'ports':'24 x 10GbE','managed':True},2024,1299),
('Ubiquiti AirWire Wi-Fi 7 Client Adapter','Ubiquiti','U-AirWire','https://store.ui.com/us/en/category/all-wifi',{'wifi':'Wi-Fi 7','interface':'client adapter','MLO':True},2026,199),
('ASUS USB-BE93 Mini Wi-Fi 7 Adapter','ASUS','USB-BE93 Mini','https://www.asus.com/networking-iot-servers/wireless-adapters/all-series/',{'wifi':'Wi-Fi 7','interface':'USB-A/USB-C','bands':'tri-band'},2025,''),
('TP-Link Archer TXE70UH Wi-Fi 6E USB Adapter','TP-Link','Archer TXE70UH','https://www.tp-link.com/us/home-networking/adapter/archer-txe70uh/',{'wifi':'Wi-Fi 6E','interface':'USB 3.0'},2023,''),
]
for n,b,m,u,s,y,p in infra:add('Network Infrastructure','Access point / switch / network adapter',n,b,m,u,s,y,p,'USD' if p else '', 'US' if p else '', 'current listed price' if p else '')

# CONNECTIVITY ACCESSORIES — adapters and network cabling
access=[
('TP-Link UE300C USB-C to Gigabit Ethernet Adapter','UE300C','TP-Link','https://www.tp-link.com/us/home-networking/usb-converter/ue300c/','USB-C to 1GbE Ethernet', ''),
('TP-Link UE306 USB 3.0 to Gigabit Ethernet Adapter','UE306','TP-Link','https://www.tp-link.com/us/home-networking/usb-converter/ue306/','USB-A to 1GbE Ethernet', ''),
('TP-Link TXE70UH Wi-Fi 6E USB Adapter','TXE70UH','TP-Link','https://www.tp-link.com/us/home-networking/adapter/archer-txe70uh/','USB 3.0; Wi-Fi 6E',2023),
('StarTech USB-C to 2.5GbE Ethernet Adapter','US2GC30','StarTech.com','https://www.startech.com/en-us/networking-io/us2gc30','USB-C to 2.5GbE Ethernet', ''),
('Ubiquiti Ethernet Surge Protection Outdoor','ETH-SP-G2','Ubiquiti','https://store.ui.com/us/en/category/accessories-cables-dacs/collections/accessories-pro-surge-protection','Gigabit Ethernet surge protector; outdoor install', ''),
('Ubiquiti UACC-DAC-SFP10-0.5M Direct Attach Cable','UACC-DAC-SFP10-0.5M','Ubiquiti','https://store.ui.com/us/en/category/accessories-cables-dacs/collections/accessories-pro-direct-attach-cables','10GbE SFP+ direct attach cable; 0.5m', ''),
('Ubiquiti UACC-DAC-SFP10-1M Direct Attach Cable','UACC-DAC-SFP10-1M','Ubiquiti','https://store.ui.com/us/en/category/accessories-cables-dacs/collections/accessories-pro-direct-attach-cables','10GbE SFP+ direct attach cable; 1m', ''),
('TP-Link Omada SM311LS MiniGBIC SFP Module','SM311LS','TP-Link Omada','https://www.tp-link.com/us/business-networking/accessory/sm311ls/','1000BASE-LX single-mode SFP transceiver', ''),
('TP-Link Omada SM5310-T SFP+ to RJ45 Module','SM5310-T','TP-Link Omada','https://www.tp-link.com/us/business-networking/accessory/sm5310-t/','10GBASE-T SFP+ copper module', ''),
]
for n,m,b,u,s,y in access:add('Connectivity Accessories','Network adapter / transceiver / cable',n,b,m,u,{'published_features':s},y)

# GPS & NAVIGATION — vehicle and handheld positioning products
gps=[
('eTrex Touch Handheld GPS Navigator','eTrex Touch','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/garmin-unveils-the-versatile-etrex-touch-to-guide-every-outdoor-adventure/',{'display':'3-inch color touchscreen','maps':'TopoActive','battery_hours':130,'rating':'IP67'},2025,449.99),
('GPSMAP H1i Plus Handheld GPS/Satellite Communicator','GPSMAP H1i Plus','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/garmin-introduces-the-gpsmap-h1i-plus-premium-gps-handheld-with-inreach-plus-satellite-technology/',{'display':'3.5-inch touchscreen','battery_hours':145,'rating':'IP67','inReach':'satellite messaging/SOS'},2025,999.99),
('GPSMAP H1 Handheld GPS Navigator','GPSMAP H1','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/garmin-introduces-the-gpsmap-h1i-plus-premium-gps-handheld-with-inreach-plus-satellite-technology/',{'display':'3.5-inch touchscreen','maps':'TopoActive'},2025,699.99),
('Montana 710 Handheld GPS Navigator','Montana 710','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/garmin-announces-new-montana-handheld-gps-series-with-optional-sos-satellite-communication-capabilities-to-help-you-stay-in-touch/',{'display':'5-inch touchscreen','maps':'worldwide/topographic'},2025,''),
('Montana 710i Handheld GPS with inReach','Montana 710i','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/garmin-announces-new-montana-handheld-gps-series-with-optional-sos-satellite-communication-capabilities-to-help-you-stay-in-touch/',{'display':'5-inch touchscreen','inReach':'satellite communication'},2025,''),
('Montana 760i Handheld GPS with inReach','Montana 760i','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/garmin-announces-new-montana-handheld-gps-series-with-optional-sos-satellite-communication-capabilities-to-help-you-stay-in-touch/',{'display':'5-inch touchscreen','camera':True,'inReach':'satellite communication'},2025,''),
('Tread 2 Off-Road Navigator','Tread 2','Garmin','https://www.garmin.com/en-US/newsroom/press-release/automotive/find-your-next-adventure-with-the-rugged-tread-2-powersports-navigator-from-garmin/',{'display':'6-inch touchscreen','maps':'topographic','navigation':'off-road'},2024,''),
('zūmo XT2 Motorcycle Navigator','zūmo XT2','Garmin','https://www.garmin.com/en-US/p/867974/',{'display':'6-inch HD','rating':'IPX7','storage_gb':32,'battery_hours':7},2023,''),
('GPSMAP 67 Handheld GPS Navigator','GPSMAP 67','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/find-your-path-with-new-handheld-gps-devices-from-garmin/',{'display':'3-inch','battery_hours':180,'multi_band_gnss':True},2023,499.99),
('GPSMAP 67i Handheld GPS with inReach','GPSMAP 67i','Garmin','https://www.garmin.com/en-US/p/890109/',{'display':'3-inch','battery_hours':165,'multi_band_gnss':True,'inReach':'satellite SOS'},2023,599.99),
('eTrex Solar GPS Handheld Navigator','eTrex Solar','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/never-run-out-of-power-with-the-all-new-etrex-solar-from-garmin/',{'solar_charging':True,'multi_band_gps':True,'rating':'IPX7'},2023,249.99),
('eTrex SE Handheld GPS Navigator','eTrex SE','Garmin','https://www.garmin.com/en-US/newsroom/press-release/outdoor/find-your-path-with-new-handheld-gps-devices-from-garmin/',{'display':'2.2-inch','battery':'2 AA batteries','rating':'IPX7'},2023,149.99),
('inReach Mini 3 Plus Satellite Communicator','inReach Mini 3 Plus','Garmin','https://www.garmin.com/en-US/blog/outdoor/which-inreach-device-is-right-for-you/',{'display':'1.9-inch touchscreen','satellite':'Iridium','messaging':'text, voice, photo with compatible app'},2025,''),
('inReach Messenger Plus Satellite Communicator','inReach Messenger Plus','Garmin','https://www.garmin.com/en-US/blog/outdoor/which-inreach-device-is-right-for-you/',{'satellite':'Iridium','messaging':'text, photo, voice'},2024,''),
]
for n,m,b,u,s,y,p in gps:add('GPS & Navigation','GPS navigator / handheld GPS / satellite communicator',n,b,m,u,s,y,p,'USD' if p else '', 'US' if p else '', 'manufacturer suggested retail price' if p else '')

# COMMUNICATION EQUIPMENT — two-way and professional radios
radios=[
('Retevis A1 Business Two-Way Radio','A1','Retevis','https://www.retevis.com/downloads/brochure','Portable business radio; see official model brochure',''),
('Retevis A61 Portable Two-Way Radio','A61','Retevis','https://www.retevis.com/downloads/brochure','Portable two-way radio; see official model brochure',''),
('Retevis B3H Business Radio','B3H','Retevis','https://www.retevis.com/downloads/brochure','Commercial two-way radio; model brochure available',''),
('Retevis B3S Business Radio','B3S','Retevis','https://www.retevis.com/downloads/brochure','Commercial two-way radio; model brochure available',''),
('Retevis B63H Portable Two-Way Radio','B63H','Retevis','https://www.retevis.com/downloads/brochure','Portable radio; model brochure available',''),
('Retevis EZTalk 3A Two-Way Radio','EZTalk 3A','Retevis','https://www.retevis.com/downloads/brochure','Consumer two-way radio; model brochure available',''),
('Retevis RB658 Professional Radio','RB658','Retevis','https://www.retevis.com/pages/about-us','Commercial radio with Bluetooth and app integration',2024),
('Retevis RB58 Professional Radio','RB58','Retevis','https://www.retevis.com/pages/about-us','Commercial radio with Bluetooth and app integration',2024),
('Retevis MateTalk E2 Intrinsically Safe DMR Radio','MateTalk E2','Retevis','https://www.retevis.com/pages/about-us','DMR two-way radio, intrinsically safe product line',2025),
('Retevis EZTalk 5 Outdoor Bluetooth Radio','EZTalk 5','Retevis','https://www.retevis.com/shop','Outdoor two-way radio with Bluetooth app programming and GPS',''),
('Hytera P5 Series PoC Radio','P5 Series','Hytera','https://www.hytera.com/en/products/broadband-poc-radio.html','Push-to-talk over cellular radio product family',''),
('Hytera HM685 Mobile DMR Radio','HM685','Hytera','https://www.hytera.com/eu/products/dmr-radio/hm685','Digital/analogue DMR mobile radio, AI noise cancellation', ''),
('Motorola TALKABOUT T800 Radio','T800','Motorola Solutions','https://www.motorolasolutions.com/en_us/products/two-way-radios/consumer-two-way-radios.html','FRS radio with app-linked location sharing and messaging; age requires review', ''),
('Motorola TALKABOUT T470 Series Radio','T470','Motorola Solutions','https://www.motorolasolutions.com/en_us/products/two-way-radios/consumer-two-way-radios/talkabout-t470-series.html','FRS, IPX4, 22 channels, NOAA alerts; age requires review', ''),
]
for n,m,b,u,s,y in radios:add('Communication Equipment','Walkie-talkie / two-way radio',n,b,m,u,{'published_features':s},y)

# TELECOM EQUIPMENT — VoIP phones, business phone systems, conferencing devices
telecom=[
('Yealink SIP-T88 Smart Business Phone','SIP-T88','Yealink','https://www.yealink.com/en/product-list/ip-phone?filter=t7','Business SIP desk phone; T8 Series', ''),
('Yealink SIP-T87W Prime Business Phone','SIP-T87W','Yealink','https://www.yealink.com/en/product-list/ip-phone?filter=t7','Business SIP desk phone with Wi-Fi; T8 Series', ''),
('Yealink SIP-T85W Prime Business Phone','SIP-T85W','Yealink','https://www.yealink.com/en/product-list/ip-phone?filter=t7','Business SIP desk phone with Wi-Fi; T8 Series', ''),
('Yealink SIP-T77U Executive SIP Phone','SIP-T77U','Yealink','https://www.yealink.com/en/product-detail/ip-phone-t77u','7-inch 800x480 color touchscreen, USB-A/C, AI noise cancellation', ''),
('Yealink SIP-T74W Multifunctional IP Phone','SIP-T74W','Yealink','https://www.yealink.com/en/product-list/ip-phone?filter=t7','Multifunctional SIP phone with Wi-Fi', ''),
('Yealink SIP-T74U Multifunctional IP Phone','SIP-T74U','Yealink','https://www.yealink.com/en/product-list/ip-phone?filter=t7','Multifunctional executive SIP phone', ''),
('Yealink SIP-T73W All-in-One Business Phone','SIP-T73W','Yealink','https://www.yealink.com/en/product-list/ip-phone?filter=t7','Business SIP phone with Wi-Fi', ''),
('Yealink SIP-T73U All-in-One Business Phone','SIP-T73U','Yealink','https://www.yealink.com/en/product-list/ip-phone?filter=t7','Business SIP phone', ''),
('Grandstream GHP630W Wi-Fi Hotel IP Phone','GHP630W','Grandstream','https://www.grandstream.com/products/ip-voice-telephony/hotel-phones','2 SIP accounts, Wi-Fi 6, PoE, GDMS provisioning', ''),
('Grandstream GHP631W Wi-Fi Hotel IP Phone','GHP631W','Grandstream','https://www.grandstream.com/products/ip-voice-telephony/hotel-phones','2 SIP accounts, Wi-Fi 6, PoE, GDMS provisioning', ''),
('Grandstream GHP620W Wi-Fi Hotel IP Phone','GHP620W','Grandstream','https://www.grandstream.com/products/ip-voice-telephony/hotel-phones','2 SIP accounts, dual-band Wi-Fi, GDMS provisioning', ''),
('Yealink MVC S50 Microsoft Teams Rooms System','MVC S50','Yealink','https://www.yealink.com/en/product-detail/microsoft-teams-rooms-mvcs50','MeetingBar A50 triple 50MP cameras; 16 MEMS microphones; 11.6-inch touch console',2025),
('Yealink MeetingBar A50 Video Conferencing Bar','MeetingBar A50','Yealink','https://www.yealink.com/en/product-detail/microsoft-teams-rooms-meetingbar-a50','Triple camera system, 16 MEMS microphones, 10m voice pickup',2025),
('Yealink MeetingBar A25 Video Conferencing Bar','MeetingBar A25','Yealink','https://www.yealink.com/en/onepage/what-is-new','All-in-one video bar for compact focus rooms',2025),
('Yealink MeetingBoard Pro Collaboration Display','MeetingBoard Pro','Yealink','https://www.yealink.com/en/onepage/what-is-new','All-in-one interactive collaboration display for meeting rooms',2025),
('Logitech Rally Bar Huddle','Rally Bar Huddle','Logitech','https://www.logitech.com/en-us/products/video-conferencing/room-solutions/rallybarhuddle.960-001485.html','All-in-one video bar for huddle/small rooms; appliance, USB, or BYOD modes',2023),
('Logitech MeetUp 2 Conference Camera','MeetUp 2','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras','All-in-one USB conference camera for huddle/small rooms',2024),
('Logitech Rally Board 65 Collaboration System','Rally Board 65','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras','All-in-one meeting device with 65-inch touchscreen',2025),
('Logitech Rally AI Camera Pro','Rally AI Camera Pro','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras','PTZ conference camera with AI framing and optical imaging',2025),
]
for n,m,b,u,s,y in telecom:add('Telecom Equipment','VoIP phone / conferencing system / communication terminal',n,b,m,u,{'published_features':s},y)

fields=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes']
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
print('N rows',len(data),'subtypes',len(set(r['subcategory'] for r in data)),'brands',len(set(r['brand'] for r in data)),'duplicate keys',len(data)-len(set((r['brand'].lower(),r['model'].lower()) for r in data)))
print(dict(Counter(r['subcategory'] for r in data)))
