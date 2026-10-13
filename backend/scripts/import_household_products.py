"""Fill household product types from configured verified recent sources."""
import argparse
import json
from pathlib import Path
import sys
import uuid

PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT))
from backend.main import db
from backend.product_sources import ImportService,ICECAT_CATEGORIES


def run(minimum=50,max_products=700,daily=False,adapter='icecat',full_index=False):
    service=ImportService(db)
    service.initialize()
    source=next(row for row in service.sources() if row['adapter']==adapter)
    # Only this manual run uses the selected index and targets; admin schedules
    # remain as configured. Source aliases and identities use the normal importer.
    types=[item for item in ICECAT_CATEGORIES if item not in {'Televisions','Laptops','Smartphones','Tablets'}]
    if adapter=='lg':
        from backend.lg_catalog import CATEGORIES
        types=list(CATEGORIES)
    elif adapter=='eprel':
        from backend.eprel_catalog import GROUPS
        types=list(GROUPS)
    filename='daily.index.csv.gz' if daily else 'files.index.csv.gz' if full_index else '1314.vertical.files.index.xml.gz'
    source={**source,'endpoint':source['endpoint'] if adapter!='icecat' else 'https://data.icecat.biz/export/freexml/EN/'+filename,
        'categories':types,
        'max_products':max_products,'minimum_per_type':minimum,'xml_workers':8}
    job_id=str(uuid.uuid4())
    try:
        with db() as conn,conn.cursor() as cursor:
            cursor.execute('SELECT id FROM product_import_sources WHERE id=%s FOR UPDATE',[source['id']])
            cursor.execute("SELECT id FROM product_import_jobs WHERE source_id=%s AND status IN ('queued','running')",[source['id']])
            if cursor.fetchone():raise RuntimeError('A job for this source is already queued or running; finish it first.')
            cursor.execute("INSERT INTO product_import_jobs (id,source_id,status,details_json,created_at,updated_at) VALUES (%s,%s,'queued',%s,UTC_TIMESTAMP(),UTC_TIMESTAMP())",[job_id,source['id'],json.dumps({'minimum_per_type':minimum,'index_url':source['endpoint']})])
        print('Import job:',job_id,flush=True)
        print('Source:',source['endpoint'],'Minimum per household type:',minimum,flush=True)
        service.run(job_id,source)
        job=next(row for row in service.jobs() if row['id']==job_id)
        print(json.dumps(job,default=str,indent=2),flush=True)
        return 0 if job['status']=='completed' else 1
    finally:service.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minimum',type=int,default=50,choices=range(1,501))
    parser.add_argument('--max-products',type=int,default=700,choices=range(1,2001))
    indexes=parser.add_mutually_exclusive_group()
    indexes.add_argument('--daily',action='store_true',help='Use only daily changes; default is the full household vertical.')
    indexes.add_argument('--full-index',action='store_true',help='Use the much larger full index across all product verticals.')
    parser.add_argument('--source',choices=['icecat','lg','eprel'],default='icecat')
    args=parser.parse_args();raise SystemExit(run(args.minimum,args.max_products,args.daily,args.source,args.full_index))
