import csv,json,os,requests
from bs4 import BeautifulSoup
root=os.path.dirname(__file__);path=os.path.join(root,'I-personal-care-grooming-appliances.csv')
with open(path,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f)); fields=list(rows[0])
items=[
{'subcategory':'Hair Care','product_type':'Hair Dryer','product_name':'Dyson Supersonic Nural Hair Dryer','manufacturer':'Dyson Technology India Pvt Ltd','brand':'Dyson','model':'HD16','product_url':'https://www.dyson.in/supersonic-nural-hair-dryer-blue-topaz','release_year':'2024','price':'41900','currency':'INR','market':'India','specs':{'motor_power_w':1380,'airflow_lps':13.3,'weight_kg':0.66,'scalp_protect_target_temperature_c':55,'smart_features':['time-of-flight scalp protection','attachment recognition','pause detection'],'model_family':'Supersonic Nural'},'notes':'Dyson India product page lists HD16 and ₹41,900; Dyson India hair-care page identifies Supersonic Nural as a 2024 product. Price and specifications are manufacturer-published.'},
{'subcategory':'Shaving & Grooming','product_type':'Electric Shaver','product_name':'Braun Series 9 PRO+ Electric Shaver 9677cc','manufacturer':'Procter & Gamble (Braun)','brand':'Braun','model':'9677cc','product_url':'https://us.braun.com/en-us/male-grooming/electric-shavers/series-9-pro-power-case-9677cc','release_year':'','price':'449.99','currency':'USD','market':'United States','specs':{'shaving_elements':'5+1','battery_runtime_min':60,'full_charge_min':60,'quick_charge_min':5,'waterproof':'100% wet & dry','head_adaptation_degrees':40,'included_accessories':['6-in-1 SmartCare Center','PowerCase','cleaning cartridge','travel pouch']},'notes':'Official Braun US page lists the model, technical specs and MSRP $449.99 (sale price may vary). The current product page does not establish the original launch year; age needs verification before using the 3-year recency filter.'},
{'subcategory':'Shaving & Grooming','product_type':'Multi-Grooming Trimmer','product_name':'Xiaomi Grooming Kit','manufacturer':'Xiaomi Communications Co., Ltd.','brand':'Xiaomi','model':'Xiaomi Grooming Kit','product_url':'https://www.mi.com/in/product/xiaomi-grooming-kit/','release_year':'','price':'','currency':'','market':'','specs':{'minimum_trim_length_mm':0.5,'length_settings_count':40,'length_range_mm':'0.5–20','charging_port':'USB Type-C','runtime_min':90,'quick_charge_min':5,'quick_charge_runtime_min':10,'attachments':['U blade','precision blade','body grooming blade','nose and ear trimmer'],'washable_attachments':True},'notes':'Official Xiaomi India product page supplies model family and listed specifications. No reliable release year or price was captured; age and current availability need verification.'}
]
existing={(r['brand'].strip().lower(),r['model'].strip().lower()) for r in rows}; added=[]
for it in items:
 if (it['brand'].lower(),it['model'].lower()) in existing:continue
 src=it['product_url'];img=''
 try:
  html=requests.get(src,headers={'User-Agent':'Mozilla/5.0'},timeout=20).text
  soup=BeautifulSoup(html,'html.parser');m=soup.find('meta',attrs={'property':'og:image'});img=m.get('content','') if m else ''
 except Exception:pass
 notes=it['notes'];missing=[]
 if not it['release_year']:missing.append('release year not established')
 if not it['price']:missing.append('official price not captured')
 if not img:missing.append('official image URL not captured')
 if missing:notes += ' Missing/unverified fields: '+', '.join(missing)+'.'
 added.append(dict(category_code='I',department='Personal Care & Grooming Appliances',subcategory=it['subcategory'],product_type=it['product_type'],product_name=it['product_name'],manufacturer=it['manufacturer'],brand=it['brand'],model=it['model'],manufacturer_part_number=it['model'],gtin='',description=it['product_name'],specifications_json=json.dumps(it['specs'],ensure_ascii=False,separators=(',',':')),image_url=img,product_url=src,release_date='',release_date_precision='year' if it['release_year'] else '',release_year=it['release_year'],official_price=it['price'],price_currency=it['currency'],price_type='current_listed' if it['price'] else '',price_market=it['market'],price_source_url=src if it['price'] else '',product_source_url=src,source_attribution='Official manufacturer product page',collected_on='2026-10-13',verification_status='official_page_verified',notes=notes))
with open(path,'a',encoding='utf-8-sig',newline='') as f:csv.DictWriter(f,fieldnames=fields).writerows(added)
print('Added:',[(x['brand'],x['model'],x['official_price'],bool(x['image_url'])) for x in added])
