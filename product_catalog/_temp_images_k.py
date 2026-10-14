import csv,requests,concurrent.futures,os
from bs4 import BeautifulSoup
p='product_catalog/K-gaming-virtual-reality.csv'
with open(p,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f)); fields=list(rows[0])
def get(pair):
 i,u=pair
 try:
  x=requests.get(u,headers={'User-Agent':'Mozilla/5.0 (compatible; ProductCatalogue/1.0)'},timeout=12)
  if x.status_code!=200:return i,''
  s=BeautifulSoup(x.text,'html.parser');m=s.find('meta',attrs={'property':'og:image'}) or s.find('meta',attrs={'name':'twitter:image'})
  image=m.get('content','').strip() if m else ''
  if any(g in image.lower() for g in ('social-share','default-share','logo','placeholder')):image=''
  return i,image
 except Exception:return i,''
urls=list({r['product_source_url'] for r in rows if r['product_source_url']})
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: imgs=dict(ex.map(get,enumerate(urls)))
lookup=dict(zip(urls,imgs.values()));changed=0
for r in rows:
 if not r['image_url'] and r['product_source_url'] in lookup and lookup[r['product_source_url']]:r['image_url']=lookup[r['product_source_url']];changed+=1
with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('K: official product image URLs recovered',changed,'/',len(rows),'from',len(urls),'unique source pages')
