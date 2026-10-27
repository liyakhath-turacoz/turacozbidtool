"""Persistent Rust inverted index; SQL remains authoritative for access and IDs.

One 16 MB writer, disk-backed readers, no resident search-server process.
Generation directories let concurrent readers finish while a new index commits.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
import uuid

import tantivy

ROOT = Path(__file__).resolve().parent / 'search_engine' / 'indexes'
_lock = threading.RLock()
_index = None
_signature = None
_generation = None
_checked = 0
VERSION = 3
SYNONYMS = {
    'fridge': 'refrigerators', 'fridges': 'refrigerators', 'frij': 'refrigerators',
    'refrigerator': 'refrigerators', 'ac': 'air_conditioners', 'aircon': 'air_conditioners',
    'geyser': 'water_heaters', 'geysers': 'water_heaters', 'gijar': 'water_heaters',
    'geezer': 'water_heaters', 'pankha': 'fans', 'pankhe':'fans', 'friz':'refrigerators', 'fan': 'fans', 'tv': 'televisions',
    'tvs': 'televisions', 'mobile': 'smartphones', 'mobiles': 'smartphones', 'phone': 'smartphones',
    'phones': 'smartphones', 'laptop': 'laptops', 'notebook': 'laptops', 'washer': 'washers',
    'pendrive': 'usb_drives', 'pendrives': 'usb_drives', 'hdd': 'hard_drives',
    'powerbank': 'power_banks', 'microwave': 'microwaves', 'earbud': 'earbuds',
}


def normalize(value):
    text = str(value or '').casefold()
    text = re.sub(r'\b(\d+(?:\.\d+)?)\s+(gb|tb|mb|ghz|mhz|ton|kg|mah|w)\b', r'\1\2', text)
    return ' '.join(re.findall(r'[^\W_]+', text, re.UNICODE))


def schema():
    from .catalog_filters import SPEC_DEFINITIONS
    b = tantivy.SchemaBuilder()
    for field in ('id', 'model_key', 'type', 'brand', 'category', 'product_type', 'year', 'status', 'public'):
        b.add_text_field(field, stored=field == 'id', tokenizer_name='raw', fast=True)
    for field in ('name', 'model', 'text'):
        b.add_text_field(field)
    b.add_text_field('name_sort', tokenizer_name='raw', fast=True)
    b.add_unsigned_field('created', fast=True)
    b.add_float_field('price_min', fast=True, indexed=True)
    b.add_float_field('price_max', fast=True, indexed=True)
    for key in SPEC_DEFINITIONS:
        b.add_text_field('spec_' + key, tokenizer_name='raw', fast=True)
    return b.build()


def fingerprint(db):
    with db() as conn, conn.cursor() as c:
        c.execute('''SELECT COUNT(*) n,MAX(updated_at) changed FROM products WHERE catalog_visible=TRUE AND deleted_at IS NULL''')
        products = c.fetchone()
        c.execute('SELECT COUNT(*) n,MAX(updated_at) changed FROM categories')
        categories = c.fetchone()
        c.execute('SELECT COUNT(*) n FROM catalog_variant_links')
        links = c.fetchone()
    revision=(ROOT/'DIRTY').read_text(encoding='utf-8') if (ROOT/'DIRTY').exists() else ''
    return hashlib.sha256(json.dumps([VERSION, products, categories, links, revision], default=str, sort_keys=True).encode()).hexdigest()


def rebuild(db, signature=None):
    global _index, _signature, _checked, _generation
    from . import catalog_filters as cf, catalog_taxonomy as taxonomy
    with _lock:
        signature = signature or fingerprint(db)
        ROOT.mkdir(parents=True, exist_ok=True)
        path = ROOT / uuid.uuid4().hex
        path.mkdir()
        idx = tantivy.Index(schema(), path=str(path))
        writer = idx.writer(heap_size=16_000_000, num_threads=1)
        last = ''; count = 0
        while True:
            with db() as conn, conn.cursor() as c:
                c.execute('''SELECT p.*,c.name category,sc.name subcategory,c.status category_status,
                    c.deleted_at category_deleted,sc.status subcategory_status,sc.deleted_at subcategory_deleted,
                    a.type_id,v.family_id model_key,m.name model_name
                    FROM products p JOIN categories c ON c.id=p.category_id
                    LEFT JOIN categories sc ON sc.id=p.subcategory_id
                    LEFT JOIN catalog_type_assignments a ON a.product_id=p.id
                    LEFT JOIN catalog_variant_links v ON v.product_id=p.id
                    LEFT JOIN catalog_model_families m ON m.id=v.family_id
                    WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE AND p.id>%s ORDER BY p.id LIMIT 200''', [last])
                rows = c.fetchall()
            if not rows:
                break
            for row in rows:
                typeid = row.get('type_id') or taxonomy.classify(row['name'], row.get('subcategory') or '')[0]
                typeinfo = taxonomy.TYPES.get(typeid, {})
                public = row['status'] == 'active' and row['category_status'] == 'active' and not row['category_deleted'] and (not row['subcategory_id'] or (row['subcategory_status'] == 'active' and not row['subcategory_deleted']))
                doc = {
                    'id': row['id'], 'model_key': row.get('model_key') or row['id'],
                    'type': typeid or 'unclassified', 'brand': row.get('manufacturer') or row.get('brand') or '',
                    'category': row['category'], 'product_type': row.get('subcategory') or '',
                    'year': str(row.get('release_year') or 'unknown'), 'status': row['status'],
                    'public': 'yes' if public else 'no', 'name': normalize(row['name']),
                    'model': normalize(' '.join(str(row.get(k) or '') for k in ('model', 'model_name', 'mpn', 'gtin'))),
                    'name_sort': row['name'].casefold(),
                    'created': max(0, int(row['created_at'].timestamp())) if row.get('created_at') else 0,
                    'price_min': float(row.get('price_min') or 0), 'price_max': float(row.get('price_max') or 0),
                    'text': normalize(' '.join([str(row.get('brand') or ''), ' '.join(typeinfo.get('path', [])),
                        str(row.get('subcategory') or ''), cf._searchable_text(row.get('highlights')),
                        cf._searchable_text(row.get('manual_specifications'))])),
                }
                for key, value in cf.normalized_specs(row):
                    doc.setdefault('spec_' + key, []).append(value)
                writer.add_document(tantivy.Document.from_dict(doc, idx.schema))
                count += 1
            last = rows[-1]['id']
        writer.commit()
        del writer
        idx.reload()
        manifest = {'directory': path.name, 'signature': signature, 'documents': count}
        temp = ROOT / ('CURRENT.' + uuid.uuid4().hex + '.tmp')
        temp.write_text(json.dumps(manifest), encoding='utf-8')
        os.replace(temp, ROOT / 'CURRENT.json')
        _index, _signature, _checked, _generation = idx, signature, time.monotonic(), path.name
        generations=sorted((p for p in ROOT.iterdir() if p.is_dir() and re.fullmatch('[0-9a-f]{32}',p.name)),key=lambda p:p.stat().st_mtime,reverse=True)
        for obsolete in generations[2:]:
            if obsolete.resolve().parent==ROOT.resolve() and time.time()-obsolete.stat().st_mtime>600:
                try:shutil.rmtree(obsolete)
                except OSError:pass  # Windows readers may still map this generation.
        return manifest


def engine(db):
    global _index, _signature, _checked, _generation
    with _lock:
        if _index is None and (ROOT / 'CURRENT.json').exists():
            meta = json.loads((ROOT / 'CURRENT.json').read_text(encoding='utf-8'))
            if (ROOT / meta['directory']).is_dir():
                _index = tantivy.Index.open(str(ROOT / meta['directory']))
                _signature = meta['signature']
                _generation = meta['directory']
        if _index is None or time.monotonic() - _checked > 3:
            current = fingerprint(db)
            if (ROOT / 'CURRENT.json').exists():
                latest=json.loads((ROOT / 'CURRENT.json').read_text(encoding='utf-8'))
                if latest['directory']!=_generation and latest['signature']==current:
                    _index=tantivy.Index.open(str(ROOT / latest['directory']))
                    _signature=current;_generation=latest['directory']
            if _index is None or current != _signature:
                for attempt in range(2):
                    try:
                        rebuild(db,current)
                        break
                    except ValueError as error:
                        if attempt or 'Access is denied' not in str(error):raise
                        # Retry in a fresh generation after a transient Windows
                        # file lock; never reuse a partially committed writer.
                        time.sleep(0.2)
            _checked = time.monotonic()
        return _index


def invalidate():
    global _signature, _checked
    _signature = None; _checked = 0
    ROOT.mkdir(parents=True,exist_ok=True)
    temp=ROOT/('DIRTY.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(uuid.uuid4().hex,encoding='utf-8')
    os.replace(temp,ROOT/'DIRTY')


def combine(queries, occur):
    return tantivy.Query.boolean_query([(occur, q) for q in queries]) if queries else tantivy.Query.all_query()


def query(idx, filters, admin=False, omit=None):
    s = idx.schema; must = []
    def term(field, value):
        return tantivy.Query.term_query(s, field, str(value))
    def choices(field, values):
        if values:
            must.append(combine([term(field, v) for v in values], tantivy.Occur.Should))
    if not admin:
        must.append(term('public', 'yes'))
    if filters.get('status'):
        must.append(term('status', filters['status']))
    for key, field, single in [('canonical_types', 'type', 'type_id'), ('brands', 'brand', 'brand'), ('categories', 'category', 'category'), ('product_types', 'product_type', 'product_type'), ('years', 'year', None)]:
        if key != omit:
            choices(field, list(filters.get(key) or []) + ([filters[single]] if single and filters.get(single) else []))
    for key, values in (filters.get('specs') or {}).items():
        if 'spec_' + key != omit:
            choices('spec_' + key, values)
    for key, field, low in [('minimum', 'price_max', True), ('maximum', 'price_min', False)]:
        if filters.get(key) is not None:
            must.append(tantivy.Query.range_query(s, field, tantivy.FieldType.Float,
                lower_bound=float(filters[key]) if low else None, upper_bound=None if low else float(filters[key])))
    from .catalog_filters import explicit_ram_capacity
    ram=explicit_ram_capacity(filters.get('q'))
    if ram:must.append(term('spec_ram',f'{float(ram[0]):g} {ram[1].upper()}'))
    text = normalize(filters.get('q'))
    if ram:text=' '.join(t for t in text.split() if t not in {'ram',f'{float(ram[0]):g}{ram[1].lower()}'})
    for phrase, replacement in [('air conditioner', 'ac'), ('water heater', 'geyser'), ('washing machine', 'washer'), ('pen drive', 'pendrive'), ('power bank', 'powerbank'), ('kapde dhone ki machine','washer'), ('kapde dhone wali machine','washer')]:
        text = text.replace(phrase, replacement)
    for token in text.split()[:12]:
        alternatives = []
        alias = token if token in SYNONYMS else next(iter(difflib.get_close_matches(token, [k for k in SYNONYMS if len(k)>=5], n=1, cutoff=0.78)), None) if len(token)>=4 and token.isalpha() else None
        if alias and not (alias=='ac' and any(x in text for x in ('adapter','adaptor','power supply'))):
            must.append(term('type', SYNONYMS[alias]))
            continue
        for field, boost in [('name', 5), ('model', 6), ('text', 1)]:
            alternatives.append(tantivy.Query.boost_query(term(field, token), boost))
            if len(token) >= 3:
                # Prefix and transpositions are applied in the inverted index.
                distance = 0 if any(c.isdigit() for c in token) else (2 if len(token) >= 8 else 1 if len(token) >= 4 else 0)
                alternatives.append(tantivy.Query.boost_query(tantivy.Query.fuzzy_term_query(s, field, token, distance=distance, prefix=True), boost / 3))
        must.append(combine(alternatives, tantivy.Occur.Should))
    return combine(must, tantivy.Occur.Must)


def search(db, filters, admin=False, include_facets=True):
    from . import catalog_filters as cf, catalog_metadata as metadata, catalog_taxonomy as taxonomy
    idx = engine(db); reader = idx.searcher(); q = query(idx, filters, admin)
    grouped = bool(filters.get('group_models', False)) and not admin
    limit = min(250, max(1, int(filters.get('limit') or 50)))
    offset = max(0, int(filters.get('offset') or 0))
    result = reader.search(q, limit=1)
    total = result.count
    sort = filters.get('sort', 'Newest')
    ordering = {'Newest': ('created', tantivy.Order.Desc), 'Year': ('year', tantivy.Order.Desc),
        'Name': ('name_sort', tantivy.Order.Asc), 'A-Z': ('name_sort', tantivy.Order.Asc),
        'Lowest Price': ('price_min', tantivy.Order.Asc), 'Highest Price': ('price_max', tantivy.Order.Desc)}
    order = {} if filters.get('q') and sort == 'Newest' else dict(zip(('order_by_field', 'order'), ordering.get(sort, ordering['Newest'])))
    variant_total = total
    if grouped and variant_total:
        buckets = reader.aggregate(q, {'models': {'terms': {'field': 'model_key', 'size': 100000}}})['models']['buckets']
        if len(buckets) >= 100000:
            raise RuntimeError('Model grouping capacity exceeded; increase the index aggregation limit')
        total = len(buckets)
        model_by_id = None
        needed = min(variant_total, max(100, (offset + limit) * 4))
        while True:
            hits = reader.search(q, limit=needed, **order).hits
            # Only the ranked prefix is decoded. No SQL/Python catalogue scan.
            found = []; seen = set()
            with db() as conn, conn.cursor() as c:
                ids = [reader.doc(address)['id'][0] for _, address in hits]
                if ids:
                    c.execute('SELECT product_id,family_id FROM catalog_variant_links WHERE product_id IN (' + ','.join(['%s'] * len(ids)) + ')', ids)
                    model_by_id = {r['product_id']: r['family_id'] for r in c.fetchall()}
                else: model_by_id = {}
            for pid in ids:
                model = model_by_id.get(pid, pid)
                if model not in seen: found.append(pid); seen.add(model)
            if len(found) >= offset + limit or needed >= variant_total: break
            needed = min(variant_total, needed * 2)
        ids = found[offset:offset + limit]
    else:
        ids = [reader.doc(address)['id'][0] for _, address in reader.search(q, limit=limit, offset=offset, **order).hits]
    items = []
    facets = {}
    with db() as conn, conn.cursor() as c:
        if ids:
            where, args = cf.conditions({}, admin)
            provenance = ',p.source,p.source_url' if admin else ''
            c.execute(f'''SELECT p.id,p.name,p.brand,p.model,p.price_min,p.price_max,p.status,p.created_at,p.image_url{provenance},p.release_year,p.release_date,p.release_date_basis,
                c.name category,sc.name item,sc.name subcategory,CONCAT(l.city,', ',l.state) location,p.highlights specifications,
                EXISTS(SELECT 1 FROM bid_requests br WHERE br.product_id=p.id) has_bid_history
                {cf.JOINS} WHERE {where} AND p.id IN ({','.join(['%s'] * len(ids))})''', args + ids)
            rows = {r['id']: r for r in c.fetchall()}
            items = [rows[pid] for pid in ids if pid in rows]
            metadata.attach(c, items)
        c.execute('SELECT COUNT(*) total FROM products WHERE deleted_at IS NULL AND catalog_visible=TRUE')
        catalog_total = c.fetchone()['total']
    for row in items:
        row['specifications'] = cf.decode(row['specifications'], {})
        row['variant_id'] = row['id']
        if not admin: row['specifications'] = cf.public_catalog_data(row['specifications'])
        metadata.hide_release_dates(row, admin)
    if include_facets:
        for key, field in [('canonical_types', 'type'), ('brands', 'brand'), ('years', 'year')]:
            scoped = query(idx, filters, admin, key)
            buckets = reader.aggregate(scoped, {'values': {'terms': {'field': field, 'size': 1000}}})['values']['buckets']
            facets[key] = [{'value': b['key'], 'count': b['doc_count'], **({'label': ' / '.join(taxonomy.TYPES[b['key']]['path']) if b['key'] in taxonomy.TYPES else 'Other electronics'} if key == 'canonical_types' else {})} for b in buckets if b['key']]
            facets[key].sort(key=lambda r: r.get('label', r['value']))
        facets['specs'] = {}
        # Contextual facets: broad unfiltered browsing should not show dozens of
        # unrelated capacity, socket and screen controls together.
        if filters.get('type_id') or filters.get('canonical_types') or filters.get('q'):
            for key, (label, _) in cf.SPEC_DEFINITIONS.items():
                buckets = reader.aggregate(query(idx, filters, admin, 'spec_' + key), {'values': {'terms': {'field': 'spec_' + key, 'size': 1000}}})['values']['buckets']
                if buckets:
                    facets['specs'][key] = {'label': label, 'values': [{'value': b['key'], 'count': b['doc_count']} for b in buckets]}
    return {'items': items, 'total': total, 'variant_total': variant_total, 'catalog_total': catalog_total,
        'facets': facets, 'brands': [r['value'] for r in facets.get('brands', [])], 'search_engine': 'tantivy', 'group_models': grouped}
