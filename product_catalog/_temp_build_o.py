import csv,json,os
from collections import Counter
ROOT=os.path.dirname(__file__);OUT=os.path.join(ROOT,'O-printers-scanners-office-electronics.csv');TODAY='2026-10-13'
data=[]
def add(sub,typ,name,brand,model,url,spec=None,year='',price='',currency='',market='',price_type='',note_extra=''):
 note=[]
 if not year:note.append('Official product listing found; release year not stated in source and needs age review.')
 if not price:note.append('Official listed price not captured.')
 note.append('No official image URL captured.')
 if note_extra:note.append(note_extra)
 data.append(dict(category_code='O',department='Printers, Scanners & Office Electronics',subcategory=sub,product_type=typ,product_name=name,manufacturer=brand,brand=brand,model=model,manufacturer_part_number='',gtin='',description=f'{name}; normalized specifications include only manufacturer-published details captured from the official source.',specifications_json=json.dumps(spec or {},separators=(',',':'),ensure_ascii=False),image_url='',product_url=url,release_date='',release_date_precision='year' if year else '',release_year=str(year) if year else '',official_price=str(price) if price else '',price_currency=currency,price_type=price_type,price_market=market,price_source_url=url if price else '',product_source_url=url,source_attribution='Official manufacturer product page, catalogue, newsroom, or support source',collected_on=TODAY,verification_status='official_source_linked',notes=' '.join(note)))

# PRINTERS: inkjet, laser, photo, multifunction and production MFPs.
printers=[
('EcoTank ET-4950 Wireless All-in-One Color Printer','Epson','ET-4950','https://epson.com/For-Home/Printers/Inkjet/EcoTank-ET-4950-Wireless-All-in-One-Color-Supertank-Printer-%E2%80%93-Black/p/C11CL40201',{'functions':'print, copy, scan, fax','speed_iso_ppm':18,'paper_input_sheets':250,'duplex':True},2025,499.99),
('WorkForce Enterprise AM-C550 Color MFP','Epson','AM-C550','https://epson.com/For-Work/Printers/Inkjet/WorkForce-Enterprise-AM-C550-A4-Color-Multifunction-Printer/p/C11CJ92201',{'functions':'print, copy, scan','speed_iso_ppm':55,'scan_ipm_duplex':100,'monthly_volume_range':'4,500-30,000'},2024,''),
('WorkForce Enterprise AM-C400 Color MFP','Epson','AM-C400','https://news.epson.com/news/workforce-enterprise-am-c550-C400-mfps',{'functions':'print, copy, scan','technology':'PrecisionCore Heat-Free'},2024,''),
('WorkForce Enterprise AM-M5500 Monochrome MFP','Epson','AM-M5500','https://epson.com/For-Work/Printers/Inkjet/WorkForce-Enterprise-AM-M5500-Monochrome-Multifunction-Printer/p/C11CL48201',{'functions':'print, copy, scan','speed_iso_ppm':55,'monthly_volume_range':'8,000-60,000'},2024,''),
('PIXMA TR7820 Wireless Home All-in-One','Canon','TR7820','https://www.usa.canon.com/shop/catalog/product/view/id/196338/s/pixma-tr7820-wireless-home-all-in-one-printer/',{'functions':'print, copy, scan, fax','connectivity':'dual-band Wi-Fi'},2024,''),
('Color imageCLASS MF665Cdw Wireless Laser MFP','Canon','MF665Cdw','https://www.usa.canon.com/shop/p/color-imageclass-mf665cdw-all-in-one-wireless-laser-printer',{'technology':'color laser','functions':'print, copy, scan, fax','duplex':True},2025,''),
('imageCLASS LBP246dw Monochrome Laser Printer','Canon','LBP246dw','https://www.usa.canon.com/printers/office-printers',{'technology':'monochrome laser','functions':'print','duplex':True,'network':'Wi-Fi/Ethernet'},2024,''),
('imageCLASS MF465dw Monochrome Laser MFP','Canon','MF465dw','https://www.usa.canon.com/printers/office-printers',{'technology':'monochrome laser','functions':'print, copy, scan, fax'},2024,''),
('MFC-L2900DW XL Compact Monochrome Laser All-in-One','Brother','MFC-L2900DWXL','https://www.brother-usa.com/p/laser-printers/MFCL2900DWXL',{'technology':'monochrome laser','functions':'print, copy, scan, fax','speed_ppm':36,'duplex_scan':True,'adf_sheets':50},2024,379.99),
('MFC-J5010DW INKvestment Color Inkjet All-in-One','Brother','MFC-J5010DW','https://www.brother-usa.com/home/printers-fax/products',{'technology':'inkjet ink tank','functions':'print, copy, scan, fax, wireless'},2026,''),
('MFC-J1355DW INKvestment Color Inkjet All-in-One','Brother','MFC-J1355DW','https://www.brother-usa.com/home/printers-fax/products',{'technology':'inkjet','functions':'print, copy, scan, fax'},2025,''),
('MFC-J1260W Wireless Color Inkjet All-in-One','Brother','MFC-J1260W','https://www.brother-usa.com/home/printers-fax/products',{'technology':'inkjet','functions':'print, copy, scan, wireless'},2025,''),
('MFC-J6560DW INKvestment Color Inkjet All-in-One','Brother','MFC-J6560DW','https://www.brother-usa.com/home/printers-fax/products',{'technology':'inkjet','functions':'print, copy, scan, fax'},2025,''),
('HP OfficeJet Pro 9135e All-in-One','HP','9135e','https://www.hp.com/us-en/printers/home-printers.html',{'technology':'inkjet','functions':'print, copy, scan, fax','speed_iso_ppm':24,'input_capacity_sheets':500,'duplex_scan':True},2024,''),
('HP OfficeJet Pro 9125e All-in-One','HP','9125e','https://www.hp.com/us-en/shop/mdp/printers',{'technology':'inkjet','functions':'print, copy, scan, fax','speed_color_ppm':18},2024,''),
('HP Smart Tank 7602 All-in-One','HP','7602','https://www.hp.com/us-en/printers/home-printers.html',{'technology':'ink tank','functions':'print, copy, scan, wireless','ethernet':True,'adf':True},2023,''),
('HP Smart Tank 6001 All-in-One','HP','6001','https://www.hp.com/us-en/printers/home-printers.html',{'technology':'ink tank','functions':'print, copy, scan, wireless','ink_yield_claim':'up to 2 years included'},2023,''),
('HP Smart Tank 5101 All-in-One','HP','5101','https://www.hp.com/us-en/printers/home-printers.html',{'technology':'ink tank','functions':'print, copy, scan, wireless'},2024,''),
('HP Color LaserJet Pro MFP 3301fdw','HP','3301fdw','https://www.hp.com/us-en/shop/vwa/printers/prntbrnd=OfficeJet,LaserJet',{'technology':'color laser','functions':'print, copy, scan, fax','speed_color_ppm':26,'duplex':True},2024,''),
('HP LaserJet Pro MFP 3105sdw','HP','3105sdw','https://www.hp.com/us-en/shop/mdp/printers',{'technology':'monochrome laser','functions':'print, copy, scan','speed_ppm':35,'duplex':True},2025,''),
('HP LaserJet 100/200 Series Printer','HP','LaserJet 100/200 Series','https://www.hp.com/us-en/printers/ai-printers.html',{'technology':'laser','functions':'print; model configuration varies'},2025,''),
('HP LaserJet Pro 4000 Series','HP','LaserJet Pro 4000 Series','https://www.hp.com/us-en/printers/ai-printers.html',{'technology':'laser','functions':'print; model configuration varies'},2026,''),
('HP ENVY Inspire 7255e Photo Printer','HP','7255e','https://www.hp.com/us-en/printers/home-printers.html',{'technology':'inkjet photo','functions':'print, copy, scan','photo_tray':True},2023,''),
('Epson SureColor P5370 Photo Printer','Epson','P5370','https://epson.com/For-Work/Printers/Photo-Fine-Art/c/w160',{'technology':'professional photo inkjet','format':'17-inch'},2024,''),
('Canon imagePROGRAF PRO-1100 Professional Photo Printer','Canon','PRO-1100','https://www.usa.canon.com/printers/professional-photo-printers',{'technology':'professional photo inkjet','format':'17-inch'},2024,''),
('HP DesignJet T850 36-inch Large-Format Printer','HP','T850','https://www.hp.com/us-en/shop/Printers',{'technology':'large-format inkjet','format':'36-inch'},2023,''),
('HP DesignJet T870 Large-Format Printer','HP','T870','https://www.hp.com/us-en/shop/Printers',{'technology':'large-format inkjet'},2025,''),
]
for n,b,m,u,s,y,p in printers:add('Printers','Inkjet / laser / photo / multifunction printer',n,b,m,u,s,y,p,'USD' if p else '', 'US' if p else '', 'current official price' if p else '')

# SCANNERS: document, flatbed, photo and network scanners.
scanners=[
('Epson DS-790WN Wireless Network Document Scanner','DS-790WN','Epson','https://epson.com/For-Work/Scanners/Document-Scanners/Epson-DS-790WN-Wireless-Network-Color-Document-Scanner/p/B11B265201',{'speed_ppm':45,'duplex_ipm':90,'adf_sheets':100,'resolution_optical_dpi':600,'connectivity':'USB, Ethernet, Wi-Fi'},2023,829),
('Epson DS-800WN EdgeLink Wireless Network Scanner','DS-800WN','Epson','https://epson.com/For-Work/Scanners/Document-Scanners/c/w241',{'speed_ppm':50,'duplex_ipm':100,'adf_sheets':100,'connectivity':'USB, Ethernet, Wi-Fi'},2025,849),
('Epson DS-900WN EdgeLink High-Speed Network Scanner','DS-900WN','Epson','https://epson.com/For-Work/Scanners/Document-Scanners/c/w241',{'speed_ppm':70,'duplex_ipm':140,'adf_sheets':100,'connectivity':'USB, Ethernet, Wi-Fi'},2025,''),
('Epson DS-C490 Compact Desktop Document Scanner','DS-C490','Epson','https://epson.com/For-Work/Scanners/Document-Scanners/c/w241',{'scanner_type':'compact desktop document'},2024,''),
('Ricoh fi-8040 Network Scanner','fi-8040','Ricoh','https://www.ricoh-usa.com/en/products/pd/equipment/scanners/fi-8040-scanner',{'screen_inches':4.3,'adf_sheets':50,'daily_capacity_sheets':6000,'connectivity':'USB 3.2, Ethernet'},2023,''),
('Ricoh fi-8170 Desktop Document Scanner','fi-8170','Ricoh','https://www.ricoh-usa.com/en/products/pd/equipment/scanners/fi-8170-desktop-scanner',{'daily_capacity_sheets':10000,'connectivity':'USB, LAN'},2023,''),
('Canon imageFORMULA DR-S350NW Office Scanner','DR-S350NW','Canon','https://www.usa.canon.com/newsroom/2024/20241107-scanner',{'scanner_type':'network office document','connectivity':'Wi-Fi, USB, Ethernet'},2024,''),
('Canon imageFORMULA R40 Photo and Document Scanner','R40','Canon','https://www.usa.canon.com/shop/p/imageformula-rs40-photo-and-document-scanner',{'scanner_type':'sheet-fed photo/document','adf_sheets':40},2023,''),
('HP ScanJet Pro 3600 f1 Document Scanner','3600 f1','HP','https://www.hp.com/us-en/shop/pdp/hp-scanjet-pro-3600-f1-scanner',{'scanner_type':'flatbed/document','adf_sheets':60,'duplex':True},2023,''),
('HP ScanJet Enterprise Flow N6600 fnw1','N6600 fnw1','HP','https://www.hp.com/us-en/shop/pdp/hp-scanjet-enterprise-flow-n6600-fnw1',{'scanner_type':'network document','adf_sheets':100,'connectivity':'Ethernet, Wi-Fi'},2023,''),
('Brother ADS-4900W Professional Desktop Scanner','ADS-4900W','Brother','https://www.brother-usa.com/products/ads4900w',{'scanner_type':'network document','adf_sheets':100,'connectivity':'Ethernet, Wi-Fi'},2024,''),
('Brother ADS-4700W Desktop Scanner','ADS-4700W','Brother','https://www.brother-usa.com/products/ads4700w',{'scanner_type':'network document','adf_sheets':80,'connectivity':'Ethernet, Wi-Fi'},2023,''),
('Canon imageFORMULA R50 Office Document Scanner','R50','Canon','https://www.usa.canon.com/scanners/document-scanners',{'scanner_type':'desktop document','adf_sheets':60},2024,''),
('Epson Perfection V39 II Photo and Document Scanner','V39 II','Epson','https://epson.com/For-Home/Scanners/Photo-Scanners/c/h130',{'scanner_type':'flatbed photo/document','resolution_optical_dpi':4800},2023,''),
]
for n,m,b,u,s,y,p in scanners:add('Scanners','Flatbed / document / photo scanner',n,b,m,u,s,y,p,'USD' if p else '', 'US' if p else '', 'current official price' if p else '')

# BUSINESS PRINTING: barcode and label printers, including industrial devices.
business=[
('Zebra ZD421 Desktop Label Printer','ZD421','Zebra','https://www.zebra.com/us/en/support-downloads/printers/desktop/zd421.html',{'print_width_inches':4,'print_methods':'direct thermal or thermal transfer'},''),
('Zebra ZD611 Desktop Label Printer','ZD611','Zebra','https://www.zebra.com/us/en/products/printers.html',{'print_width_inches':2,'print_methods':'direct thermal or thermal transfer'},''),
('Zebra ZD621 Desktop Label Printer','ZD621','Zebra','https://www.zebra.com/us/en/products/printers.html',{'print_width_inches':4,'print_methods':'direct thermal or thermal transfer'},''),
('Zebra ZT610 Industrial Barcode Printer','ZT610','Zebra','https://www.zebra.com/us/en/support-downloads/printers/industrial/zt610.html',{'print_width_inches':4,'print_methods':'thermal transfer/direct thermal','industrial':True},''),
('Zebra ZT411 Industrial Barcode Printer','ZT411','Zebra','https://www.zebra.com/us/en/products/printers/industrial/zt400-series.html',{'print_width_inches':4,'industrial':True},''),
('Brother QL-1110NWB Wide Format Label Printer','QL-1110NWB','Brother','https://www.brother-usa.com/products/ql1110nwb',{'print_type':'direct thermal label','max_label_width_mm':103.6,'connectivity':'USB, Ethernet, Wi-Fi, Bluetooth'},''),
('Brother QL-820NWBc Professional Label Printer','QL-820NWBc','Brother','https://www.brother-usa.com/products/ql820nwbc',{'print_type':'direct thermal label','connectivity':'USB, Ethernet, Wi-Fi, Bluetooth'},''),
('Brother TD-4550DNWB Label Printer','TD-4550DNWB','Brother','https://www.brother-usa.com/products/td4550dnwb',{'print_type':'thermal label','connectivity':'USB, Ethernet, Wi-Fi, Bluetooth'},''),
('Epson ColorWorks C4000 Label Printer','C4000','Epson','https://epson.com/For-Work/Printers/Label/c/w141',{'print_type':'color inkjet label','print_width_inches':4},''),
('Epson ColorWorks C6000A Label Printer','C6000A','Epson','https://epson.com/For-Work/Printers/Label/c/w141',{'print_type':'color inkjet label','auto_cutter':True},''),
('Epson ColorWorks C8000 Label Printer','C8000','Epson','https://epson.com/For-Work/Printers/Label/c/w141',{'print_type':'industrial color inkjet label'},''),
('DYMO LabelWriter 550 Turbo Label Printer','LabelWriter 550 Turbo','DYMO','https://www.dymo.com/label-makers-printers/labelwriter-label-printers/',{'print_type':'direct thermal labels','usb':True},''),
('DYMO LabelManager Executive 640 CB','LabelManager Executive 640 CB','DYMO','https://www.dymo.com/label-makers-printers/labelmanager-label-makers/',{'print_type':'portable label maker','connectivity':'Bluetooth, USB-C'},''),
('TSC MH341 Industrial Barcode Printer','MH341','TSC Auto ID','https://usca.tscprinters.com/en/products/industrial-printers',{'print_width_inches':4,'print_type':'thermal transfer/direct thermal','industrial':True},''),
('SATO CL4NX Plus Industrial Label Printer','CL4NX Plus','SATO','https://www.sato-global.com/products/printer/industrial/cl4nx-plus/',{'print_width_inches':4,'print_type':'thermal transfer/direct thermal'},''),
('SATO CT4-LX Desktop Label Printer','CT4-LX','SATO','https://www.sato-global.com/products/printer/desktop/ct4-lx/',{'print_width_inches':4,'print_type':'thermal transfer/direct thermal'},''),
]
for n,m,b,u,s,y in business:add('Business Printing','Label / barcode printer',n,b,m,u,{'published_features':s},y)

# POINT-OF-SALE: receipt printers, POS terminals, barcode scanners.
pos=[
('Epson TM-m50II POS Receipt Printer','TM-m50II','Epson','https://files.support.epson.com/pdf/pos/bulk/tm-m50ii_trg_en_rev_f.pdf',{'print_speed_mm_s':500,'print_type':'thermal receipt','interface':'model options vary'},''),
('Epson TM-T88VII POS Receipt Printer','TM-T88VII','Epson','https://files.support.epson.com/pdf/pos/bulk/tm-t88vii_trg_en_revg.pdf',{'print_type':'thermal receipt','interface':'Ethernet, USB options'},''),
('Epson TM-L100 Liner-Free Label Printer','TM-L100','Epson','https://epson.com/For-Work/Printers/POS-Printers/c/w150',{'print_type':'liner-free thermal label/receipt'},''),
('Star Micronics mC-Print3 Receipt Printer','mC-Print3','Star Micronics','https://starmicronics.com/product/mc-print3/',{'print_type':'thermal receipt','connectivity':'USB, Ethernet, Bluetooth, Lightning varies'},''),
('Star Micronics mC-Label3 Label Printer','mC-Label3','Star Micronics','https://starmicronics.com/product/mc-label3/',{'print_type':'linerless/label thermal'},''),
('Zebra DS9308 Presentation Barcode Scanner','DS9308','Zebra','https://www.zebra.com/us/en/products/scanners/presentation/ds9308.html',{'scanner_type':'presentation barcode imager','interface':'USB, RS-232'},''),
('Zebra DS8178 Cordless Barcode Scanner','DS8178','Zebra','https://www.zebra.com/us/en/products/scanners/general-purpose-handheld-scanners/ds8100-series.html',{'scanner_type':'cordless handheld 1D/2D imager','wireless':'Bluetooth'},''),
('Zebra DS3678 Ultra-Rugged Barcode Scanner','DS3678','Zebra','https://www.zebra.com/us/en/products/scanners/ultra-rugged-scanners/ds3600-series.html',{'scanner_type':'ultra-rugged cordless 1D/2D imager','rating':'IP67/IP65'},''),
('Honeywell Xenon Ultra 1960g Barcode Scanner','1960g','Honeywell','https://automation.honeywell.com/us/en/products/productivity/barcode-scanners/general-purpose-handheld-barcode-scanners/xenon-ultra-1960g',{'scanner_type':'wired 1D/2D handheld imager'},''),
('Honeywell Xenon Ultra 1962g Barcode Scanner','1962g','Honeywell','https://automation.honeywell.com/us/en/products/productivity/barcode-scanners/general-purpose-handheld-barcode-scanners/xenon-ultra-1960g',{'scanner_type':'wireless 1D/2D handheld imager','wireless':'Bluetooth'},''),
('Square Terminal','Square Terminal','Block, Inc.','https://squareup.com/us/en/hardware/terminal',{'device_type':'all-in-one POS payment terminal','printer':'built-in receipt printer'},''),
('Square Register','Square Register','Block, Inc.','https://squareup.com/us/en/hardware/register',{'device_type':'dual-screen POS terminal'},''),
('Square Handheld','Square Handheld','Block, Inc.','https://squareup.com/us/en/hardware/handheld',{'device_type':'portable POS terminal','connectivity':'Wi-Fi, cellular'},2025,''),
('Stripe Reader S700','Stripe Reader S700','Stripe','https://stripe.com/terminal/stripe-reader-s700',{'device_type':'smart POS payment terminal','display':'5-inch touchscreen'},2024,''),
('Clover Flex 4 POS Terminal','Clover Flex 4','Clover Network','https://www.clover.com/pos-hardware/flex',{'device_type':'portable payment/POS terminal'},''),
]
for n,m,b,u,s,y,*maybe in pos:
 p=maybe[0] if maybe else ''
 add('Point-of-Sale Equipment','POS terminal / receipt printer / barcode scanner',n,b,m,u,{'published_features':s},y,p,'USD' if p else '', 'US' if p else '', 'current official price' if p else '')

# OFFICE DOCUMENT EQUIPMENT: copier, shredder and laminator models.
office=[
('Canon imageRUNNER ADVANCE DX C3935i Color Copier MFP','DX C3935i','Canon','https://www.usa.canon.com/business/products/office-printers-and-facsimile/multifunction-copiers',{'device_type':'color copier/MFP','functions':'print, copy, scan'},''),
('Ricoh IM C6010 Color Copier MFP','IM C6010','Ricoh','https://www.ricoh-usa.com/en/products/pd/equipment/multifunction-copiers-printers/color-multifunction-printers/im-c6010',{'device_type':'color copier/MFP'},2024),
('Xerox AltaLink C8230 Color Copier MFP','AltaLink C8230','Xerox','https://www.xerox.com/en-us/office/multifunction-printers/altalink-c8200-series',{'device_type':'color copier/MFP'},2024),
('Fellowes Powershred LX220 Micro-Cut Shredder','LX220','Fellowes','https://www.fellowes.com/us/en/resources/information-security/pg/lx-series-shredders',{'cut_type':'micro-cut','sheet_capacity':12,'bin_gallons':5,'duty_cycle_minutes':'20 on / 30 off'},2024,299.99),
('Fellowes Powershred LX210 Micro-Cut Shredder','LX210','Fellowes','https://www.fellowes.com/us/en/resources/information-security/pg/lx-series-shredders',{'cut_type':'micro-cut','sheet_capacity':10,'bin_gallons':6,'duty_cycle_minutes':'6 on / 20 off'},2024,229.99),
('Fellowes Powershred LX190 Cross-Cut Shredder','LX190','Fellowes','https://www.fellowes.com/us/en/resources/information-security/pg/lx-series-shredders',{'cut_type':'cross-cut','sheet_capacity':11,'bin_gallons':4.8},2024,''),
('Fellowes AutoMax 550C Auto-Feed Shredder','AutoMax 550C','Fellowes','https://www.fellowes.com/us/en/catalog/business-products/paper-shredders',{'cut_type':'cross-cut','auto_feed':True},''),
('Fellowes Powershred 12C15 Cross-Cut Shredder','12C15','Fellowes','https://www.fellowes.com/us/en/catalog/business-products/paper-shredders',{'cut_type':'cross-cut'},''),
('GBC Fusion 7000L 12-inch Pouch Laminator','Fusion 7000L','GBC','https://www.gbc.com/p/laminating/laminating-machines/pouch-laminators/fusion-7000l-pouch-laminator-12-inch-includes-50-ezuse-laminating-pouches/',{'lamination_width_inches':12,'warmup_minutes':1,'pouch_mil_range':'3-10'},''),
('GBC Fusion 6000L Pouch Laminator','Fusion 6000L','GBC','https://www.gbc.com/laminating/laminating-machines/pouch-laminators/',{'laminator_type':'office pouch laminator'},''),
('GBC Catena 65 Roll Laminator','Catena 65','GBC','https://www.gbc.com/p/laminating/laminating-machines/roll-laminators/',{'laminator_type':'wide-format roll laminator'},''),
('Fellowes Saturn 3i 125 Laminator','Saturn 3i 125','Fellowes','https://www.fellowes.com/us/en/catalog/business-products/laminating-machines',{'lamination_width_mm':125,'warmup':'Fast'},''),
]
for n,m,b,u,s,y,*maybe in office:
 p=maybe[0] if maybe else ''
 add('Office Document Equipment','Photocopier / shredder / laminator',n,b,m,u,{'published_features':s},y,p,'USD' if p else '', 'US' if p else '', 'manufacturer list price' if p else '')

# MEETING ROOM: camera, speakerphone and collaboration systems.
meeting=[
('Logitech Rally Bar Huddle Conference Camera','Rally Bar Huddle','Logitech','https://www.logitech.com/en-us/products/video-conferencing/room-solutions/rallybarhuddle.960-001485.html',{'device_type':'all-in-one video bar','room_size':'huddle/small','deployment':'appliance, USB, BYOD'},2023),
('Logitech MeetUp 2 Conference Camera','MeetUp 2','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras',{'device_type':'USB conference camera','room_size':'huddle/small'},2024),
('Logitech Rally Board 65 Collaboration Display','Rally Board 65','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras',{'device_type':'all-in-one collaboration display','display_inches':65},2025),
('Logitech Rally AI Camera Pro','Rally AI Camera Pro','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras',{'device_type':'PTZ conference camera','AI_features':True},2025),
('Yealink MeetingBar A25 Video Conferencing Bar','MeetingBar A25','Yealink','https://www.yealink.com/en/onepage/what-is-new',{'device_type':'all-in-one video bar','room_size':'compact focus room'},2025),
('Yealink MeetingBoard Pro','MeetingBoard Pro','Yealink','https://www.yealink.com/en/onepage/what-is-new',{'device_type':'interactive collaboration display'},2025),
('Poly Studio X52 Video Bar','Studio X52','HP Poly','https://www.hp.com/us-en/poly/video-conferencing/room-solutions.html',{'device_type':'all-in-one video bar','room_size':'medium'},2023),
('Poly Studio V72 Video Bar','Studio V72','HP Poly','https://www.hp.com/us-en/poly/video-conferencing/room-solutions.html',{'device_type':'all-in-one video bar','room_size':'large'},2024),
('Poly Studio G62 Modular Video Conferencing System','Studio G62','HP Poly','https://www.hp.com/us-en/poly/video-conferencing/room-solutions.html',{'device_type':'modular video conferencing system'},2024),
('Logitech Sight Tabletop Companion Camera','Sight','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras',{'device_type':'tabletop companion camera','participant_framing':'multi-participant'},2023),
('Logitech MeetUp ConferenceCam','MeetUp','Logitech','https://www.logitech.com/en-us/shop/c/conference-cameras',{'device_type':'USB conference camera','room_size':'small'},''),
]
for n,m,b,u,s,y in meeting:add('Meeting Room Equipment','Conference camera / speakerphone / presentation system',n,b,m,u,{'published_features':s},y)

# PRINTING ACCESSORIES: current manufacturer-brand ink/toner consumable SKUs.
accessories=[
('HP 936 Black Original Ink Cartridge','936 Black','HP','https://www.hp.com/us-en/shop/supplies/printers/936',{'supply_type':'ink cartridge','color':'black','compatible_family':'OfficeJet Pro 9100 series'},''),
('HP 936 Cyan Original Ink Cartridge','936 Cyan','HP','https://www.hp.com/us-en/shop/supplies/printers/936',{'supply_type':'ink cartridge','color':'cyan','compatible_family':'OfficeJet Pro 9100 series'},''),
('HP 936 Magenta Original Ink Cartridge','936 Magenta','HP','https://www.hp.com/us-en/shop/supplies/printers/936',{'supply_type':'ink cartridge','color':'magenta','compatible_family':'OfficeJet Pro 9100 series'},''),
('HP 936 Yellow Original Ink Cartridge','936 Yellow','HP','https://www.hp.com/us-en/shop/supplies/printers/936',{'supply_type':'ink cartridge','color':'yellow','compatible_family':'OfficeJet Pro 9100 series'},''),
('Brother TN830 Standard Yield Toner','TN830','Brother','https://www.brother-usa.com/supplies/tn830',{'supply_type':'toner','color':'black','compatible_family':'MFC-L2900DW series'},''),
('Brother TN830XL High Yield Toner','TN830XL','Brother','https://www.brother-usa.com/supplies/tn830xl',{'supply_type':'toner','color':'black','compatible_family':'MFC-L2900DW series'},''),
('Brother DR830 Drum Unit','DR830','Brother','https://www.brother-usa.com/supplies/dr830',{'supply_type':'drum unit','compatible_family':'MFC-L2900DW series'},''),
('Canon Toner Cartridge 075 Black','Toner 075 Black','Canon','https://www.usa.canon.com/shop/consumables/toner',{'supply_type':'toner','color':'black','compatible_family':'imageCLASS color laser series'},''),
('Canon Toner Cartridge 075 Cyan','Toner 075 Cyan','Canon','https://www.usa.canon.com/shop/consumables/toner',{'supply_type':'toner','color':'cyan','compatible_family':'imageCLASS color laser series'},''),
('Canon Toner Cartridge 075 Magenta','Toner 075 Magenta','Canon','https://www.usa.canon.com/shop/consumables/toner',{'supply_type':'toner','color':'magenta','compatible_family':'imageCLASS color laser series'},''),
('Canon Toner Cartridge 075 Yellow','Toner 075 Yellow','Canon','https://www.usa.canon.com/shop/consumables/toner',{'supply_type':'toner','color':'yellow','compatible_family':'imageCLASS color laser series'},''),
('Epson 502 Black Ink Bottle','502 Black','Epson','https://epson.com/For-Home/Ink-and-Paper/Ink-Bottles/c/ink-bottles',{'supply_type':'ink bottle','color':'black','compatible_family':'EcoTank ET-series'},''),
('Epson 502 Cyan Ink Bottle','502 Cyan','Epson','https://epson.com/For-Home/Ink-and-Paper/Ink-Bottles/c/ink-bottles',{'supply_type':'ink bottle','color':'cyan','compatible_family':'EcoTank ET-series'},''),
('Epson 502 Magenta Ink Bottle','502 Magenta','Epson','https://epson.com/For-Home/Ink-and-Paper/Ink-Bottles/c/ink-bottles',{'supply_type':'ink bottle','color':'magenta','compatible_family':'EcoTank ET-series'},''),
('Epson 502 Yellow Ink Bottle','502 Yellow','Epson','https://epson.com/For-Home/Ink-and-Paper/Ink-Bottles/c/ink-bottles',{'supply_type':'ink bottle','color':'yellow','compatible_family':'EcoTank ET-series'},''),
('Zebra Z-Select 4000D Direct Thermal Label Roll','Z-Select 4000D','Zebra','https://www.zebra.com/us/en/products/supplies/labels-tags.html',{'supply_type':'direct thermal label','compatibility':'Zebra desktop/industrial printers; sizes vary'},''),
]
for n,m,b,u,s,y in accessories:add('Printing Accessories','Ink / toner / drum / print media',n,b,m,u,{'published_features':s},y)

fields=['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes']
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
print('O rows',len(data),'subtypes',len(set(r['subcategory'] for r in data)),'brands',len(set(r['brand'] for r in data)),'duplicate keys',len(data)-len(set((r['brand'].lower(),r['model'].lower()) for r in data)))
print(dict(Counter(r['subcategory'] for r in data)))
