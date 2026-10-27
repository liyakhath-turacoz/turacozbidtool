"""Bulk discover and verify India-market product candidates before publication."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend import bulk_catalog as bulk
from backend.catalog_importer import connect
from backend import catalog_publication

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['discover','collect','pages','enrich','enrich-index','icecat-images','releases','store-release-years','reprocess','revalidate-listings','audit','publish','report','verification-queue','search-index','variant-pages','manufacturer-pages','model-specs','quarantine-invalid'])
    parser.add_argument('--apply',action='store_true',help='Apply publication or additive taxonomy metadata (audit never changes visibility)')
    parser.add_argument('--sources',help='Comma-separated registry ids; default all sources relevant to the operation')
    parser.add_argument('--max-pages',type=int,default=20)
    parser.add_argument('--max-maps',type=int,default=25)
    parser.add_argument('--limit',type=int,default=200)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if min(args.max_pages,args.max_maps,args.limit,args.workers)<1:parser.error('limits must be positive')
    bulk.load_local_environment();bulk.initialize()
    selected=[s for s in bulk.registry() if not args.sources or s['id'] in args.sources.split(',')]
    if args.sources and set(args.sources.split(','))-{s['id'] for s in selected}:parser.error('Unknown source id')
    runid=str(uuid.uuid4());results={}
    with connect() as conn,conn.cursor() as cur:
        cur.execute('INSERT INTO catalog_ingestion_runs(id,started_at,status) VALUES (%s,%s,%s)',[runid,bulk.utcnow(),'running']);conn.commit()
    try:
        if args.operation in {'discover','collect','pages'}:
            kinds={'shopify','vtex'} if args.operation=='collect' else {'sitemap'}
            selected=[s for s in selected if s['kind'] in kinds]
            def work(source):
                if args.operation=='discover':return bulk.collect_sitemaps(source,args.max_maps)
                if args.operation=='pages':return bulk.collect_pages(source,args.limit,min(args.workers,4))
                if source['kind']=='vtex':return bulk.collect_vtex(source)
                return bulk.collect_shopify(source,args.max_pages)
            with ThreadPoolExecutor(max_workers=min(args.workers,8)) as pool:
                futures={pool.submit(work,s):s for s in selected}
                for future in as_completed(futures):
                    source=futures[future]
                    try:results[source['id']]=future.result()
                    except Exception as exc:results[source['id']]={'error':type(exc).__name__,'reason':str(exc)[:140] if isinstance(exc,ValueError) else 'Source unavailable; see source access report'}
                    print(source['id']+': '+bulk.packed(results[source['id']]),flush=True)
        elif args.operation=='verification-queue':
            from backend.catalog_verification import build_queue
            results=build_queue()
        elif args.operation=='search-index':
            from backend.tantivy_search import rebuild
            results=rebuild(connect)
        elif args.operation=='model-specs':results=bulk.apply_reviewed_model_specs()
        elif args.operation=='store-release-years':results=bulk.apply_india_store_launch_years(args.limit)
        elif args.operation=='variant-pages':results=bulk.enrich_india_variant_pages(args.limit)
        elif args.operation=='manufacturer-pages':results=bulk.enrich_manufacturer_pages(args.limit)
        elif args.operation=='quarantine-invalid':results=catalog_publication.quarantine_invalid_conditions(args.apply)
        elif args.operation=='enrich':results=bulk.enrich(args.limit,min(args.workers,8),args.sources.split(',') if args.sources else None)
        elif args.operation=='enrich-index':results=bulk.enrich_from_icecat_index(args.limit,min(args.workers,8))
        elif args.operation=='icecat-images':results=bulk.refresh_icecat_images(args.limit,min(args.workers,8))
        elif args.operation=='reprocess':results=bulk.reprocess(args.sources.split(',') if args.sources else None,args.limit)
        elif args.operation=='revalidate-listings':results=bulk.revalidate_india_listings()
        elif args.operation=='audit':results=catalog_publication.audit_existing(args.apply)
        elif args.operation=='publish':results=catalog_publication.publish(args.limit,args.apply)
        elif args.operation=='releases':results=bulk.apply_reviewed_releases()
        summary=bulk.report();summary['operation']=args.operation;summary['run_id']=runid;summary['source_results']=results
        output=ROOT/'product_catalog'/'bulk_ingestion_report.json';output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        status='partial' if any(isinstance(v,dict) and (v.get('error') or v.get('errors')) for v in results.values()) else 'completed'
        with connect() as conn,conn.cursor() as cur:
            cur.execute('UPDATE catalog_ingestion_runs SET completed_at=%s,status=%s,report_json=%s WHERE id=%s',[bulk.utcnow(),status,bulk.packed(summary),runid]);conn.commit()
        print(bulk.packed(summary),flush=True)
    except BaseException:
        with connect() as conn,conn.cursor() as cur:
            cur.execute('UPDATE catalog_ingestion_runs SET completed_at=%s,status=%s WHERE id=%s',[bulk.utcnow(),'interrupted',runid]);conn.commit()
        raise

if __name__=='__main__':main()
