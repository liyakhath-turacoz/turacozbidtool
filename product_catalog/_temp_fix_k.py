from pathlib import Path
p=Path(__file__).parent/'_temp_build_k.py';s=p.read_text(encoding='utf-8')
repls={
"nintendo-switch-2-dock-set-122946/":"nintendo-switch-2-dock-set-123791/",
"'2025',119.99,'USD','US','MSRP','https://www.nintendo.com/us/whatsnew/nintendo-maintains-nintendo-switch-2-pricing-retail-pre-orders-to-begin-april-24-in-u-s/'":"'2025',124.99,'USD','US','current listed price','https://www.nintendo.com/us/store/hardware/'",
"/handheld/legion-go-series/legion-go-s/len106g0001":"/handheld/legion-go-s/83l3001vus",
"https://gpd.hk/gpdwin4":"https://www.gpd.hk/gpdwin42025",
"('Nintendo','Nintendo Switch 2 Pro Controller','BEE-011','https://www.nintendo.com/us/store/products/nintendo-switch-2-pro-controller-122935/'":"('Nintendo','Nintendo Switch 2 Pro Controller','BEE-008','https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/'",
"nintendo-switch-2-camera-122940/":"nintendo-switch-2-camera-123682/",
"('Logitech G','PRO X 2 LIGHTSPEED Gaming Headset','PRO X 2','https://www.logitechg.com/en-us/products/gaming-audio/pro-x-2-wireless-headset.html','2023',{'connection':'LIGHTSPEED wireless / Bluetooth / 3.5 mm'}),":"",
"ch-931D100-NA/m75-air-wireless-gaming-mouse":"ch-931d100-na/m75-air-wireless-gaming-mouse",
"https://hyperx.com/products/hyperx-alloy-rise-gaming-keyboard":"https://hyperx.com/collections/gaming-keyboards",
"https://www.logitechg.com/en-us/products/gaming-mouse-pads/g840-xl-gaming-mouse-pad.html":"https://www.logitechg.com/en-us/products/gaming-mouse-pads.html",
"https://secretlab.co/products/magnus-pro-xl":"https://secretlab.co/products/magnus-pro",
"https://www.onexplayerstore.com/collections/onexplayer-x1":"https://onexplayerstore.com/collections/one-xplayer-x1",
"https://www.andaseat.com/products/kaiser-4-series-premium-gaming-chair":"https://www.andaseat.com/collections/kaiser-series",
"https://www.corsair.com/us/en/p/gaming-mouse/ch-931D100-NA/m75-air-wireless-gaming-mouse":"https://www.corsair.com/us/en/p/gaming-mouse/ch-931d100-na/m75-air-wireless-gaming-mouse",
"https://www.nintendo.com/us/store/products/nintendo-switch-2-camera-122940/":"https://www.nintendo.com/us/store/products/nintendo-switch-2-camera-123682/",
"https://www.nintendo.com/us/store/products/nintendo-switch-2-dock-set-122946/":"https://www.nintendo.com/us/store/products/nintendo-switch-2-dock-set-123791/",
"https://www.nintendo.com/us/store/products/nintendo-switch-2-pro-controller-122935/":"https://www.nintendo.com/us/store/hardware/joy-con-and-controllers/",
"('Bigscreen','Beyond 2','Beyond 2','https://www.bigscreenvr.com/','2025',{'type':'PC VR headset','display':'micro-OLED'},1019)":"('Bigscreen','Beyond 2','Beyond 2','https://www.bigscreenvr.com/','2025',{'type':'PC VR headset','display':'micro-OLED'},'')",
"https://hyperx.com/collections/gaming-keyboards":"https://hyperx.com/collections/gaming-keyboards/products/hyperx-alloy-rise-mechanical-gaming-keyboard",
"https://www.logitechg.com/en-us/products/gaming-mouse-pads.html":"https://www.logitechg.com/en-us/shop/p/g840-cloth-xl-gaming-mouse-pad.943-000117",
"https://www.andaseat.com/collections/kaiser-series":"https://www.andaseat.com/products/andaseat-kaiser-4-6d-armrest-gaming-chair",
"https://www.xbox.com/en-US/games/senuas-saga-hellblade-ii":"https://www.xbox.com/en-us/play/games/senuas-saga-hellblade-ii/9pmbb7nghv95",
"https://www.msi.com/Handheld/Claw-A8-BZ2EM":"https://www.msi.com/Handheld/Claw-A8-BZ2EMX",
"https://www.lenovo.com/us/en/c/laptops/legion-laptops/legion-go/":"https://www.lenovo.com/us/en/p/handheld/legion-go-gen-2/83n10009us",
}
for a,b in repls.items():s=s.replace(a,b)
p.write_text(s,encoding='utf-8');print('K URLs and unsupported price corrected')
