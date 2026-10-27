"""Add verified variants without replacing existing catalogue or bid references."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import date, datetime
import gzip
import hashlib
import io
import json
import re
import shutil
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from PIL import Image, ImageOps
from openpyxl import Workbook
from . import bulk_catalog as bulk, catalog_taxonomy as taxonomy, product_identity as identity
from . import catalogue_app_import as importer
from . import catalog_metadata
from .catalog_importer import connect

FOLDER=bulk.ROOT/'product_catalog'


def canonical_url(value):
    u=urlparse(value or '')
    query=urlencode(sorted((k,v) for k,v in parse_qsl(u.query) if k in {'variant','sku','pid'}))
    return urlunparse((u.scheme.lower(),u.netloc.lower(),u.path.rstrip('/'),' ',query,'')).replace('/?','?').replace('; ','')


def family_id(record):
    rule=reviewed_family(record)
    if rule:return bulk.digest('manufacturer_family|'+rule['family_key'])
    u=urlparse(record.get('url') or '')
    # Retailer parent grouping is evidence; similar names alone are not.
    return bulk.digest('family|'+u.netloc.lower()+'|'+u.path.rstrip('/'))


def reviewed_family(record):
    rules=json.loads((FOLDER/'model_release_evidence.json').read_text(encoding='utf-8'))['rules']
    return next((r for r in rules if r.get('family_key') and record.get('type_id')==r['type_id']
        and identity.norm_brand(record.get('brand'))==identity.norm_brand(r['brand'])
        and re.fullmatch(r.get('mpn_pattern','.*'),identity.norm_code(record.get('mpn')))
        and re.search(r['name_pattern'],record.get('name',''),re.I)),None)


def same_mpn_variant(record,product):
    """Compare variant dimensions before reusing a product with the same MPN.

    Some manufacturers reuse one model code across storage/RAM/colour options.
    A matching MPN alone must never merge those sellable variants.
    """
    from .catalog_structure import attributes as variant_attributes
    try:specs=json.loads(product.get('manual_specifications') or '{}')
    except (TypeError,ValueError):specs={}
    typeid=taxonomy.classify(product.get('name',''),product.get('subcategory') or '')[0]
    existing=variant_attributes({'type_id':typeid,'name':product.get('name'),'specs':specs})
    incoming=variant_attributes(record)
    fields={'Storage','Capacity','RAM','Color','Size','Display size','Display finish','Connectivity'}
    def normalized(field,value):
        value=identity.norm_text(value)
        if field in {'Storage','Capacity','RAM','Size','Display size'}:
            value=re.sub(r'\s+(?=(?:gb|tb|mb|kg|l|inches|inch|in)\b)', '', value)
        return value
    old={k:normalized(k,v) for k,v in existing.items() if k in fields and v}
    new={k:normalized(k,v) for k,v in incoming.items() if k in fields and v}
    overlap=set(old)&set(new)
    if any(old[k]!=new[k] for k in overlap):return False
    if not overlap or set(old)!=set(new):return None
    return True


def variant_attributes(record):
    from .catalog_structure import attributes as derive_attributes
    return derive_attributes(record)


def attach_metadata(cur,pid,record,identity_key=None,basis='manufacturer_identifier'):
    from .catalog_structure import describe
    meta=describe(record);taxon=taxonomy.TYPES[record['type_id']];fid=meta['model_id'];family=reviewed_family(record)
    cur.execute('INSERT INTO catalog_product_families(id,brand,name,type_id) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE name=VALUES(name)',[meta['family_id'],record['brand'],meta['family_name'][:255],taxon['id']])
    cur.execute('''INSERT INTO catalog_model_families(id,brand,name,type_id,created_at,family_id) VALUES (%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE name=VALUES(name),type_id=VALUES(type_id)''',
        [fid,record.get('brand','')[:190],meta['model_name'][:255],taxon['id'],bulk.utcnow(),meta['family_id']])
    cur.execute('''INSERT INTO catalog_type_assignments VALUES (%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE type_id=VALUES(type_id),taxonomy_version=VALUES(taxonomy_version),path_json=VALUES(path_json),reason=VALUES(reason),checked_at=VALUES(checked_at)''',
        [pid,taxon['id'],taxonomy.VERSION,bulk.packed(taxon['path']),record.get('classification_reason','reviewed classification')[:255],bulk.utcnow()])
    cur.execute('SELECT product_id FROM catalog_variant_links WHERE identity_key=%s',[identity_key or bulk.variant_identity(record)])
    found=cur.fetchone()
    if found and found['product_id']!=pid:raise ValueError('canonical_variant_already_linked')
    cur.execute('''INSERT INTO catalog_variant_links VALUES (%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE attributes_json=VALUES(attributes_json),identity_key=VALUES(identity_key),identity_basis=VALUES(identity_basis)''',
        [pid,fid,identity_key or bulk.variant_identity(record),bulk.packed(variant_attributes(record)),basis])
    if family:cur.execute('UPDATE catalog_variant_links SET family_id=%s WHERE product_id=%s',[fid,pid])


def audit_existing(apply_metadata=False):
    """Assess legacy visibility without changing it; taxonomy metadata is additive."""
    results=[];counts=Counter()
    with connect() as conn,conn.cursor() as cur:
        cur.execute('SELECT product_id FROM catalog_variant_links');already_mapped={r['product_id'] for r in cur.fetchall()}
        cur.execute('''SELECT p.*,c.name department,sc.name subcategory FROM products p
            JOIN categories c ON c.id=p.category_id LEFT JOIN categories sc ON sc.id=p.subcategory_id
            WHERE p.catalog_visible=TRUE AND p.deleted_at IS NULL ORDER BY p.id''')
        products=cur.fetchall()
        url_counts=Counter(canonical_url(p.get('product_url') or p.get('source_url')) for p in products if p.get('product_url') or p.get('source_url'))
        for p in products:
            typeid,reason=taxonomy.classify(p['name'],p.get('subcategory') or '')
            r={'name':p['name'],'brand':p.get('brand'),'mpn':p.get('mpn'),'gtin':p.get('gtin'),
               'url':p.get('product_url') or p.get('source_url'),'type_id':typeid,'classification_reason':reason,'attributes':{}}
            problems=[]
            if r['url'] and url_counts[canonical_url(r['url'])]>1:problems.append('duplicate_existing_variant_url')
            if not typeid:problems.append('unmapped_product_type')
            proof_kind=p.get('release_date_basis')
            year_only=not p.get('release_date') and p.get('release_date_precision')=='year' and p.get('release_year')
            if not p.get('release_date') and not year_only:problems.append('missing_verified_release_date')
            elif p.get('release_date') and not bulk.cutoff()<=p['release_date']<=date.today():problems.append('outside_release_window')
            elif year_only:
                start=date(int(p['release_year']),1,1);end=date(int(p['release_year']),12,31)
                if start>date.today() or end<bulk.cutoff():problems.append('outside_release_window')
                elif start<bulk.cutoff():problems.append('release_window_uncertain')
            if (p.get('release_date') or year_only) and proof_kind not in {'official_release_date','manufacturer_release','manufacturer_model_year','icecat_explicit_release','india_store_launch_year'}:
                problems.append('unsupported_release_evidence')
            if not identity.gtins(p.get('gtin')):problems.append('missing_gtin')
            image=FOLDER/'images'/str(p.get('image_url') or '').rsplit('/',1)[-1]
            if not p.get('image_url') or not image.is_file():problems.append('missing_local_image')
            try:specs=json.loads(p.get('manual_specifications') or '{}')
            except (TypeError,ValueError):specs={}
            if typeid and taxonomy.missing_attributes(typeid,specs):problems.append('missing_type_attributes')
            if apply_metadata and typeid:
                taxon=taxonomy.TYPES[typeid]
                cur.execute('INSERT INTO catalog_type_assignments(product_id,type_id,taxonomy_version,path_json,reason,checked_at) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE type_id=VALUES(type_id),taxonomy_version=VALUES(taxonomy_version),path_json=VALUES(path_json),reason=VALUES(reason),checked_at=VALUES(checked_at)',[p['id'],typeid,taxonomy.VERSION,bulk.packed(taxon['path']),reason])
            if apply_metadata and typeid and p['id'] not in already_mapped:
                key=bulk.digest('existing_variant|'+canonical_url(r['url'])) if r['url'] else bulk.digest('existing_id|'+p['id'])
                try:attach_metadata(cur,p['id'],r,key,'existing_retailer_variant')
                except ValueError:problems.append('duplicate_existing_variant_url')
            counts.update(problems)
            results.append({'product_id':p['id'],'name':p['name'],'type_id':typeid,'issues':problems,
                'proposed_action':'review' if any(x in problems for x in ('missing_verified_release_date','outside_release_window','missing_local_image','unsupported_release_evidence')) else 'retain'})
        if apply_metadata:conn.commit()
    report={'as_of':date.today().isoformat(),'visible_products':len(products),'issues':dict(counts),
            'visibility_changed':False,'products':results}
    private=bulk.ROOT/'backend'/'recovery';private.mkdir(exist_ok=True)
    (private/'existing-catalog-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {k:v for k,v in report.items() if k!='products'}


def quarantine_invalid_conditions(apply=False):
    """Hide explicit used/restricted-condition listings; preserve IDs and bids."""
    pattern=r'\b(?:pulled[ -]?out|refurbished|renewed|pre[ -]?owned|employee)\b|\bEMP$'
    with connect() as conn,conn.cursor() as cur:
        cur.execute('SELECT id,name FROM products WHERE catalog_visible=TRUE AND deleted_at IS NULL')
        invalid=[r for r in cur.fetchall() if re.search(pattern,r['name'],re.I)]
    if not apply:return {'proposed_hidden':len(invalid)}
    if not invalid:return {'hidden':0}
    backup=bulk.ROOT/'backend'/'recovery'/('quarantine-'+datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    backup.mkdir(parents=True)
    shutil.copy2(FOLDER/'all_products.csv',backup/'all_products.csv')
    (backup/'hidden_products.json').write_text(json.dumps(invalid,indent=2),encoding='utf-8')
    ids={r['id'] for r in invalid}
    with (FOLDER/'all_products.csv').open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames
        rows=[r for r in reader if importer.row_product_id(r) not in ids]
    if not rows:raise ValueError('Refusing an empty catalogue export')
    with connect() as conn,conn.cursor() as cur:
        cur.executemany('UPDATE products SET catalog_visible=FALSE,updated_at=NOW() WHERE id=%s',[(pid,) for pid in ids])
        conn.commit()
    exports(rows,fields)
    from .tantivy_search import invalidate
    invalidate()
    return {'hidden':len(ids),'reason':'explicit used condition or employee-only offer','backup':str(backup)}


def write_csv(path,fields,rows):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
    temp.replace(path)


def safe_photo(record):
    for url in record.get('image_sources',[]):
        if re.search(r'placeholder|no[-_]image|image[-_]not[-_]available',url,re.I):continue
        try:
            data=bulk.body(url,max_bytes=8_000_000)
            with Image.open(io.BytesIO(data)) as im:
                if min(im.size)<180 or max(im.size)>16000:continue
                im.load();im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((900,900))
                out=io.BytesIO();im.save(out,'WEBP',quality=84,method=1);content=out.getvalue()
                sha=hashlib.sha256(content).hexdigest();filename=sha[:24]+'.webp'
                (FOLDER/'images'/filename).write_bytes(content)
                return '/catalog-images/'+filename,{'image_source_url':url,'local_image':filename,'image_sha256':sha,'width':im.width,'height':im.height}
        except Exception:continue
    raise ValueError('image_download_or_decode_failed')


def exports(rows,fields):
    """Keep the checked-in CSV/XLSX deployment bundle in sync, additively."""
    write_csv(FOLDER/'all_products.csv',fields,rows)
    with (FOLDER/'category_plan.csv').open(encoding='utf-8-sig') as stream:plans=list(csv.DictReader(stream))
    wb=Workbook();wb.remove(wb.active);summaries=[];coverage=[];brands=[];years=[]
    for p in plans:
        code=p['department_code'];group=[r for r in rows if r['category_code']==code]
        write_csv(next(FOLDER.glob(code+'-*.csv')),fields,group)
        sheet=wb.create_sheet(code);sheet.append(fields)
        for r in group:sheet.append([r.get(k,'') for k in fields])
        sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
        summaries.append({'category_code':code,'department':p['department'],'products':len(group),'brands':len({r['brand'] for r in group}),'status':'VERIFIED_SUBSET' if group else 'NO_VERIFIED_PRODUCTS'})
        coverage.append({'category_code':code,'products':len(group),'with_price':sum(bool(r['official_price']) for r in group),
            'with_image':sum(bool(r['image_url']) for r in group),'with_specs':sum(bool(r['specifications_json']) for r in group),
            'with_store_source':sum(bool(r['product_url']) for r in group),'with_verified_release_date':sum(bool(r['release_date']) for r in group)})
        brands.extend({'category_code':code,'brand':b,'products':n} for b,n in sorted(Counter(r['brand'] for r in group).items()))
        years.extend({'category_code':code,'release_year':y,'products':n} for y,n in sorted(Counter(r['release_year'] or 'Unknown' for r in group).items()))
    for filename,data in [('master_summary.csv',summaries),('category_coverage.csv',coverage),('brand_summary.csv',brands),('release_year_summary.csv',years)]:write_csv(FOLDER/filename,list(data[0]),data)
    summary=wb.create_sheet('Summary');summary.append(list(summaries[0]))
    for r in summaries:summary.append(list(r.values()))
    temp=FOLDER/'master_catalogue.tmp.xlsx';wb.save(temp);temp.replace(FOLDER/'master_catalogue.xlsx')
    report_path=FOLDER/'verification_report.json'
    report=json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    report.setdefault('legacy_initial_scan',{'scanned':report.get('scanned'),'accepted_before_bulk':report.get('accepted'),
        'note':'Legacy rejection/listing-cutoff counts refer to the original collection, not subsequent bulk ingestion.'})
    report.update(accepted=len(rows),brands=dict(sorted(Counter(r['brand'] for r in rows).items())),
        categories=dict(sorted(Counter(r['department'] for r in rows).items())),with_exact_release_date=sum(bool(r['release_date']) for r in rows),
        bulk_ingestion_report='bulk_ingestion_report.json')
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def publish(limit=200,apply=False):
    catalog_metadata.ensure_schema(connect)
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT GET_LOCK('turacoz.bulk.catalog.publish',0) acquired")
        if not cur.fetchone()['acquired']:raise ValueError('Another bulk publication is running')
        try:return _publish(limit,apply)
        finally:cur.execute("SELECT RELEASE_LOCK('turacoz.bulk.catalog.publish')")


def _publish(limit=200,apply=False):
    """Eligible rows only. Dry-run unless explicitly applied; safe to repeat."""
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT * FROM catalog_ingestion_candidates WHERE state IN ('eligible','published') ORDER BY (state='eligible') DESC,id LIMIT %s",[limit]);candidates=cur.fetchall()
        cur.execute('''SELECT p.id,p.name,p.brand,p.mpn,p.gtin,p.product_url,p.source,p.manual_specifications,
            sc.name subcategory FROM products p LEFT JOIN categories sc ON sc.id=p.subcategory_id
            WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE''');existing=cur.fetchall()
        cur.execute('''SELECT l.product_id,l.identity_key FROM catalog_variant_links l
            JOIN products p ON p.id=l.product_id
            WHERE p.deleted_at IS NULL AND p.catalog_visible=TRUE''')
        links={r['identity_key']:r['product_id'] for r in cur.fetchall()}
    byurl=defaultdict(set);bygtin=defaultdict(set);bympn=defaultdict(set);byname=defaultdict(set)
    existing_by_id={p['id']:p for p in existing}
    for p in existing:
        if p['product_url']:byurl[canonical_url(p['product_url'])].add(p['id'])
        for g in identity.gtins(p['gtin']):bygtin[g.zfill(14)].add(p['id'])
        if p['mpn']:bympn[(identity.norm_brand(p['brand']),identity.norm_code(p['mpn']))].add(p['id'])
        byname[(identity.norm_brand(p['brand']),identity.norm_text(p['name']))].add(p['id'])
    counts=Counter();selected=[];newrows=[];proofs=[];photo_jobs=[];proposed_products=[]
    with (FOLDER/'all_products.csv').open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);rows=list(reader);fields=reader.fieldnames
    with (FOLDER/'category_plan.csv').open(encoding='utf-8-sig') as stream:departments={p['department_code']:p['department'] for p in csv.DictReader(stream)}
    existing_ids={p['id'] for p in existing}
    csv_ids={importer.row_product_id(row) for row in rows}
    batch_keys={}
    for candidate in candidates:
        r=json.loads(candidate['record_json'])
        # Accept exact Icecat content or a detailed India product listing.
        # Both routes still require independently validated release evidence,
        # a current India offer, a product-specific image and type attributes.
        icecat_content=bool(r.get('icecat_evidence'))
        if icecat_content:
            if (r.get('release_evidence') or {}).get('kind')!='icecat_explicit_release':
                counts['held_without_icecat_release_year']+=1;continue
            if not r.get('icecat_image_sources'):
                counts['held_without_icecat_image']+=1;continue
            if not r.get('icecat_specs') or len(r['icecat_specs'])<3:
                counts['held_without_icecat_details']+=1;continue
        else:
            if bulk.release_issues(r):
                counts['held_without_verified_release_year']+=1;continue
            if not r.get('image_sources'):
                counts['held_without_listing_image']+=1;continue
            listing_specs=r.get('specs') if isinstance(r.get('specs'),dict) else {}
            if len(listing_specs)<3:
                counts['held_without_listing_details']+=1;continue
        if taxonomy.is_accessory(r):
            counts['held_accessory_or_non_target']+=1;continue
        problems=bulk.issues(r)
        if problems:counts['held_by_current_validation']+=1;continue
        key=bulk.variant_identity(r)
        matches=set()
        if key in links:matches.add(links[key])
        matches.update(byurl.get(canonical_url(r['url']),set()))
        for g in identity.gtins(r.get('gtin')):matches.update(bygtin.get(g.zfill(14),set()))
        if len(matches)>1:counts['ambiguous_existing_identity']+=1;continue
        pid=next(iter(matches),None) or batch_keys.get(key)
        unresolved_mpn=False
        if not pid:
            for existing_id in bympn.get((identity.norm_brand(r['brand']),identity.norm_code(r.get('mpn'))),set()):
                match=same_mpn_variant(r,existing_by_id[existing_id])
                if match is True:matches.add(existing_id)
                elif match is None:unresolved_mpn=True
            if len(matches)>1:counts['ambiguous_existing_identity']+=1;continue
            pid=next(iter(matches),None)
        if not pid and byname.get((identity.norm_brand(r['brand']),identity.norm_text(r['name']))):
            counts['possible_existing_name_needs_review']+=1;continue
        if not pid and unresolved_mpn:
            counts['possible_existing_variant_needs_review']+=1;continue
        repairing=bool(pid and pid not in csv_ids and any(p['id']==pid and p['source']=='bulk_india' for p in existing))
        if not pid or repairing:
            taxon=taxonomy.TYPES[r['type_id']];row={k:'' for k in fields}
            name=r['name']
            if not re.search(taxon['pattern'],name,re.I):name=name+' '+taxon['path'][-1]
            content_specs=r.get('icecat_specs') if icecat_content else r.get('specs')
            content_description=(r.get('icecat_description') if icecat_content else r.get('description')) or name
            content_source_url=(r.get('icecat_evidence') or {}).get('url') if icecat_content else r['url']
            source_attribution=(
                'Icecat exact-model content (specifications, image and release date); '+r['source_id']+' India listing (INR price and market presence)'
                if icecat_content else
                r['source_id']+' India product listing (technical details, image, INR price and market presence); '
                +(r.get('release_evidence') or {}).get('kind','')+' release evidence'
            )
            verification_status='icecat_content_india_listing_price_image_verified' if icecat_content else 'india_store_listing_image_verified'
            row.update(category_code=taxon['legacy_code'],department=departments[taxon['legacy_code']],subcategory=taxon['path'][-1],product_type=taxon['path'][-1],
                product_name=name,manufacturer=r['brand'],brand=r['brand'],model=r.get('mpn') or (r.get('verified_model') or {}).get('name') or r['model'],manufacturer_part_number=r.get('mpn') or '',gtin=r.get('gtin') or '',
                description=content_description[:65000],specifications_json=bulk.packed(content_specs),product_url=r['url'],
                release_date=r.get('release_date') or '',release_date_precision=r['release_evidence']['precision'],release_year=str(r.get('release_year') or r['release_date'][:4]),official_price=str(r['price']),price_currency='INR',
                price_type='current_store_listed_price',price_market='India',price_source_url=r['url'],product_source_url=content_source_url,
                source_attribution=source_attribution,collected_on=r['checked_on'],verification_status=verification_status,
                notes=('Icecat product ID '+str((r.get('icecat_evidence') or {}).get('id') or '')+'; ' if icecat_content else 'India listing product content; ')+bulk.packed({'identity_basis':'gtin' if r.get('gtin') else 'brand_mpn_variant' if r.get('mpn') else 'verified_model_variant','release_evidence':r['release_evidence'],'icecat_product_id':(r.get('icecat_evidence') or {}).get('id')}))
            value='|'.join(row[k] for k in ('category_code','manufacturer','brand','model','product_name'))
            proposed_id=importer.stable_id('product',value)
            if repairing and pid!=proposed_id:counts['export_identity_conflict']+=1;continue
            pid=proposed_id
            if 'product_id' in row:row['product_id']=pid
            if apply:
                photo_jobs.append((row,r,candidate['id'],pid,repairing))
            newrows.append(row);counts['repaired_exports' if repairing else 'new_variants']+=1
            proposed_products.append({'candidate_id':candidate['id'],'product_name':row['product_name'],'brand':row['brand'],
                'model':row['model'],'product_type':row['product_type'],'source_id':r['source_id'],'product_url':r['url'],
                'release_date':row['release_date'],'release_year':row['release_year'],'release_evidence_kind':r['release_evidence']['kind'],
                'price_inr':row['official_price'],'specification_count':len(content_specs),'image_source_count':len(r.get('image_sources') or []),
                'gtin_present':bool(row['gtin'])})
        else:counts['existing_variant_matches']+=1
        batch_keys[key]=pid;selected.append((candidate,r,pid,key))
    if not apply:return {'mode':'dry-run',**dict(counts),'qualified_candidates':len(selected),'proposed_products':proposed_products}
    # Image hosts are paced independently. Fetch in a small bounded pool so a
    # large verified batch does not spend many minutes waiting on serial HTTP
    # timeouts; each image still passes the same byte, dimension and decode checks.
    failed_candidates=set();failed_rows=set()
    if photo_jobs:
        with ThreadPoolExecutor(max_workers=8) as pool:
            future_to_job={pool.submit(safe_photo,record):(row,record,candidate_id,pid,repairing)
                           for row,record,candidate_id,pid,repairing in photo_jobs}
            for completed,future in enumerate(as_completed(future_to_job),start=1):
                row,record,candidate_id,pid,repairing=future_to_job[future]
                try:row['image_url'],photo=future.result()
                except Exception:
                    failed_candidates.add(candidate_id);failed_rows.add(id(row))
                    counts['image_failed']+=1
                else:
                    proofs.append({'product_name':row['product_name'],'purchase_url':record['url'],'price':str(record['price']),'checked_on':record['checked_on'],
                        'store':record['source_id'],'variant_id':record['external_id'],'market_presence':'listed_in_india',
                        'market_presence_basis':'india_store_product_page','release_evidence':record['release_evidence'],**photo})
                if completed%50==0 or completed==len(photo_jobs):
                    print(f'Validated product images: {completed}/{len(photo_jobs)}',flush=True)
    if failed_candidates:
        selected=[item for item in selected if item[0]['id'] not in failed_candidates]
        newrows=[row for row in newrows if id(row) not in failed_rows]
        proposed_products=[product for product in proposed_products if product['candidate_id'] not in failed_candidates]
        for row,_,candidate_id,_,repairing in photo_jobs:
            if candidate_id in failed_candidates:
                counts['repaired_exports' if repairing else 'new_variants']-=1
    backup=bulk.ROOT/'backend'/'recovery'/('bulk-publication-'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));backup.mkdir(parents=True)
    for name in ('all_products.csv','availability_evidence.json','master_catalogue.xlsx'):shutil.copy2(FOLDER/name,backup/name)
    with connect() as conn,conn.cursor() as cur:
        cur.execute('SELECT * FROM products')
        with gzip.open(backup/'products.json.gz','wt',encoding='utf-8') as stream:json.dump(cur.fetchall(),stream,default=str)
    if newrows:
        batch=backup/'additions.csv';write_csv(batch,fields,newrows)
        importer.main(['--apply','--append-only','--csv',str(batch)])
        # Repeating publication after an interrupted export repairs the bundle.
        known_names={(identity.norm_brand(r['brand']),identity.norm_text(r['product_name'])) for r in rows}
        rows.extend(r for r in newrows if (identity.norm_brand(r['brand']),identity.norm_text(r['product_name'])) not in known_names)
    with connect() as conn,conn.cursor() as cur:
        for candidate,r,pid,key in selected:
            attach_metadata(cur,pid,r,key,'gtin' if r.get('gtin') else 'brand_mpn_variant' if r.get('mpn') else 'manufacturer_model_variant')
            cur.execute('''UPDATE products SET release_date_basis=IF(release_date IS NULL,%s,release_date_basis),
                release_date_precision=IF(release_date IS NULL,%s,release_date_precision),
                release_date=COALESCE(release_date,%s),release_year=COALESCE(release_year,%s),
                gtin=COALESCE(NULLIF(gtin,''),%s) WHERE id=%s''',[r['release_evidence']['kind'],r['release_evidence']['precision'],r.get('release_date') or None,int(r.get('release_year') or r['release_date'][:4]),r.get('gtin') or None,pid])
            if pid not in existing_ids:cur.execute("UPDATE products SET source='bulk_india',release_date_basis=%s WHERE id=%s",[r['release_evidence']['kind'],pid])
            cur.execute('''INSERT INTO catalog_retail_offers VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE product_id=VALUES(product_id),price=VALUES(price),availability=VALUES(availability),checked_at=VALUES(checked_at)''',
                [bulk.digest('offer|'+candidate['id']),candidate['id'],pid,r['source_id'],r.get('seller_sku','')[:190],r['url'],r['price'],'INR','listed_in_india',r['checked_on']])
            cur.execute("UPDATE catalog_ingestion_candidates SET state='published',existing_product_id=%s,identity_key=%s WHERE id=%s",[pid,key,candidate['id']])
        conn.commit()
    if newrows:exports(rows,fields)
    # Persist private date/GTIN enrichment for exact existing rows in the export too.
    by_csv_url={canonical_url(row['product_url']):row for row in rows}
    for _,r,_,_ in selected:
        row=by_csv_url.get(canonical_url(r['url']))
        if row:
            row['release_date']=row['release_date'] or r.get('release_date') or '';row['release_date_precision']=r['release_evidence']['precision']
            row['release_year']=row['release_year'] or str(r.get('release_year') or r['release_date'][:4]);row['gtin']=row['gtin'] or r.get('gtin','')
    if selected:exports(rows,fields)
    evidence=json.loads((FOLDER/'availability_evidence.json').read_text(encoding='utf-8'))
    names={e['product_name'] for e in evidence};evidence.extend(p for p in proofs if p['product_name'] not in names)
    (FOLDER/'availability_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    from .catalog_structure import rebuild as rebuild_structure
    rebuild_structure(connect)
    catalog_metadata.export_bundle(connect,FOLDER/'catalog_metadata.json')
    from .tantivy_search import invalidate
    invalidate()
    return {'mode':'applied',**dict(counts),'qualified_candidates':len(selected),'proposed_products':proposed_products,'backup':str(backup)}
