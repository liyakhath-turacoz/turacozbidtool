import csv
from pathlib import Path
p=Path(__file__).with_name('I-personal-care-grooming-appliances.csv')
with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
press='https://www.philips.com/a-w/about/news/archive/standard/news/press/2025/philips-launches-its-most-intelligent-shaver-yet-the-i9000-shaver-series-redefines-premium-personalized-male-grooming'
for r in rows:
    if r['model'] in ('XP9404/46','XP9402/11'):
        r['release_year']='2025';r['release_date']='';r['release_date_precision']='year'
        r['manufacturer_part_number']=r['model']
        r['source_attribution']='Official Philips i9000 product page and 2025 launch announcement'
        r['verification_status']='official_product_and_launch_verified'
        r['notes']=f"Philips announced the i9000 Shaver Series on 2025-04-16, including the Prestige Ultra family. Exact product model, image, and specifications are supported by the linked Philips product page; the public announcement does not establish a more precise model-specific release date. Current official price not captured. Launch source: {press}"
    elif r['model']=='X9000/10':
        r['notes']='Philips current product page identifies the model and captured specifications, but does not establish a release date/year; age remains unverified. Current official price was not captured.'
with p.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('I Philips i9000 rows reviewed')
