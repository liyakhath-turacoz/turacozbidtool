"""Shared catalog facets, normalized specification values and reporting."""
import csv
import html
import io
import json
import re
import hashlib
from collections import Counter
from datetime import date,datetime
from zoneinfo import ZoneInfo

try:
    from .catalog_metadata import hide_release_dates, attach as attach_catalog_metadata, taxonomy_facets
except ImportError:
    from catalog_metadata import hide_release_dates, attach as attach_catalog_metadata, taxonomy_facets

SPEC_DEFINITIONS = {
    'ram': ('RAM', ['RAM capacity', 'Installed RAM', 'System RAM', 'Memory (RAM)', 'Unified memory', 'RAM']),
    'storage': ('Storage', ['Internal storage capacity', 'Total storage capacity', 'SSD capacity', 'Storage capacity', 'Internal memory', 'Memory capacity', 'Storage']),
    'processor': ('Processor', ['Processor model', 'Chipset', 'Processor', 'Processor family', 'SoC']),
    'display_size': ('Display size', ['Display diagonal', 'Display size', 'Screen size', 'Size']),
    'display_type': ('Display technology', ['Display technology', 'Panel type', 'Display type']),
    'resolution': ('Resolution', ['Display resolution', 'Resolution', 'HD type', 'Maximum resolution']),
    'refresh_rate': ('Refresh rate', ['Maximum refresh rate', 'Refresh rate', 'Native refresh rate']),
    'battery': ('Battery capacity', ['Battery capacity', 'Battery capacity (typical)', 'Battery']),
    'camera': ('Camera resolution', ['Rear camera resolution (numeric)', 'Camera resolution', 'Main camera']),
    'os': ('Operating system', ['Operating system installed', 'Operating system', 'OS']),
    'connectivity': ('Connectivity', ['Mobile network generation', 'Wi-Fi standards', 'Connectivity', 'Bluetooth version']),
    'capacity': ('Capacity', ['Fridge net capacity', 'Total net capacity', 'Total capacity', 'Oven net capacity', 'Rated capacity', 'Capacity']),
    'energy_class': ('Energy efficiency', ['Energy efficiency class', 'Energy rating', 'Energy efficiency class (old)']),
    'cooling_capacity': ('Cooling capacity', ['Cooling capacity (nominal)', 'Cooling capacity in watts (nominal)', 'Cooling capacity', 'Tonnage']),
    'installation': ('Installation / design', ['Appliance placement', 'Installation type', 'Product type', 'Design']),
    'technology': ('Technology / interface', ['Print technology', 'Interface', 'NVMe', 'Inverter technology', 'Defrost function', 'Technology']),
    'colour': ('Colour', ['Product colour', 'Colour', 'Color']),
    'processor_cores': ('Processor cores', ['Processor cores', 'Number of processor cores']),
    'gpu': ('Graphics processor', ['Discrete graphics card model', 'On-board graphics card model', 'Graphics processor', 'GPU']),
    'memory_type': ('Memory type', ['Internal memory type', 'Memory type']),
    'storage_type': ('Storage technology', ['Storage media', 'SSD form factor', 'Drive type']),
    'touchscreen': ('Touchscreen', ['Touchscreen']),
    'sim': ('SIM support', ['SIM card capability', 'SIM card type']),
    'water_resistance': ('Water / dust protection', ['International Protection (IP) code', 'Water resistance']),
    'spin_speed': ('Maximum spin speed', ['Maximum spin speed']),
    'loading_type': ('Laundry loading type', ['Loading type']),
    'freezer_capacity': ('Freezer capacity', ['Freezer net capacity']),
    'oven_type': ('Oven type', ['Oven type']),
    'noise_level': ('Noise level', ['Noise level', 'Noise level (indoor unit)', 'Noise level (wash)']),
}
FACET_VERSION=hashlib.sha256(json.dumps(SPEC_DEFINITIONS,sort_keys=True).encode()).hexdigest()
APPLIANCE_TYPES = ['Refrigerators', 'Freezers', 'Ovens', 'Microwave ovens', 'Air conditioners', 'Washing machines', 'Dishwashers', 'Vacuum cleaners', 'Air purifiers', 'Cooktops', 'Tumble dryers']
TYPE_ALIASES = {'notebooks':'Laptops','mobile phones':'Smartphones','smartphone':'Smartphones','tvs':'Televisions','tv':'Televisions','refrigerator-freezers':'Refrigerators','fridge-freezers':'Refrigerators','fridges':'Refrigerators','microwaves':'Microwave ovens','air conditioning':'Air conditioners','air-conditioning':'Air conditioners','washing-machines':'Washing machines','smartwatch':'Smartwatches','watches':'Smartwatches','tablet':'Tablets','laptop':'Laptops','monitor':'Monitors','gpus':'Graphics cards (GPUs)','cpus':'Processors (CPUs)'}


def product_type(value):
    value=str(value or '').strip()
    return TYPE_ALIASES.get(value.lower(),value or 'Other electronics')


def parent_category(item):
    return 'Home Appliances' if product_type(item) in APPLIANCE_TYPES else 'Electronics'


def decode(value, default):
    if isinstance(value,str):
        try: return json.loads(value)
        except (TypeError,ValueError): return default
    return value if isinstance(value,type(default)) else default


def is_source_metadata_label(value):
    label=re.sub(r'[^a-z0-9]+','',str(value or '').casefold())
    return any(token in label for token in ('source','attribution','citation','icecat','verification','catalognote','url','uri'))


def public_catalog_data(value):
    """Remove importer and provenance fields from buyer/dealer product payloads."""
    if isinstance(value,dict):
        return {
            key:public_catalog_data(item)
            for key,item in value.items()
            if not is_source_metadata_label(key)
        }
    if isinstance(value,list):
        return [
            public_catalog_data(item)
            for item in value
            if not isinstance(item,dict) or not is_source_metadata_label(item.get('name') or item.get('label'))
        ]
    return value


def normalized_specs(record):
    values={str(k).strip().casefold():str(v).strip() for k,v in decode(record.get('highlights',record.get('specifications')),{}).items() if v is not None}
    for field in ('technical_specifications','software_specifications'):
        for group in decode(record.get(field),[]):
            for feature in group.get('features',[]):
                key=str(feature.get('name','')).strip().casefold()
                val=str(feature.get('value') or '').strip()
                unit=str(feature.get('unit') or '').strip()
                if val and unit and not re.search(re.escape(unit),val,re.I): val+=' '+unit
                if key and val: values[key]=val
    manual={str(key).casefold():str(value) for key,value in decode(record.get('manual_specifications'),{}).items()}
    values.update(manual)
    kind=str(record.get('type_id') or record.get('product_type_id') or record.get('subcategory') or record.get('item') or '').casefold()
    storage_kind=kind in {'smartphones','tablets','laptops','desktops','ssds','memory_cards','usb_drives','hard_drives'} or bool(re.search(r'smartphone|tablet|laptop|desktop|ssd|memory card|flash drive|hard disk',kind))
    capacity=values.get('capacity','')
    storage_capacity=storage_kind and bool(re.fullmatch(r'\d+(?:\.\d+)?\s*(?:GB|TB|MB)',capacity,re.I))
    if storage_capacity:values.setdefault('storage capacity',capacity)
    result=[]
    for key,(_,aliases) in SPEC_DEFINITIONS.items():
        if key=='capacity' and storage_capacity:continue
        raw=next((manual[a.casefold()] for a in aliases if manual.get(a.casefold())),None) or next((values[a.casefold()] for a in aliases if values.get(a.casefold())),None)
        if not raw: continue
        if key=='ram' and re.search(r'(graphics card|motherboard|processor|ssd)',str(record.get('item') or record.get('subcategory') or ''),re.I): continue
        raw=re.sub(r'\s+',' ',raw).strip()
        if key in {'ram','storage'}:
            capacities=re.findall(r'(\d+(?:\.\d+)?)\s*(TB|GB|MB)',raw,re.I)
            options=[f'{float(number):g} {unit.upper()}' for number,unit in capacities] if capacities else [raw]
        elif key=='display_size':
            match=re.search(r'(\d+(?:\.\d+)?)\s*(?:["″]|inch|inches)',raw,re.I)
            options=[f'{float(match[1]):g} inches'] if match else [raw]
        else: options=[raw]
        for val in dict.fromkeys(options):
            if val and len(val)<=160: result.append((key,val))
    return result


def index_product(cursor, record):
    cursor.execute('DELETE FROM product_filter_values WHERE product_id=%s',[record['id']])
    rows=[(record['id'],key,val) for key,val in normalized_specs(record)]
    if rows: cursor.executemany('INSERT IGNORE INTO product_filter_values (product_id,spec_key,spec_value) VALUES (%s,%s,%s)',rows)


def ensure_schema(db):
    with db() as conn,conn.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS catalog_filter_meta (id VARCHAR(30) PRIMARY KEY,version CHAR(64) NOT NULL,updated_at DATETIME NOT NULL) ENGINE=InnoDB")
        cursor.execute("""CREATE TABLE IF NOT EXISTS product_filter_values (
            product_id CHAR(36) NOT NULL,spec_key VARCHAR(40) NOT NULL,spec_value VARCHAR(160) NOT NULL,
            PRIMARY KEY(product_id,spec_key,spec_value),KEY idx_product_facets(spec_key,spec_value,product_id),
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        ) ENGINE=InnoDB""")
        cursor.execute("SELECT COLUMN_NAME,CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products'")
        rows=cursor.fetchall();columns={row['COLUMN_NAME'] for row in rows}
        sizes={row['COLUMN_NAME']:row['CHARACTER_MAXIMUM_LENGTH'] for row in rows}
        for name,size in {'name':255,'brand':190,'model':190}.items():
            if sizes.get(name,0)<size:cursor.execute(f'ALTER TABLE products MODIFY COLUMN {name} VARCHAR({size})'+(' NOT NULL' if name=='name' else ' NULL'))
        for name,definition in {'release_date':'DATE NULL','release_date_precision':"VARCHAR(12) NOT NULL DEFAULT 'unknown'",'release_date_basis':"VARCHAR(30) NOT NULL DEFAULT 'legacy_reported_year'",'catalog_added_at':'DATE NULL','source_url':'VARCHAR(1000) NULL','product_url':'VARCHAR(1000) NULL','price_source_url':'VARCHAR(1000) NULL','source_attribution':'VARCHAR(255) NULL','verification_status':'VARCHAR(255) NULL','catalog_notes':'TEXT NULL','official_price':'DECIMAL(14,2) NULL','price_currency':'VARCHAR(8) NULL','price_type':'VARCHAR(80) NULL','price_market':'VARCHAR(80) NULL','manual_specifications':'JSON NULL','manufacturer':'VARCHAR(190) NULL','catalog_visible':'BOOLEAN NOT NULL DEFAULT TRUE'}.items():
            if name not in columns: cursor.execute(f'ALTER TABLE products ADD COLUMN {name} {definition}')
        # Source matching locks the product it updates. Without these indexes,
        # brand/MPN and model lookups scan and lock much of the catalog per row.
        cursor.execute('SHOW INDEX FROM products');indexes={row['Key_name'] for row in cursor.fetchall()}
        for name,keys in {'idx_products_brand_mpn':'brand,mpn','idx_products_brand_model':'brand,model,release_year,subcategory_id'}.items():
            if name not in indexes:cursor.execute(f'ALTER TABLE products ADD INDEX {name} ({keys})')


def rebuild_index(db, progress=None):
    offset='';count=0
    while True:
        with db() as conn,conn.cursor() as cursor:
            cursor.execute('SELECT id,highlights,technical_specifications,software_specifications,manual_specifications FROM products WHERE id>%s ORDER BY id LIMIT 200 FOR UPDATE',[offset])
            records=cursor.fetchall()
            if not records: break
            for row in records: index_product(cursor,row)
            count+=len(records);offset=records[-1]['id']
        if progress: progress(count)
    with db() as conn,conn.cursor() as cursor:
        cursor.execute("INSERT INTO catalog_filter_meta (id,version,updated_at) VALUES ('specifications',%s,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE version=VALUES(version),updated_at=VALUES(updated_at)",[FACET_VERSION])
    return count


JOINS='FROM products p JOIN categories c ON c.id=p.category_id LEFT JOIN categories sc ON sc.id=p.subcategory_id LEFT JOIN locations l ON l.id=p.location_id'


def conditions(filters, admin=False, facets=False):
    where=['p.deleted_at IS NULL','p.catalog_visible=TRUE'];args=[]
    if not admin: where += ["p.status='active'","c.deleted_at IS NULL","c.status='active'","(sc.id IS NULL OR (sc.deleted_at IS NULL AND sc.status='active'))"]
    elif filters.get('status'): where.append('p.status=%s');args.append(filters['status'])
    query_terms=search_terms(filters.get('q'))
    for term in query_terms:
        alternatives=[]
        for variant in search_variants(term):
            pattern=regex_prefix(variant)
            alternatives.append('''(
                LOWER(CONCAT_WS(' ',p.id,p.name,p.brand,p.manufacturer,p.model,p.mpn,p.gtin,c.name,sc.name,p.highlights)) REGEXP %s
                OR EXISTS (SELECT 1 FROM product_filter_values fs WHERE fs.product_id=p.id
                  AND (LOWER(fs.spec_key) REGEXP %s OR LOWER(fs.spec_value) REGEXP %s))
            )''')
            args += [pattern,pattern,pattern]
        where.append('('+' OR '.join(alternatives)+')')
    ram_capacity=explicit_ram_capacity(filters.get('q'))
    if ram_capacity:
        number,unit=ram_capacity
        capacity_pattern=r'(^|[^[:alnum:]])'+re.escape(number)+r'[^[:alnum:]]*'+re.escape(unit)+r'([^[:alnum:]]|$)'
        title_pattern=(r'(^|[^[:alnum:]])'+re.escape(number)+r'[^[:alnum:]]*'+re.escape(unit)+r'[^[:alnum:]]*ram([^[:alnum:]]|$)'
                       r'|(^|[^[:alnum:]])ram[^[:alnum:]]*'+re.escape(number)+r'[^[:alnum:]]*'+re.escape(unit)+r'([^[:alnum:]]|$)')
        ram_key_pattern=(r'"(?:ram|ram capacity|installed ram|system ram)"\s*:\s*"[^"]*'
                         +re.escape(number)+r'[^\"]*'+re.escape(unit)+r'[^"]*"')
        memory_key_pattern=(r'"(?:memory_storage|memory)"\s*:\s*"[^"]*(?:'
                            +re.escape(number)+r'[^\"]{0,8}'+re.escape(unit)+r'[^\"]{0,16}ram'
                            +r'|ram[[:space:]:/=-]{0,4}'+re.escape(number)+r'[^\"]{0,8}'+re.escape(unit)
                            +r')[^"]*"')
        text_pattern=ram_key_pattern+'|'+memory_key_pattern
        where.append('''(
            EXISTS (SELECT 1 FROM product_filter_values rf WHERE rf.product_id=p.id
              AND rf.spec_key='ram' AND LOWER(rf.spec_value) REGEXP %s)
            OR LOWER(p.name) REGEXP %s
            OR LOWER(p.highlights) REGEXP %s
        )''')
        args += [capacity_pattern,title_pattern,text_pattern]
    elif re.search(r'\bram\b',str(filters.get('q') or ''),re.I):
        ram_field_pattern=(r'"(?:ram|ram capacity|installed ram|system ram)"\s*:\s*"[^"]*"'
                           r'|"(?:memory_storage|memory)"\s*:\s*"[^"]*ram[^"]*"')
        where.append('''(
            EXISTS (SELECT 1 FROM product_filter_values rf WHERE rf.product_id=p.id AND rf.spec_key='ram')
            OR LOWER(p.name) REGEXP %s
            OR LOWER(p.highlights) REGEXP %s
        )''')
        args += [regex_prefix('ram'),ram_field_pattern]
    for key,column in [('categories','c.name'),('product_types','sc.name')]:
        choices=filters.get(key) or []
        if choices: where.append(column+' IN ('+','.join(['%s']*len(choices))+')');args+=choices
    if filters.get('category'):
        where.append('(c.name=%s OR sc.name=%s)');args += [filters['category']]*2
    if filters.get('product_type'): where.append('sc.name=%s');args.append(filters['product_type'])
    if filters.get('type_id'):
        where.append('EXISTS (SELECT 1 FROM catalog_type_assignments ta WHERE ta.product_id=p.id AND ta.type_id=%s)')
        args.append(filters['type_id'])
    if filters.get('canonical_types'):
        types=filters['canonical_types']
        where.append('EXISTS (SELECT 1 FROM catalog_type_assignments ta WHERE ta.product_id=p.id AND ta.type_id IN ('+','.join(['%s']*len(types))+'))')
        args.extend(types)
    if not facets:
        brands=filters.get('brands') or ([filters['brand']] if filters.get('brand') else [])
        if brands:
            placeholders=','.join(['%s']*len(brands))
            where.append('(COALESCE(NULLIF(p.manufacturer,\'\'),p.brand) IN ('+placeholders+') OR p.brand IN ('+placeholders+'))')
            args += brands + brands
        years=filters.get('years') or []
        if years:
            actual=[int(y) for y in years if y!='unknown']
            clause=[]
            if actual: clause.append('p.release_year IN ('+','.join(['%s']*len(actual))+')');args+=actual
            if 'unknown' in years: clause.append('p.release_year IS NULL')
            where.append('('+' OR '.join(clause)+')')
        for key,column in [('minimum','p.price_min'),('maximum','p.price_max')]:
            val=filters.get(key)
            if val is not None and val!='':
                where.append(column+(' >= %s' if key=='minimum' else ' <= %s'));args.append(val)
        for key,values in (filters.get('specs') or {}).items():
            if key not in SPEC_DEFINITIONS or not isinstance(values,list) or not values: continue
            where.append('EXISTS (SELECT 1 FROM product_filter_values f WHERE f.product_id=p.id AND f.spec_key=%s AND f.spec_value IN ('+','.join(['%s']*len(values))+'))')
            args += [key]+values
    return ' AND '.join(where),args


def search_terms(value):
    """Return normalized terms; every term must be present on the same product."""
    raw=re.findall(r'[\w]+(?:[.+#-][\w]+)*',str(value or '').casefold(),flags=re.UNICODE)
    terms=[]
    for term in raw:
        capacity=re.fullmatch(r'(\d+(?:\.\d+)?)(tb|gb|mb)',term)
        terms.extend([capacity.group(1),capacity.group(2)] if capacity else [term])
    return list(dict.fromkeys(term[:48] for term in terms if term))[:8]


def explicit_ram_capacity(value):
    """Return a capacity explicitly qualified as RAM in a search query."""
    query=str(value or '').casefold()
    if not re.search(r'\bram\b',query):
        return None
    match=re.search(r'(?<![\w.])(\d+(?:\.\d+)?)\s*(tb|gb|mb)\s*ram\b',query) or re.search(r'\bram\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(tb|gb|mb)\b',query)
    return (match.group(1),match.group(2)) if match else None


SEARCH_SYNONYMS={
    'pendrive':('pendrive','pen drive','usb flash drive','usb drive'),
    'pendrives':('pendrives','pen drives','usb flash drives','usb drives'),
    'flash':('flash','pen','usb'),
    'hdd':('hdd','hard disk','hard drive'),
    'harddisk':('harddisk','hard disk','hard drive','hdd'),
    'microsd':('microsd','micro sd','memory card'),
    'sdcard':('sdcard','sd card','memory card'),
    'geyser':('geyser','water heater'),
    'geysers':('geysers','water heaters'),
    'powerbank':('powerbank','power bank'),
    'powerbanks':('powerbanks','power banks'),
    'phone':('phone','smartphone','telephone','mobile'),
    'phones':('phones','smartphones','telephones','mobiles'),
    'mobile':('mobile','phone','smartphone'),
    'mobiles':('mobiles','phones','smartphones'),
    'smartphone':('smartphone','mobile phone','cell phone'),
    'smartphones':('smartphones','mobile phones','cell phones'),
    'tv':('tv','television'),
    'tvs':('tvs','televisions'),
    'fridge':('fridge','refrigerator'),
    'fridges':('fridges','refrigerators'),
    'refrigerator':('refrigerator','fridge'),
    'refrigerators':('refrigerators','fridges'),
    'ac':('ac','air conditioner'),
    'acs':('acs','air conditioners'),
    'aircon':('aircon','air conditioner','air conditioning'),
    'laptop':('laptop','notebook','portable computer'),
    'laptops':('laptops','notebooks','portable computers'),
    'notebook':('notebook','laptop','portable computer'),
    'notebooks':('notebooks','laptops','portable computers'),
    'computer':('computer','pc','laptop','notebook'),
    'computers':('computers','pcs','laptops','notebooks'),
    'washer':('washer','washing machine'),
    'washers':('washers','washing machines'),
}


def search_variants(value):
    return SEARCH_SYNONYMS.get(str(value).casefold(),(str(value).casefold(),))


def regex_prefix(value):
    """Match a term at a word boundary, including an unfinished word prefix."""
    return r'(^|[^[:alnum:]])'+re.escape(str(value).casefold())


def relevance_order(value):
    """Produce deterministic relevance scoring for a search query."""
    terms=search_terms(value)
    if not terms:
        return '',[]
    phrase=' '.join(terms)
    score='''CASE
        WHEN LOWER(p.name)=LOWER(%s) OR LOWER(p.model)=LOWER(%s) OR LOWER(p.brand)=LOWER(%s) THEN 1000
        WHEN LOWER(p.name) REGEXP %s THEN 850
        WHEN LOWER(p.model) REGEXP %s THEN 800
        WHEN LOWER(p.brand) REGEXP %s THEN 750
        WHEN LOWER(p.manufacturer) REGEXP %s THEN 700
        ELSE 0 END'''
    phrase_pattern=regex_prefix(phrase)
    args=[phrase,phrase,phrase,phrase_pattern,phrase_pattern,phrase_pattern,phrase_pattern]
    token_scores=[]
    for term in terms:
        patterns=[regex_prefix(variant) for variant in search_variants(term)]
        def matches(expression):
            return '('+' OR '.join(f'{expression} REGEXP %s' for _ in patterns)+')'
        token_scores.append(f'''(CASE WHEN {matches('LOWER(p.name)')} THEN 100 ELSE 0 END
            + CASE WHEN {matches('LOWER(p.model)')} THEN 80 ELSE 0 END
            + CASE WHEN {matches('LOWER(p.brand)')} THEN 70 ELSE 0 END
            + CASE WHEN {matches('LOWER(p.manufacturer)')} THEN 60 ELSE 0 END
            + CASE WHEN {matches("LOWER(CONCAT_WS(' ',c.name,sc.name))")} THEN 40 ELSE 0 END
            + CASE WHEN EXISTS (SELECT 1 FROM product_filter_values sr WHERE sr.product_id=p.id AND ({matches('LOWER(sr.spec_key)')} OR {matches('LOWER(sr.spec_value)')})) THEN 30 ELSE 0 END)''')
        args.extend(patterns*7)
    return score+' + '+' + '.join(token_scores),args


def _searchable_text(value):
    if value is None:
        return ''
    if isinstance(value,str):
        stripped=value.strip()
        if stripped[:1] in {'{','['}:
            try:
                return _searchable_text(json.loads(stripped))
            except (TypeError,ValueError):
                pass
        stripped=re.sub(r'https?://\S+',' ',stripped,flags=re.I)
        stripped=re.sub(r'<[^>]*>',' ',stripped)
        return re.sub(r'\s+',' ',html.unescape(stripped)).strip()
    if isinstance(value,dict):
        parts=[]
        for key,item in value.items():
            if is_source_metadata_label(key):
                continue
            text=_searchable_text(item)
            if text:
                parts.extend((str(key),text))
        return ' '.join(parts)
    if isinstance(value,(list,tuple)):
        return ' '.join(filter(None,(_searchable_text(item) for item in value)))
    return str(value)


def statistics(db):
    with db() as conn,conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) total,COUNT(DISTINCT CONCAT(COALESCE(brand,''),'|',COALESCE(NULLIF(model,''),name))) model_codes,SUM(status='active') active,SUM(release_year IS NULL) unknown_year,SUM(release_year<2017) pre_2017,SUM(release_date_basis='legacy_reported_year') unverified_legacy_years FROM products WHERE deleted_at IS NULL AND catalog_visible=TRUE")
        result=cursor.fetchone()
        queries={
            'categories':f'SELECT c.name category,COALESCE(sc.name,c.name) product_type,COUNT(*) count {JOINS} WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE GROUP BY c.name,sc.name ORDER BY c.name,sc.name',
            'years':"SELECT release_year,COUNT(*) count,COUNT(DISTINCT CONCAT(COALESCE(brand,''),'|',COALESCE(NULLIF(model,''),name))) model_codes,SUM(release_date_basis!='legacy_reported_year') verified_records FROM products WHERE deleted_at IS NULL AND catalog_visible=TRUE GROUP BY release_year ORDER BY release_year",
            'category_years':f"SELECT c.name category,COALESCE(sc.name,c.name) product_type,p.release_year,COUNT(*) count,COUNT(DISTINCT CONCAT(COALESCE(p.brand,''),'|',COALESCE(NULLIF(p.model,''),p.name))) model_codes {JOINS} WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE GROUP BY c.name,sc.name,p.release_year ORDER BY c.name,sc.name,p.release_year",
            'brands':"SELECT COALESCE(NULLIF(manufacturer,''),brand) brand,COUNT(*) count FROM products WHERE deleted_at IS NULL AND catalog_visible=TRUE GROUP BY COALESCE(NULLIF(manufacturer,''),brand) ORDER BY count DESC,brand",
            'category_brands':f'SELECT c.name category,COALESCE(sc.name,c.name) product_type,COALESCE(NULLIF(p.manufacturer,\'\'),p.brand) brand,COUNT(*) count {JOINS} WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE GROUP BY c.name,sc.name,COALESCE(NULLIF(p.manufacturer,\'\'),p.brand) ORDER BY c.name,sc.name,count DESC',
            'older_products':f'SELECT p.id,p.name,p.brand,sc.name product_type,p.release_year,p.release_date,p.release_date_basis {JOINS} WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE AND (p.release_year<%s OR (p.release_year=%s AND (p.release_date IS NULL OR p.release_date<%s))) ORDER BY p.release_year,p.name',
        }
        today=datetime.now(ZoneInfo('Asia/Kolkata')).date()
        try:cutoff=today.replace(year=today.year-3)
        except ValueError:cutoff=today.replace(year=today.year-3,day=28)
        for key,sql in queries.items():
            cursor.execute(sql,[cutoff.year,cutoff.year,cutoff] if key=='older_products' else [])
            result[key]=cursor.fetchall()
        for row in result['older_products']:
            row['reported_age_years']=today.year-row['release_year'] if row['release_year'] else None
            row['age_confidence']='Unverified catalog year' if row['release_date_basis']=='legacy_reported_year' else 'Verified release year/date'
        result['as_of']=today.isoformat();result['latest_import_cutoff']=cutoff.isoformat()
        result['count_note']='Counts are product/SKU records, including configurations and regional variants; they are not counts of unique marketing model names. Legacy Icecat years may use catalog-added dates where release dates were absent.'
        return result


def statistics_csv(report):
    output=io.StringIO();writer=csv.writer(output)
    writer.writerow(['section','category','product_type','brand','release_year','product_records','distinct_model_codes','verified_release_records'])
    for key in ('categories','years','category_years','brands','category_brands'):
        for row in report[key]:
            values=[key,row.get('category',''),row.get('product_type',''),row.get('brand',''),row.get('release_year',''),row['count'],row.get('model_codes',''),row.get('verified_records','')]
            writer.writerow(["'"+val if isinstance(val,str) and val.startswith(('=','+','-','@')) else val for val in values])
    return '\ufeff'+output.getvalue()


def search(db,filters,admin=False,include_facets=True):
    from .tantivy_search import search as indexed_search
    return indexed_search(db,filters,admin,include_facets)
