"""Model-level release research queue. No inferred or invented launch dates."""
from collections import Counter
import json
import re
from urllib.parse import quote_plus

from . import bulk_catalog as bulk, catalog_structure as structure, catalog_taxonomy as taxonomy
from .catalog_importer import connect

DOMAINS = {'apple':'apple.com/in/newsroom','samsung':'news.samsung.com/in',
    'noise':'gonoise.com/blogs','boat':'boat-lifestyle.com/blogs',
    'crucial':'investors.micron.com','intel':'intel.com','amd':'amd.com/en/newsroom',
    'hp':'hp.com','lenovo':'psref.lenovo.com','asus':'asus.com/in',
    'crompton':'crompton.co.in','orient electric':'orientelectric.com',
    'philips':'philips.co.in','sony':'sony.co.in','voltas':'voltas.com'}
PRIMARY_TYPES = {'smartphones','tablets','laptops','televisions','refrigerators','washers',
    'air_conditioners','dishwashers','freezers','microwaves','water_heaters','desktops',
    'monitors','cameras','projectors','printers','graphics_cards','processors','motherboards',
    'routers','ups'}
SECONDARY_TYPES = {'soundbars','speakers','headphones','earbuds','smartwatches','air_purifiers',
    'air_coolers','vacuum_cleaners','ram','ssds','hard_drives','network_switches'}


def build_queue():
    """Rank each model once; keep candidate IDs in SQL, compact summary in Git."""
    groups = {}; excluded = Counter()
    with connect() as conn, conn.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS catalog_release_verification_queue(
            id CHAR(64) PRIMARY KEY,brand VARCHAR(190) NOT NULL,type_id VARCHAR(60) NOT NULL,
            model VARCHAR(255) NOT NULL,priority INT NOT NULL,candidate_ids_json LONGTEXT NOT NULL,
            research_json LONGTEXT NOT NULL,status VARCHAR(24) NOT NULL DEFAULT 'pending',
            checked_at DATETIME NOT NULL,KEY idx_release_queue(priority,status)) ENGINE=InnoDB''')
        c.execute('''SELECT a.type_id,COUNT(*) n FROM catalog_type_assignments a JOIN products p ON p.id=a.product_id
            WHERE p.catalog_visible=TRUE AND p.deleted_at IS NULL GROUP BY a.type_id''')
        coverage = {r['type_id']:r['n'] for r in c.fetchall()}
        c.execute("SELECT id,record_json FROM catalog_ingestion_candidates WHERE state IN ('pending','eligible')")
        candidates = c.fetchall()
        for item in candidates:
            r = json.loads(item['record_json'])
            release_problems=bulk.release_issues(r)
            if not release_problems: continue
            product_problems=set(bulk.issues(r))
            invalid_product=product_problems & {'unmapped_product_type','product_type_mismatch',
                'non_product_accessory','not_new_condition','demonstration_unit','restricted_offer'}
            if invalid_product:
                excluded['product_type_or_condition_review']+=1;continue
            if not r.get('india_listing_evidence') or r.get('condition')!='new':
                excluded['not_current_new_india_listing']+=1;continue
            if taxonomy.is_accessory(r):
                excluded['accessory']+=1;continue
            if not r.get('type_id') or r['type_id'] not in taxonomy.TYPES:
                excluded['needs_product_type']+=1;continue
            if re.search(r'employee|telegram|partner deal|\bemp\b|healthify|marketplace|do not delete',r['name'],re.I):
                excluded['restricted_or_promotional_parent']+=1;continue
            meta=structure.describe(r);gid=meta['model_id']
            group=groups.setdefault(gid,{'id':gid,'brand':r['brand'],'type_id':r['type_id'],
                'model':meta['model_name'],'candidate_ids':[],'offer_urls':set(),
                'existing_type_count':coverage.get(r['type_id'],0)})
            group['candidate_ids'].append(item['id']);group['offer_urls'].add(r['url'])
        # This table is a materialized work queue, not an append-only history.
        # Remove groups that no longer qualify after a taxonomy or evidence
        # change so stale accessory and rejected-model rows cannot be researched.
        c.execute('DELETE FROM catalog_release_verification_queue')
        for group in groups.values():
            brand=group['brand'];model=group['model']
            domain=DOMAINS.get(brand.casefold())
            queries=[f'"{brand}" "{model}" launch release date',f'"{brand}" "{model}" India launch']
            if domain:queries.insert(0,f'site:{domain} "{model}" launch')
            type_bonus=25000 if group['type_id'] in PRIMARY_TYPES else 5000 if group['type_id'] in SECONDARY_TYPES else 0
            group['priority']=type_bonus+10000//(group['existing_type_count']+1)+min(500,len(group['candidate_ids'])*10)
            group['queries']=queries
            group['search_urls']=['https://www.google.com/search?q='+quote_plus(q) for q in queries]
            group['offer_urls']=sorted(group['offer_urls'])[:5]
            group['variants']=len(group['candidate_ids'])
            c.execute('''INSERT INTO catalog_release_verification_queue(id,brand,type_id,model,priority,candidate_ids_json,research_json,checked_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE
                priority=VALUES(priority),candidate_ids_json=VALUES(candidate_ids_json),research_json=VALUES(research_json),checked_at=VALUES(checked_at)''',
                [group['id'],brand,group['type_id'],model[:255],group['priority'],bulk.packed(group['candidate_ids']),
                 bulk.packed({k:v for k,v in group.items() if k!='candidate_ids'})])
        conn.commit()
    ranked=sorted(groups.values(),key=lambda g:(-g['priority'],-g['variants'],g['model']))
    result={'generated_at':bulk.utcnow().isoformat(),'rolling_cutoff':bulk.cutoff().isoformat(),
        'models_requiring_research':len(groups),'variants_covered':sum(g['variants'] for g in ranked),
        'excluded':dict(excluded),'by_type':dict(Counter(g['type_id'] for g in ranked)),
        'method':['Search exact manufacturer model once, then apply evidence only to matching variants.',
            'Use manufacturer press releases, model specifications and explicit Icecat release fields.',
            'Do not substitute page publication, sitemap modification, catalog-added or certification dates.',
            'Keep unresolved dates pending; do not invent a day from a year.',
            'Recheck exact India offers, variant specifications, identity and image before publishing.'],
        'next_models':[{k:v for k,v in g.items() if k!='candidate_ids'} for g in ranked[:100]]}
    (bulk.ROOT/'product_catalog'/'release_research_queue.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {k:v for k,v in result.items() if k not in {'next_models','by_type','method'}}
