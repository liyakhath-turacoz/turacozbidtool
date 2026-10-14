from pathlib import Path
p=Path(__file__).parent/'_temp_build_l.py';s=p.read_text(encoding='utf-8')
repls={
"https://www.apple.com/apple-watch-series-11/ ":"https://www.apple.com/us/shop/goto/buy_watch",
"https://www.apple.com/apple-watch-series-11/":"https://www.apple.com/us/shop/goto/buy_watch",
"https://www.apple.com/apple-watch-ultra-3/":"https://www.apple.com/us/shop/goto/buy_watch",
"https://www.apple.com/apple-watch-se-3/":"https://www.apple.com/us/shop/goto/buy_watch",
"https://www.garmin.com/en-US/p/forerunner-570/":"https://www.garmin.com/en-US/p/1464001/",
"https://www.garmin.com/en-US/p/venu-4/":"https://www.garmin.com/en-US/p/1613801/",
"https://www.garmin.com/en-US/p/instinct-3-amoled-45mm/":"https://www.garmin.com/en-US/p/1316397/",
"https://www.garmin.com/en-US/p/1611937/":"https://www.garmin.com/en-US/p/1555457/",
"https://www.garmin.com/en-US/p/1393829/":"https://www.garmin.com/en-US/p/1196650/",
"https://www.garmin.com/en-US/c/wearable-smartwatch-accessories/":"https://www.garmin.com/en-US/p/993337/pn/010-13302-10/",
"https://www.xreal.com/one/":"https://us.shop.xreal.com/products/xreal-one",
"https://www.xreal.com/onepro/":"https://www.xreal.com/one-pro",
"https://ouraring.com/store/accessories":"https://ouraring.com/store/accessories/oura-ring-4-charger",
"https://us.amazfit.com/products/helio-ring":"https://us.amazfit.com/products/amazfit-helio-ring",
"https://us.amazfit.com/products/helio-strap":"https://us.amazfit.com/products/helio-strap",
"https://us.amazfit.com/products/t-rex-3-pro-strap-20-22mm":"https://us.amazfit.com/products/t-rex-3-pro",
"add('Smart Rings','Health tracking ring','Circular Ring 2','Circular','Ring 2','https://www.circular.xyz/ring-2',{'type':'health tracking smart ring'},'2025')":"add('Wearable Accessories','charging case','Oura Ring 4 Charging Case','Oura','Ring 4 charging case','https://ouraring.com/store/accessories/oura-ring-4-charging-case',{'compatibility':'Oura Ring 4','charges':5},'2024')",
}
for a,b in repls.items():s=s.replace(a,b)
# Keep this export limited to rows with an official product page link; replace the unsupported circular row with a verified Oura charger case.
s=s.replace("add('Smart Rings','Health tracking ring','Circular Ring 2','Circular','Ring 2','https://www.circular.xyz/','2025',{'type':'health tracking smart ring'},'2025')","add('Wearable Accessories','charging case','Oura Ring 4 Charging Case','Oura','Ring 4 charging case','https://ouraring.com/store/accessories/oura-ring-4-charging-case',{'compatibility':'Oura Ring 4','charges':5},'2024')")
# Garmin wearable accessories below are model-specific products rather than broad inferred compatibility rows.
s=s.replace("('Garmin','QuickFit 26mm Silicone Band','QuickFit 26mm','https://www.garmin.com/en-US/p/993337/pn/010-13302-10/','replacement watch band'),\n('Garmin','QuickFit 22mm Silicone Band','QuickFit 22mm','https://www.garmin.com/en-US/p/993337/pn/010-13302-10/','replacement watch band'),","('Garmin','Lily 2 Bands 14mm','Lily 2 quick-release band','https://www.garmin.com/en-US/p/993337/pn/010-13302-10/','replacement watch band'),")
p.write_text(s,encoding='utf-8');print('L broken links and unsupported ring row corrected')
