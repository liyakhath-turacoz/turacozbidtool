"""Optional canonical taxonomy/variant metadata, with private date display."""
import json
import os
import re
from pathlib import Path

_SCHEMA = [
    '''CREATE TABLE IF NOT EXISTS catalog_product_families (id CHAR(64) PRIMARY KEY, brand VARCHAR(190) NOT NULL, name VARCHAR(255) NOT NULL, type_id VARCHAR(60) NOT NULL) ENGINE=InnoDB''',
    '''CREATE TABLE IF NOT EXISTS catalog_model_families (id CHAR(64) PRIMARY KEY, brand VARCHAR(190) NOT NULL, name VARCHAR(255) NOT NULL, type_id VARCHAR(60) NOT NULL, created_at DATETIME NOT NULL) ENGINE=InnoDB''',
    '''CREATE TABLE IF NOT EXISTS catalog_variant_links (product_id CHAR(36) PRIMARY KEY, family_id CHAR(64) NOT NULL, identity_key CHAR(64) NOT NULL, attributes_json LONGTEXT NOT NULL, identity_basis VARCHAR(80) NOT NULL, KEY idx_variant_family(family_id), UNIQUE KEY uq_canonical_variant(identity_key)) ENGINE=InnoDB''',
    '''CREATE TABLE IF NOT EXISTS catalog_retail_offers (id CHAR(64) PRIMARY KEY, candidate_id CHAR(64) NOT NULL, product_id CHAR(36) NOT NULL, source_id VARCHAR(60) NOT NULL, seller_sku VARCHAR(190) NULL, url TEXT NOT NULL, price DECIMAL(20,2) NOT NULL, currency CHAR(3) NOT NULL, availability VARCHAR(24) NOT NULL, checked_at DATETIME NOT NULL, KEY idx_retail_offer_product(product_id)) ENGINE=InnoDB''',
    '''CREATE TABLE IF NOT EXISTS catalog_type_assignments (product_id CHAR(36) PRIMARY KEY, type_id VARCHAR(60) NOT NULL, taxonomy_version INT NOT NULL, path_json LONGTEXT NOT NULL, reason VARCHAR(255) NOT NULL, checked_at DATETIME NOT NULL, KEY idx_catalog_type(type_id)) ENGINE=InnoDB'''
]
_COLUMNS={
    'catalog_product_families':('id','brand','name','type_id'),
    'catalog_model_families':('id','brand','name','type_id','created_at','family_id'),
    'catalog_type_assignments':('product_id','type_id','taxonomy_version','path_json','reason','checked_at'),
    'catalog_variant_links':('product_id','family_id','identity_key','attributes_json','identity_basis'),
    'catalog_retail_offers':('id','candidate_id','product_id','source_id','seller_sku','url','price','currency','availability','checked_at'),
}


def ensure_schema(db):
    with db() as conn,conn.cursor() as cursor:
        for sql in _SCHEMA:cursor.execute(sql)
        cursor.execute("SHOW COLUMNS FROM catalog_model_families LIKE 'family_id'")
        if not cursor.fetchone():cursor.execute('ALTER TABLE catalog_model_families ADD family_id CHAR(64) NULL, ADD KEY idx_hardware_model_family(family_id)')
        conn.commit()


def export_bundle(db,path):
    tables={}
    with db() as conn,conn.cursor() as cursor:
        for table,columns in _COLUMNS.items():
            cursor.execute('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY '+columns[0]);tables[table]=cursor.fetchall()
    temp=path.with_suffix('.tmp.json');temp.write_text(json.dumps({'version':1,'tables':tables},ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8');temp.replace(path)


def restore_bundle(cursor,path=None):
    path=path or Path(__file__).resolve().parent.parent/'product_catalog'/'catalog_metadata.json'
    if not path.exists():return
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('version')!=1:raise ValueError('Unsupported catalog metadata version')
    cursor.execute('SELECT id FROM products');products={r['id'] for r in cursor.fetchall()}
    cursor.execute('SELECT product_id,identity_key FROM catalog_variant_links');owners={r['identity_key']:r['product_id'] for r in cursor.fetchall()}
    for row in data['tables'].get('catalog_variant_links',[]):
        if row['identity_key'] in owners and owners[row['identity_key']]!=row['product_id']:raise ValueError('Conflicting variant identity in metadata bundle')
    for table,columns in _COLUMNS.items():
        rows=[r for r in data['tables'].get(table,[]) if 'product_id' not in r or r['product_id'] in products]
        if not rows:continue
        updates=','.join(c+'=VALUES('+c+')' for c in columns[1:])
        cursor.executemany('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join(['%s']*len(columns))+') ON DUPLICATE KEY UPDATE '+updates,
            [[r.get(c) for c in columns] for r in rows])

_RELEASE_KEY=re.compile(
    r'^(?:release(?:[ _-]?(?:date|year))?|launch(?:[ _-]?(?:date|year))?(?:[ _-]?\(india\))?|'
    r'model[ _-]?year|date of (?:release|launch)(?:[ _-]?\(india\))?)$',
    re.I,
)


def _without_dates(value):
    if isinstance(value,dict):
        if _RELEASE_KEY.fullmatch(str(value.get('name',''))):return None
        return {k:clean for k,v in value.items() if not _RELEASE_KEY.fullmatch(str(k)) and (clean:=_without_dates(v)) is not None}
    if isinstance(value,list):return [clean for v in value if (clean:=_without_dates(v)) is not None]
    return value

def show_release_dates():
    return os.getenv('TURACOZ_SHOW_PRODUCT_RELEASE_DATES','false').strip().lower() in {'true','1','yes'}

def hide_release_dates(row,admin=False):
    row['release_year_verified']=bool(row.get('release_year') and row.get('release_date_basis') in {'manufacturer_release','manufacturer_model_year','retailer_model_year','model_year','official_release_date','icecat_explicit_release','india_store_launch_year'})
    if not admin and not show_release_dates():
        for key in ('release_date','release_year','release_date_basis','release_date_precision','release_date_source_url','release_evidence'):
            row.pop(key,None)
        for key in ('specifications','technical_specifications','software_specifications','manual_specifications'):
            if key in row:
                value=row[key]
                if isinstance(value,str):
                    try:value=json.loads(value)
                    except ValueError:pass
                row[key]=_without_dates(value)
    return row

def table_exists(cursor,name):
    cursor.execute('SHOW TABLES LIKE %s',[name])
    return bool(cursor.fetchone())

def attach(cursor,rows):
    if not rows or not table_exists(cursor,'catalog_type_assignments'):return rows
    ids=[r['id'] for r in rows];marks=','.join(['%s']*len(ids))
    cursor.execute(f'''SELECT a.product_id,a.type_id,a.path_json,v.family_id,v.attributes_json,v.identity_basis
      FROM catalog_type_assignments a LEFT JOIN catalog_variant_links v ON v.product_id=a.product_id
      WHERE a.product_id IN ({marks})''',ids)
    byid={r['product_id']:r for r in cursor.fetchall()}
    for row in rows:
        meta=byid.get(row['id'])
        if not meta:continue
        row['product_type_id']=meta['type_id'];row['taxonomy_path']=json.loads(meta['path_json'])
        row['model_id']=meta['family_id']
        row['variant_id']=row['id']
        row['variant_attributes']=json.loads(meta['attributes_json'] or '{}')
        row['variant_identity_basis']=meta['identity_basis']
    cursor.execute(f'''SELECT v.product_id,m.id model_id,m.name model_name,m.family_id,f.name family_name,
        (SELECT COUNT(*) FROM catalog_variant_links siblings JOIN products sp ON sp.id=siblings.product_id WHERE siblings.family_id=m.id AND sp.catalog_visible=TRUE AND sp.status='active' AND sp.deleted_at IS NULL) variant_count
        FROM catalog_variant_links v JOIN catalog_model_families m ON m.id=v.family_id
        LEFT JOIN catalog_product_families f ON f.id=m.family_id WHERE v.product_id IN ({marks})''',ids)
    hierarchy={r['product_id']:r for r in cursor.fetchall()}
    for row in rows:
        if row['id'] in hierarchy:row.update({k:v for k,v in hierarchy[row['id']].items() if k!='product_id'})
        row['variant_id']=row['id']
    return rows

def variants(cursor,product_id):
    if not table_exists(cursor,'catalog_variant_links'):return []
    cursor.execute('''SELECT p.id,p.name,p.model,p.image_url,v.attributes_json
      FROM catalog_variant_links selected JOIN catalog_variant_links v ON v.family_id=selected.family_id
      JOIN products p ON p.id=v.product_id
      JOIN categories c ON c.id=p.category_id LEFT JOIN categories sc ON sc.id=p.subcategory_id
      WHERE selected.product_id=%s AND p.catalog_visible=TRUE AND p.status='active' AND p.deleted_at IS NULL
        AND c.status='active' AND c.deleted_at IS NULL
        AND (sc.id IS NULL OR (sc.status='active' AND sc.deleted_at IS NULL))
      ORDER BY p.name,p.id''',[product_id])
    rows=cursor.fetchall()
    for row in rows:row['attributes']=json.loads(row.pop('attributes_json') or '{}')
    return rows


def taxonomy_tree(cursor):
    try:
        from .catalog_taxonomy import TYPES,VERSION
    except ImportError:
        from catalog_taxonomy import TYPES,VERSION
    counts={}
    if table_exists(cursor,'catalog_type_assignments'):
        cursor.execute('''SELECT a.type_id,COUNT(*) n FROM catalog_type_assignments a
            JOIN products p ON p.id=a.product_id JOIN categories c ON c.id=p.category_id
            LEFT JOIN categories sc ON sc.id=p.subcategory_id
            WHERE p.catalog_visible=TRUE AND p.deleted_at IS NULL AND p.status='active'
                AND c.status='active' AND c.deleted_at IS NULL
                AND (sc.id IS NULL OR (sc.status='active' AND sc.deleted_at IS NULL)) GROUP BY a.type_id''')
        counts={r['type_id']:r['n'] for r in cursor.fetchall()}
    return {'version':VERSION,'types':[{'id':t['id'],'path':t['path'],'count':counts.get(t['id'],0),'required_attributes':t['required_groups']} for t in TYPES.values()]}


def taxonomy_facets(cursor):
    return [{'value':t['id'],'label':' / '.join(t['path']),'count':t['count']}
            for t in taxonomy_tree(cursor)['types'] if t['count']]
