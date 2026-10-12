"""Shared catalog facets, normalized specification values and reporting."""
import csv
import io
import json
import re
import hashlib
from datetime import date,datetime
from zoneinfo import ZoneInfo

SPEC_DEFINITIONS = {
    'ram': ('RAM', ['RAM capacity', 'RAM', 'Internal memory', 'Memory capacity']),
    'storage': ('Storage', ['Internal storage capacity', 'Total storage capacity', 'SSD capacity', 'Storage capacity', 'Storage']),
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
    result=[]
    for key,(_,aliases) in SPEC_DEFINITIONS.items():
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
        for name,definition in {'release_date':'DATE NULL','release_date_precision':"VARCHAR(12) NOT NULL DEFAULT 'unknown'",'release_date_basis':"VARCHAR(30) NOT NULL DEFAULT 'legacy_reported_year'",'catalog_added_at':'DATE NULL','source_url':'VARCHAR(1000) NULL','source_attribution':'VARCHAR(255) NULL','manual_specifications':'JSON NULL'}.items():
            if name not in columns: cursor.execute(f'ALTER TABLE products ADD COLUMN {name} {definition}')


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
    where=['p.deleted_at IS NULL'];args=[]
    if not admin: where += ["p.status='active'","c.deleted_at IS NULL","c.status='active'","(sc.id IS NULL OR (sc.deleted_at IS NULL AND sc.status='active'))"]
    elif filters.get('status'): where.append('p.status=%s');args.append(filters['status'])
    query=str(filters.get('q') or '').strip()
    if query:
        where.append('(p.id LIKE %s OR p.name LIKE %s OR p.brand LIKE %s OR p.model LIKE %s OR c.name LIKE %s OR sc.name LIKE %s OR p.highlights LIKE %s OR EXISTS (SELECT 1 FROM product_filter_values fs WHERE fs.product_id=p.id AND fs.spec_value LIKE %s))')
        args += ['%'+query+'%']*8
    for key,column in [('categories','c.name'),('product_types','sc.name')]:
        choices=filters.get(key) or []
        if choices: where.append(column+' IN ('+','.join(['%s']*len(choices))+')');args+=choices
    if filters.get('category'):
        where.append('(c.name=%s OR sc.name=%s)');args += [filters['category']]*2
    if filters.get('product_type'): where.append('sc.name=%s');args.append(filters['product_type'])
    if not facets:
        brands=filters.get('brands') or ([filters['brand']] if filters.get('brand') else [])
        if brands: where.append('p.brand IN ('+','.join(['%s']*len(brands))+')');args += brands
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


def search(db,filters,admin=False,include_facets=True):
    where,args=conditions(filters,admin)
    sort={'Newest':'p.created_at DESC,p.id DESC','Year':'p.release_year DESC,p.id','Name':'p.name,p.id','A-Z':'p.name,p.id','Lowest Price':'p.price_min,p.id','Highest Price':'p.price_max DESC,p.id'}.get(filters.get('sort'),'p.created_at DESC,p.id DESC')
    with db() as conn,conn.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) total {JOINS} WHERE {where}',args);total=cursor.fetchone()['total']
        cursor.execute(f"""SELECT p.id,p.name,p.brand,p.model,p.price_min,p.price_max,p.status,p.created_at,p.image_url,p.source,p.release_year,p.release_date,p.release_date_basis,p.source_url,
            c.name category,sc.name item,sc.name subcategory,CONCAT(l.city,', ',l.state) location,p.highlights specifications,
            EXISTS(SELECT 1 FROM bid_requests br WHERE br.product_id=p.id) has_bid_history
            {JOINS} WHERE {where} ORDER BY {sort} LIMIT %s OFFSET %s""",args+[min(250,int(filters.get('limit') or 50)),max(0,int(filters.get('offset') or 0))])
        items=cursor.fetchall()
        for row in items: row['specifications']=decode(row['specifications'],{})
        cursor.execute('SELECT COUNT(*) total FROM products WHERE deleted_at IS NULL');catalog_total=cursor.fetchone()['total']
        facets={}
        if include_facets:
            scope,scope_args=conditions(filters,admin,facets=True)
            for key,column in [('categories','c.name'),('product_types','sc.name'),('brands','p.brand'),('years',"COALESCE(CAST(p.release_year AS CHAR),'unknown')")]:
                facet_scope,facet_args=scope,scope_args
                if key=='categories':
                    facet_scope,facet_args=conditions({**filters,'category':'','categories':[],'product_type':'','product_types':[]},admin,facets=True)
                elif key=='product_types':
                    facet_scope,facet_args=conditions({**filters,'product_type':'','product_types':[]},admin,facets=True)
                cursor.execute(f'SELECT {column} value,COUNT(*) count {JOINS} WHERE {facet_scope} AND {column} IS NOT NULL GROUP BY {column} ORDER BY {column}',facet_args)
                facets[key]=cursor.fetchall()
        return {'items':items,'total':total,'catalog_total':catalog_total,'facets':facets,'brands':[row['value'] for row in facets.get('brands',[])]}


def statistics(db):
    with db() as conn,conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) total,COUNT(DISTINCT CONCAT(COALESCE(brand,''),'|',COALESCE(NULLIF(model,''),name))) model_codes,SUM(status='active') active,SUM(release_year IS NULL) unknown_year,SUM(release_year<2017) pre_2017,SUM(release_date_basis='legacy_reported_year') unverified_legacy_years FROM products WHERE deleted_at IS NULL")
        result=cursor.fetchone()
        queries={
            'categories':f'SELECT c.name category,COALESCE(sc.name,c.name) product_type,COUNT(*) count {JOINS} WHERE p.deleted_at IS NULL GROUP BY c.name,sc.name ORDER BY c.name,sc.name',
            'years':"SELECT release_year,COUNT(*) count,COUNT(DISTINCT CONCAT(COALESCE(brand,''),'|',COALESCE(NULLIF(model,''),name))) model_codes,SUM(release_date_basis!='legacy_reported_year') verified_records FROM products WHERE deleted_at IS NULL GROUP BY release_year ORDER BY release_year",
            'category_years':f"SELECT c.name category,COALESCE(sc.name,c.name) product_type,p.release_year,COUNT(*) count,COUNT(DISTINCT CONCAT(COALESCE(p.brand,''),'|',COALESCE(NULLIF(p.model,''),p.name))) model_codes {JOINS} WHERE p.deleted_at IS NULL GROUP BY c.name,sc.name,p.release_year ORDER BY c.name,sc.name,p.release_year",
            'brands':"SELECT brand,COUNT(*) count FROM products WHERE deleted_at IS NULL GROUP BY brand ORDER BY count DESC,brand",
            'category_brands':f'SELECT c.name category,COALESCE(sc.name,c.name) product_type,p.brand,COUNT(*) count {JOINS} WHERE p.deleted_at IS NULL GROUP BY c.name,sc.name,p.brand ORDER BY c.name,sc.name,count DESC',
            'older_products':f'SELECT p.id,p.name,p.brand,sc.name product_type,p.release_year,p.release_date,p.release_date_basis {JOINS} WHERE p.deleted_at IS NULL AND (p.release_year<%s OR (p.release_year=%s AND (p.release_date IS NULL OR p.release_date<%s))) ORDER BY p.release_year,p.name',
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
