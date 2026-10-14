import csv,json
p='product_catalog/B-computers-laptops-it-equipment.csv'
with open(p,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
updates={
'AOC AG276QZD':('2023-06-20','release_date','https://aoc.com/it/products/505/leaflet?language=en-US','AOC official model leaflet lists Launch date (ETA) as 2023-06-20. This predates the preferred three-year window as of 2026-10-13, so retained as older reference data.'),
'AOC AG456UCZD':('2024-03-01','release_date','https://aoc.com/uk/products/636/leaflet?language=en','AOC official model leaflet lists Launch date (ETA) as 2024-03-01.'),
'AOC PD49':('2024-01-29','announcement_date','https://ap.aoc.com/index/article/id/1333','AOC manufacturer announcement dated 2024-01-29; exact retail availability date was not stated in the captured release.'),
}
for r in rows:
 key=f"{r['brand']} {r['model']}"
 if key in updates:
  d,prec,url,note=updates[key];r['release_date']=d;r['release_date_precision']=prec;r['release_year']=d[:4];r['notes']=(r['notes']+' ' if r['notes'] else '')+note;r['product_source_url']=r['product_url']
 if r['brand']=='AOC' and r['model']=='AG326UD':
  r.update(official_price='579.99',price_currency='USD',price_type='current_listed',price_market='United States',price_source_url=r['product_url'],collected_on='2026-10-13')
  r['notes']=(r['notes']+' ' if r['notes'] else '')+'Official AOC US page displayed a starting price of $579.99 when checked on 2026-10-13; configuration and market-specific price may change.'
with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('Updated sourced AOC launch/announcement dates and AG326UD current listed price.')
