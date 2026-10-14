import csv,os
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urljoin
import requests
ROOT=os.path.dirname(__file__);path=os.path.join(ROOT,'P-power-backup-batteries-electrical-equipment.csv')
with open(path,encoding='utf-8-sig',newline='') as f:rd=csv.DictReader(f);fields=rd.fieldnames;rows=list(rd)
usage={}
for r in rows:usage[r['product_source_url']]=usage.get(r['product_source_url'],0)+1
targets=sorted(u for u,n in usage.items() if n==1 and u.startswith('https://'))
class Meta(HTMLParser):
 def __init__(self):super().__init__();self.image=''
 def handle_starttag(self,tag,attrs):
  if tag!='meta':return
  a=dict(attrs);k=(a.get('property') or a.get('name') or '').lower()
  if k in ('og:image','twitter:image','twitter:image:src') and a.get('content') and not self.image:self.image=a['content'].strip()
def get(u):
 try:
  x=requests.get(u,timeout=12,allow_redirects=True,headers={'User-Agent':'Mozilla/5.0 catalogue-review/1.0','Accept-Encoding':'gzip, deflate'})
  if x.status_code!=200 or 'html' not in x.headers.get('content-type','').lower():return u,''
  p=Meta();p.feed(x.text);return u,urljoin(x.url,p.image) if p.image else ''
 except Exception:return u,''
with ThreadPoolExecutor(max_workers=10) as ex:images=dict(ex.map(get,targets))
changed=0
for r in rows:
 if not r['image_url'] and images.get(r['product_source_url']):r['image_url']=images[r['product_source_url']];changed+=1
with open(path,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('Product-specific official page image URLs captured:',changed,'of',len(rows),'products; shared family listings skipped.')
