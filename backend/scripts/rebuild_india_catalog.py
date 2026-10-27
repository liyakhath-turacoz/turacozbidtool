"""Build a staged, evidence-backed India catalogue from public store inventory.

Requires requests, beautifulsoup4, Pillow and openpyxl (see requirements-catalog.txt).
This command never changes the database. Review the staged report before importing.
Store listing dates are deliberately NOT represented as manufacturer release dates.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import time
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ('https://www.boat-lifestyle.com', 'boAt'),
    ('https://www.gonoise.com', 'Noise'),
    ('https://www.portronics.com', 'Portronics'),
    ('https://zebronics.com', 'Zebronics'),
    ('https://shopatsc.com', 'Sony'),
    ('https://www.domesticappliances.philips.co.in', 'Philips'),
    ('https://agarolifestyle.com', 'AGARO'),
    ('https://www.crompton.co.in', 'Crompton'),
    ('https://www.wonderchef.com', 'Wonderchef'),
    ('https://www.ambraneindia.com', 'Ambrane'),
    ('https://www.bajajelectricals.com', 'Bajaj'),
    ('https://www.voltas.com', 'Voltas'),
    ('https://shop.lavamobiles.com', 'Lava'),
    ('https://infinixmobiles.in', 'Infinix'),
    ('https://www.imagineonline.store', 'Apple'),
    ('https://iplanet.one', 'Apple'),
    ('https://www.tpstech.in', None),
]
EXCLUDE = re.compile(r'\b(refurbished|renewed|refab|repacked|pre.?owned|open.?box|pre.?order|coming soon|warrant(?:y|ies)|gift|combo|bundle|spare|refill|replacement|strap|ear tips|screen protector|screen guard|tempered glass|case|cover|mount|stand|bag|sleeve|cleaning kit|cookware|kadhai|tawa|fry pan|platter|container|ink|toner|cartridge)\b', re.I)
NON_ELECTRICAL_HOUSEWARE = re.compile(r'\b(?:glass bottle|glass cups?|espresso coffee cups?|pour[- ]over coffee maker|coffee dripper)\b', re.I)
MEDICAL_INSPECTION_TOOLS = re.compile(r'\b(?:otoscope|earwax remover|ear endoscope)\b', re.I)
# Specific types precede broad matches; unmatched inventory is excluded, never guessed.
TYPES = [
 ('A','Smartphones',r'\biphone\b|\bsmartphone\b'), ('A','Tablets',r'\bipad\b|\btablet\b'),
 ('J','Camera lenses',r'\blens\b|\bg.master\b'), ('J','Cameras',r'digital imaging|\bcamera\b|\bcamcorder\b|\bdashcam\b|\bdash cam\b|\bprocam\b'),
 ('K','Game consoles',r'playstation.*console|\bps5\b.*(?:slim|digital|console)|\bconsole\b'),
 ('K','Game controllers',r'game controller|dualsense|ps5 controller'),
 ('K','Gaming headsets',r'gaming headphones|gaming headset'),
 ('K','Gaming keyboards',r'gaming keyboard'), ('K','Gaming mice',r'gaming mouse'),
 ('L','Smartwatches',r'smart.?watch|smart watches|\bwatch series\b|\bwatch ultra\b|\bwatch se\b|^smart$'),
 ('L','Smart rings',r'\bsmart ring\b|\bluna ring\b'),
 ('B','Laptops',r'macbook|\blaptop\b|\bnotebook\b'), ('B','Desktop computers',r'mac mini|mac studio|\bimac\b|mini pc|desktop'),
 ('B','Monitors',r'\bmonitor'), ('B','SSDs',r'\bssd\b|solid.state'), ('B','RAM',r'^ram$|\bddr[45]\b'),
 ('B','Motherboards',r'motherboard'), ('B','Graphics cards',r'graphics card|geforce|radeon rx'), ('B','Processors',r'\bprocessor\b|^cpu$'),
 ('B','USB hubs and docks',r'usb hub|docking|multiport|mport'), ('B','Keyboards',r'keyboard|wireless combo'), ('B','Mice',r'\bmouse\b'),
 ('B','PC cooling',r'cpu.*cooler|liquid cool'), ('B','PC cabinets',r'\bcabinet\b|chassis'),
 ('B','Memory cards',r'memory card|microsd'),
 ('M','Security cameras',r'security camera|home safety|homeview|\bcctv\b'),
 ('C','Televisions',r'\btelevision\b|\bled tv\b|\bbravia\b|\bgoogle tv\b|^tvs?$'), ('C','Projectors',r'projector'),
 ('C','Streaming devices',r'apple tv|streaming'),
 ('D','Soundbars',r'soundbar|home theatre|home audio|home cinema'),
 ('D','Microphones',r'microphone|\bmic\b'),
 ('D','Earbuds',r'earbuds|\btws\b|airpods|airdopes'),
 ('D','Earphones',r'earphone|neckband|in.ear|bassheads|rockerz in'),
 ('D','Headphones',r'headphone|headset|rockerz|bh.onear'),
 ('D','Speakers',r'speaker|bt.speaker|partypal|homepod'),
 ('E','Water heaters',r'water heater|\bgeyser\b'), ('E','Refrigerators',r'refrigerator'), ('E','Washing machines',r'washing machine'),
 ('E','Dishwashers',r'dishwasher'), ('E','Freezers',r'freezer'), ('E','Water purifiers',r'water purifier'),
 ('G','Vacuum cleaners',r'vacuum|canister'), ('G','Garment steamers',r'garment steamer|standing steamer|handheld steamer'),
 ('G','Irons',r'\biron\b|fabric care irons'),
 ('H','Air conditioners',r'air conditioner|split ac|window ac'), ('H','Air coolers',r'air cooler|desert cooler'),
 ('H','Air purifiers',r'air purifier'), ('H','Humidifiers',r'humidifier'),
 ('H','Fans',r'\bfan\b|ceiling fans|personal fans'), ('H','Room heaters',r'room heater|radiator|heat convector'),
 ('F','Air fryers',r'air.?fryer'), ('F','Coffee machines',r'coffee|espresso'), ('F','Mixer grinders',r'mixer|grinder|nutri.blend'),
 ('F','Blenders',r'blender'), ('F','Juicers',r'juicer'), ('F','Choppers',r'chopper|food processor'),
 ('F','Electric kettles',r'kettle'), ('F','Cooktops',r'cooktop|\bhob\b|\bhobs\b|induction|\bstove\b'),
 ('F','Ovens',r'\botg\b|\botgs\b|\boven\b|microwave'), ('F','Chimneys',r'chimney|chimneys'),
 ('F','Sandwich makers',r'sandwich|grill|toaster|waffle'), ('F','Electric cookers',r'(?=.*(?:electric|rice|nutri))(?=.*(?:cook|pot))'),
 ('I','Trimmers',r'trimmer|shaver'), ('I','Hair dryers',r'hair dryer'), ('I','Hair stylers',r'hair.*(?:straight|curl|styl)'),
 ('I','Electric toothbrushes',r'electric toothbrush'), ('I','Massagers',r'massager'),
 ('N','Network adapters',r'lan card|network adapter|usb adapter|wi.fi adapter'), ('N','Routers',r'router|mesh wi.fi'), ('N','Network switches',r'ethernet switch|network switch'),
 ('O','Printers',r'\bprinter\b'), ('O','Scanners',r'\bscanner\b'), ('O','Writing tablets',r'writing pad|writing tablet'),
 ('P','Power banks',r'power bank|\bmah\b'), ('P','Chargers',r'charger|charging|adaptor'),
 ('P','Power strips',r'extension board|power strip|surge protector'), ('P','UPS',r'\bups\b'),
]
PATTERNS = [(code, name, re.compile(pattern, re.I)) for code, name, pattern in TYPES]
LEGACY_TITLE = re.compile(r'\bDDR[23]\b|\bLGA[ -]?(?:775|1155|1156)\b|\bCore\s*2\b|\bGT\s*(?:710|730)\b|\biPhone\s*(?:[6-9]|1[0-4])\b', re.I)


def classify(product):
    kind = product.get('product_type', '').strip()
    name = re.split(r'\b(?:compatible|compatibility|supports|for use with)\b', product.get('title', ''), flags=re.I)[0]
    if re.search(r'cable|connector|battery|accessor|cooling pad|cover|case|tip|ear pad|mouse pad|strap|warrant', kind, re.I):
        return None
    if re.search(r'\b(?:NAS|storage server)\b', kind, re.I):
        return 'B', 'NAS and storage servers'
    if re.search(r'\b(?:VoIP|telephone|IP phone|FXS|FXO)\b', name, re.I):
        return 'N', 'VoIP phones and adapters'
    if re.search(r'\b(?:DVR|NVR|video recorder)\b', name, re.I):
        return 'M', 'Security video recorders'
    if re.search(r'\badapter card\b', kind, re.I) and re.search(r'(?:\d+GbE|ethernet|network)', name, re.I):
        return 'N', 'Network adapters'
    if kind.casefold() in {'digital imaging', 'personal audio', 'power series', 'playstation'}:
        kind = ''
    # Classify the explicit store type first, rather than words in compatibility copy.
    for text in (kind, name):
        for label, pattern in [('Power banks', r'power bank'), ('Chargers', r'charger|charging station'), ('Security cameras', r'security camera|cctv|homeview')]:
            if re.search(pattern, text, re.I):
                return ('M' if label == 'Security cameras' else 'P'), label
        for code, label, pattern in PATTERNS:
            if pattern.search(text):
                return code, label
    return None


def text(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def specifications(markup, title):
    soup = BeautifulSoup(markup or '', 'html.parser')
    for node in soup(['script', 'style']):
        node.decompose()
    specs = {}
    for tr in soup.select('tr'):
        cells = [text(c.get_text(' ', strip=True)) for c in tr.select('th,td')]
        if len(cells) == 2 and 1 < len(cells[0]) < 70 and 0 < len(cells[1]) < 350:
            if not re.search(r'price|mrp|warranty|review|rating|manufacturer|address|import|customer|country|contact', cells[0], re.I):
                specs[cells[0].rstrip(':')] = cells[1]
    plain = text(soup.get_text(' ', strip=True))
    for key, pattern in [
        ('Capacity', r'\b\d+(?:\.\d+)?\s*(?:mAh|TB|GB|litres?|liters?|[lL])\b'),
        ('Power', r'\b\d+(?:\.\d+)?\s*(?:W|watts?)\b'),
        ('Display size', r'\b\d+(?:\.\d+)?[ -]*(?:inches|inch|cm)\b'),
        ('Processor', r'\b(?:Apple\s+)?M[2-9](?:\s+(?:Pro|Max|Ultra))?\s+chip\b|\bA\d{2}\s*(?:Pro)?\s*chip\b'),
        ('Camera', r'\b\d+(?:\.\d+)?\s*MP\b'),
        ('CPU cores', r'\b\d+[ -]core\s+CPU\b'),
        ('GPU cores', r'\b\d+[ -]core\s+GPU\b'),
        ('Bluetooth', r'\bBluetooth\s*(?:version\s*)?\d(?:\.\d)?\b'),
        ('Refresh rate', r'\b\d+\s*Hz\b'),
        ('Playback', r'\b\d+\s*(?:hours?|hrs?)\s*(?:of\s*)?(?:playback|playtime)\b'),
        ('Cooling capacity', r'\b\d+(?:\.\d+)?\s*tons?\b'),
        ('Energy rating', r'\b[1-5][ -]*star\b'),
    ]:
        match = re.search(pattern, title + ' ' + plain, re.I)
        if match and key not in specs:
            specs[key] = match.group()
    bullets = [text(li.get_text(' ', strip=True)) for li in soup.select('li')]
    bullets = [v for v in bullets if 20 <= len(v) <= 280 and not re.search(r'cashback|discount|shipping|return|warranty|refund', v, re.I)]
    for i, value in enumerate(bullets[:6], 1):
        specs.setdefault(f'Feature {i}', value)
    return plain[:6000], dict(list(specs.items())[:30])


def get_json(url):
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=(10, 35), headers={'User-Agent': 'TuracozCatalogVerifier/1.0', 'Accept-Encoding': 'identity'})
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def samsung_candidates(fields, departments, as_of, cache, reuse_cache=False):
    """Accept exact Samsung India variants with a public India product listing."""
    found = []
    for section, family, kind in [('smartphones', 'galaxy-s26', 'Smartphones'), ('smartphones', 'galaxy-s26-ultra', 'Smartphones'), ('smartphones', 'galaxy-a27', 'Smartphones'), ('tablets', 'galaxy-tab-s12', 'Tablets')]:
        url = f'https://www.samsung.com/in/{section}/{family}/buy/'
        path = cache / (family + '.html')
        try:
            if reuse_cache and path.exists():
                markup = path.read_text(encoding='utf-8')
            else:
                response = requests.get(url, timeout=(10, 30), headers={'Accept-Encoding':'identity'})
                response.raise_for_status()
                markup = response.text
                path.write_text(markup, encoding='utf-8')
            soup = BeautifulSoup(markup, 'html.parser')
            for node in soup.select('script[type="application/ld+json"]'):
                data = json.loads(node.string or node.text)
                groups = data if isinstance(data, list) else [data]
                for group in groups:
                    variants = group.get('hasVariant', []) if group.get('@type') == 'ProductGroup' else [group]
                    for product in variants:
                        offer = product.get('offers') or {}
                        if not isinstance(offer, dict) or offer.get('priceCurrency') != 'INR':
                            continue
                        if not str(offer.get('itemCondition', '')).endswith('/NewCondition'):
                            continue
                        sku, name = product.get('sku'), text(product.get('name'))
                        photo = product.get('image')
                        if not sku or not name or not isinstance(photo, str):
                            continue
                        if photo.startswith('//'):photo = 'https:' + photo
                        if not photo.startswith('https://'):continue
                        price = Decimal(str(offer.get('price', 0)))
                        if not price.is_finite() or price <= 0:continue
                        specs = {'Model code':sku}
                        for i, memory in enumerate(re.findall(r'\d+\s*(?:GB|TB)', name, re.I)):
                            specs['Storage' if i == 0 else 'RAM'] = memory
                        if len(specs) < 2:continue
                        row = dict.fromkeys(fields, '')
                        row.update(category_code='A',department=departments['A'],subcategory=kind,product_type=kind,product_name=name,manufacturer='Samsung',brand='Samsung',model=sku,manufacturer_part_number=sku,description=name+'. '+text(product.get('description'))[:450],specifications_json=json.dumps(specs),product_url=offer.get('url') or url,product_source_url=url,price_source_url=url,release_date_precision='unknown',official_price=str(price),price_currency='INR',price_type='current_store_selling_price',price_market='India',source_attribution='Samsung India exact-variant product listing',collected_on=as_of,verification_status='india_store_listing_image_verified',notes=f'Exact SKU product listing and INR price observed on Samsung India on {as_of}; stock is not used as an inclusion criterion. No release date inferred.')
                        found.append((row,[photo],{'store':'https://www.samsung.com/in','store_product_id':sku,'variant_id':sku,'sku':sku,'listed_at':None}))
        except (requests.RequestException, ValueError, KeyError):
            print(f'No usable exact-SKU India product listing: {url}', flush=True)
    return found


def fetch_store(source, cache, max_pages, reuse_cache=False):
    url, brand = source
    currency_path = cache / (hashlib.sha256(url.encode()).hexdigest()[:12] + '-currency.txt')
    currency = currency_path.read_text().strip() if reuse_cache and currency_path.exists() else get_json(url+'/cart.js').get('currency')
    if currency != 'INR':
        raise ValueError('Storefront currency is not verified INR')
    currency_path.write_text(currency)
    result = []
    for page in range(1, max_pages + 1):
        path = cache / (hashlib.sha256(url.encode()).hexdigest()[:12] + f'-{page}.json')
        if reuse_cache and path.exists():
            products = json.loads(path.read_text(encoding='utf-8'))
        else:
            products = get_json(f'{url}/products.json?limit=250&page={page}').get('products', [])
            path.write_text(json.dumps(products, ensure_ascii=False), encoding='utf-8')
        result.extend((url, brand, p) for p in products)
        if len(products) < 250:
            break
    return result


def make_row(url, brand, product, fields, departments, as_of, cutoff):
    title = text(product.get('title'))
    if EXCLUDE.search(title + ' ' + product.get('product_type', '')) or '🎁' in title:
        return None, 'used_bundle_accessory_or_non_product'
    water_bottle_only = re.search(r'\bwater bottle\b', title, re.I) and not re.search(r'\b(?:electric|pump|dispenser)\b', title, re.I)
    if NON_ELECTRICAL_HOUSEWARE.search(title) or water_bottle_only or MEDICAL_INSPECTION_TOOLS.search(title):
        return None, 'out_of_scope_houseware_or_medical_tool'
    source_description = BeautifulSoup(product.get('body_html') or '', 'html.parser').get_text(' ', strip=True)
    if (re.search(r'\bkettle\b', title, re.I)
            and not re.search(r'\belectric\b', title, re.I)
            and re.search(r'\bstovetop\b|\bstove[- ]top\b|microwave.safe', source_description, re.I)):
        return None, 'out_of_scope_houseware_or_medical_tool'
    if (re.search(r'robot vacuum cleaner kit', title, re.I)
            and re.search(r'mop cloth pads?|easy to install and easy to replace', source_description, re.I)):
        return None, 'used_bundle_accessory_or_non_product'
    if LEGACY_TITLE.search(title):
        return None, 'known_legacy_hardware_generation'
    created = product.get('created_at', '')[:10]
    published = product.get('published_at', '')[:10]
    if not created or not published or not cutoff <= created <= as_of or published > as_of:
        return None, 'not_recent_store_listing'
    category = classify(product)
    if brand == 'Lava' and re.match(r'(?:lava )?(?:agni|blaze|storm|shark|bold|yuv)', title, re.I):
        category = ('A', 'Smartphones')
    if not category:
        return None, 'unmapped_product_type'
    code, kind = category
    # Cross-brand retailer: allow only a named, well-identified make.
    if brand == 'Apple':
        vendor = text(product.get('vendor'))
        if vendor.casefold() not in {'apple', 'beats'}:
            return None, 'unknown_reseller_brand'
        brand = 'Beats' if vendor.casefold() == 'beats' else 'Apple'
    brand = brand or text(product.get('vendor'))
    if not brand or brand.casefold() in {'generic', 'oem', 'tpstech', 'tps technologies'}:
        return None, 'unknown_brand'
    if kind in {'Smartphones', 'Tablets'} and brand.casefold() not in {'apple', 'lava', 'infinix', 'samsung', 'motorola', 'google', 'oneplus', 'realme', 'vivo', 'oppo', 'xiaomi', 'redmi', 'itel'}:
        return None, 'accessory_not_phone_or_tablet'
    if kind in {'Laptops', 'Desktop computers'} and brand.casefold() in {'agaro', 'portronics', 'ambrane', 'crompton', 'philips', 'noise', 'boat'}:
        return None, 'accessory_not_computer'
    candidates = []
    for v in product.get('variants', []):
        try:
            price = Decimal(str(v.get('price', '0')))
        except InvalidOperation:
            continue
        if Decimal('100') <= price <= Decimal('2000000'):
            candidates.append((price, v))
    if not candidates:
        return None, 'invalid_price'
    price, variant = min(candidates, key=lambda v: v[0])
    variant_title = text(variant.get('title'))
    description, specs = specifications(product.get('body_html'), title)
    if not description and len(title) >= 60 and len(specs) >= 3:
        description = title
    if len(description) < 60 or len(specs) < 2:
        return None, 'incomplete_description_or_specs'
    for option in product.get('options', []):
        position = option.get('position', 0)
        value = variant.get(f'option{position}')
        if value and value != 'Default Title':
            specs[text(option.get('name'))] = text(value)
    images = product.get('images') or []
    mapped = [im for im in images if variant['id'] in im.get('variant_ids', [])]
    featured = variant.get('featured_image')
    if isinstance(featured, dict) and featured.get('src'):
        mapped.insert(0, featured)
    has_colours = any(re.search(r'colou?r', o.get('name', ''), re.I) and len(o.get('values', [])) > 1 for o in product.get('options', []))
    if has_colours and not mapped:
        return None, 'no_exact_colour_image'
    photos = [im.get('src') for im in (mapped or images) if im.get('src') and im.get('width', 0) >= 180 and im.get('height', 0) >= 180]
    photos = [s for s in photos if s.startswith('https://') and not re.search(r'placeholder|no.image|logo', s, re.I)]
    if not photos:
        return None, 'no_product_photo'
    name = title.split('|')[0].strip()
    if variant_title and variant_title != 'Default Title' and variant_title.casefold() not in name.casefold():
        name += ' — ' + variant_title
    if len(name) > 255:
        return None, 'overlong_or_ambiguous_name'
    # Manufacturer model is not invented from a retailer SKU.
    model = text(product.get('title')).split('|')[0].strip()[:190]
    sku = text(variant.get('sku'))
    if sku:
        specs['Store SKU'] = sku
    row = dict.fromkeys(fields, '')
    row.update(category_code=code, department=departments[code], subcategory=kind, product_type=kind,
               product_name=name, manufacturer=brand, brand=brand, model=model,
               description=(f'{brand} {kind}: {name}. ' + '; '.join(f'{k}: {v}' for k, v in list(specs.items())[:6]))[:1500], specifications_json=json.dumps(specs, ensure_ascii=False),
               product_url=f"{url}/products/{product['handle']}?variant={variant['id']}",
               release_date_precision='unknown', official_price=str(price), price_currency='INR',
               price_type='current_store_selling_price', price_market='India',
               source_attribution=f'{url.split("//")[1]} public India store listing', collected_on=as_of,
               verification_status='india_store_listing_image_verified',
               notes=f'India store product listing and price observed on {as_of}; stock is not used as an inclusion criterion. Store listing created {created}; this is NOT a release date. Exact selected variant: {variant_title}. Current listing and price should be reconfirmed before purchase. Store product ID {product["id"]}; variant ID {variant["id"]}.')
    row['product_source_url'] = row['price_source_url'] = row['product_url']
    return (row, photos[:3], {'store': url, 'store_product_id': str(product['id']), 'variant_id': str(variant['id']), 'sku': sku, 'listed_at': created}), ''


def download_image(candidate, out, known=None):
    row, urls, evidence = candidate
    for url in urls:
        try:
            prior = (known or {}).get(url)
            if prior:
                cached = out / 'images' / prior['local_image']
                if cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == prior['image_sha256']:
                    row['image_url'] = '/catalog-images/' + prior['local_image']
                    evidence.update({key: prior[key] for key in ('image_source_url', 'local_image', 'image_sha256', 'width', 'height')})
                    return row, evidence
            with requests.get(url, stream=True, timeout=(10, 25)) as response:
                response.raise_for_status()
                if not response.headers.get('Content-Type', '').startswith('image/'):
                    continue
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > 8_000_000:
                        raise ValueError('image exceeds 8MB')
            with Image.open(io.BytesIO(data)) as im:
                im.load()
                if min(im.size) < 180 or max(im.size) > 16000:
                    continue
                im = ImageOps.exif_transpose(im).convert('RGB')
                im.thumbnail((900, 900))
                body = io.BytesIO()
                im.save(body, 'WEBP', quality=84, method=1)
                content = body.getvalue()
                filename = hashlib.sha256(content).hexdigest()[:24] + '.webp'
                (out / 'images' / filename).write_bytes(content)
                row['image_url'] = '/catalog-images/' + filename
                evidence.update(image_source_url=url, local_image=filename, image_sha256=hashlib.sha256(content).hexdigest(), width=im.width, height=im.height)
                return row, evidence
        except (requests.RequestException, OSError, ValueError, Image.DecompressionBombError):
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(ZoneInfo('Asia/Kolkata')).date())
    parser.add_argument('--listed-since', type=date.fromisoformat, required=True)
    parser.add_argument('--max-pages', type=int, default=4)
    parser.add_argument('--reuse-cache', action='store_true', help='Replay same-day product-listing evidence for debugging')
    parser.add_argument('--output', type=Path, default=ROOT / '.firecrawl' / 'india-catalog-staged')
    args = parser.parse_args()
    if not args.reuse_cache and args.as_of != datetime.now(ZoneInfo('Asia/Kolkata')).date():
        parser.error('Fresh inventory evidence must use the current India date; use --reuse-cache only to replay saved evidence')
    as_of, cutoff = args.as_of.isoformat(), args.listed_since.isoformat()
    out = args.output
    (out / 'images').mkdir(parents=True, exist_ok=True)
    cache = ROOT / '.firecrawl' / f'inventory-{as_of}'
    cache.mkdir(parents=True, exist_ok=True)
    import csv
    with (ROOT / 'product_catalog' / 'all_products.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
    with (ROOT / 'product_catalog' / 'category_plan.csv').open(encoding='utf-8-sig') as stream:
        departments = {r['department_code']: r['department'] for r in csv.DictReader(stream)}
    products, errors = [], []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [(s, pool.submit(fetch_store, s, cache, args.max_pages, args.reuse_cache)) for s in SOURCES]
        for source, future in futures:
            try:
                found = future.result()
                products.extend(found)
                print(f'Inventory: {source[0]}: {len(found)}', flush=True)
            except Exception as exc:
                errors.append({'source': source[0], 'error': type(exc).__name__})
                print(f'Unavailable source: {source[0]} ({type(exc).__name__})', flush=True)
    rejected, candidates, seen = Counter(), [], set()
    for url, brand, product in products:
        candidate, reason = make_row(url, brand, product, fields, departments, as_of, cutoff)
        if candidate:
            row, photos, evidence = candidate
            key = (row['brand'].casefold(), re.sub(r'\W+', '', evidence['sku'] or row['product_name']).casefold())
            if key in seen:
                rejected['duplicate_exact_product'] += 1
                continue
            seen.add(key)
            candidates.append(candidate)
        else:
            rejected[reason] += 1
    candidates.extend(samsung_candidates(fields, departments, as_of, cache, args.reuse_cache))
    unique, identities, skus = [], set(), set()
    for candidate in candidates:
        row, photos, proof = candidate
        key = (row['brand'].casefold(), re.sub(r'\W+', '', row['product_name']).casefold())
        sku_key = (row['brand'].casefold(), proof.get('sku', '').casefold()) if proof.get('sku') else None
        if key in identities or (sku_key and sku_key in skus):
            rejected['duplicate_exact_product'] += 1
            continue
        identities.add(key)
        if sku_key:skus.add(sku_key)
        unique.append(candidate)
    candidates = unique
    print(f'Candidates meeting listing/detail/recency gates: {len(candidates)}; downloading exact-product photos', flush=True)
    accepted, evidence = [], []
    previous = out / 'availability_evidence.json'
    known = {r['image_source_url']: r for r in json.loads(previous.read_text(encoding='utf-8'))} if previous.exists() else {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for index, result in enumerate(pool.map(lambda c: download_image(c, out, known), candidates), 1):
            if result:
                row, proof = result
                accepted.append(row)
                evidence.append({'product_name': row['product_name'], **proof, 'checked_on': as_of, 'market_presence': 'listed_in_india', 'market_presence_basis': 'india_store_product_page', 'currency': 'INR', 'price': row['official_price'], 'purchase_url': row['product_url']})
            else:
                rejected['image_download_or_decode_failed'] += 1
            if index % 100 == 0:
                print(f'Image verification {index}/{len(candidates)}; accepted {len(accepted)}', flush=True)
    accepted.sort(key=lambda r: (r['category_code'], r['brand'], r['product_name']))
    with (out / 'all_products.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(accepted)
    (out / 'availability_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    report = {'as_of': as_of, 'listing_cutoff': cutoff, 'scanned': len(products), 'accepted': len(accepted), 'brands': dict(Counter(r['brand'] for r in accepted)), 'categories': dict(Counter(r['department'] for r in accepted)), 'rejected': dict(rejected), 'unavailable_sources': errors, 'limitations': ['Store listing date is not release date; unknown release dates remain blank.', 'An India product page establishes market presence; stock is not inferred.', 'Only current structured public listings from the configured Indian stores are covered.']}
    (out / 'verification_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
