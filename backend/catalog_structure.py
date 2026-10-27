"""Family -> hardware model -> saleable variant, without changing product IDs."""
from functools import lru_cache
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

try:
    from . import product_identity as identity, catalog_taxonomy as taxonomy
except ImportError:
    import product_identity as identity, catalog_taxonomy as taxonomy


def key(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def clean(value):
    return ' '.join(unicodedata.normalize('NFKC',str(value or '')).replace('\xa0',' ').split())


def attributes(record):
    aliases={'colour':'Color','color':'Color','finish':'Color','storage':'Storage','capacity':'Capacity',
        'ram':'RAM','unified memory':'RAM','memory':'RAM','display size':'Display size','screen size':'Display size',
        'display glass':'Display finish','screen glass':'Display finish','screen finish':'Display finish',
        'display finish':'Display finish','glass type':'Display finish',
        'gpu cores':'GPU cores','size':'Size','connectivity':'Connectivity'}
    result={aliases.get(str(k).lower(),str(k)):clean(v) for k,v in (record.get('attributes') or {}).items() if v and str(v)!='Default Title'}
    specs=record.get('specs') or record.get('specifications') or {}
    if isinstance(specs,str):
        try:specs=json.loads(specs)
        except ValueError:specs={}
    for name,value in specs.items():
        name=str(name).lower().strip();value=clean(value)
        if name in {'color','colour','finish','product colour'} and len(value)<60 and not re.search(r'[;,/]|\bor\b',value,re.I):result.setdefault('Color',value)
        storage_types={'smartphones','tablets','laptops','desktops','ssds','memory_cards','usb_drives','hard_drives'}
        capacity_value=re.fullmatch(r'\d+(?:\.\d+)?\s*(?:GB|TB|MB|kg|L)(?:\s+SSD)?',value,re.I)
        explicit_storage=re.fullmatch(r'(?:internal |total |ssd |storage |memory )?storage(?: capacity)?',name)
        generic_capacity=name in {'capacity','capacity size'}
        if capacity_value and explicit_storage:
            # Explicit storage fields are stronger evidence than previously
            # derived attributes. This also repairs stale variant metadata
            # during idempotent rebuilds (for example, RAM copied into
            # ``Storage`` on a tablet must not mask ``Internal Storage``).
            result['Storage' if record.get('type_id') in storage_types else 'Capacity']=value
        elif capacity_value and generic_capacity and record.get('type_id') in {'ssds','memory_cards','usb_drives','hard_drives'}:
            result.setdefault('Storage',value)
        elif capacity_value and generic_capacity and record.get('type_id') not in {'smartphones','tablets','laptops','desktops'}:
            result.setdefault('Capacity',value)
        if re.fullmatch(r'(?:unified |installed |system )?(?:ram|memory)(?: size| capacity)?',name) and re.fullmatch(r'\d+\s*(?:GB|MB)',value,re.I):
            result.setdefault('RAM',value)
        if re.fullmatch(r'(?:display|screen) size',name) and re.fullmatch(r'\d+(?:\.\d+)?\s*(?:inches|inch|in|\")',value,re.I):
            result.setdefault('Display size',value)
        if re.search(r'(?:display|screen) glass|glass type|display finish|screen finish',name,re.I) and re.search(r'nano.?texture|standard glass',value,re.I):
            result.setdefault('Display finish','Nano-Texture Glass' if re.search(r'nano.?texture',value,re.I) else 'Standard Glass')
        if re.search(r'connectivity|network type|wireless network',name,re.I) and re.search(r'wi[ -]?fi|cellular|\b5g\b|\blte\b',value,re.I):
            result.setdefault('Connectivity',value)
        if re.fullmatch(r'(?:gpu|graphics)(?: core| cores)?',name) and re.fullmatch(r'\d+\s*[- ]?core(?:\s+GPU)?',value,re.I):
            result.setdefault('GPU cores',re.sub(r'\s+',' ',value))
    title=clean(record.get('name'))
    if record.get('type_id') in {'smartphones','tablets','laptops','desktops'} and 'RAM' not in result:
        ram=re.search(r'\b(\d+(?:\.\d+)?)\s*(?:GB|MB)\s+(?:LPDDR\dX?|DDR\d)?\s*RAM\b',title,re.I)
        if ram:result['RAM']=ram[1]+' GB'
    if record.get('type_id') in {'smartphones','tablets','ssds','memory_cards','usb_drives','hard_drives'}:
        capacities=re.findall(r'\b(\d+(?:\.\d+)?)\s*(GB|TB)\b(?!\s*(?:RAM|GDDR))',title,re.I)
        if len(capacities)==1:result.setdefault('Storage',capacities[0][0]+capacities[0][1].upper())
    if record.get('type_id') in {'smartphones','tablets','laptops','televisions','monitors'} and 'Display size' not in result:
        match=re.search(r'\b(\d+(?:\.\d+)?)\s*(?:-?\s*inch(?:es)?\b|\")',title,re.I)
        if match:result['Display size']=match.group(1)+' in'
    if record.get('type_id') in {'smartphones','tablets'}:
        wifi_cellular=re.search(r'\bwi[ -]?fi\s*\+\s*(cellular|5g|4g)\b',title,re.I)
        if wifi_cellular:
            network=wifi_cellular[1].upper() if wifi_cellular[1].lower() in {'5g','4g'} else 'Cellular'
            result['Connectivity']='Wi-Fi + '+network
        elif record.get('type_id')=='tablets' and re.search(r'\bwi[ -]?fi\b',title,re.I):result['Connectivity']='Wi-Fi'
        elif re.search(r'\bwi[ -]?fi\b',title,re.I):result.setdefault('Connectivity','Wi-Fi')
        elif re.search(r'\b5G\b',title,re.I):result.setdefault('Connectivity','5G')
    if record.get('type_id')=='tablets':
        if re.search(r'\bnano.?texture glass\b',title,re.I):result['Display finish']='Nano-Texture Glass'
        elif re.search(r'\bstandard glass\b',title,re.I):result['Display finish']='Standard Glass'
    if 'Color' not in result:
        match=re.search(r'\b((?:(?:natural|black|white|blue|desert|silver) titanium|titanium (?:black|white|blue|silver)|space (?:black|grey|gray)|jet black|rose gold|cosmic orange|deep blue|soft pink|mist blue|silver shadow|star white|night sky|cobalt violet|cloud white|sky blue|blueblack|icyblue|coralred|pinkgold|astral trail|nebula noir|artic dawn|moonstone|lemongrass|hibiscus|obsidian|glacier|canyon|blush|indigo|citrus|sage|lavender|midnight|starlight|ultramarine|teal|pistachio|blueberry|graphite|black|white|blue|silver|grey|gray|gold|pink|purple|green|yellow|orange))\b',title,re.I)
        if match:result['Color']=match.group(1)
    return dict(sorted(result.items()))


@lru_cache(maxsize=1)
def release_rules():
    return json.loads((Path(__file__).resolve().parent.parent/'product_catalog'/'model_release_evidence.json').read_text(encoding='utf-8')).get('rules',[])


def describe(record):
    """Known generation patterns group models. Unknowns retain exact seller parents."""
    # Match reviewed model rules against the raw product title. During rebuilds
    # family_name is populated from the previous model assignment and can omit
    # the manufacturer's model code, causing identical screen-size variants to
    # fall back into separate retailer-parent models.
    brand=clean(record.get('brand'));title=clean(record.get('name') or record.get('family_name'))
    typeid=record.get('type_id') or 'unclassified';family=model=None;confidence='retailer_parent'
    rules=release_rules()
    reviewed=next((r for r in rules if r.get('family_key') and r['type_id']==typeid and identity.norm_brand(r['brand'])==identity.norm_brand(brand)
        and re.fullmatch(r.get('mpn_pattern','.*'),identity.norm_code(record.get('mpn'))) and re.search(r['name_pattern'],title,re.I)),None)
    if reviewed:
        family=reviewed.get('family_name') or reviewed.get('model_name')
        model=reviewed.get('model_name') or family
        confidence='manufacturer_evidence'
    if typeid=='smartphones' and not model:
        patterns=[
          (r'\biPhone\s*(\d{2})(e)?(?:\s*(Pro\s*Max|Pro|Plus|Air))?\b',lambda m:('iPhone '+m[1],'iPhone '+m[1]+(m[2] or '')+(' '+m[3] if m[3] else ''))),
          (r'\bGalaxy\s*(S\d{2})(?:\s*(Ultra|Plus|\+|FE))?(?=[^A-Za-z0-9]|$)',lambda m:('Galaxy '+m[1],'Galaxy '+m[1]+(' '+('Plus' if m[2]=='+' else m[2]) if m[2] else ''))),
          (r'\bGalaxy\s*Z\s*(Fold|Flip)\s*(\d+)\b',lambda m:('Galaxy Z '+m[1]+' '+m[2],'Galaxy Z '+m[1]+' '+m[2])),
          (r'\bPixel\s*(\d{1,2})(a)?(?:\s*(Pro\s*XL|Pro\s*Fold|Pro|XL))?\b',lambda m:('Pixel '+m[1],'Pixel '+m[1]+(m[2] or '')+(' '+m[3] if m[3] else ''))),
        ]
        for pattern,formatter in patterns:
            m=re.search(pattern,title,re.I)
            if m:family,model=formatter(m);confidence='explicit_model_generation';break
    if typeid in {'smartphones','tablets','laptops','desktops'} and not model:
        m=re.search(r'\b((?:Galaxy\s+)?(?:A\d{2}|Tab\s+S\d{1,2})(?:\s*(?:Ultra|Plus|FE|\+))?)\b',title,re.I)
        if m and identity.norm_brand(brand)=='samsung':model=m[1];family=re.sub(r'\s*(Ultra|Plus|FE|\+)$','',model,flags=re.I);confidence='explicit_model_generation'
    if typeid=='tablets' and not model and identity.norm_brand(brand)=='apple':
        patterns=[
            (r'\biPad\s+(Air|Pro)\s+(M\d+)\b',lambda m:(f'iPad {m[1]}',f'iPad {m[1]} {m[2]}')),
            (r'\biPad\s+mini\s+(A\d+\s+Pro)\b',lambda m:('iPad mini',f'iPad mini {m[1]}')),
            (r'\biPad\s+(A\d+)\b',lambda m:('iPad',f'iPad {m[1]}')),
        ]
        for pattern,formatter in patterns:
            match=re.search(pattern,title,re.I)
            if match:family,model=formatter(match);confidence='explicit_model_generation';break
    if typeid=='smartphones' and not model and identity.norm_brand(brand)=='apple' and re.search(r'\biPhone\s+Duo\b',title,re.I):
        family,model='iPhone','iPhone Duo';confidence='explicit_model_generation'
    if not model:
        explicit=record.get('verified_model') or {}
        if explicit.get('name') and explicit.get('family'):
            model=explicit['name'];family=explicit['family'];confidence='manufacturer_evidence'
    if not model:
        # Do not group unrelated configurations merely because they share words.
        model=clean(record.get('family_name')) or title or clean(record.get('model'))
        family=model
    family=clean(family);model=clean(model)
    if confidence=='retailer_parent':
        u=urlsplit(record.get('url') or '')
        scope=(u.netloc.lower()+u.path.rstrip('/')) if u.netloc else record.get('mpn') or model
    else:scope=identity.norm_text(model)
    familyid=key('family|'+identity.norm_brand(brand)+'|'+typeid+'|'+identity.norm_text(family))
    modelid=key('model|'+identity.norm_brand(brand)+'|'+typeid+'|'+str(scope))
    return {'family_id':familyid,'family_name':family,'model_id':modelid,'model_name':model,
        'type_id':typeid,'brand':brand,'attributes':attributes(record),'grouping_basis':confidence}


def rebuild(db):
    """Idempotent metadata migration. Bid/cart product IDs are preserved."""
    try:from . import catalog_metadata
    except ImportError:import catalog_metadata
    catalog_metadata.ensure_schema(db)
    with db() as conn,conn.cursor() as cur:
        cur.execute('''SELECT p.id,p.name,p.brand,p.model,p.mpn,p.product_url url,p.manual_specifications,
            sc.name subcategory,a.type_id,v.attributes_json,m.name family_name FROM products p
            LEFT JOIN categories sc ON sc.id=p.subcategory_id LEFT JOIN catalog_type_assignments a ON a.product_id=p.id
            LEFT JOIN catalog_variant_links v ON v.product_id=p.id
            LEFT JOIN catalog_model_families m ON m.id=v.family_id
            WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE ORDER BY p.id''')
        rows=cur.fetchall()
        for row in rows:
            row['type_id']=row['type_id'] or taxonomy.classify(row['name'],row.get('subcategory') or '')[0]
            row['specs']=json.loads(row.get('manual_specifications') or '{}');row['attributes']=json.loads(row.get('attributes_json') or '{}')
            meta=describe(row)
            cur.execute('''INSERT INTO catalog_product_families(id,brand,name,type_id) VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE name=VALUES(name),type_id=VALUES(type_id)''',[meta['family_id'],meta['brand'],meta['family_name'][:255],meta['type_id']])
            cur.execute('''INSERT INTO catalog_model_families(id,brand,name,type_id,created_at,family_id) VALUES (%s,%s,%s,%s,UTC_TIMESTAMP(),%s)
                ON DUPLICATE KEY UPDATE name=VALUES(name),family_id=VALUES(family_id)''',[meta['model_id'],meta['brand'],meta['model_name'][:255],meta['type_id'],meta['family_id']])
            # Existing identities are deliberately retained; unlinked legacy rows
            # have a product-ID identity until a reviewed exact match is found.
            cur.execute('''INSERT INTO catalog_variant_links(product_id,family_id,identity_key,attributes_json,identity_basis)
                VALUES (%s,%s,%s,%s,'legacy_exact_product_id') ON DUPLICATE KEY UPDATE family_id=VALUES(family_id),attributes_json=VALUES(attributes_json)''',
                [row['id'],meta['model_id'],key('legacy_variant|'+row['id']),json.dumps(meta['attributes'],ensure_ascii=False)])
        conn.commit()
    return {'variants':len(rows),'models':len({describe({**r,'attributes':json.loads(r.get('attributes_json') or '{}')})['model_id'] for r in rows})}
