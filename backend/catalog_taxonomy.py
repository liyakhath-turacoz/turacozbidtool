"""Versioned product types independent of legacy browse departments.

Classify the actual product, never words buried in marketing/compatibility copy.
Unknown inventory remains unclassified for review rather than guessed.
"""
import re

VERSION = 10
# Stable id, browse path, legacy department code, title/type pattern, required
# groups of alternative specification-name patterns. Groups are all required.
_DEFINITIONS = [
 ('usb_drives','Computing|Storage|USB flash drives','B',r'pen ?drive|usb flash|flash drive',('capacity|storage','interface|usb')),
 ('memory_cards','Computing|Storage|Memory cards','B',r'micro ?sd|memory card|sdxc|sdhc|cfexpress',('capacity|storage','speed|class|interface')),
 ('hard_drives','Computing|Storage|Hard disk drives','B',r'hard (?:disk|drive)|\bhdd\b',('capacity|storage','interface|usb|sata|sas')),
 ('ssds','Computing|Storage|SSDs','B',r'\bssd\b|solid.state',('capacity|storage','interface|nvme|sata|usb')),
 ('power_banks','Mobile & charging|Portable power|Power banks','P',r'power ?bank',('capacity|battery','output|power|charging')),
 ('led_bulbs','Lighting|Lamps|LED bulbs','P',r'led bulb|led lamp',('power|watt','lumen|flux','base|cap|holder','colou?r|temperature|cct')),
 ('smart_plugs','Smart home|Power control|Smart plugs','M',r'smart plug|wi.fi plug',('current|rating|amp','connectivity|wi.fi')),
 ('switches','Electrical installation|Controls|Switches','P',r'modular switch|wall switch|electrical switch|\d+\s*a\s+.*switch',('current|rating|amp','module|gang|pole|type')),
 ('multimeters','Test & measurement|Electrical meters|Multimeters','P',r'multimeter|multi.meter',('voltage','current|resistance','accuracy|resolution')),
 ('ups','Power systems|Backup power|UPS','P',r'\bups\b|uninterruptible',('power|capacity|va','battery|runtime|voltage')),
 ('water_heaters','Home appliances|Water heating|Water heaters','E',r'water heater|\bgeyser\b',('capacity|litre','power|watt','pressure|mount|installation')),
 ('microwaves','Kitchen appliances|Ovens|Microwave ovens','F',r'microwave',('capacity|volume','power|watt','type|function|mode')),
 ('ovens','Kitchen appliances|Ovens|OTG ovens','F',r'\botg\b|oven toaster',('capacity|volume','power|watt','temperature|function')),
 ('refrigerators','Home appliances|Refrigeration|Refrigerators','E',r'refrigerator|\bfridge\b',('capacity|volume','door|type','energy|star|power')),
 ('freezers','Home appliances|Refrigeration|Freezers','E',r'freezer',('capacity|volume','temperature|power|energy')),
 ('washers','Home appliances|Laundry|Washing machines','E',r'washing machine|washer dryer',('capacity','spin|rpm','type|load')),
 ('dishwashers','Kitchen appliances|Dish care|Dishwashers','E',r'dishwasher',('place|capacity','program|mode|cycle')),
 ('air_conditioners','Climate & air care|Cooling|Air conditioners','H',r'air conditioner|split ac|window ac',('capacity|ton','energy|star','power|inverter|refrigerant')),
 ('air_coolers','Climate & air care|Cooling|Air coolers','H',r'air cooler|desert cooler',('capacity|tank','power|watt|air')),
 ('air_purifiers','Climate & air care|Air treatment|Air purifiers','H',r'air purifier|purifier.*(?:hot|cool)|hushjet',('filter|filtration','cadr|coverage|area')),
 ('fans','Climate & air care|Air circulation|Fans','H',r'ceiling fan|pedestal fan|table fan|exhaust fan|tower fan|^fans?$',('power|watt','sweep|size|speed|rpm')),
 ('vacuum_cleaners','Home care|Floor care|Vacuum cleaners','G',r'vacuum cleaner|cordless vacuum|robot vacuum',('power|suction','capacity|bin|tank|runtime|battery')),
 ('garment_steamers','Home care|Garment care|Garment steamers','G',r'garment steamer|handheld steamer',('power|watt','tank|capacity|steam')),
 ('air_fryers','Kitchen appliances|Cooking|Air fryers','F',r'air ?fryer',('capacity','power|watt','temperature|function')),
 ('multi_cookers','Kitchen appliances|Cooking|Multi-cookers','F',r'multi.cooker|onechef|ninja combi',('capacity','power|voltage','function|mode')),
 ('mixers','Kitchen appliances|Food preparation|Mixer grinders','F',r'mixer grinder|nutri.blend',('power|watt','jar|capacity')),
 ('blenders','Kitchen appliances|Food preparation|Blenders','F',r'blender',('power|watt','capacity|jar')),
 ('choppers','Kitchen appliances|Food preparation|Choppers','F',r'electric chopper|vegetable.*chopper',('capacity|bowl','power|blade')),
 ('juicers','Kitchen appliances|Food preparation|Juicers','F',r'juicer',('power|watt','capacity|speed|motor')),
 ('kettles','Kitchen appliances|Beverage preparation|Electric kettles','F',r'electric kettle|^kettles?$',('capacity','power|watt')),
 ('coffee_machines','Kitchen appliances|Beverage preparation|Coffee machines','F',r'espresso machine|coffee maker|coffee machine',('capacity|tank','power|pressure|type')),
 ('smartphones','Phones & tablets|Mobile phones|Smartphones','A',r'\biphone\b|smartphones?|\b(?:mobile|cell)\s+phones?\b|\bphone\b',('storage|capacity','display|screen','processor|chip|soc')),
 ('tablets','Phones & tablets|Tablets|Tablets','A',r'\bipad\b|\btablet\b|^tablets?$|galaxy tab',('storage|capacity','display|screen','processor|chip|soc')),
 ('laptops','Computing|Computers|Laptops','B',r'laptop|notebook|macbook',('processor|cpu','ram|memory','storage|ssd|capacity')),
 ('desktops','Computing|Computers|Desktop computers','B',r'desktop computer|mini pc|mac mini|imac|mac studio',('processor|cpu|chip','ram|memory','storage|ssd')),
 ('monitors','Computing|Displays|Monitors','B',r'\bmonitor\b',('display|screen|size','resolution','interface|port|hdmi|connectivity')),
 ('motherboards','Computing|Components|Motherboards','B',r'motherboard',('socket|processor','chipset','memory|ram')),
 ('graphics_cards','Computing|Components|Graphics cards','B',r'graphics card|geforce.*(?:gddr|gb)|radeon rx',('gpu|processor|chipset','memory','interface|pci')),
 ('processors','Computing|Components|Processors','B',r'(?:ryzen|core ultra|intel core|pentium|celeron).*processor|^cpu$|^processors?$',('core','clock|frequency','socket')),
 ('ram','Computing|Components|RAM','B',r'\bram\b|ddr[45].*(?:memory|dimm)|^memory modules$',('capacity|memory','speed|frequency','type|ddr')),
 ('pc_cases','Computing|Components|PC cases','B',r'pc cabinet|computer case|pc case|chassis',('form|motherboard','dimension|size')),
 ('routers','Networking|Wireless networking|Routers','N',r'router|mesh wi.fi',('wireless|wi.fi|standard','port|interface','speed|rate')),
 ('network_switches','Networking|Wired networking|Network switches','N',r'network switch|ethernet switch',('port','speed|rate|bandwidth')),
 ('televisions','TV & entertainment|Displays|Televisions','C',r'television|\btv\b|\bbravia\b',('display|screen|size','resolution','hdmi|port|connectivity')),
 ('cameras','Photography|Cameras|Cameras','J',r'mirrorless|digital camera|dslr|^cameras?$',('sensor','resolution|pixel|megapixel','mount|lens')),
 ('camera_lenses','Photography|Lenses|Camera lenses','J',r'^camera lenses?$|^lenses$|\blens\b',('mount','focal','aperture')),
 ('game_controllers','Gaming|Controllers|Game controllers','K',r'gamepad|game controller|gaming controller|dualsense',('platform|compatib','connection|connectivity|interface')),
 ('gaming_headsets','Gaming|Audio|Gaming headsets','K',r'gaming headset|gaming headphone',('driver|frequency','connection|interface|connectivity')),
 ('gaming_keyboards','Gaming|Peripherals|Gaming keyboards','K',r'gaming keyboard',('key|switch','connection|interface|connectivity')),
 ('headphones','Audio|Personal audio|Headphones','D',r'headphone|headset|rockerz',('driver|frequency','bluetooth|connection|interface|connectivity')),
 ('earbuds','Audio|Personal audio|Earbuds','D',r'earbuds|\btws\b|airpods|airdopes',('driver|frequency','bluetooth|connection|connectivity')),
 ('earphones','Audio|Personal audio|Earphones','D',r'earphone|neckband',('driver|frequency','bluetooth|connection|interface')),
 ('speakers','Audio|Speakers|Speakers','D',r'\bspeaker\b',('power|output','bluetooth|connection|interface')),
 ('smartwatches','Wearables|Watches|Smartwatches','L',r'smart.?watch|watch series|watch ultra|t.rex',('display','battery','connectivity|bluetooth|wireless')),
 ('hair_dryers','Personal care|Hair care|Hair dryers','I',r'hair ?dryer|supersonic',('power|watt','speed|temperature|heat')),
 ('hair_stylers','Personal care|Hair care|Hair stylers','I',r'hair.*(?:styler|straightener|curler)|airwrap|airstrait',('temperature|heat|power','attachment|plate|mode')),
 ('toothbrushes','Personal care|Oral care|Electric toothbrushes','I',r'electric toothbrush|sonicare',('mode','battery|charging')),
 ('shavers','Personal care|Grooming|Electric shavers','I',r'electric shaver|wet.*dry.*shaver',('blade|head','battery|charging|runtime')),
 ('printers','Office|Printing|Printers','O',r'\bprinters?\b',('print|technology','connectivity|interface|usb')),
 ('scanners','Office|Imaging|Scanners','O',r'\bscanners?\b',('resolution','interface|usb|connectivity')),
 ('security_cameras','Security|Surveillance|Security cameras','M',r'security camera|cctv|ip camera',('resolution|pixel','connection|interface|wi.fi')),
 ('security_recorders','Security|Surveillance|Security video recorders','M',r'\bdvr\b|\bnvr\b|video recorder',('channel','resolution|storage')),
 ('chargers','Mobile & charging|Charging|Chargers','P',r'charger|charging station|ac adapt[eo]r',('power|output','connector|interface|port')),
 ('soundbars','Audio|Home audio|Soundbars','D',r'soundbars?',('power|output','connection|interface|bluetooth')),
 ('mice','Computing|Peripherals|Mice','B',r'\bmouse\b|^mice$',('sensor|dpi|resolution','connection|interface')),
 ('gaming_mice','Gaming|Peripherals|Gaming mice','K',r'gaming mouse',('sensor|dpi|resolution','connection|interface')),
 ('keyboards','Computing|Peripherals|Keyboards','B',r'\bkeyboards?\b',('key|layout','connection|interface')),
 ('microphones','Audio|Recording|Microphones','D',r'\bmicrophones?\b',('frequency|pattern|sensitivity','connection|interface')),
 ('usb_hubs','Computing|Connectivity|USB hubs and docks','B',r'usb hub|docking station|usb.*dock',('port','interface|usb')),
 ('nas','Computing|Storage|NAS and storage servers','B',r'\bnas\b|storage server',('drive|bay','processor|memory')),
 ('projectors','TV & entertainment|Projection|Projectors','C',r'\bprojectors?\b',('resolution','brightness|lumen')),
 ('network_adapters','Networking|Connectivity|Network adapters','N',r'network adapter|lan card|wi.fi adapter',('interface|usb|pci','speed|rate|standard')),
 ('voip_phones','Networking|Telephony|VoIP phones and adapters','N',r'voip|ip phone|fxs|fxo',('port|interface','protocol|sip')),
 ('massagers','Personal care|Wellness|Massagers','I',r'\bmassagers?\b',('power|battery','speed|mode')),
 ('trimmers','Personal care|Grooming|Trimmers','I',r'\btrimmers?\b',('blade|length','battery|power|charging')),
 ('irons','Home care|Garment care|Irons','G',r'\birons?\b',('power|watt','soleplate|steam|type')),
 ('power_strips','Electrical installation|Power distribution|Power strips','P',r'power strip|extension board|surge protector',('socket|outlet','power|current|rating')),
 ('pc_cooling','Computing|Components|PC cooling','B',r'cpu.{0,24}\bcooler\b|pc cooling|liquid cooler',('socket|compatibility','fan|speed|airflow')),
 ('writing_tablets','Office|Writing|Writing tablets','O',r'writing tablet|writing pad',('display|screen|size',)),
 ('sandwich_makers','Kitchen appliances|Cooking|Sandwich makers','F',r'sandwich maker|waffle maker|bread toaster',('power|watt','capacity|plate|slice')),
 ('humidifiers','Climate & air care|Air treatment|Humidifiers','H',r'humidifier',('capacity|tank','power|area|coverage')),
 ('cooktops','Kitchen appliances|Cooking|Cooktops','F',r'cooktop|induction stove|gas hob',('power|burner','type|control')),
 ('chimneys','Kitchen appliances|Ventilation|Chimneys','F',r'chimney|chimneys',('suction|airflow','size|width')),
]

TYPES = {code: {'id':code, 'path':path.split('|'), 'legacy_code':legacy,
                 'pattern':pattern, 'required_groups':list(groups)}
         for code,path,legacy,pattern,groups in _DEFINITIONS}
_TITLE_PRIORITY = (
    'printers','voip_phones','tablets','projectors','soundbars','televisions','camera_lenses','cameras',
    'smartwatches','gaming_headsets','headphones','earbuds','earphones','speakers',
    'desktops','laptops','smartphones','game_controllers','gaming_keyboards','gaming_mice',
    'pc_cooling','freezers','refrigerators','washers','dishwashers','microwaves','ovens',
    'air_conditioners','air_coolers','air_purifiers','fans','water_heaters','vacuum_cleaners',
    'garment_steamers','air_fryers','multi_cookers','mixers','blenders','choppers','juicers',
    'kettles','coffee_machines','cooktops','chimneys','usb_drives','memory_cards','hard_drives',
    'ssds','power_banks','led_bulbs','smart_plugs','switches','multimeters','ups','routers',
    'network_switches','motherboards','graphics_cards','processors','ram','pc_cases','mice',
    'keyboards','usb_hubs','nas','network_adapters','security_cameras','security_recorders',
    'massagers','trimmers','irons','power_strips','writing_tablets','sandwich_makers','humidifiers',
    'hair_dryers','hair_stylers','toothbrushes','shavers','scanners','chargers'
)
ACCESSORY = re.compile(r'\b(?:replacement|refill|spare|screen protector|tempered glass|privacy glass|screen guard|camera lens protection|camera lens protector|lens protector|smart folio|applecare|(?:iphone|ipad|macbook).*(?:case|cover|wallet|folio|sleeve|screen protector)|magic keyboard.{0,80}\bipad\b|(?:case|cover|wallet|folio|bag|sleeve|stand|filter).*(?:iphone|ipad|macbook|airpods)|jar assembly|jar coupler|motor coupler|bar assembly|sieve assembly|grill pan|power cord|watch strap|watch band|silicone strap|airtag holder|airpods.*(?:case|cover)|airdopes.*(?:case|cover)|(?:case|cover) for (?:iphone|ipad|samsung|galaxy|pixel)|magsafe case|metal case for ipad|ink cartridge|toner|sliding tray|cutlery|coffee mug|pitcher|remote control|warranty|gift card|(?:laptop|notebook).{0,40}(?:charger|adapter|keyboard|battery|\bstand\b|sleeve|bag|cover|case)|(?:charger|adapter|keyboard|battery|\bstand\b|sleeve|bag|cover|case).{0,40}(?:laptop|notebook)|(?:iphone|phone|mobile|smartphone|tablet).{0,40}(?:magsafe|magnetic).{0,25}battery|(?:magsafe|magnetic).{0,25}battery.{0,40}(?:iphone|phone|mobile|smartphone|tablet)|\b\d{2,4}\s*w.{0,30}\bac\s+adapter\b|replacement.{0,30}\bbattery\b|(?:phone|mobile|smartphone|tablet|watch).{0,30}(?:case|cover|strap|band|protector|charger|stand)|\b(?:hdmi|usb(?:[ -]?c)?|displayport|ethernet|printer)\b.{0,80}\b(?:cable|cord|lead)\b)\b',re.I)
COMPUTER_ACCESSORY = re.compile(r'\b(?:laptop|notebook)\b.{0,80}\b(?:cooling pad|cooler|table|desk|stand|bag|sleeve|case|cover|charger|adapter|battery)\b|\b(?:cooling pad|laptop cooler|laptop table|laptop desk|laptop stand|notebook stand|laptop bag|notebook bag|laptop sleeve|notebook sleeve)\b',re.I)
MOBILE_ACCESSORY = re.compile(r'\b(?:panzerglass|magsafe wallet|wallet for (?:a )?(?:smartphone|iphone|mobile)|(?:mobile|phone|smartphone|tablet) holder|(?:mobile|phone|smartphone|tablet) stand|type[ -]?c cable|usb[ -]?c cable|lightning cable|mobile phone cable|phone cable)\b',re.I)

def is_accessory(record):
    """Identify common phone/laptop accessories even when retailer taxonomy says device."""
    title=' '.join(str(record.get(k) or '') for k in ('name','family_name'))
    body=title+' '+str(record.get('description') or '')
    return bool(ACCESSORY.search(title) or COMPUTER_ACCESSORY.search(body) or MOBILE_ACCESSORY.search(body))

def classify(title, source_type=''):
    if ACCESSORY.search(title):
        return None, 'accessory_or_non_product'
    # Utensils and food-storage products often say "microwave safe" or
    # "dishwasher safe". Those compatibility claims are not appliance nouns.
    classification_title=re.sub(
        r'\b(?:dishwasher|microwave(?:\s+oven)?|freezer)(?:\s*(?:,|&|and)\s*(?:dishwasher|microwave(?:\s+oven)?|freezer)){0,2}\s*[- ]+safe\b',
        ' ',title,flags=re.I)
    classification_title=re.sub(
        r'\bsafe\s+for\s+(?:the\s+)?(?:dishwasher|microwave(?:\s+oven)?|freezer)\b',
        ' ',classification_title,flags=re.I)
    # Retailers sometimes put their Apple part number before the marketed
    # model (for example, "Apple MDHA4HN/A MacBook Air ..."). Keep the match
    # anchored so compatibility copy such as "SSD for MacBook Air" cannot win.
    if re.search(r'^(?:Apple\s+)?(?:[A-Z0-9]{2,8}/[A-Z0-9]{1,8}\s+)?(?:(?:[0-9]+(?:\.[0-9]+)?[ -]inch)\s+)*(?:MacBook)(?:\s+(?:Air|Pro|Neo))?\b',title,re.I):return 'laptops','explicit computer model in title'
    if re.search(r'^(?:Apple\s+)?(?:iMac|Mac mini|Mac Studio)\b',title,re.I):return 'desktops','explicit computer model in title'
    if re.search(TYPES['smart_plugs']['pattern'],title,re.I):return 'smart_plugs','product noun in title'
    # Compatibility text can mention a smartphone before the actual product
    # noun; classify portable photo printers as printers, not phones.
    if re.search(r'\bprinters?\b',title,re.I):return 'printers','explicit printer noun in title'
    if re.search(TYPES['voip_phones']['pattern'],title,re.I):return 'voip_phones','explicit VoIP phone noun in title'
    # Product titles are more reliable than a broad or malformed retailer
    # classification (e.g. a Redmi Pad listing filed under RAM).
    if re.search(TYPES['tablets']['pattern'],title,re.I):return 'tablets','explicit tablet model in title'
    # A specific product noun in the title outranks a broad or incorrect
    # retailer category (for example, a smartwatch filed under monitors).
    for key in ('smart_plugs', *_TITLE_PRIORITY):
        if re.search(TYPES[key]['pattern'],classification_title,re.I):
            return key,'product noun in title'
    exact = next((code for code,t in TYPES.items() if source_type.strip().casefold()==t['path'][-1].casefold()),None)
    # A compatibility phrase such as "freezer safe" is not enough to confirm
    # one of these appliance categories from a retailer tag alone.
    sensitive={'microwaves','freezers','dishwashers','ovens'}
    if exact in sensitive:exact=None
    if exact:return exact,'exact retailer product type'
    for code,taxon in TYPES.items():
        if code in sensitive:continue
        if re.search(taxon['pattern'],source_type,re.I):
            return code,'explicit retailer product type'
    return None,'unmapped_product_type'

def missing_attributes(type_id,specs):
    names='\n'.join(str(key) for key,value in specs.items() if str(value or '').strip())
    return [pattern for pattern in TYPES[type_id]['required_groups'] if not re.search(pattern,names,re.I)]
