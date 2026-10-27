"""Read LG India's public catalog; model identity and release evidence come from the manufacturer."""
import json
import re
import urllib.parse
from datetime import datetime,timezone

try:from .product_sources import fetch,is_recent,validate_url,cutoff
except ImportError:from product_sources import fetch,is_recent,validate_url,cutoff

SEARCH='https://lgcorporationproduction0fxcu0qx.org.coveo.com/rest/search/v2'
# IDs come from data-facets.inputCategoryId on the official category pages.
CATEGORIES={'Air conditioners':'CT52006744','Refrigerators':'CT52006709','Microwave ovens':'CT52006695','Washing machines':'CT52006634','Freezers':'CT53101137','Dishwashers':'CT52006645'}
FIELDS=['ec_model_release_date','ec_model_year','ec_model_id','ec_model_name','ec_model_url_path','ec_user_friendly_name','ec_sku',
    'ec_preorder_flag','ec_medium_image_addr','ec_small_image_addr','ec_filter_category_name','ec_model_status_code']


def normalize(raw,item):
    stamp=raw.get('ec_model_release_date');released=''
    if isinstance(stamp,(int,float)) and not isinstance(stamp,bool):
        try:released=datetime.fromtimestamp(stamp/1000,timezone.utc).date().isoformat()
        except (ValueError,OverflowError,OSError):pass
    elif isinstance(stamp,str):released=stamp
    model=str(raw.get('ec_model_name') or '').strip()
    title=str(raw.get('ec_user_friendly_name') or '').strip()
    year=str(raw.get('ec_model_year') or '').strip()
    path=raw.get('ec_model_url_path') or ''
    url=urllib.parse.urljoin('https://www.lg.com',path)
    if urllib.parse.urlparse(url).hostname!='www.lg.com' or not path:raise ValueError('Invalid LG product link')
    specs={'Model year':year} if re.fullmatch(r'20\d{2}',year) else {}
    image=raw.get('ec_medium_image_addr') or raw.get('ec_small_image_addr') or ''
    if image.startswith('/in/'):image='/content/dam/channel/wcms'+image
    return {'name':'LG '+model+' '+item.rstrip('s'),'brand':'LG','model':model,'mpn':model,'source_product_id':raw.get('ec_sku') or raw.get('ec_model_id'),
        'subcategory':item,'release_date':released,'release_date_basis':'lg_catalog_release_date','source_url':url,
        'source_attribution':'LG India official product catalog','image_url':urllib.parse.urljoin('https://www.lg.com',image) if image else '',
        'description':title,'highlights':specs,'on_market':raw.get('ec_model_status_code')=='ACTIVE' and raw.get('ec_preorder_flag')!='Y'}


def records(source,progress):
    validate_url(source['endpoint'],'lg')
    token=json.loads(fetch('https://www.lg.com/ncms/api/v1/coveo/token?locale=IN','lg',cache_seconds=60))['token']
    for item in source['categories']:
        if item in source.get('_completed_types',set()):continue
        category=CATEGORIES.get(item)
        if not category:progress('unsupported_catalog_category');continue
        seen=set()
        for offset in range(0,min(2000,max(200,source['max_products']*10)),200):
            if item in source.get('_completed_types',set()):break
            payload={'locale':'en-IN','searchHub':'IN-B2C-Listing','aq':f'@ec_locale_code=="IN" AND @ec_category_id=="{category}" AND @ec_model_status_code=="ACTIVE"',
                'numberOfResults':200,'firstResult':offset,'sortCriteria':'ec_model_release_date descending','fieldsToInclude':FIELDS}
            response=json.loads(fetch(SEARCH,'lg',cache_seconds=300,data=json.dumps(payload).encode(),request_headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}))
            for result in response.get('results',[]):
                if item in source.get('_completed_types',set()):break
                raw=result.get('raw') or {};model=raw.get('ec_model_name')
                if not model or model in seen:continue
                record=normalize(raw,item);allowed,reason=is_recent(record)
                # An old model relisted recently must not become a "new" product.
                model_year=raw.get('ec_model_year')
                if model_year and re.fullmatch(r'20\d{2}',str(model_year)) and int(model_year)<=cutoff().year:
                    progress('old_or_ambiguous_model_year');continue
                if not allowed:progress(reason);continue
                seen.add(model);yield record
            if offset+200>=response.get('totalCount',0):break
