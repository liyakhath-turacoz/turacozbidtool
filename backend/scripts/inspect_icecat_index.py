"""Download and count the accessible English Open Icecat index without importing products."""
import argparse
from collections import Counter
import csv
import gzip
import json
from pathlib import Path
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT))
from backend.configuration import load_local_environment
from backend.product_sources import fetch,ICECAT_CATEGORIES,icecat_index_rows


def inspect(daily=False,download_minutes=10,household=False):
    load_local_environment()
    url='https://data.icecat.biz/export/freexml/EN/'+('1314.vertical.files.index.xml.gz' if household else 'daily.index.csv.gz' if daily else 'files.index.csv.gz')
    path=fetch(url,'icecat',max_bytes=512*1024*1024,cache_seconds=24*3600,as_file=True,max_seconds=download_minutes*60,revalidate=True,
        download_progress=lambda size:print(f'Downloaded {size//1048576} MiB',flush=True))
    print(f'Index downloaded: {path.stat().st_size:,} bytes. Counting records...',flush=True)
    ids={str(code):item for item,codes in ICECAT_CATEGORIES.items() for code in codes}
    totals=Counter();live=Counter();candidates=Counter();brands={item:Counter() for item in ICECAT_CATEGORIES};records=0
    for row in icecat_index_rows(path):
        records+=1;item=ids.get(row.get('catid'))
        if item:
            totals[item]+=1
            if row.get('on_market')=='1':
                live[item]+=1
                if row.get('quality','').upper() not in {'REMOVED','NOEDITOR'}:
                    candidates[item]+=1;brands[item][row.get('m_supplier_name') or 'Unknown']+=1
        if records%1000000==0:print(f'Counted {records:,} records',flush=True)
    report={'as_of':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'source_url':url,'downloaded_bytes':path.stat().st_size,
        'index_records':records,'note':'English Open Icecat index entries accessible to this account; not the entire commercial Icecat database. Index dates do not establish release age.',
        'product_types':[{'product_type':item,'index_records':totals[item],'on_market':live[item],'discovery_candidates':candidates[item],
            'brands':dict(brands[item].most_common())} for item in ICECAT_CATEGORIES]}
    folder=PROJECT/'products'/'reports';folder.mkdir(parents=True,exist_ok=True)
    name='icecat-'+('household' if household else 'daily' if daily else 'full')+'-index-report.json'
    (folder/name).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='product_types'},indent=2),flush=True)
    for item in report['product_types']:print(item['product_type'],item['index_records'],item['on_market'],item['discovery_candidates'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    kind=parser.add_mutually_exclusive_group();kind.add_argument('--daily',action='store_true');kind.add_argument('--household',action='store_true')
    parser.add_argument('--download-minutes',type=int,choices=range(1,61),default=10)
    args=parser.parse_args();inspect(args.daily,args.download_minutes,args.household)
