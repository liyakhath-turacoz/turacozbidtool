"""India-first, resumable catalog ingestion. Discovery is never publication.

Network inputs are retained separately from normalized variant candidates. The
live products table is only changed by the explicit publish operation.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import html as html_lib
import json
import re
import threading
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlencode
from urllib.robotparser import RobotFileParser
from pymysql.cursors import SSDictCursor
import xml.etree.ElementTree as ET
import requests

from bs4 import BeautifulSoup
from . import catalog_taxonomy as taxonomy
from . import product_identity as identity
from .catalog_importer import connect
from .configuration import load_local_environment
from .product_sources import fetch, parse_date, cutoff, validate_url
from .scripts.rebuild_india_catalog import specifications

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT/'product_catalog'/'source_registry.json'
CACHE = ROOT/'.firecrawl'/'bulk-catalog'
HEADERS = {'User-Agent':'TuracozCatalogVerifier/1.0','Accept-Encoding':'gzip, deflate'}

def packed(value):
    return json.dumps(value,ensure_ascii=False,default=str,separators=(',',':'))

def digest(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None,microsecond=0)

def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))['sources']

def india_listing_evidence(source,record):
    """An India-market product page is sufficient; stock status is irrelevant."""
    if source.get('market')!='India':return None
    page=urlparse(str(record.get('url') or ''));base=urlparse(str(source.get('url') or ''))
    host=(page.hostname or '').lower();base_host=(base.hostname or '').lower()
    if (page.scheme!='https' or not host or not base_host or
        not (host==base_host or host.endswith('.'+base_host))):return None
    checked=str(record.get('checked_on') or '')
    try:date.fromisoformat(checked)
    except ValueError:return None
    return {'source_id':source['id'],'url':record['url'],'market':'India',
        'kind':'india_store_product_page','checked_on':checked}

def initialize():
    statements = [
      '''CREATE TABLE IF NOT EXISTS catalog_ingestion_runs (id CHAR(36) PRIMARY KEY, started_at DATETIME NOT NULL, completed_at DATETIME NULL, status VARCHAR(24) NOT NULL, report_json LONGTEXT NULL) ENGINE=InnoDB''',
      '''CREATE TABLE IF NOT EXISTS catalog_ingestion_documents (id CHAR(64) PRIMARY KEY, source_id VARCHAR(60) NOT NULL, external_id VARCHAR(190) NOT NULL, url TEXT NOT NULL, payload_json LONGTEXT NOT NULL, fetched_at DATETIME NOT NULL, KEY idx_ingest_document_source(source_id)) ENGINE=InnoDB''',
      '''CREATE TABLE IF NOT EXISTS catalog_ingestion_urls (id CHAR(64) PRIMARY KEY, source_id VARCHAR(60) NOT NULL, url TEXT NOT NULL, state VARCHAR(32) NOT NULL DEFAULT 'discovered', error_code VARCHAR(100) NULL, checked_at DATETIME NOT NULL, KEY idx_ingest_url_source(source_id,state)) ENGINE=InnoDB''',
      '''CREATE TABLE IF NOT EXISTS catalog_ingestion_candidates (id CHAR(64) PRIMARY KEY, document_id CHAR(64) NOT NULL, source_id VARCHAR(60) NOT NULL, external_id VARCHAR(190) NOT NULL, identity_key CHAR(64) NOT NULL, state VARCHAR(40) NOT NULL, issues_json LONGTEXT NOT NULL, record_json LONGTEXT NOT NULL, existing_product_id CHAR(36) NULL, checked_at DATETIME NOT NULL, KEY idx_ingest_candidate_state(state), KEY idx_ingest_identity(identity_key)) ENGINE=InnoDB''',
      '''CREATE TABLE IF NOT EXISTS catalog_model_families (id CHAR(64) PRIMARY KEY, brand VARCHAR(190) NOT NULL, name VARCHAR(255) NOT NULL, type_id VARCHAR(60) NOT NULL, created_at DATETIME NOT NULL) ENGINE=InnoDB''',
      '''CREATE TABLE IF NOT EXISTS catalog_variant_links (product_id CHAR(36) PRIMARY KEY, family_id CHAR(64) NOT NULL, identity_key CHAR(64) NOT NULL, attributes_json LONGTEXT NOT NULL, identity_basis VARCHAR(80) NOT NULL, KEY idx_variant_family(family_id), UNIQUE KEY uq_canonical_variant(identity_key)) ENGINE=InnoDB''',
      '''CREATE TABLE IF NOT EXISTS catalog_retail_offers (id CHAR(64) PRIMARY KEY, candidate_id CHAR(64) NOT NULL, product_id CHAR(36) NOT NULL, source_id VARCHAR(60) NOT NULL, seller_sku VARCHAR(190) NULL, url TEXT NOT NULL, price DECIMAL(20,2) NOT NULL, currency CHAR(3) NOT NULL, availability VARCHAR(24) NOT NULL, checked_at DATETIME NOT NULL, KEY idx_retail_offer_product(product_id)) ENGINE=InnoDB''',
      '''CREATE TABLE IF NOT EXISTS catalog_type_assignments (product_id CHAR(36) PRIMARY KEY, type_id VARCHAR(60) NOT NULL, taxonomy_version INT NOT NULL, path_json LONGTEXT NOT NULL, reason VARCHAR(255) NOT NULL, checked_at DATETIME NOT NULL, KEY idx_catalog_type(type_id)) ENGINE=InnoDB'''
    ]
    with connect() as conn,conn.cursor() as cur:
        for sql in statements:cur.execute(sql)
        conn.commit()

_host_lock=threading.Lock()
_next_request={}
_robots={}

def body(url, max_bytes=32*1024*1024, fresh=False):
    """Public-URL validation, bounded caching, host pacing, no auth in URLs/logs."""
    validate_url(url,'bulk')
    CACHE.mkdir(parents=True,exist_ok=True)
    cached=CACHE/(digest(url)+'.body')
    if not fresh and cached.exists() and time.time()-cached.stat().st_mtime<6*3600 and cached.stat().st_size<=max_bytes:
        return cached.read_bytes()
    host=urlparse(url).netloc
    with _host_lock:
        due=max(time.monotonic(),_next_request.get(host,0))
        _next_request[host]=due+0.6
    pause=due-time.monotonic()
    if pause>0:time.sleep(pause)
    current=url;started=time.monotonic()
    for hop in range(6):
        validate_url(current,'bulk')
        with requests.get(current,headers=HEADERS,timeout=(8,20),stream=True,allow_redirects=False) as response:
            if response.status_code in {301,302,303,307,308}:
                current=urljoin(current,response.headers['Location']);continue
            response.raise_for_status()
            result=bytearray()
            while chunk:=response.raw.read1(65536,decode_content=True):
                result.extend(chunk)
                if len(result)>max_bytes or time.monotonic()-started>90:raise ValueError('source_size_or_time_limit')
            cached.write_bytes(result)
            return bytes(result)
    raise ValueError('too_many_source_redirects')

def allowed(url):
    base=f'{urlparse(url).scheme}://{urlparse(url).netloc}'
    if base not in _robots:
        parser=RobotFileParser()
        try:
            parser.parse(body(base+'/robots.txt',max_bytes=100000).decode('utf-8','replace').splitlines())
        except Exception:
            # A robots denial is a source failure, not permission to bypass it.
            return False
        _robots[base]=parser
    return _robots[base].can_fetch('TuracozCatalogVerifier',url)

def save_document(source, external_id, url, payload, connection=None):
    docid=digest(source['id']+'|'+str(external_id))
    owns_connection=connection is None
    with (connect() if owns_connection else nullcontext(connection)) as conn,conn.cursor() as cur:
        cur.execute('''INSERT INTO catalog_ingestion_documents VALUES (%s,%s,%s,%s,%s,%s)
          ON DUPLICATE KEY UPDATE url=VALUES(url),payload_json=VALUES(payload_json),fetched_at=VALUES(fetched_at)''',
          [docid,source['id'],str(external_id)[:190],url,packed(payload),utcnow()])
        if owns_connection:conn.commit()
    return docid

def variant_identity(record):
    """Seller SKUs never become MPNs; model alone never merges variants."""
    gtins=identity.gtins(record.get('gtin'))
    if gtins:
        # Preserve leading-zero equivalence across UPC/EAN/GTIN-14.
        key='gtin:'+gtins[0].zfill(14)
    elif record.get('mpn') and record.get('brand'):
        key='mpn:'+identity.norm_brand(record['brand'])+':'+identity.norm_code(record['mpn'])+':'+packed(normalized_attributes(record))
    elif (record.get('verified_model') or {}).get('url'):
        key='manufacturer_model:'+identity.norm_brand(record['brand'])+':'+identity.norm_text(record['verified_model']['name'])+':'+identity.norm_text(record['name'])+':'+packed(normalized_attributes(record))
    else:
        key='name:'+identity.norm_brand(record.get('brand'))+':'+identity.norm_text(record.get('name'))+':'+packed(record.get('attributes',{}))
    return digest(key)


def normalized_attributes(record):
    # Variant facts often live in structured specs or the seller title rather
    # than in a dedicated JSON-LD `color`/`size` field. Include those facts in
    # identity so storage/RAM/finish variants sharing one MPN stay distinct.
    from .catalog_structure import attributes as variant_attributes
    return dict(sorted((identity.norm_text(k).replace('colour','color'),identity.norm_text(v))
                       for k,v in variant_attributes(record).items() if str(v or '').strip()))


def same_source_variant(left,right):
    verified_sku=bool(left.get('icecat_evidence') and left.get('mpn') and right.get('seller_sku') and
        identity.norm_code(left['mpn'])==identity.norm_code(right['seller_sku']) and
        identity.norm_brand(left.get('brand'))==identity.norm_brand(right.get('brand')) and
        normalized_attributes(left)==normalized_attributes(right))
    same_exact_listing=bool(left.get('type_id')==right.get('type_id') and
        identity.norm_brand(left.get('brand'))==identity.norm_brand(right.get('brand')) and
        identity.norm_text(left.get('name'))==identity.norm_text(right.get('name')) and
        normalized_attributes(left)==normalized_attributes(right))
    return (variant_identity(left)==variant_identity(right) or verified_sku or bool(
        left.get('mpn') and right.get('mpn') and
        identity.norm_code(left['mpn'])==identity.norm_code(right['mpn']) and
        identity.norm_brand(left.get('brand'))==identity.norm_brand(right.get('brand')) and
        normalized_attributes(left)==normalized_attributes(right)) or same_exact_listing)

def india_store_launch_year(record):
    """Return an explicitly labelled year from the exact current India listing.

    Manufacturing/packing dates, page dates, unlabelled years, and third-party
    evidence are deliberately not treated as launch-year evidence. A retailer's
    exact product title may provide year-only evidence when it explicitly says
    "2025 Model" or "2025 Launch" (or the equivalent word order).
    """
    listing=record.get('india_listing_evidence') or {}
    if (listing.get('kind')!='india_store_product_page' or listing.get('market')!='India'
        or listing.get('source_id')!=record.get('source_id') or listing.get('url')!=record.get('url')
        or not listing.get('checked_on') or listing.get('checked_on')!=record.get('checked_on')):
        return None
    specs=record.get('specs') or {}
    if not isinstance(specs,dict):return None
    matches=[]
    for label,value in specs.items():
        if not re.fullmatch(r'\s*(?:launch|release)\s*year\s*',str(label),re.I):continue
        match=re.fullmatch(r'\s*(20\d{2})\s*',str(value))
        if match:matches.append((str(label).strip(),int(match.group(1))))
    title=str(record.get('name') or '')
    title_labels=(
        (r'\b(20\d{2})\s+model\b','product title: model year'),
        (r'\bmodel\s+(20\d{2})\b','product title: model year'),
        (r'\b(20\d{2})\s+launch\b','product title: launch year'),
        (r'\blaunch\s+(20\d{2})\b','product title: launch year'),
    )
    for pattern,label in title_labels:
        matches.extend((label,int(year)) for year in re.findall(pattern,title,re.I))
    years={year for _,year in matches}
    if len(years)!=1:return None
    mpn=identity.norm_code(record.get('mpn') or '')
    verified=record.get('verified_model') or {}
    exact_identity=bool(identity.gtins(record.get('gtin')) or verified.get('url'))
    if mpn:
        context=identity.norm_code(' '.join(str(record.get(k) or '') for k in ('name','family_name','url')))
        # A conflicting part number is a manual-review case, not a launch-year
        # match. The code must occur in the exact listing's model/title context.
        if mpn not in context:return None
        exact_identity=True
    if not exact_identity:return None
    label=next(label for label,year in matches if year in years)
    return {'year':next(iter(years)),'field':label}


def release_issues(record,today=None):
    today=today or date.today()
    proof=record.get('release_evidence') or {}
    value=record.get('release_date') or str(record.get('release_year') or '')
    kind=proof.get('kind')
    if not proof.get('url') or kind not in {'manufacturer_release','icecat_explicit_release','manufacturer_model_year','india_store_launch_year'}:
        return ['missing_verified_release_date'] if not value else ['unsupported_release_evidence']
    if kind=='india_store_launch_year':
        retailer_year=india_store_launch_year(record)
        listing=record.get('india_listing_evidence') or {}
        if (not retailer_year or proof.get('url')!=record.get('url')
            or proof.get('field')!=retailer_year['field']
            or proof.get('checked_on')!=listing.get('checked_on')
            or not re.fullmatch(r'20\d{2}',str(value))
            or int(value)!=retailer_year['year']):
            return ['unsupported_release_evidence']
    try:
        if proof.get('precision')=='day':
            earliest=latest=date.fromisoformat(value)
        elif proof.get('precision')=='month' and re.fullmatch(r'20[0-9]{2}-[0-9]{2}',value):
            import calendar
            year,month=map(int,value.split('-'))
            earliest=date(year,month,1);latest=date(year,month,calendar.monthrange(year,month)[1])
            if (year,month)==(today.year,today.month) and record.get('india_listing_evidence'):latest=today
        elif proof.get('precision')=='year' and re.fullmatch(r'20[0-9]{2}',value):
            earliest=date(int(value),1,1);latest=date(int(value),12,31)
            # A verified model year plus a current India listing proves the
            # model exists by today without asserting stock.
            if int(value)==today.year and record.get('india_listing_evidence'):latest=today
        else:return ['incomplete_release_date']
    except ValueError:return ['missing_verified_release_date']
    if earliest>today:return ['future_release']
    if latest>today:return ['release_window_uncertain']
    try:minimum=date(today.year-4,today.month,today.day)
    except ValueError:minimum=date(today.year-4,today.month,28)
    if earliest<minimum:return ['older_than_four_years' if latest<minimum else 'release_window_uncertain']
    return []

def issues(record,today=None):
    today=today or date.today()
    result=[]
    if not record.get('type_id'):result.append('unmapped_product_type')
    else:
        title_type,_=taxonomy.classify(record.get('name',''))
        if title_type and title_type!=record['type_id']:result.append('product_type_mismatch')
        elif record['type_id'] in {'microwaves','freezers','dishwashers','ovens'} and not title_type:
            # Require the appliance noun in the product title. Retail category
            # labels alone misclassify "microwave-safe" dishes and "freezer-safe"
            # bottles as appliances.
            result.append('product_type_mismatch')
    if not record.get('brand'):result.append('missing_brand')
    if taxonomy.is_accessory(record):result.append('non_product_accessory')
    if re.search(r'\b(?:demo|demonstration|display unit|floor model)\b',record.get('name',''),re.I):result.append('demonstration_unit')
    if re.search(r'\b(?:emp|employee|staff.only)\b',record.get('name',''),re.I):result.append('restricted_offer')
    if record.get('variant_conflict'):result.append('conflicting_variant_specifications')
    if len(identity.gtins(record.get('gtin')))>1:result.append('ambiguous_variant_gtin')
    if not identity.gtins(record.get('gtin')) and not record.get('mpn') and not (record.get('verified_model') or {}).get('url'):result.append('needs_manufacturer_identifier')
    listing=record.get('india_listing_evidence') or {}
    if (listing.get('kind')!='india_store_product_page' or listing.get('market')!='India' or
        listing.get('source_id')!=record.get('source_id') or listing.get('url')!=record.get('url')):
        result.append('missing_india_listing_evidence')
    try:
        if not 0<=(today-date.fromisoformat(listing.get('checked_on') or '')).days<=30:
            result.append('stale_india_listing_evidence')
    except ValueError:result.append('stale_india_listing_evidence')
    if record.get('currency')!='INR' or record.get('market')!='India':result.append('unverified_india_market')
    try:
        price=Decimal(str(record.get('price','0')))
        if not price.is_finite() or not 0<price<=Decimal('999999999999.99'):result.append('invalid_price')
    except InvalidOperation:result.append('invalid_price')
    result.extend(release_issues(record,today))
    if record.get('type_id'):
        missing=taxonomy.missing_attributes(record['type_id'],record.get('specs',{}))
        if missing:result.append('missing_type_attributes')
    if not record.get('image_sources'):result.append('missing_variant_image')
    if record.get('variant_image_ambiguous'):result.append('ambiguous_variant_image')
    if record.get('condition')!='new':result.append('unknown_condition' if record.get('condition')=='unknown' else 'not_new_condition')
    return list(dict.fromkeys(result))

def save_candidate(source,docid,record,connection=None):
    cid=digest(source['id']+'|'+str(record['external_id']))
    record['india_listing_evidence']=india_listing_evidence(source,record)
    problems=issues(record)
    state='eligible' if not problems else 'pending'
    if any(p in problems for p in ('older_than_four_years','future_release','not_new_condition','demonstration_unit')):state='rejected'
    owns_connection=connection is None
    with (connect() if owns_connection else nullcontext(connection)) as conn,conn.cursor() as cur:
        # Refresh raw inventory without destroying successful enrichment.
        cur.execute('SELECT record_json FROM catalog_ingestion_candidates WHERE id=%s',[cid])
        prior=cur.fetchone()
        if prior:
            old=json.loads(prior['record_json'])
            if same_source_variant(old,record):
                for key in ('release_date','release_year','release_evidence','verified_model','identifier_evidence','icecat_evidence','enrichment_attempt','variant_conflict'):
                    if old.get(key):record[key]=old[key]
                if old.get('icecat_evidence'):record['specs']={**old.get('specs',{}),**record.get('specs',{})}
                if not record.get('gtin') and old.get('icecat_evidence'):record['gtin']=old.get('gtin','')
                if not record.get('mpn') and (old.get('icecat_evidence') or old.get('identifier_evidence')):record['mpn']=old.get('mpn','')
            problems=issues(record);state='eligible' if not problems else 'pending'
            if any(p in problems for p in ('older_than_four_years','future_release','not_new_condition','demonstration_unit')):state='rejected'
        cur.execute('''INSERT INTO catalog_ingestion_candidates
          (id,document_id,source_id,external_id,identity_key,state,issues_json,record_json,checked_at)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
          ON DUPLICATE KEY UPDATE identity_key=VALUES(identity_key),state=IF(state='published','published',VALUES(state)),
          issues_json=VALUES(issues_json),record_json=VALUES(record_json),checked_at=VALUES(checked_at)''',
          [cid,docid,source['id'],str(record['external_id'])[:190],variant_identity(record),state,packed(problems),packed(record),utcnow()])
        if owns_connection:conn.commit()
    return cid

def manufacturer_code(specs):
    for name,value in specs.items():
        # A marketing label such as "Model: S25" is a generation name, not a
        # manufacturer part number. Require an explicit number/code field.
        if re.fullmatch(r'(?:manufacturer part number|mpn|model number|model no\.?|model code|product code)',name.strip(),re.I):
            value=str(value).strip()
            if 2<len(value)<100 and re.search(r'\d',value):return value
        # Some retailers label the manufacturer SKU simply "Model". Accept
        # that field only when it is a compact alphanumeric code, never a model
        # family such as "Galaxy A17 5G" or a retailer item code.
        if re.fullmatch(r'model',name.strip(),re.I):
            value=str(value).strip().upper()
            if (re.fullmatch(r'[A-Z0-9][A-Z0-9._/-]{6,31}',value)
                and re.search(r'[A-Z]',value) and re.search(r'\d',value)):
                return value
    return ''

def shopify_records(source,product,currency):
    title=str(product.get('title') or '').strip()
    typeid,reason=taxonomy.classify(title,product.get('product_type',''))
    plain,specs=specifications(product.get('body_html',''),title)
    brand=str(product.get('vendor') or source.get('brand') or '').strip()
    if source.get('brand') and source['id'] not in {'amkette','sharkninja','imagine'}:
        brand=source['brand']
    # Retailer product IDs and store SKU numbers are not manufacturer identities.
    mpn=manufacturer_code(specs)
    if not mpn and source['id']=='philips':
        found=re.search(r'\b[A-Z]{2,4}\d{3,5}/\d{2}\b',title)
        if found:mpn=found.group()
    if not mpn and source['id']=='sony' and typeid=='televisions':
        # ShopAtSC exposes Sony TV model codes in the product title instead
        # of its Shopify variant SKU. Keep only the manufacturer-style K-...
        # code; never treat the retailer's variant id as the model number.
        found=re.search(r'\bK-\d{2,3}[A-Z0-9]{4,}\b',title,re.I)
        if found:mpn=found.group().upper()
    if source['id']=='sony' and typeid=='televisions':
        # Sony store descriptions include label/value pairs inside Feature N
        # fields. Promote those explicit labels so type validation can check
        # resolution and connectivity without parsing marketing text by guess.
        for value in list(specs.values()):
            if not str(value).startswith(('Resolution:','Connectivity:','Sound :','Display :','Smart TV Features:')):continue
            for segment in re.split(r'\s*\|\s*',str(value)):
                label,sep,detail=segment.partition(':')
                if sep and label.strip().casefold() in {'resolution','refresh rate','connectivity','sound','display','smart tv features'} and detail.strip():
                    specs.setdefault(label.strip().title(),detail.strip())
    if not mpn and source['id']=='voltas':
        # Voltas Shopify descriptions label the model as "Model No." inside
        # prose, while the generic specification parser keeps it in the
        # description. These 3-digit INV codes are the manufacturer models;
        # the six-digit number beside them is a retailer SKU.
        found=re.search(r'\b\d{3}INV\b',(title+' '+plain).upper())
        if found:mpn=found.group()
    for variant in product.get('variants',[]):
        sku=str(variant.get('sku') or '').strip()
        variant_mpn=mpn
        if not variant_mpn and len(sku)>=5 and re.search('[A-Za-z]',sku) and re.search('[0-9]',sku) and re.search(r'(?<![\w])'+re.escape(sku)+r'(?![\w])',title,re.I):
            variant_mpn=sku
        attrs={o.get('name','Option'):variant.get('option'+str(o.get('position',0)))
               for o in product.get('options',[]) if variant.get('option'+str(o.get('position',0))) not in (None,'Default Title')}
        photo=[im.get('src') for im in product.get('images',[]) if variant['id'] in im.get('variant_ids',[]) and im.get('src')]
        color_variants=any(re.search('colou?r',o.get('name',''),re.I) and len(o.get('values',[]))>1 for o in product.get('options',[]))
        ambiguous=color_variants and not photo
        if not photo and not ambiguous:photo=[im['src'] for im in product.get('images',[]) if im.get('src')][:3]
        variant_name=str(variant.get('title') or '')
        name=title+((' — '+variant_name) if variant_name and variant_name!='Default Title' and variant_name.casefold() not in title.casefold() else '')
        yield {'external_id':str(variant['id']),'parent_external_id':str(product['id']),'family_name':title,
          'name':name,'brand':brand,'model':variant_mpn or title[:190],'mpn':variant_mpn,'gtin':';'.join(identity.gtins(variant.get('barcode'))),
          'seller_sku':variant.get('sku') or '', 'attributes':attrs,'type_id':typeid,'classification_reason':reason,
          'description':plain,'specs':{**specs,**{str(k):str(v) for k,v in attrs.items()}},'price':str(variant.get('price') or '0'),
          'availability':'listed_in_india','currency':currency,'market':source['market'],
          'condition':'used' if re.search(r'refurb|renewed|pre.owned|open.box|pre.order|repacked|pulled.out',title,re.I) else 'new',
          'image_sources':photo,'variant_image_ambiguous':ambiguous,
          'url':source['url']+'/products/'+product['handle']+'?variant='+str(variant['id']),
          'source_id':source['id'],'store_listing_date':str(product.get('created_at') or '')[:10],
          'release_date':None,'checked_on':date.today().isoformat()}

def collect_shopify(source,max_pages=20):
    # Cart paths commonly disallow crawling. Read the publicly rendered
    # storefront currency instead; do not request cart/session endpoints.
    if not allowed(source['url']+'/'):raise ValueError('robots_disallowed_storefront')
    home=body(source['url']+'/').decode('utf-8','replace')
    match=re.search(r'Shopify\.currency\s*=\s*\{[^}]*"active"\s*:\s*"([A-Z]{3})"',home)
    if not match:match=re.search(r'"currencyCode"\s*:\s*"([A-Z]{3})"',home)
    currency=match.group(1) if match else None
    if currency!='INR':raise ValueError('store_currency_not_INR')
    products=variants=0
    for page in range(1,max_pages+1):
        url=source['url']+f'/products.json?limit=250&page={page}'
        if not allowed(url):raise ValueError('robots_disallowed_feed')
        items=json.loads(body(url,fresh=True)).get('products')
        if not isinstance(items,list):raise ValueError('invalid_inventory_feed')
        for p in items:
            docid=save_document(source,p['id'],source['url']+'/products/'+p['handle'],p)
            for record in shopify_records(source,p,currency):save_candidate(source,docid,record);variants+=1
            products+=1
        print(f"{source['id']}: page {page}, {products} parent listings / {variants} variants staged",flush=True)
        if len(items)<250:break
    return {'parents':products,'variants':variants,'page_limit_reached':len(items)==250}


def _vtex_values(value):
    if isinstance(value,list):return ', '.join(str(v).strip() for v in value if v is not None and str(v).strip())
    if isinstance(value,dict):return packed(value)
    return str(value).strip() if value is not None else ''


def vtex_records(source,product):
    """Normalize one public Indian VTEX product using only its own SKU data."""
    title=str(product.get('productName') or product.get('productTitle') or '').strip()
    categories=product.get('categories') or []
    source_type=categories[-1].strip('/').split('/')[-1] if categories else ''
    typeid,reason=taxonomy.classify(title,source_type)
    brand=str(product.get('brand') or source.get('brand') or '').strip()
    raw_specs={}
    for key,value in product.items():
        if isinstance(value,(str,int,float,list)) and key not in {'productName','productTitle','categories','categoriesIds','items','productClusters','searchableClusters','releaseDate','allSpecifications','allSpecificationsGroups','skuSpecifications'}:
            text=_vtex_values(value)
            if text:raw_specs[str(key)]=text
    all_specs=product.get('allSpecifications') or []
    if isinstance(all_specs,dict):
        for key,value in all_specs.items():
            text=_vtex_values(value)
            if text:raw_specs.setdefault(str(key),text)
    else:
        for key in all_specs:
            if key in product:
                text=_vtex_values(product.get(key))
                if text:raw_specs.setdefault(str(key),text)
    item_specs=product.get('skuSpecifications') or []
    # SKU specifications vary by VTEX account; retain them only when the
    # returned object explicitly names both the field and this SKU's value.
    for item in product.get('items') or []:
        variations={}
        for spec in item_specs:
            if not isinstance(spec,dict):continue
            name=str(spec.get('field') or spec.get('name') or spec.get('fieldName') or '').strip()
            values=spec.get('values') or spec.get('valuesBySku') or []
            if isinstance(values,dict):values=values.get(str(item.get('itemId')),[])
            for value in values if isinstance(values,list) else []:
                if isinstance(value,dict) and str(value.get('id') or value.get('itemId') or '')==str(item.get('itemId')):
                    actual=value.get('name') or value.get('value')
                    if name and actual:variations[name]=str(actual)
        option=str(item.get('name') or '').strip()
        if option and option.casefold() not in {'default','default title'}:
            variations.setdefault('Variant',option)
        item_variations=item.get('variations') or {}
        if isinstance(item_variations,dict):
            for key,value in item_variations.items():
                text=_vtex_values(value)
                if key and text:variations.setdefault(str(key),text)
        specs={**raw_specs,**variations}
        images=[str(image.get('imageUrl') or image.get('url') or '') for image in item.get('images') or [] if isinstance(image,dict)]
        images=[url for url in images if url.startswith('https://')]
        reference_ids=item.get('referenceId') or []
        seller_sku=''
        if isinstance(reference_ids,list):
            seller_sku=next((str(row.get('Value')) for row in reference_ids if isinstance(row,dict) and row.get('Value')), '')
        sellers=sorted(item.get('sellers') or [],key=lambda seller:not seller.get('sellerDefault',False))
        offers=[]
        for seller in sellers:
            offer=seller.get('commertialOffer') or {}
            try:price=float(offer.get('Price') or 0)
            except (ValueError,TypeError):price=0
            if price>0:
                offers.append((price,seller,offer))
        offer=offers[0] if offers else (0,{},{});
        price,seller,offer_doc=offer
        # Only SKU-level EAN is assigned to a variant. A parent EAN is used
        # when the parent has exactly one sellable SKU.
        gtins=identity.gtins(item.get('ean'))
        if not gtins and len(product.get('items') or [])==1:
            gtins=identity.gtins(_vtex_values(product.get('EAN code')))
        launch=_vtex_values(product.get('Launch Year'))
        launch_match=re.search(r'\b(20[0-9]{2})\b',launch)
        release_year=int(launch_match.group(1)) if launch_match else None
        description=BeautifulSoup(str(product.get('description') or product.get('metaTagDescription') or ''),'html.parser').get_text(' ',strip=True)
        full_name=str(item.get('nameComplete') or '').strip()
        variant_label=str(item.get('name') or '').strip()
        name=full_name or title+(' — '+variant_label if variant_label and variant_label.casefold() not in title.casefold() else '')
        url=urljoin(source['url'].rstrip('/')+'/',str(product.get('link') or ''))
        if seller_sku:url=url+'?skuId='+str(item.get('itemId') or seller_sku)
        if not seller_sku:seller_sku=str(item.get('itemId') or '')
        record={'external_id':str(item.get('itemId') or seller_sku or product.get('productId')),
            'parent_external_id':str(product.get('productId') or ''),'family_name':title,'name':name,
            'brand':brand,'model':manufacturer_code(specs) or seller_sku or title[:190],'mpn':manufacturer_code(specs),
            'gtin':';'.join(gtins),'seller_sku':seller_sku,'attributes':variations,'type_id':typeid,
            'classification_reason':reason,'description':description,'specs':specs,'price':str(price),
            'currency':'INR','market':'India','availability':'listed_in_india',
            'condition':'new','image_sources':images,'url':url,'source_id':source['id'],
            'release_date':None,'release_year':release_year,'checked_on':date.today().isoformat()}
        record['verified_model']={'name':title,'url':url,'external_code':str(product.get('productReference') or '')}
        if release_year:
            record['release_evidence']={'url':url,'kind':'manufacturer_model_year','precision':'year','scope':'Whirlpool India model Launch Year specification'}
        yield record


def collect_vtex(source,batch_size=50,max_items=50000):
    endpoint=source['url'].rstrip('/')+source.get('api_path','/api/catalog_system/pub/products/search')
    if not allowed(endpoint):raise ValueError('robots_disallowed_public_catalog_api')
    offset=0;parents=variants=0;reported_total=None;errors=[]
    while offset<max_items:
        end=min(offset+batch_size-1,max_items-1)
        query=endpoint+f'?_from={offset}&_to={end}'
        page=None
        for attempt in range(1,4):
            try:
                page=json.loads(body(query,fresh=True))
                if not isinstance(page,list):raise ValueError('invalid_vtex_catalog_page')
                break
            except Exception as exc:
                errors.append({'from':offset,'to':end,'error':type(exc).__name__})
                time.sleep(min(attempt*2,6))
        if page is None:break
        response=page
        if not response:break
        with connect() as conn:
            for product in response:
                docid=save_document(source,product.get('productId') or digest(packed(product)),
                    urljoin(source['url'].rstrip('/')+'/',str(product.get('link') or '')),product,connection=conn)
                parents+=1
                for record in vtex_records(source,product):
                    save_candidate(source,docid,record,connection=conn);variants+=1
            conn.commit()
        print(f"{source['id']}: catalog offset {offset}, {parents} parent products / {variants} SKU candidates staged",flush=True)
        offset+=len(response)
        if reported_total is not None and offset>=reported_total:break
        if len(response)<batch_size:break
        time.sleep(.6)
    return {'parents':parents,'variants':variants,'reported_total':reported_total,'next_offset':offset,'errors':errors}

def collect_sitemaps(source,max_maps=25):
    pending=[source['url']];seen=set();found=set();errors=[]
    while pending and len(seen)<max_maps:
        url=pending.pop(0)
        if url in seen:continue
        if urlparse(url).hostname!=urlparse(source['url']).hostname:continue
        seen.add(url)
        try:
            if not allowed(url):raise ValueError('robots_disallowed_sitemap')
            content=body(url)
            if content.startswith(b'\x1f\x8b'):
                import io
                with gzip.GzipFile(fileobj=io.BytesIO(content)) as stream:content=stream.read(32*1024*1024+1)
                if len(content)>32*1024*1024:raise ValueError('decompressed_sitemap_size_limit')
            root=ET.fromstring(content)
            locs=[n.text.strip() for n in root.iter() if n.tag.rsplit('}',1)[-1]=='loc' and n.text]
            if root.tag.rsplit('}',1)[-1]=='sitemapindex':
                # Product maps first; category/brand URLs are not product records.
                pending.extend(sorted(locs,key=lambda x:('product' not in x.lower(),x)))
            elif root.tag.rsplit('}',1)[-1]=='urlset':
                found.update(u for u in locs if not source.get('product_path') or source['product_path'] in urlparse(u).path)
            else:raise ValueError('not_a_sitemap')
        except Exception as error:errors.append({'url':url,'error':type(error).__name__})
    with connect() as conn,conn.cursor() as cur:
        values=[(digest(source['id']+'|'+u),source['id'],u,utcnow()) for u in sorted(found)]
        if values:cur.executemany('''INSERT INTO catalog_ingestion_urls(id,source_id,url,checked_at) VALUES (%s,%s,%s,%s)
          ON DUPLICATE KEY UPDATE checked_at=VALUES(checked_at)''',values)
        conn.commit()
    return {'sitemaps_visited':len(seen),'product_urls':len(found),'maps_pending':len(pending),'errors':errors}

def jsonld_products(markup):
    soup=BeautifulSoup(markup,'html.parser')
    def walk(value):
        if isinstance(value,list):
            for item in value:yield from walk(item)
        elif isinstance(value,dict):
            kind=value.get('@type',[]);kind=kind if isinstance(kind,list) else [kind]
            if 'Product' in kind:yield value
            if '@graph' in value:yield from walk(value['@graph'])
            if 'hasVariant' in value:yield from walk(value['hasVariant'])
    for script in soup.select('script[type="application/ld+json"]'):
        try:yield from walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):continue

def vijaysales_model_code(title):
    """Extract a likely manufacturer code from the exact Vijay Sales title."""
    parenthetical=[]
    for group in re.findall(r'\(([^()]*)\)',str(title or '')):
        parenthetical.extend(re.split(r'[|;,]',group))
    def valid(token):
        return (len(token)>=7 and sum(char.isalpha() for char in token)>=3 and
            sum(char.isdigit() for char in token)>=2)
    tokens=[]
    for value in parenthetical:
        tokens.extend(re.findall(r'(?<![A-Za-z0-9])([A-Za-z0-9][A-Za-z0-9./-]{5,31})(?![A-Za-z0-9])',value))
    for token in tokens:
        if valid(token):return token.strip(' .-/')
    suffix=str(title or '').rsplit(')',1)[-1]
    for token in re.findall(r'(?<![A-Za-z0-9])([A-Za-z0-9][A-Za-z0-9./-]{5,31})(?![A-Za-z0-9])',suffix):
        if valid(token):return token.strip(' .-/')
    tokens=[]
    tokens.extend(re.findall(r'(?<![A-Za-z0-9])([A-Za-z0-9][A-Za-z0-9./-]{5,31})(?![A-Za-z0-9])',str(title or '')))
    for token in tokens:
        if valid(token):return token.strip(' .-/')
    return ''

def vijaysales_page_details(soup,product,url):
    """Accept a listed India product with an exact price and product image.

    Vijay Sales emits AggregateOffer even for a single exact product page.
    Cross-check its offer against the page SKU, visible selling-price field,
    and SKU-specific image gallery; stock is not a market-presence requirement.
    """
    sku=str(product.get('sku') or product.get('productID') or '').strip()
    page=urlparse(url);product_url=urlparse(str(product.get('url') or ''))
    if (not sku.isdigit() or product_url.scheme!='https' or
        product_url.netloc.lower()!=page.netloc.lower() or product_url.path.rstrip('/')!=page.path.rstrip('/') or
        sku not in re.findall(r'\d+',page.path)):
        return None
    offers=product.get('offers') or []
    offers=offers if isinstance(offers,list) else [offers]
    if len(offers)!=1 or not isinstance(offers[0],dict):return None
    offer=offers[0]
    kind=offer.get('@type') or ''
    if isinstance(kind,list):kind=kind[0] if len(kind)==1 else ''
    if kind not in {'AggregateOffer','Offer'}:return None
    if str(offer.get('itemCondition','')).rstrip('/').rsplit('/',1)[-1]!='NewCondition':return None
    if offer.get('priceCurrency')!='INR':return None
    raw_price=offer.get('price') or offer.get('lowPrice')
    if not raw_price:return None
    try:
        price=Decimal(str(raw_price))
        if not price.is_finite() or price<=0:return None
        for field in ('lowPrice','highPrice'):
            value=offer.get(field)
            if value and Decimal(str(value))!=price:return None
    except (InvalidOperation,ValueError):return None
    dom_prices=set()
    for node in soup.select('.product__price .product__price--price'):
        match=re.search(r'(?:₹|INR)\s*([\d,]+(?:\.\d{1,2})?)',node.get_text(' ',strip=True),re.I)
        if match:
            try:dom_prices.add(Decimal(match.group(1).replace(',','')))
            except InvalidOperation:continue
    if dom_prices!={price}:return None
    title=str(product.get('name') or '').strip()
    type_id,_=taxonomy.classify(title,str(product.get('category') or ''))
    code=vijaysales_model_code(title)
    image_urls=[]
    for image in soup.select('.carousel__currentImage,.thumbnail__image'):
        raw=image.get('src') or image.get('data-src') or image.get('data-lazy-src') or ''
        if not raw and image.get('srcset'):
            raw=image.get('srcset').split(',')[0].strip().split()[0]
        if not raw:continue
        photo=urljoin(url,raw);parsed=urlparse(photo)
        if parsed.scheme!='https' or not (parsed.hostname or '').lower().endswith('.vijaysales.com'):continue
        if sku not in re.findall(r'\d+',parsed.path):continue
        if re.search(r'placeholder|no[-_]image|image[-_]not[-_]available',parsed.path,re.I):continue
        if photo not in image_urls:image_urls.append(photo)
    if not image_urls:return None
    description_node=soup.select_one('.productFullDetail__description')
    description=description_node.get_text(' ',strip=True) if description_node else str(product.get('description') or '')
    description=re.sub(r'^Product Description\s*','',description,flags=re.I).strip()
    specs_source=str(description_node) if description_node else str(product.get('description') or '')
    _,specs=specifications(specs_source,title)
    feature_list=soup.select_one('.product__keyfeatures--list')
    if feature_list:
        feature_index=0
        # Vijay Sales HTML entity-escapes the markup inside this list.
        decoded_features=BeautifulSoup(html_lib.unescape(feature_list.get_text()),'html.parser')
        for label_node in decoded_features.select('b'):
            label=label_node.get_text(' ',strip=True).strip().rstrip(':')
            values=[]
            for sibling in label_node.next_siblings:
                if getattr(sibling,'name',None) in {'b','br'}:break
                value=sibling.get_text(' ',strip=True) if hasattr(sibling,'get_text') else str(sibling).strip()
                if value:values.append(value)
            value=' '.join(values).strip()
            if not label or not value or len(label)>80:continue
            specs[label]=value[:1000]
            feature_index+=1
            if feature_index>=24:break
    if type_id=='washers':
        capacity=re.search(r'\b(\d+(?:\.\d+)?\s*kg)\b',title+' '+description,re.I)
        spin=re.search(r'\b(\d{2,4}\s*rpm)\b',title+' '+description,re.I)
        load=re.search(r'\b(front\s+load|top\s+load|semi[ -]?automatic|fully\s+automatic)\b',title,re.I)
        if capacity:specs.setdefault('Capacity',capacity.group(1))
        if spin:specs.setdefault('Spin speed',spin.group(1))
        if load:specs.setdefault('Load type',load.group(1))
    if type_id=='televisions':
        resolution=re.search(r'\b(\d{3,4}\s*[x×]\s*\d{3,4}|8K|4K|UHD|Full HD|FHD)\b',title,re.I)
        if resolution:specs.setdefault('Resolution',resolution.group(1))
    return {'sku':sku,'mpn':code,'price':str(price),'image_sources':image_urls,
        'description':description or str(product.get('description') or ''),'specs':specs,
        'offer':{'@type':'Offer','price':str(price),'priceCurrency':'INR',
            'itemCondition':'https://schema.org/NewCondition'}}

def retail_records(source,url,markup):
    retailer_specs={};poorvika_pim={};poorvika_offer={};soup=None
    if source['id']=='reliance':
        soup=BeautifulSoup(markup,'html.parser')
        for entry in soup.select('li.specifications-list'):
            cells=entry.find_all('span',recursive=False)
            if len(cells)==2:
                name,value=(c.get_text(' ',strip=True) for c in cells)
                if name and value:retailer_specs[name]=value
    elif source['id']=='poorvika':
        soup=BeautifulSoup(markup,'html.parser');next_data=soup.find('script',id='__NEXT_DATA__')
        if next_data and next_data.string:
            try:
                page=json.loads(next_data.string).get('props',{}).get('pageProps',{})
                poorvika_pim=page.get('pimData') or {};poorvika_offer=page.get('additionalData') or {}
                for group in (poorvika_pim.get('specifications') or {}).get('attributeGroups') or []:
                    for item in group.get('attributes') or []:
                        name=str(item.get('name') or '').strip();value=str(item.get('value') or '').strip()
                        if name and value and value.casefold() not in {'-', 'n/a', 'na', 'not available'}:
                            retailer_specs[name]=value
            except (TypeError,ValueError,AttributeError):poorvika_pim={};poorvika_offer={}
    elif source['id']=='vijaysales':soup=BeautifulSoup(markup,'html.parser')
    for p in jsonld_products(markup):
        title=str(p.get('name') or '').strip()
        if not title:continue
        vijay_page=vijaysales_page_details(soup,p,url) if source['id']=='vijaysales' else None
        if source['id']=='vijaysales' and not vijay_page:continue
        typeid,reason=taxonomy.classify(title,str(p.get('category') or ''))
        brand=p.get('brand') or '';brand=brand.get('name','') if isinstance(brand,dict) else str(brand)
        # Only this product's structured properties/description are evidence.
        # Whole-page tables can contain recommendations for other products.
        _,specs=specifications(str(p.get('description') or ''),title)
        specs.update(retailer_specs)
        if vijay_page:specs.update(vijay_page['specs'])
        properties=p.get('additionalProperty',[])
        if isinstance(properties,dict):properties=[properties]
        for prop in properties:
            if isinstance(prop,dict) and prop.get('name') and prop.get('value') is not None:specs[str(prop['name'])]=str(prop['value'])
        if source['id']=='poorvika' and poorvika_pim and identity.norm_text(poorvika_pim.get('name'))==identity.norm_text(title):
            specs.update(retailer_specs)
        image=p.get('image') or [];image=[image] if isinstance(image,(str,dict)) else image
        image=[im.get('url') or im.get('contentUrl') if isinstance(im,dict) else im for im in image]
        offers=p.get('offers') or [];offers=offers if isinstance(offers,list) else [offers]
        if vijay_page:
            image=vijay_page['image_sources'];offers=[vijay_page['offer']]
        for i,offer in enumerate(offers):
            if not isinstance(offer,dict) or str(offer.get('@type',''))=='AggregateOffer':continue
            seller_sku=str((poorvika_pim.get('sku') if source['id']=='poorvika' else '') or p.get('sku') or p.get('productID') or digest(url)[:24])
            gtin=';'.join(identity.gtins(' '.join(str(p.get(k) or '') for k in ('gtin','gtin8','gtin12','gtin13','gtin14'))))
            if source['id']=='poorvika' and poorvika_pim:
                gtin=';'.join(identity.gtins(' '.join([gtin,str(poorvika_pim.get('gtin') or ''),str(poorvika_pim.get('ean') or '')])))
            model=p.get('model');model=model.get('name','') if isinstance(model,dict) else str(model or '')
            if vijay_page:model=vijay_page['mpn'] or model
            if source['id']=='poorvika' and poorvika_pim:
                pim_model=poorvika_pim.get('model') or {}
                if isinstance(pim_model,dict):model=str(pim_model.get('name') or model)
            description=vijay_page['description'] if vijay_page else str(p.get('description') or '')
            if source['id']=='poorvika' and poorvika_pim:description=str(poorvika_pim.get('description') or description)
            mpn=p.get('mpn') or (poorvika_pim.get('mpn') if source['id']=='poorvika' else '') or (vijay_page['mpn'] if vijay_page else '') or manufacturer_code(specs) or (model if re.search(r'\d',model) and len(model)<80 else '')
            attributes={k:str(p[k]) for k in ('color','size') if p.get(k)}
            if vijay_page:
                color=re.search(r'\|\s*([A-Za-z][A-Za-z -]{1,30})\s*\)',title)
                if color:attributes.setdefault('color',color.group(1).strip())
            yield {'external_id':seller_sku+':'+str(i),
              'parent_external_id':str(p.get('productID') or seller_sku),
              'family_name':title,'name':title,'brand':brand,'model':model or manufacturer_code(specs) or title[:190],
              'mpn':str(mpn), 'gtin':gtin,'seller_sku':seller_sku,
              'attributes':attributes,'type_id':typeid,'classification_reason':reason,
              'description':BeautifulSoup(description,'html.parser').get_text(' ',strip=True),
              'specs':specs,'price':str(offer.get('price') or '0'),'currency':str(offer.get('priceCurrency') or ''),
              'market':source['market'],'availability':'listed_in_india',
              'condition':'new' if str(offer.get('itemCondition','')).endswith('/NewCondition') else 'unknown',
              'image_sources':[urljoin(url,u) for u in image if u],'url':url,'source_id':source['id'],
              'release_date':None,'checked_on':date.today().isoformat()}

def collect_pages(source,limit=30,workers=4):
    # Prioritise the buyer's major appliances and computing/mobile devices.
    # Matching a URL only orders discovery; every record still passes identity,
    # date, specification, condition and image checks before publication.
    priority=('smartphone','mobile-phone','tablet','iphone','ipad','macbook','laptop','notebook','desktop',
              'television','smart-tv','4k-tv','refrigerator','fridge','washing-machine','washer','dryer','dishwasher',
              'air-conditioner','split-ac','window-ac','microwave','freezer','water-purifier','air-purifier','vacuum-cleaner',
              'monitor','projector','digital-camera','mirrorless-camera','printer','gaming-console','soundbar')
    order=' OR '.join(['LOWER(url) LIKE %s']*len(priority))
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT id,url FROM catalog_ingestion_urls WHERE source_id=%s AND state='discovered' ORDER BY ("+order+") DESC,id LIMIT %s",[source['id']]+['%'+v+'%' for v in priority]+[limit]);urls=cur.fetchall()
    def process(item):
        state='parsed';error=None
        parsed=0
        try:
            if not allowed(item['url']):raise ValueError('robots_disallowed_product_page')
            markup=body(item['url']).decode('utf-8','replace')
            records=list(retail_records(source,item['url'],markup))
            if not records:state='needs_adapter';error='no_exact_product_offer'
            docid=save_document(source,item['id'],item['url'],{'html':markup})
            for record in records:save_candidate(source,docid,record);parsed+=1
        except Exception as exc:state='unavailable';error=type(exc).__name__
        with connect() as conn,conn.cursor() as cur:
            cur.execute('UPDATE catalog_ingestion_urls SET state=%s,error_code=%s,checked_at=%s WHERE id=%s',[state,error,utcnow(),item['id']]);conn.commit()
        return parsed
    # Requests remain paced per host by body(); a small worker pool lets slow
    # retailer responses overlap without increasing the configured request rate.
    with ThreadPoolExecutor(max_workers=max(1,min(int(workers),4))) as pool:
        parsed=sum(pool.map(process,urls))
    return {'urls_attempted':len(urls),'variants_parsed':parsed}

def icecat_enrichment(record,index_row=None):
    """Enrich India listings through exact GTIN or brand/MPN matches.

    A stale barcode must not block a fallback to the exact manufacturer
    model code, and a fallback response is still checked against its identity.
    """
    gtins=identity.gtins(record.get('gtin'));mpn=record.get('mpn') or lookup_sku(record);brand=record.get('brand')
    if not gtins and not (mpn and brand):return None
    lookups=[]
    if gtins:lookups.append({'ean_upc':gtins[0]})
    if mpn and brand:lookups.append({'prod_id':mpn,'vendor':brand})
    matched=None;lookup_errors=[]
    lookups=lookups if index_row is None else []
    if index_row is not None:
        path=str(index_row.get('path') or '').lstrip('/')
        if not path.startswith('export/freexml/'):raise ValueError('Unexpected Icecat XML path')
        url='https://data.icecat.biz/'+path
        root=ET.fromstring(fetch(url,'icecat',max_bytes=5*1024*1024,cache_seconds=86400,max_seconds=50))
        p=root.find('.//Product')
        if p is not None:
            supplier=p.find('Supplier');returned_brand=supplier.get('Name','') if supplier is not None else ''
            returned_gtins=identity.gtins(';'.join(x.get('EAN') or x.get('EAN_UPC') or x.get('Value') or '' for x in list(p.findall('.//EAN_UPC'))+list(p.findall('./EANCode')) if x.get('IsApproved','1')=='1'))
            same_mpn=bool(mpn and identity.norm_code(mpn)==identity.norm_code(p.get('Prod_id')) and identity.norm_brand(brand)==identity.norm_brand(returned_brand))
            same_gtin=bool({g.zfill(14) for g in gtins}&{g.zfill(14) for g in returned_gtins})
            if same_mpn or same_gtin:matched=(url,p,returned_gtins,same_mpn,same_gtin)
    else:
        for lookup in lookups:
            params={'lang':'EN','output':'productxml',**lookup}
            url='https://data.icecat.biz/xml_s3/xml_server3.cgi?'+urlencode(params)
            try:
                root=ET.fromstring(fetch(url,'icecat',max_bytes=5*1024*1024,cache_seconds=86400,max_seconds=50))
            except Exception as exc:
                lookup_errors.append(exc);continue
            p=root.find('.//Product')
            if p is None:continue
            supplier=p.find('Supplier');returned_brand=supplier.get('Name','') if supplier is not None else ''
            returned_gtins=identity.gtins(';'.join(x.get('EAN') or x.get('EAN_UPC') or x.get('Value') or '' for x in list(p.findall('.//EAN_UPC'))+list(p.findall('./EANCode')) if x.get('IsApproved','1')=='1'))
            same_mpn=bool(mpn and identity.norm_code(mpn)==identity.norm_code(p.get('Prod_id')) and identity.norm_brand(brand)==identity.norm_brand(returned_brand))
            same_gtin=bool({g.zfill(14) for g in gtins}&{g.zfill(14) for g in returned_gtins})
            if same_mpn or same_gtin:
                matched=(url,p,returned_gtins,same_mpn,same_gtin);break
    if not matched:
        if lookup_errors:raise lookup_errors[-1]
        return None
    url,p,returned_gtins,same_mpn,same_gtin=matched
    specs={}
    for f in p.findall('ProductFeature'):
        n=f.find('./Feature/Name');v=f.get('Presentation_Value') or f.get('LocalValue') or f.get('Value')
        if n is not None and n.get('Value') and v:specs[n.get('Value')]=v
    # Icecat's model gallery was previously discarded, leaving publication to
    # use only the retailer's image. Keep the Icecat image URLs separately and
    # use the main image first. safe_photo() later validates and downloads the
    # selected image into the local catalog bundle.
    gallery=[]
    pictures=p.findall('./ProductGallery/ProductPicture')
    pictures.sort(key=lambda picture:picture.get('IsMain','').upper()!='Y')
    for picture in pictures:
        image=next((picture.get(key) for key in ('Original','Pic','LowPic') if picture.get(key)),None)
        if image and image.startswith('https://images.icecat.biz/') and image not in gallery:
            gallery.append(image)
    description=''
    descriptions=p.findall('./ProductDescription')
    descriptions.sort(key=lambda item:item.get('langid',item.get('langId','0'))!='1')
    for item in descriptions:
        value=item.get('LongDesc') or item.get('MiddleDesc') or item.get('ShortDesc') or ''
        if value:
            description=BeautifulSoup(value,'html.parser').get_text(' ',strip=True)
            if description:break
    # Icecat's legacy attribute may FALL BACK TO DATE_ADDED. Never use it.
    dates=[d.get('Value') for d in p.findall('./ReleaseDate/Date') if d.get('Value') and d.get('langId',d.get('langid','0')) in {'0','1'}]
    valid=[]
    for value in dates:
        parsed,precision=parse_date(value)
        if parsed and precision in {'day','month','year'}:valid.append((parsed,precision))
    result={'icecat_evidence':{'url':url,'id':p.get('ID'),'match':'brand_mpn' if same_mpn else 'gtin','mpn':p.get('Prod_id'),'gtins':returned_gtins},
        'specs':specs,'icecat_image_sources':gallery}
    if description:result['icecat_description']=description
    # A retailer SKU is only promoted after an independent exact manufacturer
    # match. Merely appearing in a seller feed never establishes an MPN.
    if same_mpn and not record.get('mpn'):result['mpn']=p.get('Prod_id')
    if gtins and returned_gtins and not same_gtin:
        result['variant_conflict']='gtin'
    colors=r'\b(?:black|white|silver|grey|gray|blue|red|green|yellow|pink|purple|gold|orange)\b'
    requested=' '.join(str(v) for k,v in record.get('attributes',{}).items() if re.search(r'colou?r',k,re.I))
    returned=' '.join(str(v) for k,v in specs.items() if re.fullmatch(r'product colou?r|colou?r',k,re.I))
    tokens=lambda text:{v.replace('gray','grey') for v in re.findall(colors,text.lower())}
    if tokens(requested) and tokens(returned) and not tokens(requested)&tokens(returned):result['variant_conflict']='colour'
    if not gtins and len(returned_gtins)==1:result['gtin']=returned_gtins[0]
    if valid:
        # Icecat exposes an explicit ReleaseDate field at mixed precision.
        # Preserve only the precision supported by every EN/global value;
        # never turn a month or year into an invented day.
        years={parsed.year for parsed,_ in valid}
        months={(parsed.year,parsed.month) for parsed,_ in valid}
        days={(parsed.year,parsed.month,parsed.day) for parsed,_ in valid}
        if len(days)==1 and all(precision=='day' for _,precision in valid):
            parsed,precision=valid[0];release_value=parsed.isoformat()
        elif len(months)==1:
            parsed,precision=valid[0];precision='month';release_value=parsed.strftime('%Y-%m')
        elif len(years)==1:
            parsed,precision=valid[0];precision='year';release_value=str(parsed.year)
        else:precision=None;release_value=None
        if precision:
            result.update(release_date=release_value,release_evidence={'url':url,'kind':'icecat_explicit_release','precision':precision,'scope':'international_or_English_locale; explicit Icecat ReleaseDate field','values':[value for value in dates]})
    return result

def apply_icecat_enrichment(record,extra):
    """Persist Icecat-only descriptive content while retaining store price evidence."""
    values=dict(extra);specs=values.pop('specs',{})
    record['icecat_specs']=specs;record['specs']=specs
    images=values.get('icecat_image_sources') or []
    if images:
        record['icecat_image_sources']=images;record['image_sources']=images
    if values.get('icecat_description'):
        record['icecat_description']=values['icecat_description'];record['description']=values['icecat_description']
    record.update(values)
    return record


def lookup_sku(record):
    sku=str(record.get('seller_sku') or '').strip()
    return sku if 5<=len(sku)<=60 and re.search('[A-Za-z]',sku) and re.search('[0-9]',sku) and not re.search(r'\s',sku) else ''

def enrich(limit=200,workers=4,sources=None):
    with connect() as conn,conn.cursor() as cur:
        clause='';params=[]
        if sources:
            clause=' AND source_id IN ('+','.join(['%s']*len(sources))+')';params.extend(sources)
        # Rank all India-listed staged records by buyer-relevant product type first. A
        # recent accessory-heavy retailer feed must not starve phones,
        # computers and major appliances from exact-identifier enrichment.
        cur.execute("SELECT id,record_json FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible')"+clause+" ORDER BY checked_at DESC,id",params)
        rows=cur.fetchall()
    # Prioritize India-listed variants with exact identities, not arbitrary Icecat records.
    # Cover large electronics and home appliances before smaller product
    # types; Icecat lookups require an exact identifier from the India listing.
    priority_types=('smartphones','laptops','tablets','televisions','refrigerators','air_conditioners','washers',
        'dishwashers','freezers','microwaves','desktops','monitors','graphics_cards','processors',
        'cameras','projectors','printers','motherboards','routers','ups','water_heaters',
        'soundbars','speakers','smartwatches','air_purifiers','vacuum_cleaners','hard_drives','ssds','ram')
    by_type={type_id:[] for type_id in priority_types}
    for row in rows:
        r=json.loads(row['record_json'])
        if (r.get('india_listing_evidence') and r.get('type_id') in by_type
            and not taxonomy.is_accessory(r)
            and (r.get('mpn') or identity.gtins(r.get('gtin')) or lookup_sku(r))
            and not r.get('icecat_evidence') and not r.get('enrichment_attempt')):
            by_type[r['type_id']].append((row['id'],r))
    # Round-robin by product type so a large phone backlog cannot consume the
    # whole batch before laptop, appliance, and other device candidates run.
    candidates=[];positions={type_id:0 for type_id in priority_types}
    while len(candidates)<limit:
        added=False
        for type_id in priority_types:
            position=positions[type_id]
            if position<len(by_type[type_id]):
                candidates.append(by_type[type_id][position]);positions[type_id]+=1;added=True
                if len(candidates)>=limit:break
        if not added:break
    counts=Counter()
    def work(item):
        cid,r=item
        try:return cid,r,icecat_enrichment(r),None
        except Exception as e:return cid,r,None,type(e).__name__
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for cid,r,extra,error in pool.map(work,candidates):
            counts['attempted']+=1
            if error:counts['error_'+error]+=1
            r['enrichment_attempt']={'checked_on':date.today().isoformat(),'result':error or ('matched' if extra else 'unmatched')}
            if not extra:counts['unmatched_or_unavailable']+=1
            else:
                # Keep Icecat product content separate from the India listing's
                # price and market-presence evidence.
                apply_icecat_enrichment(r,extra)
            problems=issues(r);state='eligible' if not problems else 'pending'
            if any(x in problems for x in ('older_than_four_years','future_release','not_new_condition','demonstration_unit')):state='rejected'
            with connect() as conn,conn.cursor() as cur:
                cur.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,identity_key=%s,issues_json=%s,state=%s WHERE id=%s',[packed(r),variant_identity(r),packed(problems),state,cid]);conn.commit()
            if extra:counts['exact_matches']+=1
            # Count only dates provided by this exact Icecat response. A date
            # already present on the retailer/manufacturer record is not an
            # Icecat contribution.
            if extra and extra.get('release_date') and (extra.get('release_evidence') or {}).get('kind')=='icecat_explicit_release':
                counts['explicit_release_dates']+=1
            if counts['attempted']%25==0:print('Icecat exact-identifier enrichment: '+packed(counts),flush=True)
    return dict(counts)

def refresh_icecat_images(limit=50000,workers=8):
    """Recover Icecat gallery media for prior exact matches from cached XML."""
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT id,record_json,state FROM catalog_ingestion_candidates WHERE record_json LIKE %s ORDER BY id LIMIT %s",
            ['%"icecat_evidence"%',limit])
        rows=cur.fetchall()
    candidates=[]
    for row in rows:
        record=json.loads(row['record_json'])
        if record.get('icecat_evidence') and not record.get('icecat_image_sources'):
            candidates.append((row['id'],row['state'],record))
    counts=Counter(total_candidates=len(candidates))
    def work(item):
        cid,state,record=item
        try:return cid,state,record,icecat_enrichment(record),None
        except Exception as exc:return cid,state,record,None,type(exc).__name__
    with ThreadPoolExecutor(max_workers=max(1,min(int(workers),8))) as pool:
        for cid,state,record,extra,error in pool.map(work,candidates):
            counts['attempted']+=1
            images=(extra or {}).get('icecat_image_sources') or []
            if error:counts['errors']+=1
            if not images:counts['no_gallery']+=1;continue
            if extra:
                apply_icecat_enrichment(record,extra)
            problems=issues(record)
            next_state=state if state in {'published','rejected'} else ('eligible' if not problems else 'pending')
            with connect() as conn,conn.cursor() as cur:
                cur.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,issues_json=%s,state=%s WHERE id=%s',
                    [packed(record),packed(problems),next_state,cid]);conn.commit()
            counts['with_icecat_gallery']+=1
    return dict(counts)

def enrich_from_icecat_index(limit=50000,workers=8):
    """Join the downloadable Icecat index to current India listings, then read exact XML sheets.

    The compressed index is a product locator, not a source of India price or
    launch date. We use exact brand/MPN or GTIN joins and then validate the XML
    sheet against that identity before saving any Icecat details.
    """
    from .product_sources import icecat_index_rows
    endpoint='https://data.icecat.biz/export/freexml/EN/files.index.csv.gz'
    index_path=fetch(endpoint,'icecat',max_bytes=400*1024*1024,cache_seconds=86400,as_file=True,max_seconds=3600)
    allowed_types={'smartphones','laptops','tablets','televisions','refrigerators','air_conditioners','washers',
        'dishwashers','freezers','microwaves','desktops','monitors','graphics_cards','processors','cameras',
        'projectors','printers','motherboards','routers','ups','water_heaters','soundbars','speakers',
        'smartwatches','air_purifiers','vacuum_cleaners','hard_drives','ssds','ram'}
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT id,record_json,state FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible','published')")
        candidates=cur.fetchall()
    by_mpn=defaultdict(set);by_gtin=defaultdict(set);candidate_data={}
    for row in candidates:
        record=json.loads(row['record_json'])
        if (not record.get('india_listing_evidence') or record.get('type_id') not in allowed_types
            or taxonomy.is_accessory(record) or record.get('icecat_evidence')):continue
        candidate_data[row['id']]=(row['state'],record)
        if record.get('mpn') and record.get('brand'):
            by_mpn[(identity.norm_brand(record['brand']),identity.norm_code(record['mpn']))].add(row['id'])
        for gtin in identity.gtins(record.get('gtin')):by_gtin[gtin.zfill(14)].add(row['id'])
    matches=defaultdict(dict);scanned=0;quality_filtered=0
    for row in icecat_index_rows(index_path):
        scanned+=1
        if row.get('quality','').upper()!='ICECAT':
            quality_filtered+=1;continue
        brand=row.get('m_supplier_name') or row.get('supplier_name') or row.get('brand') or ''
        mpn=row.get('prod_id') or row.get('Prod_ID') or row.get('Prod_id') or ''
        mpn_ids=by_mpn.get((identity.norm_brand(brand),identity.norm_code(mpn)),set()) if brand and mpn else set()
        row_gtins=set()
        for raw in (row.get('ean_upc') or row.get('EAN_UPC') or '').split(';'):
            row_gtins.update(g.zfill(14) for g in identity.gtins(raw))
        gtin_ids=set().union(*(by_gtin.get(gtin,set()) for gtin in row_gtins)) if row_gtins else set()
        for cid in mpn_ids|gtin_ids:
            pid=str(row.get('product_id') or row.get('Product_ID') or '')
            if not pid or not row.get('path'):continue
            basis='gtin' if cid in gtin_ids else 'brand_mpn'
            prior=matches[cid].get(pid)
            if prior is None or (basis=='gtin' and prior[1]!='gtin'):matches[cid][pid]=(row,basis)
        if scanned%500000==0:print(f'Icecat index rows scanned: {scanned}',flush=True)
    selected=[];ambiguous=0
    for cid,products in matches.items():
        gtin_hits=[v for v in products.values() if v[1]=='gtin']
        if len(gtin_hits)==1:match=gtin_hits[0]
        elif len(products)==1:match=next(iter(products.values()))
        else:ambiguous+=1;continue
        state,record=candidate_data[cid];selected.append((cid,state,record,match[0]))
    selected.sort(key=lambda item:(item[2].get('type_id',''),item[0]))
    selected=selected[:max(1,int(limit))]
    counts=Counter(index_rows=scanned,index_match_candidates=len(matches),ambiguous_index_matches=ambiguous,
        non_icecat_quality_rows=quality_filtered,exact_index_xml_reads=len(selected))
    def work(item):
        cid,state,record,index_row=item
        try:return cid,state,record,icecat_enrichment(record,index_row=index_row),None
        except Exception as exc:return cid,state,record,None,'HTTP_'+str(exc.code) if hasattr(exc,'code') else type(exc).__name__
    with ThreadPoolExecutor(max_workers=max(1,min(int(workers),8))) as pool:
        for cid,state,record,extra,error in pool.map(work,selected):
            counts['attempted']+=1
            if error:
                counts['error_'+error]+=1
                continue
            if not extra:
                counts['index_xml_identity_mismatch']+=1
                continue
            apply_icecat_enrichment(record,extra)
            record['enrichment_attempt']={'checked_on':date.today().isoformat(),'result':'matched_full_icecat_index'}
            problems=issues(record)
            next_state=state if state=='published' else ('rejected' if any(x in problems for x in ('older_than_four_years','future_release','not_new_condition','demonstration_unit')) else ('eligible' if not problems else 'pending'))
            with connect() as conn,conn.cursor() as cur:
                cur.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,identity_key=%s,issues_json=%s,state=%s WHERE id=%s',
                    [packed(record),variant_identity(record),packed(problems),next_state,cid]);conn.commit()
            counts['exact_xml_matches']+=1
            counts['with_icecat_gallery']+=bool(record.get('icecat_image_sources'))
            counts['with_explicit_icecat_release']+=((record.get('release_evidence') or {}).get('kind')=='icecat_explicit_release')
            counts['with_gtin']+=bool(identity.gtins(record.get('gtin')))
            if counts['attempted']%25==0:print('Icecat full-index enrichment: '+packed(counts),flush=True)
    return dict(counts)

def reprocess(sources=None,limit=None):
    """Replay retained source documents in bounded memory; no network."""
    selected={s['id']:s for s in registry() if not sources or s['id'] in sources}
    total=0
    for source in selected.values():
        with connect() as read_conn,connect() as write_conn:
            cur=read_conn.cursor(SSDictCursor)
            query='SELECT id,source_id,url,payload_json,fetched_at FROM catalog_ingestion_documents WHERE source_id=%s ORDER BY fetched_at DESC,id DESC'
            params=[source['id']]
            if limit is not None:
                query+=' LIMIT %s';params.append(int(limit))
            cur.execute(query,params)
            for d in cur:
                payload=json.loads(d['payload_json'])
                if source['kind']=='shopify':records=shopify_records(source,payload,'INR')
                elif source['kind']=='vtex':records=vtex_records(source,payload)
                else:records=retail_records(source,d['url'],payload.get('html',''))
                for record in records:
                    record['checked_on']=d['fetched_at'].date().isoformat()
                    save_candidate(source,d['id'],record,connection=write_conn);total+=1
                    if total%100==0:write_conn.commit()
                    if total%500==0:print('Reprocessed '+str(total)+' retained variants',flush=True)
            write_conn.commit()
    return {'records_reprocessed':total}

def revalidate_india_listings():
    """Backfill India-page evidence and recalculate staging gates; never publishes."""
    sources={s['id']:s for s in registry()}
    counts=Counter();issues_count=Counter()
    with connect() as read_conn,connect() as write_conn:
        cur=read_conn.cursor(SSDictCursor)
        cur.execute('SELECT id,source_id,record_json,state FROM catalog_ingestion_candidates ORDER BY id')
        with write_conn.cursor() as update:
            for row in cur:
                record=json.loads(row['record_json'])
                source=sources.get(row['source_id'])
                record['india_listing_evidence']=india_listing_evidence(source,record) if source else None
                problems=issues(record);issues_count.update(problems)
                if row['state']=='published':state='published'
                elif any(code in problems for code in ('older_than_four_years','future_release','not_new_condition','demonstration_unit')):state='rejected'
                else:state='eligible' if not problems else 'pending'
                update.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,issues_json=%s,state=%s WHERE id=%s',
                    [packed(record),packed(problems),state,row['id']])
                counts[state]+=1
                counts['india_listing_evidence']+=bool(record.get('india_listing_evidence'))
                if sum(counts[key] for key in ('eligible','pending','published','rejected'))%1000==0:
                    write_conn.commit();print('Revalidated '+str(sum(counts[key] for key in ('eligible','pending','published','rejected')))+' staged variants',flush=True)
            write_conn.commit()
    return {'candidates_by_state':{key:counts[key] for key in ('eligible','pending','published','rejected')},
        'with_india_listing_evidence':counts['india_listing_evidence'],'top_issues':dict(issues_count.most_common(12))}

def report():
    with connect() as conn,conn.cursor() as cur:
        cur.execute('SELECT state,COUNT(*) n FROM catalog_ingestion_candidates GROUP BY state');states={r['state']:r['n'] for r in cur.fetchall()}
        cur.execute('SELECT source_id,COUNT(*) n FROM catalog_ingestion_documents GROUP BY source_id');docs=cur.fetchall()
        cur.execute('SELECT source_id,state,COUNT(*) n FROM catalog_ingestion_urls GROUP BY source_id,state');urls=cur.fetchall()
        cur.execute('SELECT COUNT(*) n FROM catalog_ingestion_candidates');candidate_count=cur.fetchone()['n']
        cur.execute("""SELECT COUNT(*) total,SUM(source='bulk_india') bulk_variants,
          SUM(release_date IS NOT NULL) with_release_date,SUM(release_year IS NOT NULL) with_release_year,
          SUM(release_date IS NULL AND release_year IS NOT NULL) year_only_release,
          SUM(release_year IS NOT NULL AND release_date_basis IN ('manufacturer_release','manufacturer_model_year','official_release_date','icecat_explicit_release','india_store_launch_year')) with_verified_release_year,
          SUM(gtin IS NOT NULL AND gtin!='') with_gtin FROM products WHERE deleted_at IS NULL AND catalog_visible=TRUE""");live={k:int(v or 0) for k,v in cur.fetchone().items()}
        # Group separately so every stable type has an explicit coverage count.
        cur.execute('SELECT a.type_id,COUNT(*) n FROM catalog_type_assignments a JOIN products p ON p.id=a.product_id WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE GROUP BY a.type_id');coverage={r['type_id']:r['n'] for r in cur.fetchall()}
        cur.execute("SELECT report_json FROM catalog_ingestion_runs WHERE report_json IS NOT NULL AND status!='running' ORDER BY started_at DESC LIMIT 100");runs=cur.fetchall()
    source_results={};known_sources={s['id'] for s in registry()}
    for run in runs:
        saved=json.loads(run['report_json']);operation=saved.get('operation')
        for source,result in saved.get('source_results',{}).items():
            if source in known_sources and isinstance(result,dict):
                source_results.setdefault(source,{}).setdefault(operation,result)
    types=Counter();problems=Counter();listed=0;dated=0;years=0;verified_years=0;gtins=0
    with connect() as conn:
        with conn.cursor(SSDictCursor) as candidates:
            candidates.execute('SELECT record_json,issues_json FROM catalog_ingestion_candidates')
            for row in candidates:
                r=json.loads(row['record_json']);types[r.get('type_id') or 'unclassified']+=1
                problems.update(json.loads(row['issues_json']));listed+=bool(r.get('india_listing_evidence'));dated+=bool(r.get('release_date'));years+=bool(r.get('release_year'))
                verified_years+=bool(r.get('release_year') and not release_issues(r));gtins+=bool(identity.gtins(r.get('gtin')))
    audit_path=ROOT/'backend'/'recovery'/'existing-catalog-audit.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.exists() else {}
    audit.pop('products',None)
    return {'generated_at':utcnow().isoformat(),'candidates':candidate_count,'states':states,'india_market_listings':listed,
      'live_catalog':live,'existing_catalog_audit':audit,'source_access_results':source_results,
      'coverage_by_type':[{'id':tid,'path':t['path'],'live':coverage.get(tid,0),'staged':types[tid]} for tid,t in taxonomy.TYPES.items()],
      'candidates_with_explicit_date':dated,'candidates_with_release_year':years,'candidates_with_verified_release_year':verified_years,
      'candidates_with_valid_gtin':gtins,'source_documents':docs,'discovery_urls':urls,
      'product_types':dict(types),'pending_issues':dict(problems),'rolling_cutoff':cutoff().isoformat(),
      'limitations':['Discovery URLs alone are not India product-page evidence.','An India-market product page is sufficient; stock status is neither collected nor used.','Pending candidates are not visible products.','A valid GTIN checksum alone does not establish assignment.','ReleaseDate attributes, listing dates and sitemap dates are never used as release evidence.']}


def apply_reviewed_releases():
    """Bulk exact-generation matching against reviewed manufacturer evidence."""
    rules=json.loads((ROOT/'product_catalog'/'model_release_evidence.json').read_text(encoding='utf-8'))['rules']
    counts=Counter()
    scanned=0
    with connect() as read_conn,connect() as write_conn:
        cur=read_conn.cursor(SSDictCursor)
        cur.execute("SELECT id,record_json,state FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible') ORDER BY id")
        with write_conn.cursor() as update:
          for row in cur:
            scanned+=1
            r=json.loads(row['record_json'])
            if r.get('release_date'):continue
            existing_precision=(r.get('release_evidence') or {}).get('precision')
            if taxonomy.is_accessory(r):continue
            for rule in rules:
                if (r.get('type_id')==rule['type_id'] and identity.norm_brand(r.get('brand'))==identity.norm_brand(rule['brand'])
                    and re.fullmatch(rule.get('mpn_pattern','.*'),identity.norm_code(r.get('mpn')))
                    and re.search(rule['name_pattern'],r.get('name',''),re.I)):
                    # Keep year-only evidence when no exact launch date is
                    # available, but upgrade it when a reviewed exact date is.
                    if existing_precision=='year' and not rule.get('release_date'):continue
                    r['release_date']=rule.get('release_date') or ''
                    r['release_year']=rule.get('release_year') or int(r['release_date'][:4])
                    if rule.get('verified_model'):
                        r['verified_model']={**rule['verified_model'],'url':rule['url']}
                    if rule.get('verified_mpn'):
                        r['mpn']=rule['verified_mpn']
                        r['identifier_evidence']={'url':rule.get('identifier_url') or rule['url'],'kind':'manufacturer_model_code'}
                    r['release_evidence']={'url':rule['url'],'kind':'manufacturer_release' if rule.get('release_date') else 'manufacturer_model_year','precision':'day' if rule.get('release_date') else 'year','scope':rule['scope'],'reviewed_on':rule['reviewed_on']}
                    problems=issues(r);state='eligible' if not problems else 'pending'
                    if any(x in problems for x in ('older_than_four_years','future_release','not_new_condition','demonstration_unit')):state='rejected'
                    update.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,issues_json=%s,state=%s WHERE id=%s',[packed(r),packed(problems),state,row['id']])
                    counts['manufacturer_release_matches']+=1;counts[state]+=1;break
            if scanned%1000==0:
                write_conn.commit();print('Checked '+str(scanned)+' candidates against release evidence',flush=True)
        write_conn.commit()
    return dict(counts)


def apply_india_store_launch_years(limit=50000):
    """Use explicit Launch Year/Release Year fields on exact India listings."""
    counts=Counter();scanned=0
    with connect() as read_conn,connect() as write_conn:
        cur=read_conn.cursor(SSDictCursor)
        cur.execute("SELECT id,record_json FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible') ORDER BY id LIMIT %s",[limit])
        with write_conn.cursor() as update:
            for row in cur:
                scanned+=1
                r=json.loads(row['record_json']);proof=r.get('release_evidence') or {}
                if r.get('release_date'):
                    counts['kept_existing_release_date']+=1;continue
                if proof.get('kind')=='india_store_launch_year':
                    launch=india_store_launch_year(r)
                    if (not launch or launch['field']!=proof.get('field')
                        or launch['year']!=int(r.get('release_year') or 0)):
                        r.pop('release_evidence',None);r.pop('release_year',None);r.pop('release_date',None)
                        problems=issues(r);state='eligible' if not problems else 'pending'
                        update.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,issues_json=%s,state=%s WHERE id=%s',
                            [packed(r),packed(problems),state,row['id']])
                        counts['invalidated_conflicting_store_year']+=1
                    else:counts['kept_existing_release_evidence']+=1
                    continue
                if proof.get('kind') in {'manufacturer_release','icecat_explicit_release','manufacturer_model_year'}:
                    counts['kept_existing_release_evidence']+=1;continue
                launch=india_store_launch_year(r)
                if not launch:
                    counts['no_exact_store_launch_year']+=1;continue
                if r.get('release_year') and str(r['release_year'])!=str(launch['year']):
                    counts['conflicting_existing_release_year']+=1;continue
                r['release_year']=launch['year'];r['release_date']=''
                r['release_evidence']={
                    'url':r['url'],'kind':'india_store_launch_year','precision':'year',
                    'field':launch['field'],'checked_on':(r.get('india_listing_evidence') or {}).get('checked_on'),
                    'scope':f"Exact India store product listing explicitly labels {launch['field']} {launch['year']}; no day inferred."
                }
                problems=issues(r);state='eligible' if not problems else 'pending'
                if any(x in problems for x in ('older_than_four_years','future_release','not_new_condition','demonstration_unit')):state='rejected'
                update.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,issues_json=%s,state=%s WHERE id=%s',
                    [packed(r),packed(problems),state,row['id']])
                counts['store_launch_year_matches']+=1;counts[state]+=1
                for problem in problems:counts['remaining_'+problem]+=1
                if scanned%5000==0:
                    write_conn.commit();print('Checked '+str(scanned)+' candidates for explicit India-store launch years',flush=True)
        write_conn.commit()
    return dict(counts)


def enrich_manufacturer_pages(limit=100):
    """Fetch each reviewed model once. Use its own specification container only."""
    pending={};counts=Counter()
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT id,record_json FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible')")
        for row in cur.fetchall():
            r=json.loads(row['record_json'])
            if r['source_id']!='boat' or not r.get('verified_model') or not r.get('india_listing_evidence'):continue
            url=r['url'].split('?')[0]
            pending.setdefault(url,[]).append((row['id'],r))
    for url,variants in list(pending.items())[:limit]:
        try:
            if not allowed(url):raise ValueError('robots_disallowed')
            markup=body(url);soup=BeautifulSoup(markup,'html.parser')
            section=soup.select_one('.shopify-section--tech-specs')
            if not section:counts['missing_specification_container']+=1;continue
            specs={}
            for pair in section.select('.specs-item'):
                name,value=pair.select_one('.spec-type'),pair.select_one('.spec')
                if name and value:
                    label=name.get_text(' ',strip=True);text=value.get_text(' ',strip=True)
                    if not re.search('mrp|marketed|manufactured|complaint|quantity|^name$',label,re.I) and text:specs[label]=text
            # The product's own notes/FAQ may document a driver missing from
            # the specification table. No recommendations or reviews are read.
            own=soup.select_one('.product_notes_section')
            if own:
                match=re.search(r'\b(\d+(?:\.\d+)?)\s*mm\s+drivers?\b',own.get_text(' ',strip=True),re.I)
                if match:specs['Driver size']=match[1]+' mm'
            for _,r in variants:
                if 'Driver size' not in specs:
                    match=re.search(r'\b(\d+(?:\.\d+)?)\s*mm\s+drivers?\b',r.get('description',''),re.I)
                    if match:specs['Driver size']=match[1]+' mm'
            with connect() as conn,conn.cursor() as cur:
                for cid,r in variants:
                    r['specs']={**r.get('specs',{}),**specs,**r.get('attributes',{})}
                    r['specification_evidence']={'url':url,'checked_on':date.today().isoformat(),'container':'own_product_specifications'}
                    problems=issues(r)
                    cur.execute("UPDATE catalog_ingestion_candidates SET record_json=%s,issues_json=%s,state=%s WHERE id=%s",[packed(r),packed(problems),'eligible' if not problems else 'pending',cid])
                    counts['variants_enriched']+=1
                conn.commit()
            counts['models_fetched']+=1
        except Exception:counts['source_failed']+=1
    return dict(counts)


def enrich_india_variant_pages(limit=200):
    """Confirm a feed variant against its own Indian store's structured offer."""
    counts=Counter();selected=[]
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT id,record_json FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible') AND source_id='iplanet'")
        for row in cur.fetchall():
            r=json.loads(row['record_json'])
            if r.get('verified_model') and r.get('india_listing_evidence'):selected.append((row['id'],r))
    for cid,r in selected[:limit]:
        try:
            if not allowed(r['url']):raise ValueError('robots_disallowed')
            found=[]
            for product in jsonld_products(body(r['url'])):
                brand=product.get('brand') or {};brand=brand.get('name','') if isinstance(brand,dict) else brand
                if identity.norm_brand(brand)!=identity.norm_brand(r['brand']):continue
                offers=product.get('offers') or [];offers=offers if isinstance(offers,list) else [offers]
                for offer in offers:
                    if offer.get('@type')!='Offer' or offer.get('priceCurrency')!='INR':continue
                    if not r.get('seller_sku') or str(offer.get('sku') or product.get('sku'))!=r['seller_sku']:continue
                    if urlparse(offer.get('url','')).query and str(r['external_id']) not in urlparse(offer['url']).query:continue
                    found.append((product,offer))
            if len(found)!=1:counts['ambiguous_or_missing_offer']+=1;continue
            product,offer=found[0]
            if str(offer.get('itemCondition','')).rstrip('/').rsplit('/',1)[-1]!='NewCondition':counts['unverified_condition']+=1;continue
            gtins=set(g for value in [offer.get(k) or product.get(k) for k in ('gtin','gtin12','gtin13','gtin14')] for g in identity.gtins(value))
            if len(gtins)==1:r['gtin']=next(iter(gtins));counts['gtin_confirmed']+=1
            r['price']=str(offer['price']);r['checked_on']=date.today().isoformat()
            r['variant_offer_evidence']={'url':r['url'],'sku':r['seller_sku'],'gtin':r.get('gtin'),'checked_on':r['checked_on']}
            problems=issues(r)
            with connect() as conn,conn.cursor() as cur:
                cur.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,identity_key=%s,issues_json=%s,state=%s WHERE id=%s',
                    [packed(r),variant_identity(r),packed(problems),'eligible' if not problems else 'pending',cid]);conn.commit()
            counts['exact_offers_confirmed']+=1
        except Exception:counts['source_failed']+=1
    return dict(counts)


def apply_reviewed_model_specs():
    """Apply model-invariant manufacturer facts, retaining selected capacities."""
    rules=json.loads((ROOT/'product_catalog'/'model_release_evidence.json').read_text(encoding='utf-8'))['rules']
    counts=Counter()
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT id,record_json FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible')")
        for row in cur.fetchall():
            r=json.loads(row['record_json'])
            if not r.get('verified_model'):continue
            for rule in rules:
                specs=rule.get('model_specifications')
                if not specs or not rule.get('specifications_url'):continue
                if (r.get('type_id')!=rule['type_id'] or identity.norm_brand(r['brand'])!=identity.norm_brand(rule['brand'])
                    or not re.search(rule['name_pattern'],r['name'],re.I)):continue
                # This ledger contains only common hardware facts. Storage,
                # colour, SIM configuration and other variant options stay local.
                if any(re.search(r'capacity|storage|colou?r|finish|sim',k,re.I) for k in specs):raise ValueError('Variant-dependent field in shared model specifications')
                r['specs']={**r['specs'],**specs}
                r['specification_evidence']={'url':rule['specifications_url'],'reviewed_on':rule['reviewed_on'],'scope':'shared exact-model hardware facts'}
                problems=issues(r)
                cur.execute('UPDATE catalog_ingestion_candidates SET record_json=%s,issues_json=%s,state=%s WHERE id=%s',
                    [packed(r),packed(problems),'eligible' if not problems else 'pending',row['id']])
                counts['variants_enriched']+=1;break
        conn.commit()
    return dict(counts)
