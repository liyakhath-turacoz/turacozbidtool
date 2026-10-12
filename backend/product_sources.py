"""Bounded product-source adapters and durable, admin-controlled import schedules."""
import asyncio
import base64
import csv
import gzip
import hashlib
import io
import ipaddress
import json
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from . import catalog_filters as catalog
    from .catalog_importer import stable_id,category_id
    from .manufacturer_sources import MANUFACTURERS
except ImportError:
    import catalog_filters as catalog
    from catalog_importer import stable_id,category_id
    from manufacturer_sources import MANUFACTURERS

ROOT=Path(__file__).resolve().parent.parent
CACHE=ROOT/'products'/'tmp'/'source-imports'
DEFAULTS=[
    ('icecat','Open Icecat XML','icecat','https://data.icecat.biz/export/freexml/EN/daily.index.csv.gz',['Ovens','Refrigerators','Air conditioners','Microwave ovens','Televisions','Washing machines','Dishwashers','Freezers']),
    ('techapi','TechAPI','techapi','https://gettechapi.github.io/TechAPI/v1',['Smartphones','Tablets','Laptops','Monitors','Smartwatches']),
]
DEFAULTS += [(key,info['brand']+' official announcements',key,info['url'],info['types']) for key,info in MANUFACTURERS.items()]
ICECAT_CATEGORIES={'Ovens':[2286],'Refrigerators':[1873,1912,4964],'Freezers':[1322],'Microwave ovens':[1325],'Air conditioners':[1176,2723,2724],'Washing machines':[1331],'Dishwashers':[1324],'Televisions':[1302,1345,1584,2344,7206],'Laptops':[151],'Smartphones':[1893],'Tablets':[897]}
TECH_RESOURCES={'Smartphones':'smartphones','Tablets':'tablets','Laptops':'laptops','Monitors':'monitors','Smartwatches':'watches','Graphics cards (GPUs)':'gpus','Processors (CPUs)':'cpus'}


def cutoff(today=None):
    today=today or datetime.now(ZoneInfo('Asia/Kolkata')).date()
    try:return today.replace(year=today.year-3)
    except ValueError:return today.replace(year=today.year-3,day=28)


def parse_date(value):
    raw=str(value or '').strip()
    if not raw:return None,'unknown'
    if re.fullmatch(r'\d{14}',raw):raw=raw[:8]
    for pattern,length,precision in [('%Y-%m-%d',10,'day'),('%Y%m%d',8,'day'),('%Y-%m',7,'month'),('%Y%m',6,'month'),('%Y',4,'year')]:
        try:
            if len(raw)==length or (precision=='day' and len(raw)>length and raw[length:length+1] in ['T',' ']):return datetime.strptime(raw[:length],pattern).date(),precision
        except ValueError:pass
    for pattern in ('%B %d, %Y','%b %d, %Y','%d %B %Y','%Y, %B %d','%Y, %B','%B %Y'):
        try:return datetime.strptime(raw.replace('Released ','').strip(),pattern).date(),'month' if '%d' not in pattern else 'day'
        except ValueError:pass
    return None,'unknown'


def is_recent(record):
    released,precision=parse_date(record.get('release_date'))
    if not released:return False,'missing_release_date'
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date()
    if precision=='year':
        if released.year<today.year-2:return False,'ambiguous_or_old_release_year'
        if released.year>today.year:return False,'future_release'
    elif released>today:return False,'future_release'
    elif released<cutoff():return False,'older_than_three_years'
    if record.get('on_market') is False:return False,'discontinued'
    return True,''


def next_run(source,now=None):
    now=now or datetime.now(timezone.utc)
    local=now.astimezone(ZoneInfo(source.get('timezone') or 'Asia/Kolkata'))
    kind=source.get('schedule_type','manual')
    if not source.get('enabled') or kind=='manual':return None
    if kind=='hourly':return (now+timedelta(hours=int(source.get('interval_hours') or 1))).replace(tzinfo=None)
    if kind=='daily':
        hour,minute=map(int,(source.get('at_time') or '09:00').split(':'))
        due=local.replace(hour=hour,minute=minute,second=0,microsecond=0)
        if due<=local:due+=timedelta(days=1)
    elif kind=='fixed':
        value=source.get('run_at')
        if not value:return None
        due=datetime.fromisoformat(str(value)).replace(tzinfo=local.tzinfo)
        if due<=local:return None
    else:raise ValueError('Unknown schedule type')
    return due.astimezone(timezone.utc).replace(tzinfo=None)


def validate_url(url,adapter):
    parsed=urllib.parse.urlparse(url)
    if parsed.username or parsed.password or parsed.fragment:raise ValueError('Use a source URL without credentials or fragments')
    host=(parsed.hostname or '').lower()
    domains={'icecat':{'data.icecat.biz'},'techapi':{'gettechapi.github.io','techapi.dev'},'samsung':{'news.samsung.com','www.samsung.com'},'oppo':{'www.oppo.com','oppo.com'}}
    domains.update({key:set(info['domains']) for key,info in MANUFACTURERS.items()})
    if adapter in domains and (parsed.scheme!='https' or host not in domains[adapter]):raise ValueError('This adapter requires its official HTTPS source domain')
    if parsed.scheme!='https' or parsed.port not in {None,443}:raise ValueError('Use a public HTTPS source URL')
    try:addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    except OSError as error:raise ValueError('The source hostname could not be resolved') from error
    for address in addresses:
        if not ipaddress.ip_address(address[4][0]).is_global:raise ValueError('Private or reserved network sources are not allowed')


class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self,adapter):self.adapter=adapter
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        validate_url(newurl,self.adapter)
        if urllib.parse.urlparse(request.full_url).hostname!=urllib.parse.urlparse(newurl).hostname:
            request.remove_header('Authorization')
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def fetch(url,adapter,max_bytes=32*1024*1024,cache_seconds=3600):
    validate_url(url,adapter);CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.cache')
    if path.exists() and time.time()-path.stat().st_mtime<cache_seconds:return path.read_bytes()
    headers={'User-Agent':'TuracozCatalog/1.0','Accept':'application/json,text/html,application/xml,*/*'}
    if adapter=='icecat':
        user=os.getenv('ICECAT_USERNAME','');password=os.getenv('ICECAT_PASSWORD','')
        if not user or not password:raise ValueError('Configure ICECAT_USERNAME and ICECAT_PASSWORD in private .env')
        headers['Authorization']='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    started=time.monotonic();chunks=[];size=0
    with urllib.request.build_opener(Redirects(adapter)).open(urllib.request.Request(url,headers=headers),timeout=30) as response:
        while True:
            chunk=response.read(64*1024)
            if not chunk:break
            size+=len(chunk)
            if size>max_bytes:raise ValueError('Source response exceeds the configured download limit')
            if time.monotonic()-started>180:raise TimeoutError('Source download exceeded three minutes')
            chunks.append(chunk)
    data=b''.join(chunks)
    temporary=path.with_suffix('.'+uuid.uuid4().hex+'.tmp');temporary.write_bytes(data);temporary.replace(path)
    return data


def json_fetch(url,adapter):return json.loads(fetch(url,adapter))


def source_timestamp(value):
    raw=str(value or '').strip()
    if not raw:return None
    try:
        if re.fullmatch(r'\d{14}',raw):return datetime.strptime(raw,'%Y%m%d%H%M%S')
        stamp=datetime.fromisoformat(raw.replace('Z','+00:00'))
        return stamp.astimezone(timezone.utc).replace(tzinfo=None) if stamp.tzinfo else stamp
    except ValueError:return None


def normalize_tech(record,item,url):
    specs={}
    for field,label,unit in [('ram_gb','RAM','GB'),('battery_mah','Battery capacity','mAh'),('os','Operating system',''),('charging_wired_w','Charging power','W')]:
        value=record.get(field)
        if value is not None:specs[label]=f'{value} {unit}'.strip()
    storage=record.get('storage_options_gb') or ([record.get('storage_gb')] if record.get('storage_gb') else [])
    if storage:specs['Storage']=', '.join(f'{val} GB' for val in storage)
    display=record.get('display') or {}
    for field,label,unit in [('size_inch','Display diagonal','inches'),('resolution','Display resolution',''),('refresh_hz','Refresh rate','Hz'),('type','Display technology','')]:
        if display.get(field) is not None:specs[label]=f'{display[field]} {unit}'.strip()
    soc=record.get('soc') or record.get('cpu') or {}
    if isinstance(soc,dict) and soc.get('name'):specs['Processor']=soc['name']
    brand=record.get('brand') or record.get('manufacturer') or {}
    brand=brand.get('name','') if isinstance(brand,dict) else str(brand)
    return {'name':record.get('name'),'brand':brand,'model':record.get('name'),'subcategory':item,'mpn':record.get('mpn') or '',
        'source_product_id':record.get('slug') or str(record.get('id')),'release_date':record.get('release_date'),'release_date_basis':'source_release_date',
        'image_url':record.get('image_url') or '', 'highlights':specs,'source_url':url,'source_attribution':'TechAPI / CC-BY-SA 4.0',
        'verified':record.get('verified'),'description':record.get('description') or ''}


def tech_records(source,progress):
    base=source['endpoint'].rstrip('/');limit=source['max_products'];accepted=0;attempts=0
    for item in source['categories']:
        resource=TECH_RESOURCES.get(item)
        if not resource:continue
        response=json_fetch(base+'/'+resource+'/index.json','techapi')
        candidates=response.get('results',[]) if isinstance(response,dict) else response
        # Latest named releases first; detail release_date remains the final gate.
        candidates.sort(key=lambda row:max([int(year) for year in re.findall(r'20(?:2[3-9])',str(row))] or [0]),reverse=True)
        for row in candidates:
            if attempts>=max(limit*8,200) or accepted>=limit:return
            attempts+=1
            slug=row.get('slug')
            if not slug:continue
            url=base+'/'+resource+'/'+urllib.parse.quote(slug,safe='')+'/index.json'
            try:
                record=normalize_tech(json_fetch(url,'techapi'),item,url)
                if record.get('verified') is False:progress('unverified_source_record');continue
                allowed,reason=is_recent(record)
                if not allowed:progress(reason);continue
                accepted+=1;yield record
            except (ValueError,urllib.error.HTTPError,TimeoutError,OSError):progress('unavailable_source_record')


def icecat_xml(row,item):
    path=str(row['path']).lstrip('/')
    if not path.startswith('export/freexml/'):raise ValueError('Unexpected Icecat XML path')
    url='https://data.icecat.biz/'+path
    root=ET.fromstring(fetch(url,'icecat',max_bytes=5*1024*1024))
    product=root.find('.//Product')
    if product is None:raise ValueError('Icecat response contains no product')
    released=product.attrib.get('ReleaseDate') or product.findtext('ReleaseDate')
    supplier=product.find('Supplier');brand=supplier.attrib.get('Name','') if supplier is not None else row.get('m_supplier_name','')
    specs={};features=[]
    for feature in product.findall('ProductFeature'):
        name_node=feature.find('./Feature/Name')
        name=name_node.attrib.get('Value','') if name_node is not None else ''
        val=feature.attrib.get('Presentation_Value') or feature.attrib.get('LocalValue') or feature.attrib.get('Value','')
        if name and val:specs[name]=val;features.append({'name':name,'value':val})
    description=product.find('ProductDescription');image=product.attrib.get('HighPic') or row.get('high_pic','')
    return {'name':product.attrib.get('Title') or f"{brand} {row.get('model_name') or row['prod_id']}",'brand':brand,'model':row.get('model_name') or row['prod_id'],
        'mpn':product.attrib.get('Prod_id') or row['prod_id'],'source_product_id':row['product_id'],'release_date':released,'release_date_basis':'icecat_release_date',
        'catalog_added_at':row.get('Date_Added'),'subcategory':item,'source_updated_at':row['updated'],'source_url':url,'source_attribution':'Specs Icecat; data supplied AS IS',
        'gtin':row.get('ean_upc','').replace(';',','),'image_url':image,'highlights':specs,'technical_specifications':[{'name':'Technical specifications','features':features}],
        'description':description.attrib.get('LongDesc','') if description is not None else '', 'on_market':row.get('on_market')=='1'}


def icecat_records(source,progress):
    ids={str(identifier):item for item in source['categories'] for identifier in ICECAT_CATEGORIES.get(item,[])}
    candidates=[];limit=source['max_products']
    # Daily discovery is the default; admins may configure the full index for a broader scan.
    raw=fetch(source['endpoint'],'icecat',max_bytes=256*1024*1024,cache_seconds=24*3600)
    with gzip.open(io.BytesIO(raw),'rt',encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream,delimiter='\t'):
            item=ids.get(row.get('catid'))
            if item and row.get('on_market')=='1' and row.get('quality','').upper() not in {'REMOVED','NOEDITOR'}:
                candidates.append((item,row))
    # Index-added date is a discovery hint only, never proof of release age.
    candidates.sort(key=lambda pair:(pair[1].get('Date_Added',''),pair[1].get('updated','')),reverse=True)
    per_type=max(1,limit//max(1,len(ids)));accepted=0;counts={};attempts=0
    for item,row in candidates:
        if accepted>=limit or attempts>=max(200,limit*10):break
        if counts.get(item,0)>=max(1,limit//max(1,len(source['categories']))):continue
        attempts+=1
        try:
            record=icecat_xml(row,item);allowed,reason=is_recent(record)
            if not allowed:progress(reason);continue
            accepted+=1;counts[item]=counts.get(item,0)+1;yield record
        except (ET.ParseError,ValueError,urllib.error.HTTPError,TimeoutError,OSError):progress('unavailable_source_record')


class Page(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True);self.links=[];self.meta={};self.scripts=[];self.parts=[];self.title='';self.tag='';self.script='';self.skip=0
        self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);self.tag=tag
        if tag=='a' and attrs.get('href'):self.links.append(attrs['href'])
        if tag=='meta':self.meta[attrs.get('property') or attrs.get('name') or '']=attrs.get('content','')
        if tag=='time' and attrs.get('datetime'):self.meta.setdefault('time',attrs['datetime'])
        if tag=='script':self.script='';self.skip+=1
        if tag=='style':self.skip+=1
    def handle_endtag(self,tag):
        if tag=='script':self.scripts.append(self.script)
        if tag in {'script','style'}:self.skip=max(0,self.skip-1)
        self.tag=''
    def handle_data(self,data):
        if self.tag=='script' or self.skip:self.script+=data
        else:
            self.parts.append(data.strip())
            if self.tag=='title':self.title+=data
    @property
    def text(self):return ' '.join(part for part in self.parts if part)


def article_release(article,published):
    """Prefer stated availability dates; an announcement alone does not prove release."""
    publication,_=parse_date(published)
    if not publication:return '', 'unknown'
    month=r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    dates=[]
    for match in re.finditer(r'(?:availability\s+(?:beginning|starting)|available\s+(?:starting|from|beginning)|(?:go|goes)\s+on\s+sale|sales\s+(?:start|begin))[^.;]{0,45}?\b('+month+r')\.?\s+(\d{1,2})(?:,?\s+(20\d{2}))?',article.text,re.I):
        value,precision=parse_date(f"{match[1][:3].title()} {match[2]}, {match[3] or publication.year}")
        if value:dates.append(value)
    if dates:return max(dates).isoformat(),'manufacturer_availability'
    if re.search(r'\b(?:now available|available now|available for (?:purchase|INR)|available at (?:select|retail)|available across|starting today|on sale now)\b',article.text,re.I):
        return publication.isoformat(),'manufacturer_launch_article'
    return '', 'unknown'


def manufacturer_records(source,progress):
    adapter=source['adapter'];base=source['endpoint'];brand=MANUFACTURERS[adapter]['brand']
    if adapter not in {'samsung','oppo'}:
        yield from company_records(source,progress)
        return
    page=Page(fetch(base,adapter,max_bytes=8*1024*1024).decode('utf-8',errors='replace'))
    links=[];hints={}
    if adapter=='samsung':
        links=[link for link in page.links if re.search(r'/in/(?:[^/]*?(?:launches|introduces|unveils)[^/]*)$',link)]
        if page.meta.get('date') and re.search(r'\b(?:launches|introduces|unveils)\b',page.meta.get('og:title',''),re.I):links.insert(0,base)
    else:
        # OPPO renders its press list from the newsroom JSON model.
        links=[urllib.parse.urljoin(base,link) for link in page.links if '/in/newsroom/press/' in link and link.rstrip('/')!=base.rstrip('/')]
        for script in page.scripts:
            links += re.findall(r'https://www\.oppo\.com/in/newsroom/(?:press|stories)/[^"\s<>]+',script)
            for raw in re.findall(r'\{[^{}]*"page_url"\s*:\s*"in/newsroom/press/[^"\s]+"[^{}]*\}',script):
                try:
                    metadata=json.loads(raw);url='https://www.oppo.com/'+metadata['page_url'];links.append(url)
                    hints[url]={'title':metadata.get('title'),'published':datetime.fromtimestamp(int(metadata['sort_date']),timezone.utc).date().isoformat() if metadata.get('sort_date') else ''}
                except (ValueError,KeyError):pass
    for url in list(dict.fromkeys(links))[:source['max_products']*3]:
        try:
            article=Page(fetch(url,adapter,max_bytes=8*1024*1024).decode('utf-8',errors='replace'))
            title=article.meta.get('og:title') or hints.get(url,{}).get('title') or article.title
            published=article.meta.get('article:published_time') or article.meta.get('date') or hints.get(url,{}).get('published') or ''
            if not published:
                match=re.search(r'(?:on\s+)?([A-Z][a-z]+ \d{1,2}, 20\d{2})',article.text)
                if match:published=match[1]
            released,basis=article_release(article,published)
            # A dated official launch headline is release evidence for explicitly named models.
            if re.search(r'\b(?:launches|introduces|unveils)\b',title,re.I) and not re.search(r'\b(?:will|coming|preview)\b',title,re.I):
                if adapter=='oppo':
                    names=re.findall(r'\b((?:Reno\s*\d{1,2}[a-z]?|Find\s+[XN]\d{1,2}|[AKF]\d{1,2}|Pad\s+(?:\d{1,2}|SE))(?:\s+(?:Lite|Pro\+?|Ultra|5G|SE))*)\b',title,re.I)
                else:
                    names=re.findall(r'\b(Galaxy\s+(?:Tab\s+[SA]\d{1,2}|[SAMF]\d{1,2}|Z\s+(?:Fold|Flip)\s*\d{1,2})(?:\+|\s+(?:Ultra|FE\+?|Lite|Pro|5G))*)\b',title,re.I)
                models=[(model,'Tablets' if re.search(r'\b(?:Tab|Pad)\b',model,re.I) else 'Smartphones',{}) for model in dict.fromkeys(names)]
                if adapter=='samsung' and re.search(r'\bTVs?\b',title,re.I) and re.search(r'(?:available.*(?:today|now)|starting today)',article.text,re.I):
                    for model in dict.fromkeys(re.findall(r'\b(?:QN\d{2}[A-Z]|[RSM]\d{2}[A-Z]|LS\d{2}[A-Z])\b',article.text)):
                        technology='OLED' if model.startswith('S') else 'Neo QLED' if model.startswith('QN') else 'Micro RGB' if model.startswith('R') else 'QLED' if model.startswith('LS') else 'Mini LED'
                        models.append((model,'Televisions',{'Display technology':technology}))
                if adapter=='samsung' and re.search(r'Bespoke AI WindFree Pro',title,re.I) and re.search(r'\bis available\b',article.text,re.I):
                    models.append(('Bespoke AI WindFree Pro','Air conditioners',{'Technology':'WindFree','Refrigerant':'R32'}))
                for model,item,specs in models:
                    if item not in source['categories']:continue
                    record={'name':brand+' '+model,'brand':brand,'model':model,'source_product_id':url+':'+model,'subcategory':item,
                        'release_date':released,'release_date_basis':basis,'source_url':url,'source_attribution':brand+' official launch announcement',
                        'image_url':article.meta.get('og:image',''),'highlights':specs}
                    allowed,reason=is_recent(record)
                    if allowed:yield record
                    else:progress(reason)
            for script in article.scripts:
                try:payload=json.loads(script)
                except ValueError:continue
                values=payload if isinstance(payload,list) else payload.get('@graph',[payload]) if isinstance(payload,dict) else []
                for value in values:
                    if isinstance(value,dict) and value.get('@type')=='Product' and value.get('releaseDate') and classify_product(str(value.get('category') or '')+' '+str(value.get('name') or '')):
                        yield {'name':value.get('name'),'brand':brand,'model':value.get('model') or value.get('name'),'mpn':value.get('mpn') or '',
                            'release_date':value['releaseDate'],'release_date_basis':'manufacturer_release_date','source_product_id':value.get('sku') or url,
                            'subcategory':classify_product(str(value.get('category') or '')+' '+str(value.get('name') or '')),'source_url':url,'source_attribution':brand+' official product information','description':value.get('description',''),
                            'highlights':{prop.get('name'):prop.get('value') for prop in value.get('additionalProperty',[]) if prop.get('name') and prop.get('value')}}
            # News articles lacking a verifiable model/SKU and release date are leads, not products.
            progress('news_lead',{'url':url,'title':title or url.rsplit('/',1)[-1],'published_at':published})
        except (ValueError,urllib.error.HTTPError,TimeoutError,OSError):progress('unavailable_source_record')


def json_objects(scripts):
    for script in scripts:
        try:payload=json.loads(script)
        except (ValueError,TypeError):continue
        values=payload if isinstance(payload,list) else payload.get('@graph',[payload]) if isinstance(payload,dict) else []
        for value in values:
            if isinstance(value,dict):yield value


def classify_product(text):
    for pattern,item in [(r'\b(?:iPad|tablet|Galaxy Tab|OPPO Pad)\b','Tablets'),(r'\b(?:iPhone|smartphone|Galaxy [SZAMF]|Reno|Find [XN])\b','Smartphones'),(r'\b(?:MacBook|laptop|notebook|ThinkPad|Yoga|Zenbook|Vivobook|Swift|EliteBook|OmniBook)\b','Laptops'),(r'\b(?:television|TV|QLED|Mini LED|BRAVIA)\b','Televisions'),(r'\b(?:air conditioner|air conditioning|PortaSplit)\b','Air conditioners'),(r'\b(?:refrigerator|fridge)\b','Refrigerators'),(r'\bmicrowave\b','Microwave ovens'),(r'\boven\b','Ovens'),(r'\b(?:washing machine|washer)\b','Washing machines'),(r'\bdishwasher\b','Dishwashers'),(r'\bfreezer\b','Freezers'),(r'\bvacuum\b','Vacuum cleaners'),(r'\bmonitor\b','Monitors'),(r'\bprinter\b','Printers'),(r'\b(?:smartwatch|Apple Watch)\b','Smartwatches')]:
        if re.search(pattern,text,re.I):return item
    return None


def company_links(source):
    """Use observed feed structures, including Panasonic's public listing API."""
    adapter=source['adapter'];base=source['endpoint']
    raw=fetch(base,adapter,max_bytes=8*1024*1024)
    if adapter=='panasonic':
        payload=json_fetch('https://news.panasonic.com/api/v1/global/articles/search/category/all/recent',adapter)
        return [(urllib.parse.urljoin(base,row['url']),{'title':row.get('title',''),'published':row.get('publish_start_at','')}) for row in payload.get('articles',[]) if row.get('url')]
    if raw.lstrip().startswith(b'<?xml') or b'<rss' in raw[:500] or b'<feed' in raw[:500]:
        root=ET.fromstring(raw);links=[]
        for entry in root.iter():
            if entry.tag.rsplit('}',1)[-1] not in {'item','entry'}:continue
            fields={child.tag.rsplit('}',1)[-1]:child for child in entry}
            link=next((child for child in entry if child.tag.rsplit('}',1)[-1]=='link' and child.get('rel','alternate')=='alternate'),None);title=fields.get('title')
            if link is None:continue
            url=link.get('href') or link.text or ''
            published=next((fields[k].text for k in ('published','pubDate','updated') if k in fields),'')
            try:published=parsedate_to_datetime(published).date().isoformat()
            except (ValueError,TypeError,OverflowError):pass
            links.append((urllib.parse.urljoin(base,url),{'title':title.text if title is not None else '', 'published':published}))
        return links
    page=Page(raw.decode('utf-8',errors='replace'))
    patterns={'lenovo':r'/pressroom/press-releases/[^/]+','hp':r'/newsroom/press-releases/\d{4}/.+\.html','midea':r'/global/news/[^/?#]+','tcl':r'/global/en/news/[^/?#]+','whirlpool':r'/latest-news/[^/?#]+\.html','bosch':r'/de/en/[^/]+-\d+\.html'}
    return [(urllib.parse.urljoin(base,link),{}) for link in dict.fromkeys(page.links) if re.search(patterns.get(adapter,r'(?!)'),link)]


def company_records(source,progress):
    adapter=source['adapter'];brand=MANUFACTURERS[adapter]['brand'];emitted=0
    for url,hint in company_links(source)[:min(100,source['max_products']*3)]:
        try:
            article=Page(fetch(url,adapter,max_bytes=8*1024*1024).decode('utf-8',errors='replace'))
            title=article.meta.get('og:title') or hint.get('title') or article.title
            objects=list(json_objects(article.scripts))
            published=article.meta.get('article:published_time') or article.meta.get('date') or article.meta.get('datePublished') or article.meta.get('time') or hint.get('published') or next((obj.get('datePublished') for obj in objects if obj.get('datePublished')),'')
            if not published:
                match=re.search(r'\b(20\d{2}[/.-]\d{2}[/.-]\d{2}|[A-Z][a-z]+ \d{1,2}, 20\d{2})\b',article.text)
                if match:published=match[1].replace('/','-')
            released,basis=article_release(article,published)
            candidates=[]
            for obj in objects:
                kind=obj.get('@type');types=kind if isinstance(kind,list) else [kind]
                if 'Product' not in types or not obj.get('releaseDate'):continue
                model=obj.get('model') or obj.get('name');item=classify_product(str(obj.get('category') or '')+' '+str(model)+' '+str(obj.get('description') or ''))
                if item:
                    candidates.append({'name':obj.get('name'),'model':model,'mpn':obj.get('mpn') or '', 'subcategory':item,'release_date':obj['releaseDate'],'release_date_basis':'manufacturer_release_date','source_product_id':obj.get('sku') or url+':'+str(model),'description':obj.get('description') or '', 'highlights':{prop.get('name'):prop.get('value') for prop in obj.get('additionalProperty',[]) if isinstance(prop,dict) and prop.get('name') and prop.get('value')}})
            if not candidates and re.search(r'\b(?:launches|introduces|unveils|announces|introducing)\b',title,re.I) and not re.search(r'\b(?:will|coming|preview|concept)\b',title,re.I):
                # Only explicitly named product families become records. Corporate news stays in the review list.
                names=re.findall(r'\b((?:iPhone\s+\d{1,2}|iPad\s+(?:Pro|Air|mini)|MacBook\s+(?:Pro|Air)|ThinkPad\s+[A-Z]\d{1,3}|Zenbook\s+\w+|Vivobook\s+\w+|Swift\s+\w+|OmniBook\s+\w+|EliteBook\s+\w+|NXT(?:PAPER|VISION)\s+\w+|PortaSplit)(?:\s+(?:Pro|Max|Ultra|Plus|Gen\s*\d+))*)\b',title,re.I)
                for model in dict.fromkeys(names):
                    item=classify_product(model) or classify_product(title)
                    if item:candidates.append({'name':brand+' '+model,'model':model,'subcategory':item,'release_date':released,'release_date_basis':basis,'source_product_id':url+':'+model,'highlights':{}})
            accepted_article=False
            for record in candidates:
                record.update({'brand':brand,'source_url':url,'source_attribution':brand+' official announcement','image_url':article.meta.get('og:image','')})
                valid,reason=is_recent(record)
                if valid and record['subcategory'] in source['categories']:
                    yield record;emitted+=1;accepted_article=True
                    if emitted>=source['max_products']:return
                else:progress(reason or 'unselected_product_type')
            if not accepted_article:progress('news_lead',{'url':url,'title':title,'published_at':published})
        except (ValueError,ET.ParseError,urllib.error.HTTPError,TimeoutError,OSError):progress('unavailable_source_record')


def feed_records(source,progress):
    payload=json_fetch(source['endpoint'],'json_feed')
    records=payload if isinstance(payload,list) else payload.get('products') or payload.get('results') or payload.get('items') or []
    if not isinstance(records,list):raise ValueError('JSON source must return a product list')
    for record in records[:source['max_products']]:
        if not isinstance(record,dict):progress('invalid_record');continue
        yield {**record,'subcategory':record.get('product_type') or record.get('subcategory'),'source_product_id':record.get('id') or record.get('sku') or record.get('source_product_id'),
            'source_url':source['endpoint'],'source_attribution':source['name'],'release_date_basis':'admin_configured_source','highlights':record.get('specifications') or record.get('highlights') or {}}


class ImportService:
    def __init__(self,db):self.db=db;self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='catalog-import');self.closed=False
    def initialize(self):
        catalog.ensure_schema(self.db)
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS product_import_sources (
                id CHAR(36) PRIMARY KEY,name VARCHAR(160) NOT NULL,adapter VARCHAR(30) NOT NULL,endpoint VARCHAR(1000) NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,schedule_type VARCHAR(12) NOT NULL DEFAULT 'manual',interval_hours INT NOT NULL DEFAULT 1,
                at_time CHAR(5) NOT NULL DEFAULT '09:00',timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',run_at VARCHAR(32) NULL,
                categories_json JSON NOT NULL,max_products INT NOT NULL DEFAULT 100,next_run_at DATETIME NULL,
                created_at DATETIME NOT NULL,updated_at DATETIME NOT NULL
            ) ENGINE=InnoDB""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS product_import_jobs (
                id CHAR(36) PRIMARY KEY,source_id CHAR(36) NOT NULL,actor_id CHAR(36) NULL,status VARCHAR(20) NOT NULL,
                created_count INT NOT NULL DEFAULT 0,updated_count INT NOT NULL DEFAULT 0,skipped_count INT NOT NULL DEFAULT 0,
                details_json JSON NULL,error_message TEXT NULL,created_at DATETIME NOT NULL,started_at DATETIME NULL,finished_at DATETIME NULL,updated_at DATETIME NOT NULL,
                KEY idx_import_jobs(source_id,status),FOREIGN KEY(source_id) REFERENCES product_import_sources(id)
            ) ENGINE=InnoDB""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS product_source_records (
                source_id CHAR(36) NOT NULL,external_key VARCHAR(190) NOT NULL,product_id CHAR(36) NOT NULL,content_hash CHAR(64) NOT NULL,
                fetched_at DATETIME NOT NULL,PRIMARY KEY(source_id,external_key),FOREIGN KEY(product_id) REFERENCES products(id),FOREIGN KEY(source_id) REFERENCES product_import_sources(id)
            ) ENGINE=InnoDB""")
            for key,name,adapter,endpoint,types in DEFAULTS:
                cursor.execute("INSERT IGNORE INTO product_import_sources (id,name,adapter,endpoint,categories_json,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,NOW(),NOW())",[stable_id('product-source',key),name,adapter,endpoint,json.dumps(types)])
            cursor.execute("DELETE FROM product_import_sources WHERE adapter='mobile_specs' AND id NOT IN (SELECT source_id FROM product_import_jobs) AND id NOT IN (SELECT source_id FROM product_source_records)")
            cursor.execute("UPDATE product_import_sources SET enabled=FALSE,next_run_at=NULL WHERE adapter='mobile_specs'")
            for item in catalog.APPLIANCE_TYPES:
                parent=category_id(cursor,'Home Appliances',None);category_id(cursor,item,parent)
            cursor.execute('SELECT COUNT(*) count FROM product_filter_values');indexed=cursor.fetchone()['count']
            cursor.execute('SELECT COUNT(*) count FROM products');products=cursor.fetchone()['count']
            cursor.execute("SELECT version FROM catalog_filter_meta WHERE id='specifications'");version=cursor.fetchone()
        if products and (not indexed or not version or version['version']!=catalog.FACET_VERSION):catalog.rebuild_index(self.db)
        # Recover durable jobs after a process restart; never disturb a live importer.
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK('turacoz_catalog_source_import',0) acquired")
            if cursor.fetchone()['acquired']:
                try:
                    cursor.execute("UPDATE product_import_jobs SET status='failed',error_message='Import interrupted by backend restart; fetch again to resume safely',finished_at=UTC_TIMESTAMP(),updated_at=UTC_TIMESTAMP() WHERE status='running'")
                finally:cursor.execute("SELECT RELEASE_LOCK('turacoz_catalog_source_import')")
            cursor.execute("SELECT id,source_id FROM product_import_jobs WHERE status='queued'");queued=cursor.fetchall()
        sources={row['id']:row for row in self.sources()}
        for job in queued:
            if job['source_id'] in sources:self.executor.submit(self.run,job['id'],sources[job['source_id']])
    def sources(self):
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute("SELECT * FROM product_import_sources WHERE adapter!='mobile_specs' ORDER BY name");rows=cursor.fetchall()
            for row in rows:
                row['categories']=catalog.decode(row.pop('categories_json'),[])
                row['enabled']=bool(row['enabled'])
                row['credential_configured']=bool(os.getenv('ICECAT_USERNAME') and os.getenv('ICECAT_PASSWORD')) if row['adapter']=='icecat' else bool(row['endpoint'])
                info=MANUFACTURERS.get(row['adapter'],{})
                row['structure']=info.get('structure','Structured product records with release dates')
                row['available_types']=info.get('types') or list(ICECAT_CATEGORIES if row['adapter']=='icecat' else TECH_RESOURCES if row['adapter']=='techapi' else [])
            return rows
    def create_source(self,payload):
        adapter=payload.get('adapter','json_feed')
        if adapter not in {'json_feed','techapi','icecat',*MANUFACTURERS}:raise ValueError('Unsupported source adapter')
        identifier=str(uuid.uuid4())
        endpoint=str(payload.get('endpoint') or '')
        validate_url(endpoint,adapter)
        name=str(payload.get('name') or 'Custom product source').strip()
        if not 2<=len(name)<=160:raise ValueError('Source name must be 2 to 160 characters')
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute('INSERT INTO product_import_sources (id,name,adapter,endpoint,categories_json,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP())',[identifier,name,adapter,endpoint,json.dumps(payload.get('categories') or ['Smartphones'])])
        try:return self.save_source(identifier,payload)
        except Exception:
            with self.db() as conn,conn.cursor() as cursor:cursor.execute('DELETE FROM product_import_sources WHERE id=%s',[identifier])
            raise
    def save_source(self,identifier,payload):
        source=next((row for row in self.sources() if row['id']==identifier),None)
        if source is None:raise ValueError('Source not found')
        for key in ('name','endpoint','enabled','schedule_type','interval_hours','at_time','timezone','run_at','categories','max_products'):
            if key in payload:source[key]=payload[key]
        if not isinstance(source['name'],str) or not 2<=len(source['name'].strip())<=160:raise ValueError('Source name must be 2 to 160 characters')
        if not isinstance(source['enabled'],bool):raise ValueError('Enabled must be true or false')
        if not isinstance(source['endpoint'],str) or len(source['endpoint'])>1000:raise ValueError('Invalid source URL')
        if not isinstance(source['timezone'],str) or not isinstance(source['at_time'],str):raise ValueError('Invalid timezone or time')
        if source['endpoint']:validate_url(source['endpoint'],source['adapter'])
        elif source['enabled']:raise ValueError('Configure a source URL before enabling the schedule')
        try:ZoneInfo(source['timezone'])
        except (ValueError,KeyError):raise ValueError('Choose a valid IANA timezone')
        if source['schedule_type'] not in {'manual','hourly','daily','fixed'}:raise ValueError('Invalid schedule type')
        if not 1<=int(source['interval_hours'])<=168:raise ValueError('Interval must be 1 to 168 hours')
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',source['at_time']):raise ValueError('Use a valid HH:MM time')
        if not 1<=int(source['max_products'])<=2000:raise ValueError('Each run supports 1 to 2000 products')
        if not isinstance(source['categories'],list) or not source['categories'] or len(source['categories'])>40:raise ValueError('Choose at least one product type')
        if any(not isinstance(item,str) or not item.strip() or len(item)>100 for item in source['categories']):raise ValueError('Invalid product type')
        source['categories']=list(dict.fromkeys(catalog.product_type(item) for item in source['categories']))
        available=source.get('available_types') or []
        if available and any(item not in available for item in source['categories']):raise ValueError('Choose product types supported by this source')
        due=next_run(source)
        source['next_run_at']=due
        if source['enabled'] and source['schedule_type']=='fixed' and due is None:raise ValueError('Choose a future fixed date/time')
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute("""UPDATE product_import_sources SET name=%s,endpoint=%s,enabled=%s,schedule_type=%s,interval_hours=%s,
                at_time=%s,timezone=%s,run_at=%s,categories_json=%s,max_products=%s,next_run_at=%s,updated_at=NOW() WHERE id=%s""",
                [source['name'],source['endpoint'],source['enabled'],source['schedule_type'],source['interval_hours'],source['at_time'],source['timezone'],source.get('run_at'),json.dumps(source['categories']),source['max_products'],due,identifier])
        return source
    def jobs(self):
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute('SELECT j.*,s.name source_name FROM product_import_jobs j JOIN product_import_sources s ON s.id=j.source_id ORDER BY j.created_at DESC LIMIT 100')
            rows=cursor.fetchall()
            for row in rows:row['details']=catalog.decode(row.pop('details_json'),{})
            return rows
    def enqueue(self,identifier,actor=None):
        source=next((row for row in self.sources() if row['id']==identifier),None)
        if not source:raise ValueError('Source not found')
        if not source['endpoint']:raise ValueError('Configure the hosted API URL first')
        job_id=str(uuid.uuid4())
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute('SELECT id FROM product_import_sources WHERE id=%s FOR UPDATE',[identifier])
            cursor.execute("SELECT id FROM product_import_jobs WHERE source_id=%s AND status IN ('queued','running') AND updated_at>UTC_TIMESTAMP()-INTERVAL 45 MINUTE",[identifier])
            if cursor.fetchone():raise ValueError('This source already has a queued or running import')
            cursor.execute("INSERT INTO product_import_jobs (id,source_id,actor_id,status,created_at,updated_at) VALUES (%s,%s,%s,'queued',UTC_TIMESTAMP(),UTC_TIMESTAMP())",[job_id,identifier,actor])
            cursor.execute('UPDATE product_import_sources SET next_run_at=%s WHERE id=%s',[next_run(source),identifier])
        self.executor.submit(self.run,job_id,source)
        return {'id':job_id,'status':'queued'}
    def store_record(self,source,record):
        allowed,reason=is_recent(record)
        if not allowed:return 'skipped',reason
        if not record.get('name') or not record.get('brand') or not record.get('source_product_id'):return 'skipped','missing_identity'
        item=catalog.product_type(record.get('subcategory'))
        if item not in source['categories']:return 'skipped','unselected_product_type'
        external=hashlib.sha256(str(record.get('source_product_id') or record['source_url']).encode()).hexdigest()
        digest=hashlib.sha256(json.dumps(record,sort_keys=True,default=str).encode()).hexdigest()
        release,precision=parse_date(record['release_date'])
        with self.db() as conn,conn.cursor() as cursor:
            cursor.execute('SELECT product_id,content_hash FROM product_source_records WHERE source_id=%s AND external_key=%s',[source['id'],external]);observed=cursor.fetchone()
            if observed and observed['content_hash']==digest:return 'skipped','unchanged'
            existing=None
            if observed:
                cursor.execute('SELECT id,deleted_at,status FROM products WHERE id=%s FOR UPDATE',[observed['product_id']]);existing=cursor.fetchone()
            elif source['adapter']=='icecat':
                cursor.execute("SELECT id,deleted_at,status FROM products WHERE source='icecat' AND source_product_id=%s FOR UPDATE",[str(record['source_product_id'])]);existing=cursor.fetchone()
            if not existing and record.get('mpn'):
                cursor.execute('SELECT id,deleted_at,status FROM products WHERE brand=%s AND mpn=%s LIMIT 1 FOR UPDATE',[record['brand'],record['mpn']]);existing=cursor.fetchone()
            if not existing:
                cursor.execute("SELECT p.id,p.deleted_at,p.status FROM products p LEFT JOIN categories sc ON sc.id=p.subcategory_id WHERE p.brand=%s AND p.model=%s AND sc.name=%s AND p.release_year=%s AND (p.mpn IS NULL OR p.mpn='') LIMIT 1 FOR UPDATE",[record['brand'],record.get('model') or record['name'],item,release.year]);existing=cursor.fetchone()
            if existing and (existing['deleted_at'] is not None or existing['status']!='active'):return 'skipped','admin_removed_or_inactive'
            parent=category_id(cursor,catalog.parent_category(item),None);child=category_id(cursor,item,parent)
            product_id=existing['id'] if existing else stable_id('icecat-product',str(record['source_product_id'])) if source['adapter']=='icecat' else stable_id('sourced-product',source['id']+':'+external)
            highlights=record.get('highlights') or {}
            fields={'name':str(record['name'])[:255],'brand':str(record['brand'])[:190],'model':str(record.get('model') or record['name'])[:190],
                'category_id':parent,'subcategory_id':child,'mpn':str(record.get('mpn') or '')[:190],'gtin':str(record.get('gtin') or '')[:255],
                'release_date':release,'release_year':release.year,'release_date_precision':precision,'release_date_basis':record.get('release_date_basis','source_release_date'),
                'source_url':record.get('source_url','')[:1000],'source_attribution':record.get('source_attribution','')[:255],
                'description':str(record.get('description') or '')[:60000],'highlights':json.dumps(highlights,ensure_ascii=False),
                'technical_specifications':json.dumps(record.get('technical_specifications') or [],ensure_ascii=False),
                'software_specifications':json.dumps(record.get('software_specifications') or [],ensure_ascii=False),'image_url':str(record.get('image_url') or '')[:500]}
            added,_=parse_date(record.get('catalog_added_at'))
            if added:fields['catalog_added_at']=added
            modified=source_timestamp(record.get('source_updated_at'))
            if modified:fields['source_updated_at']=modified
            if existing:
                # Existing auction identities, prices and manual specifications remain authoritative.
                for key in ('name','brand','model','category_id','subcategory_id'):fields.pop(key,None)
                cursor.execute('SELECT highlights,technical_specifications,manual_specifications,source_updated_at FROM products WHERE id=%s',[product_id]);retained=cursor.fetchone()
                if modified and retained['source_updated_at'] and modified<retained['source_updated_at']:return 'skipped','older_source_version'
                fields['highlights']=json.dumps({**catalog.decode(retained['highlights'],{}),**highlights,**catalog.decode(retained['manual_specifications'],{})},ensure_ascii=False)
                if not record.get('technical_specifications'):fields.pop('technical_specifications',None)
                cursor.execute('UPDATE products SET '+','.join(key+'=%s' for key in fields)+',updated_at=UTC_TIMESTAMP() WHERE id=%s',[*fields.values(),product_id])
            else:
                source_key=str(record['source_product_id'])
                fields.update({'id':product_id,'source':source['adapter'],'source_product_id':source_key if len(source_key)<=80 else hashlib.sha256(source_key.encode()).hexdigest(),'price_min':0,'price_max':0,'status':'active'})
                cursor.execute('INSERT INTO products ('+','.join(fields)+',created_at,updated_at) VALUES ('+','.join(['%s']*len(fields))+',UTC_TIMESTAMP(),UTC_TIMESTAMP())',list(fields.values()))
            cursor.execute('SELECT id,highlights,technical_specifications,software_specifications,manual_specifications FROM products WHERE id=%s',[product_id]);catalog.index_product(cursor,cursor.fetchone())
            cursor.execute('INSERT INTO product_source_records (source_id,external_key,product_id,content_hash,fetched_at) VALUES (%s,%s,%s,%s,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE product_id=VALUES(product_id),content_hash=VALUES(content_hash),fetched_at=VALUES(fetched_at)',[source['id'],external,product_id,digest])
        return ('updated' if existing else 'created'),''
    def run(self,job_id,source):
        counts={'created':0,'updated':0,'skipped':0};details={'reasons':{},'leads':[]};started=time.monotonic()
        def progress(reason,lead=None):
            details['reasons'][reason]=details['reasons'].get(reason,0)+1
            if lead and len(details['leads'])<100:details['leads'].append(lead)
            counts['skipped']+=1
            if sum(counts.values())%10==0:save('running')
            if self.closed or time.monotonic()-started>1800:raise TimeoutError('Import stopped after its 30-minute run limit')
        def save(status,error=None):
            with self.db() as conn,conn.cursor() as cursor:
                cursor.execute("UPDATE product_import_jobs SET status=%s,created_count=%s,updated_count=%s,skipped_count=%s,details_json=%s,error_message=%s,started_at=COALESCE(started_at,UTC_TIMESTAMP()),finished_at=IF(%s IN ('completed','failed'),UTC_TIMESTAMP(),NULL),updated_at=UTC_TIMESTAMP() WHERE id=%s",[status,counts['created'],counts['updated'],counts['skipped'],json.dumps(details),error,status,job_id])
        try:
            with self.db() as lock_conn,lock_conn.cursor() as lock:
                lock.execute("SELECT GET_LOCK('turacoz_catalog_source_import',0) acquired")
                if not lock.fetchone()['acquired']:raise ValueError('Another catalog import is running; try again after it completes')
                try:
                    lock.execute("UPDATE product_import_jobs SET status='running',started_at=COALESCE(started_at,UTC_TIMESTAMP()),updated_at=UTC_TIMESTAMP() WHERE id=%s AND status='queued'",[job_id])
                    claimed=lock.rowcount;lock_conn.commit()
                    if not claimed:return
                    save('running')
                    adapter=manufacturer_records if source['adapter'] in MANUFACTURERS else {'icecat':icecat_records,'techapi':tech_records,'json_feed':feed_records}[source['adapter']]
                    for record in adapter(source,progress):
                        if counts['created']+counts['updated']>=source['max_products']:break
                        if self.closed or time.monotonic()-started>1800:raise TimeoutError('Import run time limit reached')
                        result,reason=self.store_record(source,record)
                        counts[result]+=1
                        if reason:details['reasons'][reason]=details['reasons'].get(reason,0)+1
                        save('running')
                    save('completed')
                finally:lock.execute("SELECT RELEASE_LOCK('turacoz_catalog_source_import')")
        except Exception as error:
            safe_error=f'HTTP {error.code}' if isinstance(error,urllib.error.HTTPError) else str(error)[:1000]
            save('failed',safe_error)
    def dispatch_due(self):
        for source in self.sources():
            if source['enabled'] and source['next_run_at'] and source['next_run_at']<=datetime.now(timezone.utc).replace(tzinfo=None):
                try:self.enqueue(source['id'])
                except ValueError:pass
    async def scheduler(self):
        while not self.closed:
            try:await asyncio.to_thread(self.dispatch_due)
            except Exception:
                import logging
                logging.getLogger('turacozbidtool').exception('Catalog schedule check failed')
            await asyncio.sleep(15)
    def close(self):self.closed=True;self.executor.shutdown(wait=False,cancel_futures=True)
