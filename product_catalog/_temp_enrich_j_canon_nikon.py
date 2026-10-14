import csv,json
from pathlib import Path
p=Path(__file__).with_name('J-cameras-photography-imaging.csv')
with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
fields=list(rows[0]); by={r['model']:r for r in rows}
canon_release='https://www.usa.canon.com/newsroom/2025/20250326-camera'
for model in ('EOS R6 Mark III','ZR'):
    r=by[model]
    if model=='EOS R6 Mark III':
        r.update(manufacturer_part_number='7084C002',product_url='https://www.usa.canon.com/shop/p/eos-r6-mark-iii',product_source_url='https://www.usa.canon.com/shop/p/eos-r6-mark-iii',
          description='Full-frame mirrorless hybrid camera with 32.5 MP sensor, up to 40 fps still capture, in-body stabilization, and internal 7K RAW video.',
          specifications_json=json.dumps({'camera_type':'full-frame interchangeable-lens mirrorless','sensor':'35.9 x 23.9 mm CMOS','effective_pixels_mpx':32.5,'processor':'DIGIC X','max_continuous_shooting_fps':40,'pre_capture_frames':20,'in_body_stabilization_stops_center':8.5,'memory_cards':['CFexpress Type B','SD UHS-II'],'max_internal_video':'7K 59.94p 12-bit Canon RAW Light','4k_video_fps_max':119.8,'video_dynamic_range_stops':'15+','lens_mount':'Canon RF'},separators=(',',':')),
          release_date='2025-11-06',release_date_precision='day',release_year='2025',official_price='2799.00',price_currency='USD',price_type='launch_msrp',price_market='United States',price_source_url='https://www.usa.canon.com/newsroom/2025/20251106-consumer',
          source_attribution='Official Canon U.S. product specifications and launch announcement',verification_status='official_sources_verified',
          notes='Canon U.S. launch announcement establishes release timing and estimated launch retail price. Canon product page provides the detailed specs, but currently marks the body discontinued; USD 2,799 is the launch MSRP, not a current offer. Product image URL not captured.')
    else:
        r.update(manufacturer_part_number='ZR',product_url='https://www.nikon.co.in/zr-body',product_source_url='https://www.nikon.co.in/zr-body',
          description='Compact full-frame cinema camera with RED colour science, internal 6K RAW recording and 32-bit float audio capture.',
          specifications_json=json.dumps({'camera_type':'full-frame cinema camera','sensor':'35.9 x 23.9 mm CMOS','effective_pixels_mpx':24.5,'total_pixels_mpx':26.79,'video_internal':'6K/59.94p 12-bit R3D NE RAW','dynamic_range_stops':'15+','base_iso':[800,6400],'audio':'32-bit float internal and external microphone recording','monitor_in':4.0,'weight_g_body_only':540,'dimensions_mm':'133 x 80.5 x 49','lens_mount':'Nikon Z','image_stabilization':'5-axis sensor-shift'},separators=(',',':')),
          release_date='2025-10-16',release_date_precision='day',release_year='2025',official_price='186995',price_currency='INR',price_type='manufacturer_listed_mrp',price_market='India',price_source_url='https://www.nikon.co.in/zr-body',
          source_attribution='Official Nikon ZR India product page and Nikon release announcement',verification_status='official_sources_verified',
          notes='Nikon announced the ZR on 2025-09-10 and stated availability from 2025-10-16. Current Nikon India body-only MRP is INR 186,995. Technical specs captured from Nikon India product page; page image did not load during verification.')

def add(name,sub,type_,model,mpn,url,source,release_date,specs,description,price,notes):
    if model in by:return
    r={'category_code':'J','department':'Cameras, Photography & Imaging','subcategory':sub,'product_type':type_,'product_name':name,'manufacturer':'Canon','brand':'Canon','model':model,'manufacturer_part_number':mpn,'gtin':'','description':description,'specifications_json':json.dumps(specs,ensure_ascii=False,separators=(',',':')),'image_url':'','product_url':url,'release_date':release_date,'release_date_precision':'month','release_year':'2025','official_price':str(price),'price_currency':'USD','price_type':'launch_estimated_retail','price_market':'United States','price_source_url':source,'product_source_url':url,'source_attribution':'Official Canon product/support page and 2025 launch announcement','collected_on':'2026-10-13','verification_status':'official_sources_verified','notes':notes}
    rows.append(r);by[model]=r

add('Canon EOS R50 V APS-C Video Mirrorless Camera','Digital Cameras','APS-C Mirrorless Video Camera','EOS R50 V','6895C002','https://www.usa.canon.com/shop/p/eos-r50-v-body',canon_release,'2025-04',
    {'sensor':'APS-C CMOS','effective_pixels_mpx':24.2,'processor':'DIGIC X','video':['4K crop 59.94p','4K full-width 29.97p','Full HD 119.8p'],'autofocus':'Dual Pixel CMOS AF II','recording_features':['Canon Log 3','HLG','PQ','false color','zebras'],'wireless':'2.4/5 GHz Wi-Fi','live_streaming_methods':['UVC/UAC','HDMI','Camera Connect','Live Switcher Mobile'],'audio_accessory_shoe':'24-bit/4-channel LPCM'},
    'Video-first APS-C mirrorless camera for creators with interchangeable RF lenses, vertical shooting support, and built-in livestream workflows.',649.99,
    'Canon announced availability in April 2025 and US body-only estimated retail price of USD 649.99. Price is launch estimate, not current price; Canon currently marks the product page discontinued. Manufacturer image URL not captured.')

add('Canon PowerShot V1 Video-First Compact Camera','Digital Cameras','Video-First Compact Camera','PowerShot V1','6390C001','https://www.usa.canon.com/support/p/powershot-v1',canon_release,'2025-04',
    {'sensor':'1.4-type CMOS, 18.4 x 12.3 mm','still_effective_pixels_mpx':22.3,'video_effective_pixels_mpx':18.7,'processor':'DIGIC X','lens':'16-50 mm equivalent for stills, f/2.8-4.5; approx. 17-52 mm equivalent for movies','autofocus':'Dual Pixel CMOS AF II','continuous_stills_fps':30,'cooling':'built-in fan','video':'4K recording','connectivity':['USB','Wi-Fi','Canon Camera Connect']},
    'Fixed-lens compact camera designed for video creators, with an integrated cooling fan, front record control, vari-angle touchscreen, and wide-angle zoom lens.',899.99,
    'Canon announced PowerShot V1 availability for April 2025 at an estimated US retail price of USD 899.99. Price is launch estimate. Technical values are transcribed from the Canon launch announcement and official support page; product image URL not captured.')

with p.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('J rows',len(rows),'; Nikon ZR and Canon R6 Mark III updated; added recent Canon camera models')
