import csv
from pathlib import Path
p=Path('product_catalog/C-tvs-video-home-entertainment.csv')
imgs={
('Panasonic','TV-65Z95B'):'https://panasonicjp.scene7.com/is/image/panasonicjp/TV-65Z95B_%E6%AD%A3%E9%9D%A2%E3%82%B5%E3%82%A4%E3%82%BA%E3%81%AF%E3%82%81%E8%BE%BC%E3%81%BF%E3%81%82%E3%82%8A?fmt=png-alpha',
('Panasonic','TV-65Z90B'):'https://panasonicjp.scene7.com/is/image/panasonicjp/TV-65Z90B_%E6%AD%A3%E9%9D%A2%E3%82%B5%E3%82%A4%E3%82%BA%E3%81%AF%E3%82%81%E8%BE%BC%E3%81%BF%E3%81%82%E3%82%8A?fmt=png-alpha&wid=1200&hei=630',
('Panasonic','DP-UB45S'):'https://panasonicjp.scene7.com/is/image/panasonicjp/DP-UB45S_%E3%83%95%E3%83%AA?fmt=png-alpha&wid=1200&hei=630',
('Panasonic','DMP-BD90S'):'https://panasonicjp.scene7.com/is/image/panasonicjp/DMP-BD90S-K_%E3%83%95%E3%83%AA?fmt=png-alpha&wid=1200&hei=630',
('Hisense','100U8QG'):'https://www.hisense-usa.com/product-page/quality_auto/991681_b16271f994e04a3dad706c494093c20e~mv2.jpg',
('Optoma','GT4000UHD'):'https://region-resource.optoma.com/country/ig4Jh8LWF0uqQAoDpEV0qNhWtjuQPVexkNYv4Q3k.png',
('NEBULA','Cosmos 4K SE'):'https://www.ankerjapan.com/cdn/shop/files/D2342001_1200x1200.jpg?v=1751506553',
('Sony','K-65XR80M2'):'https://d1ncau8tqf99kp.cloudfront.net/converted/125820_original_local_1200x1050_v3_converted.webp',
('Sony','K-65XR50'):'https://d1ncau8tqf99kp.cloudfront.net/converted/125729_original_local_1200x1050_v3_converted.webp',
('Sony','SU-WL905'):'https://sony.scene7.com/is/image/sonyglobalsolutions/TVFY23_WL905_Primary_image?%24primaryshotPreset%24&fmt=pjpeg&resMode=bisharp&wid=180'}
with p.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);cols=r.fieldnames;rows=list(r)
updated=0
for x in rows:
 u=imgs.get((x['brand'],x['model']))
 if u and not x['image_url']:x['image_url']=u;updated+=1
with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
print('Image URLs added',updated)
