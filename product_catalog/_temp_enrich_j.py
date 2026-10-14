import csv,json,requests
from bs4 import BeautifulSoup
p='product_catalog/J-cameras-photography-imaging.csv'
with open(p,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f)); fields=list(rows[0])
update={
('Fujifilm','X-M5'):{'date':'2024-11','precision':'month','year':'2024','specs':{'sensor_format':'APS-C X-Trans CMOS 4','effective_resolution_mp':26.1,'processor':'X-Processor 5','video_max':'6.2K/30P','weight_g':355,'mount':'Fujifilm X mount'},'release_source':'https://www.fujifilm-x.com/en-in/news/introducing-fujifilm-x-m5/'},
('Nikon','Z6III'):{'date':'2024-06-17','precision':'announcement_date','year':'2024','specs':{'sensor_format':'full-frame partially stacked CMOS','effective_resolution_mp':24.5,'video_max':'6K/60p RAW','continuous_shooting_fps':120,'image_stabilization':'5-axis sensor-shift VR','lens_mount':'Nikon Z'},'price':'205995','currency':'INR','market':'India','price_type':'current_listed_offer','price_url':'https://www.nikon.co.in/products/cameras/mirrorless/z6iii-camera-kits','release_source':'https://www.nikon.co.in/articles/z-series/new-z6iii-offers-exceptional-specs-for-full-frame-mid-range-class-models'},
('Canon','EOS R5 Mark II'):{'date':'2024-07-17','precision':'announcement_date','year':'2024','specs':{'sensor_format':'full-frame stacked BSI CMOS','effective_resolution_mp':45,'continuous_shooting_fps':30,'video_max':'8K/60p RAW','autofocus':['Dual Pixel Intelligent AF','Eye Control AF'],'product_code':'6536C006'},'price':'4299','currency':'USD','market':'United States','price_type':'launch_msrp','price_url':'https://www.usa.canon.com/newsroom/2024/20240717-camera','release_source':'https://www.usa.canon.com/newsroom/2024/20240717-camera'},
('GoPro','HERO13 Black'):{'date':'2024-09-10','precision':'availability_date','year':'2024','specs':{'video_max':'5.3K/60fps','photo_resolution_mp':27,'waterproof_depth_m':10,'stabilization':'HyperSmooth 6.0','battery_capacity_mAh':1900,'wireless':'Wi-Fi 6','hdr':'10-bit HLG HDR','slow_motion_max':'400fps at 720p'},'price':'399.99','currency':'USD','market':'United States','price_type':'launch_msrp','price_url':'https://investor.gopro.com/press-releases/press-release-details/2024/GoPro-Announces-Two-New-Cameras-The-399-HERO13-Black-and-the-199-HERO/default.aspx','release_source':'https://investor.gopro.com/press-releases/press-release-details/2024/GoPro-Announces-Two-New-Cameras-The-399-HERO-and-the-199-HERO/default.aspx'} }
for r in rows:
 key=(r['brand'],r['model']);u=update.get(key)
 if not u:continue
 r['release_date']=u['date'];r['release_date_precision']=u['precision'];r['release_year']=u['year'];r['specifications_json']=json.dumps(u['specs'],ensure_ascii=False,separators=(',',':'))
 r['notes']=(r['notes']+' ' if r['notes'] else '')+'Release timing and specifications checked against official manufacturer launch information; release source: '+u['release_source']+'.'
 if u.get('price'):
  r['official_price']=u['price'];r['price_currency']=u['currency'];r['price_type']=u['price_type'];r['price_market']=u['market'];r['price_source_url']=u['price_url']
  r['notes']+=' Listed '+u['price_type'].replace('_',' ')+' is regional and may differ from current local retail pricing.'
 try:
  h=requests.get(r['product_url'],headers={'User-Agent':'Mozilla/5.0'},timeout=15).text
  soup=BeautifulSoup(h,'html.parser');m=soup.find('meta',attrs={'property':'og:image'});r['image_url']=m.get('content','') if m else r['image_url']
 except Exception:pass
with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
for r in rows:
 if r['model'] in ['X-M5','Z6III','EOS R5 Mark II','HERO13 Black']:print(r['brand'],r['model'],r['release_date'],r['official_price'],bool(r['image_url']))
