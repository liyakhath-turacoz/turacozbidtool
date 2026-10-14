import csv,json
from pathlib import Path
p=Path(__file__).with_name('H-air-conditioning-cooling-air-quality.csv')
with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
fields=list(rows[0])
items={
 'AS-Q11FNVE':{
  'name':'LG 0.8 Ton 2 Star Inverter Split AC AS-Q11FNVE','url':'https://www.lg.com/in/air-conditioners/split-air-conditioners/as-q11fnve/','image':'https://www.lg.com/content/dam/channel/wcms/in/images/split-ac/as-q11fnve-v1/2010x1334-1.jpg/jcr%3Acontent/renditions/thum-1600x1062.jpeg?w=800','date':'2025-12','year':'2025','precision':'month','gtin':'8806096676813','cap':2930,'max':3200,'power':1010,'star':2,'dims':'682x299x185','indoor_kg':6.6,'outdoor_kg':20.0,'product_model':'ASNQ11FNVE.AMLG','features':['Auto Clean','Gold Fin+','Diet Mode+','Viraat Mode','Stabilizer Free operation','6-in-1 cooling']},
 'AS-Q18ZNXE':{
  'name':'LG 1.5 Ton 3 Star Inverter Split AC AS-Q18ZNXE','url':'https://www.lg.com/in/air-conditioners/split-air-conditioners/as-q18znxe-n/','image':'https://www.lg.com/content/dam/channel/wcms/in/split-ac/gallery/2026/single-inverter/as-q18znxe/AS-Q18ZNXE-ANLG-2010x1334-1-v.jpg/jcr%3Acontent/renditions/thum-1600x1062.jpeg?w=800','date':'2026-01','year':'2026','precision':'month','gtin':'8806096772379','cap':4400,'max':5000,'power':1270,'star':3,'dims':'837x308x189','indoor_kg':8.0,'outdoor_kg':23.5,'product_model':'ASNQ18ZNXE.ANLG','features':['AI Convertible 6-in-1 Cooling','Auto Clean','Gold Fin+','Diet Mode+','Viraat Mode','Stabilizer Free operation','Dehumidification']},
 'AS-Q19XNXE':{
  'name':'LG 1.5 Ton 3 Star AI Convertible Inverter Split AC AS-Q19XNXE','url':'https://www.lg.com/in/air-conditioners/split-air-conditioners/as-q19xnxe-p/','image':'https://www.lg.com/content/dam/channel/wcms/in/split-ac/gallery/new/single-inverter/as-q19xnxe/AS-Q19XNXE-AMLG-2010x1334-1-v.jpg/jcr%3Acontent/renditions/thum-1600x1062.jpeg?w=800','date':'2026-01','year':'2026','precision':'month','gtin':'','cap':5000,'max':5500,'power':1750,'star':3,'dims':'998x345x210','indoor_kg':11.0,'outdoor_kg':23.5,'product_model':'ASNQ19XNXE.AMLG','features':['AI Convertible 6-in-1 Cooling','AI cooling mode','Gold Fin+','Diet Mode+','Viraat Mode','Stabilizer Free operation']}}
by={r['model']:r for r in rows}
for model,it in items.items():
    if model not in by:
        rows.append({'category_code':'H','department':'Air Conditioning, Cooling & Air Quality','subcategory':'Air Conditioners','product_type':'Split Inverter Air Conditioner','product_name':it['name'],'manufacturer':'LG','brand':'LG','model':model,'manufacturer_part_number':model,'gtin':'','description':'','specifications_json':'{}','image_url':'','product_url':'','release_date':'','release_date_precision':'','release_year':'','official_price':'','price_currency':'','price_type':'','price_market':'','price_source_url':'','product_source_url':'','source_attribution':'','collected_on':'2026-10-13','verification_status':'official_source_verified','notes':''})
        by[model]=rows[-1]
    r=by[model]
    r.update(product_name=it['name'],manufacturer='LG',brand='LG',model=model,manufacturer_part_number=model,gtin=it['gtin'],
      description=f"{it['name']} with {it['cap']} W rated / {it['max']} W maximum cooling, {it['star']}-star rating and R32 refrigerant.",
      specifications_json=json.dumps({'installation':'wall-mounted split','refrigerant':'R32','compressor':'inverter','cooling_capacity_rated_w':it['cap'],'cooling_capacity_max_w':it['max'],'power_consumption_rated_w':it['power'],'energy_rating_star':it['star'],'input_voltage_v':230,'frequency_hz':50,'indoor_unit_dimensions_mm':it['dims'],'indoor_unit_weight_kg':it['indoor_kg'],'outdoor_unit_weight_kg':it['outdoor_kg'],'indoor_unit_color':'white','features':it['features'],'launching_month':it['date'],'product_model_name':it['product_model']},ensure_ascii=False,separators=(',',':')),
      image_url=it['image'],product_url=it['url'],release_date=it['date'],release_date_precision=it['precision'],release_year=it['year'],
      official_price='',price_currency='',price_type='',price_market='India',price_source_url='',product_source_url=it['url'],
      source_attribution='Official LG India product page; launch month and technical specifications verified',collected_on='2026-10-13',verification_status='official_product_page_verified',
      notes=f"LG India product page confirms the model, release month {it['date']}, technical specifications and product image. No official purchase price captured, so price is blank.")
with p.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('H LG models refreshed; H rows',len(rows))
