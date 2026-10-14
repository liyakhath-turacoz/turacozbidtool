import csv,json
from pathlib import Path
p=Path(__file__).with_name('K-gaming-virtual-reality.csv')
with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
by={r['model']:r for r in rows}
def setrow(model,specs,description,url,notes,price='',currency='',market='',ptype='',price_url=''):
    r=by[model];r['specifications_json']=json.dumps(specs,ensure_ascii=False,separators=(',',':'));r['description']=description;r['product_url']=url;r['product_source_url']=url;r['source_attribution']='Official manufacturer product page with technical details';r['verification_status']='official_product_page_verified';r['notes']=notes
    if price:
        r['official_price']=str(price);r['price_currency']=currency;r['price_market']=market;r['price_type']=ptype;r['price_source_url']=price_url or url

corsair='https://www.corsair.com/us/en/p/gaming-furniture/CF-9010068-WW/tc500-luxe-gaming-chair-sherwood-cf-9010068-ww'
setrow('TC500 LUXE',{'upholstery':'premium fabric','frame':'steel','foam_density_kg_m3':55,'backrest_dimensions_cm':'55x80','seat_dimensions_cm':'59x50','recline_deg':'90-160','lumbar':'4-way built-in adjustment','armrests':'OmniFlex adjustable','neck_pillow':'detachable magnetic memory foam','max_user_height_cm':188,'max_load_kg':120,'seat_height_cm':'42-52','wheel_diameter_mm':65,'warranty_years':2},'Wide, fabric-covered gaming chair with built-in adjustable lumbar support and highly adjustable armrests.',corsair,'Current Corsair listing verified for specifications and a USD 449.99 sale price (regular USD 549.99). Current promotional price may change.',449.99,'USD','United States','current_listed',corsair)

andaseat='https://www.andaseat.com/products/andaseat-kaiser-4-6d-armrest-gaming-chair'
setrow('Kaiser 4',{'sizes':['L','XL'],'recommended_height_cm':{'L':'150-180','XL':'181-210'},'recommended_load_kg':{'L':'<120','XL':'80-180'},'lumbar':'pop-out adjustable with any-angle lock','armrests':'6D','head_pillow':'magnetic memory foam with cooling layer','upholstery_options':['PVC leather','linen fabric'],'warranty_years':5},'Large gaming chair with pop-out lumbar adjustment, magnetic head pillow, and six-dimensional armrests.',andaseat,'Current AndaSeat manufacturer listing verifies sizes, fit range, adjustable lumbar, armrests, magnetic head pillow, and USD 519 listed promotional price. Listed price may change.',519,'USD','United States','current_listed',andaseat)

secret='https://secretlab.co/products/magnus-pro'
setrow('MAGNUS Pro',{'desk_type':'electric sit-to-stand metal desk','desktop_size_in':'59.1 x 27.6','height_range_in':'25.6-49.2','maximum_distributed_load_lb':265,'weight_lb':125,'frame':'steel (SPCC)','cable_management':'integrated full-length cable tray and single-cable power column','warranty_years':5},'Electric height-adjustable metal desk with a built-in cable-management system and integrated power column.',secret,'Secretlab official technical specifications provide desktop size, height range, rated load, materials and warranty. Configurable current price was not captured.')
setrow('MAGNUS Pro XL',{'desk_type':'electric sit-to-stand metal desk','desktop_size_in':'70 x 31.5','height_range_in':'25.6-49.2','maximum_distributed_load_lb':265,'weight_lb':150,'frame':'steel (SPCC)','cable_management':'integrated full-length cable tray and single-cable power column','warranty_years':5},'Large electric height-adjustable metal desk with a built-in cable-management system and integrated power column.',secret,'Secretlab official technical specifications provide desktop size, height range, rated load, materials and warranty. Configurable current price was not captured.')

razer='https://www.razer.com/gaming-chairs/razer-fujin-pro'
setrow('Fujin Pro',{'chair_type':'ergonomic mesh gaming and desk chair','mesh':'thermoplastic elastomer and polyester blend','frame':'aluminum alloy','maximum_load_kg':136,'recommended_height_cm':'170-200','lumbar':'2D height and depth adjustment','headrest':'3D contoured adjustable','armrests':'4D padded','warranty_years':5},'Breathable mesh chair with adjustable lumbar support, contoured headrest, and multi-axis padded armrests.',razer,'Razer official product page verifies material, frame, adjustment features, recommended user size, load rating and warranty. Price was not displayed on the official page.')

with p.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('K updated empty specification records:',len(rows))
