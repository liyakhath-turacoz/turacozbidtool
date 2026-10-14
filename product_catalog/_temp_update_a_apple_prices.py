import csv
p='product_catalog/A-mobile-phones-tablets.csv'
with open(p,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
prices={
'iPhone 16':('89900','https://www.apple.com/in/shop/buy-iphone/iphone-16','Current Apple India buy page lists the model from ₹89,900.'),
'iPhone 17':('99900','https://www.apple.com/in/shop/buy-iphone','Current Apple India shop lineup lists iPhone 17 from ₹99,900.'),
'iPhone 17 Pro':('134900','https://www.apple.com/in/shop/buy-iphone/iphone-17-pro','Current Apple India product page lists iPhone 17 Pro starting at ₹1,34,900.'),
'iPhone 17 Pro Max':('149900','https://www.apple.com/in/shop/buy-iphone/iphone-17-pro','Current Apple India product page lists iPhone 17 Pro Max starting at ₹1,49,900.'),
'iPhone Air':('149900','https://www.apple.com/in/shop/buy-iphone/iphone-air','Current Apple India shop lineup lists iPhone Air from ₹1,49,900.'),
'iPhone 17e':('79900','https://www.apple.com/in/shop/buy-iphone/iphone-17e','Current Apple India buy page lists iPhone 17e from ₹79,900.'),
'iPhone 18 Pro':('164900','https://www.apple.com/in/shop/buy-iphone/iphone-18-pro','Current Apple India buy page lists iPhone 18 Pro 256 GB at ₹1,64,900.'),
'iPhone 18 Pro Max':('179900','https://www.apple.com/in/shop/buy-iphone/iphone-18-pro','Current Apple India buy page lists iPhone 18 Pro Max starting at ₹1,79,900.')}
changed=[]
for r in rows:
 if r['brand']=='Apple' and r['model'] in prices:
  v,url,note=prices[r['model']]
  r.update(official_price=v,price_currency='INR',price_type='current_starting_price',price_market='India',price_source_url=url,collected_on='2026-10-13',source_attribution='Official manufacturer product page or catalogue')
  r['notes']=(r['notes']+' ' if r['notes'] else '')+note+' Collected 2026-10-13; starting price/configuration is market-specific and may change.'
  changed.append(r['model'])
with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('Updated current Apple India starting prices for:',', '.join(changed))
