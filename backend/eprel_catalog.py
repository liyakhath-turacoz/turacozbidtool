"""Public EU EPREL records with manufacturer-declared first market dates."""
import itertools
import json
from datetime import date,datetime,timezone
from zoneinfo import ZoneInfo

try:from .product_sources import fetch,is_recent,validate_url
except ImportError:from product_sources import fetch,is_recent,validate_url

GROUPS={'Ovens':'ovens','Freezers':'refrigeratingappliances2019','Refrigerators':'refrigeratingappliances2019',
    'Dishwashers':'dishwashers2019','Washing machines':'washingmachines2019','Tumble dryers':'tumbledryers20232534'}


def source_date(value):
    if not isinstance(value,list) or len(value)!=3:return ''
    try:return date(*value).isoformat()
    except (ValueError,TypeError):return ''


def normalize(raw,item):
    first=raw.get('onMarketFirstStartDate') or raw.get('onMarketStartDate')
    released=source_date(first);ended=source_date(raw.get('onMarketEndDate'))
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    active=raw.get('status')=='PUBLISHED' and not raw.get('blocked') and (not ended or ended>today)
    model=str(raw.get('modelIdentifier') or '').strip();brand=str(raw.get('supplierOrTrademark') or '').strip()
    specs={'Declared market':'EU / EEA'}
    for key,label,unit in [('capFreezeNet','Freezer capacity','L'),('capRefrNet','Fridge net capacity','L'),('noise','Noise level','dB'),
        ('ratedCapacity','Rated capacity',''),('energyConsAnnual','Annual energy consumption','kWh'),('dimensionHeight','Height','cm'),
        ('dimensionWidth','Width','cm'),('dimensionDepth','Depth','cm')]:
        if raw.get(key) is not None:specs[label]=f'{raw[key]} {unit}'.strip()
    energy=raw.get('energyClass')
    if energy:specs['Energy efficiency class']=str(energy).replace('P','+')
    for index,cavity in enumerate(raw.get('cavities') or [],1):
        if cavity.get('volume') is not None:specs[f'Cavity {index} volume']=f"{cavity['volume']} L"
        if cavity.get('heatSourceType'):specs['Heat source']=str(cavity['heatSourceType']).replace('_',' ').title()
    identifier=str(raw.get('eprelRegistrationNumber') or '')
    updated=raw.get('publishedOnDateTS')
    return {'name':f'{brand} {model} {item.rstrip("s")}','brand':brand,'model':model,'mpn':model,'source_product_id':identifier,
        'subcategory':item,'release_date':released,'release_date_basis':'eprel_first_eu_market_date','on_market':active,
        'source_url':f'https://eprel.ec.europa.eu/screen/product/{GROUPS[item]}/{identifier}',
        'source_attribution':'EU EPREL; manufacturer-declared first EU/EEA market date','highlights':specs,
        'source_updated_at':datetime.fromtimestamp(updated/1000,timezone.utc).isoformat() if isinstance(updated,(int,float)) else '',
        'image_url':''}


def category_records(source,item,progress):
    group=GROUPS[item];seen=set()
    headers={'Origin':'https://eprel.ec.europa.eu','Referer':f'https://eprel.ec.europa.eu/screen/product/{group}','Accept':'application/json',
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'}
    for page in range(1,21):
        if item in source.get('_completed_types',set()):return
        url=f'https://eprel.ec.europa.eu/api/products/{group}?_page={page}&_limit=100&sort0=onMarketStartDateTS&order0=DESC&sort1=energyClass&order1=DESC'
        payload=json.loads(fetch(url,'eprel',max_bytes=8*1024*1024,cache_seconds=300,request_headers=headers))
        rows=payload.get('hits') or []
        for raw in rows:
            if item in source.get('_completed_types',set()):return
            if item in {'Freezers','Refrigerators'}:
                freezer=raw.get('capRefrNet')==0 and (raw.get('capFreezeNet') or 0)>0
                if freezer!=(item=='Freezers'):continue
            if raw.get('orgVerificationStatus')!='VERIFIED':progress('unverified_supplier');continue
            record=normalize(raw,item);allowed,reason=is_recent(record)
            if not allowed:progress(reason);continue
            key=(record['brand'].casefold(),record['model'].casefold())
            if not record['source_product_id'] or key in seen:continue
            seen.add(key);yield record
        if len(rows)<100:return


def records(source,progress):
    validate_url(source['endpoint'],'eprel')
    generators=[category_records(source,item,progress) for item in source['categories'] if item in GROUPS and item not in source.get('_completed_types',set())]
    # Share the write allowance across selected categories.
    for group in itertools.zip_longest(*generators):
        for record in group:
            if record is not None:yield record
