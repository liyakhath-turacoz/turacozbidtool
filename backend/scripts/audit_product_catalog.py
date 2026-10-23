"""Write product age/count reports and optionally retire verified pre-2017 records."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import sys
from datetime import datetime,date

PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT))
from backend.main import db
from backend import catalog_filters

KNOWN_RELEASES=[
    ('Samsung','Galaxy Tab 3 SM-T3110',2013,'https://news.samsung.com/global/samsung-introduces-new-galaxy-tab-3-series'),
    ('Samsung','Galaxy Tab 4 SM-T330N',2014,'https://news.samsung.com/kr/삼성전자-엔터테인먼트-경험이-자유로워지는-태블'),
    ('Samsung','Galaxy Tab 4 SM-T331N',2014,'https://news.samsung.com/kr/삼성전자-엔터테인먼트-경험이-자유로워지는-태블'),
    ('Samsung','Galaxy Tab Active SM-T365',2014,'https://news.samsung.com/global/galaxy-tab-active-and-other-galaxy-tablets-in-the-logistics-and-transportation-business'),
    ('Samsung','Galaxy Tab Active2 SM-T397',2017,'https://news.samsung.com/us/samsung-advances-mobility-global-workforce-enhanced-galaxy-tab-active2-ruggedized-tablet-optimized-business/'),
    ('Samsung','Galaxy Tab S6 Lite SM-P610',2020,'https://news.samsung.com/us/galaxy-tab-s6-lite-create-learn-relax/'),
    ('Samsung','Galaxy Tab SM-T500',2020,'https://news.samsung.com/us/galaxy-tab-a7-availability/'),
]


def verified_legacy_year(brand,name):
    for expected,prefix,year,url in KNOWN_RELEASES:
        if brand==expected and name.startswith(expected+' '+prefix):return year,url
    return None,None


def audit(retire=False):
    folder=PROJECT/'products'/'reports';folder.mkdir(parents=True,exist_ok=True)
    before=catalog_filters.statistics(db)
    if not (folder/'catalog-before.json').exists():(folder/'catalog-before.json').write_text(json.dumps(before,default=str,indent=2),encoding='utf-8')
    verified=[];retired_count=0
    prior={}
    if (folder/'verified-old-products.csv').exists():
        with (folder/'verified-old-products.csv').open(encoding='utf-8-sig',newline='') as stream:prior={row['id']:row for row in csv.DictReader(stream)}
    with db() as conn,conn.cursor() as cursor:
        cursor.execute("SELECT id,name,brand,model,release_year,deleted_at FROM products WHERE deleted_at IS NULL OR release_date_basis='manufacturer_verified_year'")
        for row in cursor.fetchall():
            year,url=verified_legacy_year(row['brand'],row['name'])
            if year:
                if retire and row['deleted_at'] is None:
                    cursor.execute("UPDATE products SET release_year=%s,release_date_basis='manufacturer_verified_year',release_date_precision='year',source_url=%s WHERE id=%s",[year,url,row['id']])
                if year<2017:
                    if retire or row['deleted_at'] is not None:retired_count+=1
                    row.pop('deleted_at',None)
                    if row['id'] in prior:row['release_year']=prior[row['id']]['release_year']
                    verified.append({**row,'corrected_release_year':year,'age_years':date.today().year-year,'evidence_url':url})
        if retire:
            identifiers=[row['id'] for row in verified]+[row['id'] for row in before.get('older_products',[]) if row['release_year'] and row['release_year']<2017]
            identifiers=list(dict.fromkeys(identifiers))
            if identifiers:
                marks=','.join(['%s']*len(identifiers))
                cursor.execute(f'SELECT * FROM products WHERE id IN ({marks})',identifiers)
                snapshot=folder/('pre-2017-backup-'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.json.gz')
                with gzip.open(snapshot,'wt',encoding='utf-8') as stream:json.dump(cursor.fetchall(),stream,default=str)
                cursor.execute(f"SELECT id FROM bid_requests WHERE product_id IN ({marks}) AND status='active' FOR UPDATE",identifiers)
                requests=[row['id'] for row in cursor.fetchall()]
                for identifier in requests:
                    cursor.execute("UPDATE bids SET status='expired',updated_at=UTC_TIMESTAMP() WHERE bid_request_id=%s AND status IN ('active','updated')",[identifier])
                    cursor.execute("UPDATE bid_requests SET status='cancelled',updated_at=UTC_TIMESTAMP() WHERE id=%s",[identifier])
                cursor.execute(f"UPDATE products SET status='deleted',deleted_at=UTC_TIMESTAMP(),updated_at=UTC_TIMESTAMP() WHERE id IN ({marks}) AND deleted_at IS NULL",identifiers)
    with (folder/'verified-old-products.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=['id','name','brand','model','release_year','corrected_release_year','age_years','evidence_url']);writer.writeheader();writer.writerows(verified)
    report=catalog_filters.statistics(db)
    (folder/'product-statistics.json').write_text(json.dumps(report,default=str,indent=2),encoding='utf-8')
    (folder/'product-statistics.csv').write_text(catalog_filters.statistics_csv(report),encoding='utf-8')
    old=report['older_products']
    with (folder/'older-than-three-years-or-unconfirmed-boundary.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        fields=['id','name','brand','product_type','release_year','release_date','release_date_basis','reported_age_years','age_confidence'];writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(old)
    lines=['# Product catalog audit','',f"As of {report['as_of']}: **{report['total']:,} available product/SKU records**.",'',f"Verified pre-2017 variants identified: **{len(verified)}**; retired: **{retired_count}**. Original rows were backed up privately before retirement and bidding history is retained.",'',report['count_note'],'','## Product types and reported release years','','| Category | Product type | '+ ' | '.join(str(row['release_year'] or 'Unknown') for row in report['years'])+' | Total |','|---|---|'+ '---:|'*(len(report['years'])+1)]
    for row in report['categories']:
        years=[next((item['count'] for item in report['category_years'] if item['category']==row['category'] and item['product_type']==row['product_type'] and item['release_year']==year['release_year']),0) for year in report['years']]
        lines.append('| '+row['category']+' | '+row['product_type']+' | '+' | '.join(map(str,years))+' | '+str(row['count'])+' |')
    lines+=['','## Brands','','| Brand | Product records |','|---|---:|']+['| '+str(row['brand'])+' | '+str(row['count'])+' |' for row in report['brands']]
    lines+=['','## Model codes by reported release year','',f"**{report['model_codes']:,} distinct brand/model codes** across the available catalog. Configuration variants are counted separately in product totals.",'','| Reported year | Product records | Distinct brand/model codes | Verified release records |','|---|---:|---:|---:|']+['| '+str(row['release_year'] or 'Unknown')+' | '+str(row['count'])+' | '+str(row['model_codes'])+' | '+str(row['verified_records'])+' |' for row in report['years']]
    lines+=['',f"**{report['unverified_legacy_years']:,} records have unverified legacy release years.** Their exact ages cannot be certified from the existing bundle. The older-products CSV distinguishes confirmed release information from reported catalog years."]
    lines+=['','## Older records and date confidence','',f"{len(old)} remaining records have a reported date older than the current three-year cutoff, or an unconfirmed 2023 boundary date. They are listed in `products/reports/older-than-three-years-or-unconfirmed-boundary.csv`.",'','Legacy catalog years are not automatically treated as verified launch years. Exact-age filtering for new imports uses explicit source release dates or dated official launch announcements. Unknown or ambiguous boundary dates are skipped.','',f"Verified retired variants and source evidence: `products/reports/verified-old-products.csv`. Full category, year and category-brand counts: `products/reports/product-statistics.csv`.",'','## Verified old model evidence','', '[Samsung Galaxy Tab 3 announcement (2013)](https://news.samsung.com/global/samsung-introduces-new-galaxy-tab-3-series). Galaxy Tab 4 variants were released in 2014, documented by [Samsung Korea](https://news.samsung.com/kr/%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90-%EC%97%94%ED%84%B0%ED%85%8C%EC%9D%B8%EB%A8%BC%ED%8A%B8-%EA%B2%BD%ED%97%98%EC%9D%B4-%EC%9E%90%EC%9C%A0%EB%A1%9C%EC%9B%8C%EC%A7%80%EB%8A%94-%ED%83%9C%EB%B8%94).']
    (folder/'catalog-audit.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Available products:',report['total'],'Verified pre-2017 variants:',len(verified),'Older/uncertain boundary records:',len(old))
    print('Detailed reports: products/reports')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--retire-before-2017',action='store_true');args=parser.parse_args();audit(args.retire_before_2017)
