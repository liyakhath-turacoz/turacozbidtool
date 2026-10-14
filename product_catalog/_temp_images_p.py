import csv,requests,concurrent.futures
from bs4 import BeautifulSoup
p='product_catalog/P-power-backup-batteries-electrical-equipment.csv'
with open(p,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
def get(pair):
 i,u=pair
 try:
  x=requests.get(u,headers={'User-Agent':'Mozilla/5.0 (compatible; ProductCatalogue/1.0)'},timeout=12)
  if x.status_code!=200:return i,''
  s=BeautifulSoup(x.text,'html.parser');m=s.find('meta',attrs={'property':'og:image'}) or s.find('meta',attrs={'name':'twitter:image'});image=m.get('content','').strip() if m else ''
  if any(g in image.lower() for g in ('social-share','default-share','logo','placeholder')):image=''
  return i,image
 except Exception:return i,''
urls=list({r['product_source_url'] for r in rows if r['product_source_url']})
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:result=list(ex.map(get,enumerate(urls)))
lookup=dict(zip(urls,[v for _,v in result]));n=0
for r in rows:
 if not r['image_url'] and lookup.get(r['product_source_url']):r['image_url']=lookup[r['product_source_url']];n+=1
with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('P image URLs recovered',n,'of',len(rows))
