import csv,requests,concurrent.futures
from bs4 import BeautifulSoup
p='product_catalog/B-computers-laptops-it-equipment.csv'
with open(p,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
def get(u):
 try:
  x=requests.get(u,headers={'User-Agent':'Mozilla/5.0 (compatible; ProductCatalogue/1.0)'},timeout=14)
  if x.status_code!=200:return u,''
  s=BeautifulSoup(x.text,'html.parser');m=s.find('meta',attrs={'property':'og:image'}) or s.find('meta',attrs={'name':'twitter:image'});image=m.get('content','').strip() if m else ''
  if any(g in image.casefold() for g in ('social-share','default-share','logo','placeholder','sprite')):image=''
  return u,image
 except Exception:return u,''
urls=sorted({r['product_source_url'] for r in rows if r['product_source_url']})
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:lookup=dict(ex.map(get,urls))
n=0
for r in rows:
 if not r['image_url'] and lookup.get(r['product_source_url']):r['image_url']=lookup[r['product_source_url']];n+=1
with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('B official product images recovered',n,'/',len(rows),'using',len(urls),'unique official source URLs')
