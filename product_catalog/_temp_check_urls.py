import csv,sys,requests
from concurrent.futures import ThreadPoolExecutor
p=sys.argv[1]
rs=list(csv.DictReader(open(p,encoding='utf-8-sig')))
us=sorted(set(r['product_source_url'] for r in rs if r['product_source_url'].startswith('http')))
def check(u):
 try:
  x=requests.get(u,timeout=12,allow_redirects=True,headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'gzip, deflate'}); return x.status_code,u,x.url
 except Exception as e:return 'ERR',u,str(e)[:90]
with ThreadPoolExecutor(max_workers=12) as ex:
 for status,u,target in ex.map(check,us):
  if status==404 or status==410 or status=='ERR':print(status,u,'=>',target)
