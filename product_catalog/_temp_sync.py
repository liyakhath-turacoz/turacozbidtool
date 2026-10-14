import csv,collections,openpyxl
from pathlib import Path
from urllib.parse import urlparse
b=Path('product_catalog'); p=b/'C-tvs-video-home-entertainment.csv'
with p.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f); cols=r.fieldnames; C=list(r)
allrows=[]
for fp in sorted(b.glob('[A-P]-*.csv')):
 with fp.open(encoding='utf-8-sig',newline='') as f:allrows.extend(csv.DictReader(f))
with (b/'all_products.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(allrows)
ct=collections.Counter(x['subcategory'] for x in C); brands=len({x['brand'] for x in C})
sp=b/'master_summary.csv'
with sp.open(encoding='utf-8-sig',newline='') as f:s=list(csv.DictReader(f));sf=list(s[0])
s=[x for x in s if x.get('category_code')!='C'];s.append(dict(zip(sf,['C','TVs, Video & Home Entertainment','ALL',str(len(C)),'IN_PROGRESS',p.name])))
for k,v in sorted(ct.items()):s.append(dict(zip(sf,['C','TVs, Video & Home Entertainment',k,str(v),'IN_PROGRESS',p.name])))
with sp.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=sf);w.writeheader();w.writerows(s)
lp=b/'collection_log.csv'
with lp.open(encoding='utf-8-sig',newline='') as f:l=list(csv.DictReader(f));lf=list(l[0])
l=[x for x in l if x.get('category_code')!='C'];l.append(dict(zip(lf,['C','ALL','IN_PROGRESS',str(len(C)),str(brands),'','', '2026-10-13','Official-source category collection remains in progress; subtype coverage being expanded.'])))
hosts=collections.Counter((urlparse(x.get('product_source_url') or x.get('product_url') or '').hostname or '').removeprefix('www.') for x in C)
for h,n in sorted(hosts.items()):
 if h:l.append(dict(zip(lf,['C','SOURCE','SOURCE',str(len(C)),str(brands),h,str(n),'2026-10-13','Official product or manufacturer source host.'])))
with lp.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=lf);w.writeheader();w.writerows(l)
wb=openpyxl.load_workbook(b/'master_catalogue.xlsx');ws=wb['C'];ws.delete_rows(1,ws.max_row);ws.append(cols)
for x in C:ws.append([x.get(k,'') or None for k in cols])
cs=wb['Category Summary'];old=list(cs.iter_rows(values_only=True));keep=[x for x in old[1:] if x and x[0]!='C'];cs.delete_rows(2,cs.max_row)
for x in keep:cs.append(list(x))
for x in [['C','TVs, Video & Home Entertainment','ALL',len(C),'IN_PROGRESS',p.name]]+[['C','TVs, Video & Home Entertainment',k,v,'IN_PROGRESS',p.name] for k,v in sorted(ct.items())]:cs.append(x)
st=wb['C - Stats'];st.delete_rows(1,st.max_row)
for x in [['C Product Statistics'],['Metric','Count'],['Total products',len(C)],['Distinct brands',brands],['Verified release year',sum(bool(x['release_year']) for x in C)],['Price listed',sum(bool(x['official_price']) for x in C)],['Image URL present',sum(bool(x['image_url']) for x in C)],['Release year unknown',sum(not bool(x['release_year']) for x in C)],['Price unavailable',sum(not bool(x['official_price']) for x in C)],['Image URL missing',sum(not bool(x['image_url']) for x in C)],[],['Subtype','Products']]:st.append(x)
for k,v in sorted(ct.items()):st.append([k,v])
wb.save(b/'master_catalogue.xlsx')
print('C',len(C),'brands',brands,'combined',len(allrows),'subtypes',dict(ct))
