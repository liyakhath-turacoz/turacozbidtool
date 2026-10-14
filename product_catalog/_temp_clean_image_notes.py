import csv,glob,re
for p in glob.glob('product_catalog/[A-P]-*.csv'):
 with open(p,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
 changed=0
 for r in rows:
  if not r['image_url']:continue
  old=r['notes'];n=old
  def fix_missing(match):
   bits=[x.strip() for x in match.group(1).split(',') if 'image url' not in x.casefold() and 'image' not in x.casefold()]
   return ('Missing/unverified fields: '+', '.join(bits)+'.') if bits else ''
  n=re.sub(r'Missing/unverified fields:\s*([^.]*\.)',lambda m:fix_missing(type('M',(),{'group':lambda self,i:m.group(i)})()),n,flags=re.I)
  n=re.sub(r'Image URL not captured; fetch/confirm from the official product page before import\.?','',n,flags=re.I)
  n=re.sub(r'No official image URL captured\.?','',n,flags=re.I)
  n=re.sub(r'Official image URL not captured\.?','',n,flags=re.I)
  n=re.sub(r'No image URL captured\.?','',n,flags=re.I)
  if not r['official_price']:
   n=re.sub(r'Image URL and price not captured\.?','Official price not captured.',n,flags=re.I)
  else:n=re.sub(r'Image URL and price not captured\.?','',n,flags=re.I)
  n=re.sub(r'\s+([,;.])',r'\1',n);n=re.sub(r';\s*;',';',n);n=re.sub(r'\s{2,}',' ',n).strip(' ;')
  r['notes']=n
  if n!=old:changed+=1
 with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 if changed:print(p.split('/')[-1],changed,'notes reconciled to captured image fields')
