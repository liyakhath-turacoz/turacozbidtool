import csv, json, os, re
from datetime import date
from collections import Counter
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(__file__)
OUT = os.path.join(ROOT, 'F-kitchen-appliances.csv')
TODAY = date(2026, 10, 13).isoformat()
FIELDS = ['category_code','department','subcategory','product_type','product_name','manufacturer','brand','model','manufacturer_part_number','gtin','description','specifications_json','image_url','product_url','release_date','release_date_precision','release_year','official_price','price_currency','price_type','price_market','price_source_url','product_source_url','source_attribution','collected_on','verification_status','notes']
rows=[]

def add(sub, typ, name, brand, model, url, specs=None, desc=None, image='', price='', currency='', market='', price_type='', price_url='', year='', notes=''):
    rows.append(dict(category_code='F', department='Kitchen Appliances', subcategory=sub, product_type=typ,
        product_name=name, manufacturer=brand, brand=brand, model=model, manufacturer_part_number='', gtin='',
        description=desc or f'{name}; see manufacturer specifications at the linked official product page.',
        specifications_json=json.dumps(specs or {}, ensure_ascii=False, separators=(',',':')), image_url=image,
        product_url=url, release_date='', release_date_precision='', release_year=year, official_price=str(price),
        price_currency=currency, price_type=price_type, price_market=market, price_source_url=price_url,
        product_source_url=url, source_attribution='Official manufacturer product page or catalogue', collected_on=TODAY,
        verification_status='official_page_verified', notes=notes or 'Current official catalogue/product page verified. Release date not stated on the page; product age requires review.'))

# Cooking appliances: official Philips, Panasonic, Bosch pages.
add('Cooking Appliances','Air Fryer','Philips 1000 Series Airfryer 4.2 L','Philips','NA120/00','https://www.philips.co.in/c-p/NA120_00/1000-series-airfryer-1000-series-42l',{'capacity_l':4.2,'power_w':1300,'voltage_v':'220-240','frequency_hz':'50-60','max_temperature_c':200},'4.2 L air fryer with adjustable temperature and timer.')
add('Cooking Appliances','Air Fryer','Philips 1000 Series Airfryer 6.2 L','Philips','NA130/00','https://acc.philips.co.in/c-p/NA130_00/1000-series-airfryer-1000-series-62l',{'capacity_l':6.2},'6.2 L air fryer in the Philips 1000 Series.')
add('Cooking Appliances','Air Fryer','Philips 3000 Series Dual Basket Airfryer','Philips','NA352/00','https://www.philips.co.in/c-p/NA352_00/3000-series-dual-basket-airfryer/support',{'basket_configuration':'dual'},'Dual-basket air fryer; official support/product page identifies the model.')
add('Cooking Appliances','Connected Air Fryer','Philips 5000 Series Connected Airfryer','Philips','HD9255/90','https://www.philips.co.in/c-p/HD9255_90/airfryer-airfryer-5000-series-connected',{'capacity_l':4.1,'food_capacity_g':800,'programs':13,'connectivity':'connected'},'Connected 5000 Series air fryer, 4.1 L / 800 g capacity.')
add('Cooking Appliances','OTG Oven','Philips Avance Collection Oven Toaster Grill 36 L','Philips','HD6976/00','https://acc.philips.co.in/c-p/HD6976_00/avance-collection-oven-toast-grill',{'capacity_l':36,'power_w':2000,'voltage_v':'220-240','convection':True,'preset_programs':10,'timer_minutes':90},'36 L oven toaster grill with convection and preset programmes.')
add('Cooking Appliances','Convection Microwave Oven','Panasonic 27 L Convection Microwave Oven','Panasonic','NN-CT644M','https://www.panasonic.com/in/consumer/home-appliances/microwave-ovens/convection/nn-ct644m.html',{'capacity_l':27,'auto_menus':101,'convection':True,'cleaning':'vapor clean','magnetron_warranty_years':5,'dimensions_mm':'501x408x526','weight_kg':28},'27 L convection microwave with 101 menus and vapor-clean feature.')
add('Cooking Appliances','Convection Oven','Bosch 800 Series Single Wall Oven 30 inch','Bosch','HBL8454UC','https://www.bosch-home.com/us/en/product/cooking-baking/wall-ovens/single-ovens/HBL8454UC',{'capacity_cuft':4.6,'series':'800','type':'single wall oven'},price=3549,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/product/cooking-baking/wall-ovens/single-ovens/HBL8454UC')
add('Cooking Appliances','Convection Oven','Bosch 500 Series Single Wall Oven 30 inch','Bosch','HBL5451UC','https://www.bosch-home.com/us/en/product/cooking-baking/wall-ovens/single-ovens/HBL5451UC',{'capacity_cuft':4.6,'series':'500','type':'single wall oven'},price=2899,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/product/cooking-baking/wall-ovens/single-ovens/HBL5451UC')
add('Cooking Appliances','Convection Oven','Bosch Benchmark Side-Swing Wall Oven','Bosch','HBLP451RUC','https://www.bosch-home.com/us/en/product/cooking-baking/wall-ovens/single-ovens/HBLP451RUC',{'series':'Benchmark','door_opening':'right-side swing'},price=4049,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/product/cooking-baking/wall-ovens/single-ovens/HBLP451RUC')
add('Cooking Appliances','Combination Oven','Bosch 800 Series Combination Oven','Bosch','HBL8743UC','https://www.bosch-home.com/us/en/product/cooking-baking/wall-ovens/combination-ovens/HBL8743UC',{'series':'800','type':'wall oven + microwave combination'},price=6249,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/category/cooking-baking/wall-ovens/combination-ovens')
add('Cooking Appliances','Combination Oven','Bosch 800 Series Combination Oven HBL8753UC','Bosch','HBL8753UC','https://www.bosch-home.com/us/en/category/cooking-baking/wall-ovens/combination-ovens',{'series':'800','type':'combination oven'},price=6049,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/category/cooking-baking/wall-ovens/combination-ovens',notes='Model and current price are listed in the official Bosch combination-oven catalogue; dedicated detail URL not captured.')
add('Cooking Appliances','Combination Oven','Bosch 800 Series Speed Oven HBL87M53UC','Bosch','HBL87M53UC','https://www.bosch-home.com/us/en/category/cooking-baking/wall-ovens/combination-ovens',{'series':'800','type':'combination oven'},price=5049,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/category/cooking-baking/wall-ovens/combination-ovens',notes='Model and current price are listed in the official Bosch combination-oven catalogue; dedicated detail URL not captured.')
add('Cooking Appliances','Combination Oven','Bosch 500 Series Combination Oven HBL57M52UC','Bosch','HBL57M52UC','https://www.bosch-home.com/us/en/category/cooking-baking/wall-ovens/combination-ovens',{'series':'500','type':'combination oven'},price=4449,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/category/cooking-baking/wall-ovens/combination-ovens',notes='Model and current price are listed in the official Bosch combination-oven catalogue; dedicated detail URL not captured.')

# Cooktops and stoves: seven distinct current Bosch induction models from its official category catalogue.
for model,series,size,price in [('NIT8661UC','800',36,3099),('NITP060UC','Benchmark',30,3099),('NIT8061UC','800',30,2649),('NITP660UC','Benchmark',36,3699),('NIT5663UC','500',36,2549),('NIT5063UC','500',30,2149),('NIT8461UC','800',24,2049)]:
    url=f'https://www.bosch-home.com/us/en/product/cooking-baking/induction-electric-cooktops/induction-cooktops/{model}'
    add('Cooktops & Stoves','Induction Cooktop',f'Bosch {series} Series Induction Cooktop {size} inch','Bosch',model,url,{'series':series,'width_in':size,'cooktop_type':'induction'},price=price,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/category/cooking-baking/induction-electric-cooktops/induction-cooktops',notes='Model, size/series and current price listed on official Bosch category page; release year not stated.')

# Kitchen ventilation: current Bosch chimney-hood catalogue.
hoods=[('HIB82651UC','800 Series Island Hood 42 inch',2549),('HCG56651UC','Benchmark Wall Hood 36 inch',2349),('HCB56651UC','500 Series Wall Hood 36 inch',1849),('HCB50651UC','500 Series Wall Hood 30 inch',1749),('HCP86641UC','800 Series Wall Hood 36 inch Black Stainless',1749),('HCP36E52UC','300 Series Wall Hood 36 inch',1449),('HCP34E52UC','300 Series Wall Hood 30 inch',1249),('HCP56652UC','500 Series Wall Hood 36 inch',1849),('HCP50652UC','500 Series Wall Hood 30 inch',1749),('HCP80641UC','800 Series Wall Hood 30 inch',1549),('HCP30E52UC','300 Series Wall Hood 30 inch',1399)]
for model,name,price in hoods:
    url=f'https://www.bosch-home.com/us/en/product/cooking-baking/ventilation/chimney-hoods/{model}'
    add('Kitchen Ventilation','Range Hood / Extractor Hood',f'Bosch {name}','Bosch',model,url,{'hood_style':'wall-mounted' if 'Wall' in name else 'island','model':model},price=price,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/category/cooking-baking/ventilation/chimney-hoods',notes='Current model and listed price verified in official Bosch ventilation catalogue; confirm dimensions and airflow on product page.')

# Philips food preparation products: official catalogue and individual product pages.
philips_mixers=[('HL7777/00','Avance Collection Mixer Grinder',750,'https://www.philips.co.in/c-p/HL7777_00/avance-collection-mixer-grinder',16995),('HL7511/00','Daily Collection Mixer Grinder',550,'https://www.philips.co.in/c-p/HL7511_00/daily-collection-mixer-grinder',None),('HL7505/00','Mixer Grinder',500,'https://www.philips.co.in/c-m-ho/food-preparation/mixer-grinder/all',3995),('HL7555/00','Mixer Grinder',600,'https://www.philips.co.in/c-m-ho/food-preparation/mixer-grinder/all',None),('HL7760/00','Viva Collection Mixer Grinder',None,'https://www.philips.co.in/c-p/HL7760_00/viva-collection-mixer-grinder/support',None),('HL7763/00','Viva Collection Mixer Grinder',None,'https://www.philips.co.in/c-p/HL7763_00/viva-collection-mixer-grinder/support',None),('HL1646/00','Viva Collection Mixer Grinder',None,'https://www.philips.co.in/c-p/HL1646_00/viva-collection-mixer-grinder/support',None),('HL1645/00','Mixer Grinder',None,'https://www.philips.co.in/c-p/HL1645_00/mixer-grinder/support',None),('HL7720/00','Mixer Grinder',None,'https://www.philips.co.in/c-p/HL7720_00/mixer-grinder/support',None)]
for model,name,w,url,price in philips_mixers:
    specs={'motor_power_w':w} if w else {}
    add('Food Preparation','Mixer Grinder',f'Philips {name} {model}','Philips',model,url,specs,price=price or '',currency='INR' if price else '',market='India' if price else '',price_type='official_suggested_price' if price else '',price_url='https://www.philips.co.in/c-m-ho/food-preparation/mixer-grinder/all' if price else '',notes='Listed in Philips India official catalogue. Exact launch date not stated; older support-only models need age/current-sales review.' if '/support' in url else 'Current official product/catalogue page verified; release date not stated.')

# Official Prestige India category listings are scraped at run time so the output can be resumed from their current catalogue.
session=requests.Session(); session.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'})
def prestige_cards(url, sub, typ, limit=18):
    try:
        soup=BeautifulSoup(session.get(url,timeout=25).text,'html.parser')
        for a in soup.select('a.product-item-link')[:limit]:
            p=a.find_parent(class_='product-item-info') or a.parent
            title=a.get_text(' ',strip=True)
            product_url=a.get('href','')
            if not title or not product_url: continue
            # The product page declares its SKU; never derive an invented model from the marketing title.
            model=''; image=''; details={}; price=''
            try:
                ps=BeautifulSoup(session.get(product_url,timeout=20).text,'html.parser')
                sku=ps.select_one('.product.attribute.sku .value, .product.attribute.sku')
                if sku:
                    model=re.sub(r'^SKU\s*','',sku.get_text(' ',strip=True),flags=re.I)
                im=ps.select_one('meta[property="og:image"]')
                if im: image=im.get('content','')
                spec=' '.join(x.get_text(' ',strip=True) for x in ps.select('.product.attribute .value, .additional-attributes .data'))
                m=re.search(r'(?i)(\d{3,4})\s*W(?:att)?',title+' '+spec)
                if m: details['power_w']=int(m.group(1))
            except Exception: pass
            txt=(p.get_text(' ',strip=True) if p else '')
            m=re.search(r'(?:As low as|Regular Price)\s*₹\s*([0-9 ,]+(?:\.\d{1,2})?)',txt,re.I)
            if m: price=re.sub(r'\s+','',m.group(1))
            add(sub,typ,title,'Prestige',model,product_url,details,desc=title,image=image,price=price,currency='INR' if price else '',market='India' if price else '',price_type='current_listed' if price else '',price_url=url if price else '',notes='Official Prestige India listing/product page. Model is the manufacturer-declared SKU where captured; release date/year not stated and age needs review.' if model else 'Official Prestige India listing; manufacturer SKU not exposed to scraper. Model/release date/year require review.')
    except Exception as e:
        print('Prestige listing fetch failed',url,repr(e))

prestige_cards('https://shop.ttkprestige.com/food-preparation-appliances/mixer-grinder/mixer-grinder-collections.html','Food Preparation','Mixer Grinder',18)
prestige_cards('https://shop.ttkprestige.com/food-preparation-appliances/mixer-grinder/food-processor-collections.html','Food Preparation','Food Processor',12)
prestige_cards('https://shop.ttkprestige.com/breakfast-and-snacks-appliances/toasters/waffle-maker-toasters.html','Breakfast Appliances','Waffle Maker',12)

# Breakfast appliances: Philips official products and prices where the official store publishes them.
for model,name,url,power,price in [('HD2582/00','Daily Collection Toaster','https://www.philips.co.in/c-p/HD2582_00/daily-collection-toaster',None,2495),('HD2583/90','Daily Collection Toaster with Sandwich Rack','https://www.philips.co.in/c-p/HD2583_90/daily-collection-toaster',None,2995),('HD2512/00','Toaster','https://www.domesticappliances.philips.co.in/collections/toaster',None,2095),('HD2289/00','Viva Collection Panini Maker','https://www.philips.co.in/c-p/HD2289_00/viva-collection-panini-maker',None,3795)]:
    add('Breakfast Appliances','Toaster' if 'Toaster' in name else 'Sandwich Maker',f'Philips {name} {model}','Philips',model,url,{'settings':8} if model in ('HD2582/00','HD2583/90') else {},price=price,currency='INR',market='India',price_type='official_listed',price_url='https://www.domesticappliances.philips.co.in/collections/toaster' if 'Toaster' in name else 'https://www.philips.co.in/c-m-ho/cooking/sandwich-maker/latest',notes='Official listing reports current price; model launch date not stated.')

# Beverage appliances: official espresso and kettle catalogue models.
add('Beverage Appliances','Fully Automatic Espresso Machine','Philips Series 2200 Fully Automatic Espresso Machine','Philips','EP2230/10','https://www.philips.co.in/c-p/EP2230_10/series-2200-fully-automatic-espresso-machines',{'beverages':3,'milk_system':'LatteGo','display':'touch'},'Fully automatic espresso machine with LatteGo milk system and three beverage choices.')
add('Beverage Appliances','Fully Automatic Espresso Machine','Philips Series 3200 Fully Automatic Espresso Machine','Philips','EP3221/40','https://www.philips.co.in/c-p/EP3221_40/series-3200-fully-automatic-espresso-machines',{'beverages':4,'milk_system':'classic milk frother','display':'touch'},'Series 3200 fully automatic espresso machine.')
for model,name,url,specs in [('HD9306/06','Daily Collection Kettle','https://www.philips.co.in/c-p/HD9306_06/daily-collection-kettle',{'capacity_l':1.5,'power_w':1800,'body':'stainless steel'}),('HD9316/06','Viva Collection Kettle','https://www.philips.co.in/c-p/HD9316_06/viva-collection-kettle/support',{'capacity_l':1.7,'power_w':1800,'keep_warm':True}),('HD9329/06','Viva Collection Double-Wall Kettle','https://www.philips.co.in/c-p/HD9329_06/viva-collection-double-wall/support',{}),('HD9303/02','Daily Collection Kettle','https://www.philips.co.in/c-p/HD9303_02/daily-collection-kettle/support',{}),('HD9344/14','Daily Collection Kettle','https://www.philips.co.in/c-p/HD9344_14/daily-collection-kettle/support',{})]:
    add('Beverage Appliances','Electric Kettle',f'Philips {name} {model}','Philips',model,url,specs,notes='Official Philips product/support listing verified; release year and current sale status are not stated on this support page.')

# Specialty cooking: official Instant Brands model pages and product announcements.
add('Specialty Cooking','Multi-Cooker','Instant Pot 12-Cup Grain and Rice Multi-Cooker','Instant Pot','12-Cup Grain and Rice Multi-Cooker','https://instantpot.com/products/instant-pot-12-cup-grain-and-rice-multi-cooker',{'capacity_cups':12,'functions':7,'power_w':600,'voltage_v':120,'keep_warm_hours':10},'Multi-cooker for grain and rice cooking. Manufacturer page lists a May 2025 publication date.',price='',notes='Official Instant Pot product page published 2025-05-01; model identifier not separately stated.')
add('Specialty Cooking','Electric Pressure Cooker','Instant Pot Duo Plus 6 Quart V3','Instant Pot','Duo Plus 6QT V3','https://instantpot.com/collections/multi-cookers/products/instant-pot-duo-plus-6qt-multi-use-pressure-cooker-v3',{'capacity_qt':6,'functions':9,'power_w':1000,'voltage_v':120,'frequency_hz':60},'Multi-use pressure cooker. Manufacturer page lists a May 2025 publication date.',notes='Official Instant Pot product page published 2025-05-01.')
add('Specialty Cooking','Induction Cooktop','Prestige PIC 20.0 Induction Cooktop','Prestige','PIC 20.0','https://shop.ttkprestige.com/blog/post/buying-guides/top-8-prestige-kitchen-appliance-gifts-for-a-healthy-lifestyle-and-cooking',{'type':'induction cooktop'},notes='Model named in the manufacturer’s 2025 kitchen-appliance guide; detailed specs, dedicated product page and current price need verification.')
add('Specialty Cooking','Rice Cooker','Prestige PRWO Rice Cooker','Prestige','PRWO','https://shop.ttkprestige.com/blog/post/buying-guides/top-8-prestige-kitchen-appliance-gifts-for-a-healthy-lifestyle-and-cooking',{'type':'rice cooker'},notes='Model named in the manufacturer’s 2025 product guide; exact SKU, detailed specs, dedicated product page and current price need verification.')

# Kitchen accessories with official Bosch / Philips part numbers.
add('Kitchen Accessories','Air Fryer Baking Accessory','Philips Airfryer Essential XL Baking Kit','Philips','HD9945/01','https://www.philips.co.in/c-p/HD9945_01/airfryer-accessory-essential-xl-baking-kit',{'accessory_capacity_l':2,'included_items':'baking accessory; 9 silicone muffin cups'},'Baking kit accessory for compatible Philips Airfryer XL models.')
add('Kitchen Accessories','Air Fryer Accessory','Philips Airfryer Double-Layer Accessory','Philips','HD9904/00','https://www.philips.co.in/c-m-ho/cooking-accessories/airfryer-accessories/all',{'type':'double-layer accessory'},notes='Model listed in official Philips Airfryer accessories catalogue; compatibility details need verification.')
add('Kitchen Accessories','Air Fryer Baking Accessory','Philips Airfryer Baking Kit L','Philips','HD9925/01','https://www.philips.co.in/c-m-ho/cooking-accessories/airfryer-accessories/all',{'type':'baking kit','size':'L'},notes='Model listed in official Philips Airfryer accessories catalogue; compatibility details need verification.')
for model,name,url,price,specs in [('11041554','Bosch Pizza Pan','https://www.bosch-home.com/us/en/product/cooking-baking/cooking-and-baking-accessories/baking-pan/baking-stones/11041554',59.50,{'diameter_in':13.8,'height_in':1.2,'max_temperature_f':572}),('00097367','Bosch Pizza Peel / Paddle','https://www.bosch-home.com/us/en/category/cooking-baking/cooking-and-baking-accessories',47.99,{}),('00666710','Bosch Broiler Pan','https://www.bosch-home.com/us/en/category/cooking-baking/cooking-and-baking-accessories',35.99,{}),('00666709','Bosch Baking Tray','https://www.bosch-home.com/us/en/category/cooking-baking/cooking-and-baking-accessories',32.50,{}),('00743254','Bosch Baking Tray','https://www.bosch-home.com/us/en/category/cooking-baking/cooking-and-baking-accessories',68.99,{})]:
    add('Kitchen Accessories','Oven Tray / Attachment',name,'Bosch',model,url,specs,price=price,currency='USD',market='US',price_type='current_listed',price_url='https://www.bosch-home.com/us/en/category/cooking-baking/cooking-and-baking-accessories',notes='Part number and current listed price verified in official Bosch accessory catalogue; compatible appliance models require review.')

# Remove exact duplicates if source subcategories overlap and preserve first occurrence.
unique=[]; seen=set()
for r in rows:
    key=(r['brand'].lower(),r['model'].lower()) if r['model'] else (r['brand'].lower(),r['product_name'].lower(),r['subcategory'])
    if key in seen: continue
    seen.add(key); unique.append(r)
rows=unique
with open(OUT,'w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
print('F records',len(rows),'subtypes',dict(sorted(Counter(r['subcategory'] for r in rows).items())),'brands',len(set(r['brand'] for r in rows)))
print('missing model',sum(not r['model'] for r in rows),'missing image',sum(not r['image_url'] for r in rows),'missing price',sum(not r['official_price'] for r in rows),'missing year',sum(not r['release_year'] for r in rows))
