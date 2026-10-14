from pathlib import Path
p=Path(__file__).parent/'_temp_build_j.py'
s=p.read_text(encoding='utf-8')
repls={
"'https://www.dji.com/osmo-360'":"'https://www.dji.com/360'",
"'https://www.sigma-global.com/en/lenses/a024_ii/'":"'https://www.sigma-global.com/en/lenses/a024_24_70_28_ii'",
"'https://www.sigma-global.com/en/lenses/a025_28_105_28/'":"'https://www.sigma-global.com/en/lenses/a024_28_105_28/'",
"'https://www.manfrotto.com/global/befree-advanced-travel-tripod/'":"'https://www.manfrotto.com/global-en/befree-advanced-aluminum-travel-tripod-twist-ball-head-mkbfrta4bk-bhus/'",
"('Manfrotto','Befree Advanced Travel Tripod'":"('Manfrotto','Befree Advanced Aluminum Travel Tripod twist, ball head'",
"'https://www.manfrotto.com/global/element-mii-aluminium-tripod/'":"'https://www.manfrotto.com/global-en/element-mii-aluminium-tripod/'",
"'https://www.godox.com/product-d/V1Pro.html'":"'https://godox.com/product-b/V1Pro.html'",
"'https://www.godox.com/product-d/AD600ProII.html'":"'https://godox.com/product-b/Flash/AD600ProII.html'",
"'https://www.godox.com/product-d/AD200ProII.html'":"'https://www.godox.com/product-b/Flash/AD200ProII.html'",
"'https://www.godox.com/product-d/V100.html'":"'https://www.godox.com/product-b/Flash/V100.html'",
"'https://www.godox.com/product-d/ML100Bi.html'":"'https://www.godox.com/product-a/LED/ML100Bi.html'",
"'https://www.godox.com/product-d/LA200Bi.html'":"'https://www.godox.com/product-b/LED/LA200Bi.html'",
"('Nanlite','Forza 60C II RGBLAC LED Spotlight','https://nanliteus.com/forza-60c-ii/','2024'),":"",
"('Nanlite','Pavotube II 6C RGBWW LED Tube','https://nanliteus.com/pavotube-ii-6c/',''),":"",
"('Aputure','amaran 300c S','https://amarancreators.com/products/300c-s','2025')":"('Aputure','amaran 300c','https://amarancreators.com/products/300c','')",
"'https://www.dji.com/osmo-360'":"'https://www.dji.com/360'",
"rows=unique\nfor r in rows:":"rows=unique\nfor r in rows:\n if r['brand']=='Nikon' and r['model']=='ZR':\n  r['release_year']='2025'\n  r['notes']=(r['notes'].rstrip(' .;')+'; ' if r['notes'] else '')+'Release year supported by Nikon India press release dated 2025-09-10: https://www.nikon.co.in/articles/press-release/nikon-enters-cinema-space-with-nikon-zr-brings-cinematic-precision-to-a-compact-all-in-one-body.'\n else:\n  r['release_year']=''\n  r['notes']=(r['notes'].rstrip(' .;')+'; ' if r['notes'] else '')+'Release year not verified from the product source; age needs review.'\nfor r in rows:"
}
for a,b in repls.items():s=s.replace(a,b)
p.write_text(s,encoding='utf-8')
