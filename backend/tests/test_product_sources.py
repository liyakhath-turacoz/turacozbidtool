import io
import csv
import gzip
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from backend import product_sources as sources


class Response(io.BytesIO):
    def __init__(self, body, length=None):
        super().__init__(body)
        self.headers={} if length is None else {'Content-Length':str(length)}


class ProductSourceTests(unittest.TestCase):
    def test_nested_icecat_release_date_is_read_before_legacy_attribute(self):
        xml=b'<ICECAT-interface><Product ID="1" ReleaseDate="2001-01-01" Prod_id="MODEL"><ReleaseDate><Date Value="2025-06-01" langid="1"/></ReleaseDate><Supplier Name="Example"/></Product></ICECAT-interface>'
        row={'path':'export/freexml/EN/1.xml','product_id':'1','prod_id':'MODEL','updated':'20261012000000','on_market':'1'}
        with patch.object(sources,'fetch',return_value=xml):
            record=sources.icecat_xml(row,'Ovens')
        self.assertEqual(record['release_date'],'2025-06-01')
        self.assertTrue(sources.is_recent(record)[0])

    def test_icecat_added_date_is_never_used_as_release_date(self):
        row={'path':'export/freexml/EN/1.xml','product_id':'1','prod_id':'MODEL','updated':'20261012000000','on_market':'1','Date_Added':'20261012000000'}
        with patch.object(sources,'fetch',return_value=b'<ICECAT-interface><Product><ReleaseDate/></Product></ICECAT-interface>'):
            record=sources.icecat_xml(row,'Ovens')
        self.assertEqual(sources.is_recent(record),(False,'missing_release_date'))

    def test_partial_download_keeps_previous_cache(self):
        import hashlib
        url='https://example.com/products.json'
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);cache=folder/(hashlib.sha256(url.encode()).hexdigest()+'.cache');cache.write_bytes(b'previous')
            with patch.object(sources,'CACHE',folder),patch.object(sources,'validate_url'),patch.object(sources.urllib.request,'build_opener') as opener:
                opener.return_value.open.return_value=Response(b'partial',100)
                with self.assertRaisesRegex(ValueError,'Incomplete'):
                    sources.fetch(url,'json_feed',cache_seconds=0)
            self.assertEqual(cache.read_bytes(),b'previous')
            self.assertEqual(list(folder.glob('*.tmp')),[])

    def test_complete_download_is_saved_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sources,'CACHE',Path(directory)),patch.object(sources,'validate_url'),patch.object(sources.urllib.request,'build_opener') as opener:
                opener.return_value.open.return_value=Response(b'complete',8)
                self.assertEqual(sources.fetch('https://example.com/data','json_feed'),b'complete')

    def test_fixed_schedule_preserves_explicit_offset(self):
        source={'enabled':True,'schedule_type':'fixed','timezone':'Asia/Kolkata','run_at':'2030-01-01T12:00:00+00:00'}
        result=sources.next_run(source,datetime(2029,1,1,tzinfo=timezone.utc))
        self.assertEqual(result,datetime(2030,1,1,12))

    def test_fixed_schedule_local_time_uses_selected_timezone(self):
        source={'enabled':True,'schedule_type':'fixed','timezone':'Asia/Kolkata','run_at':'2030-01-01T12:00:00'}
        result=sources.next_run(source,datetime(2029,1,1,tzinfo=timezone.utc))
        self.assertEqual(result,datetime(2030,1,1,6,30))

    def test_feed_does_not_exhaust_write_quota_on_first_unchanged_row(self):
        source={'endpoint':'https://example.com/data','max_products':1,'name':'Example'}
        rows=[{'id':i,'name':f'Model {i}','product_type':'Ovens'} for i in range(3)]
        with patch.object(sources,'json_fetch',return_value=rows):
            records=list(sources.feed_records(source,lambda *args:None))
        self.assertEqual(len(records),3)

    def test_icecat_discovery_deduplicates_ids_and_visits_uneven_categories(self):
        rows=[['1','2286'],['1','2286'],['2','2286'],['3','1873'],['4','1873'],['5','1873']]
        with tempfile.TemporaryDirectory() as directory:
            index=Path(directory)/'index.gz'
            with gzip.open(index,'wt',encoding='utf-8',newline='') as stream:
                writer=csv.writer(stream,delimiter='\t');writer.writerow(['product_id','catid','on_market','quality','Date_Added','updated'])
                for identifier,category in rows:writer.writerow([identifier,category,'1','ICECAT','20250101000000','20261012000000'])
            source={'categories':['Ovens','Refrigerators'],'max_products':10,'endpoint':'https://data.icecat.biz/export/freexml/EN/files.index.csv.gz'}
            def xml(row,item):return {'source_product_id':row['product_id'],'subcategory':item,'release_date':'2025-01-01'}
            with patch.object(sources,'fetch',return_value=index),patch.object(sources,'icecat_xml',side_effect=xml) as reader:
                records=list(sources.icecat_records(source,lambda *args:None))
            self.assertEqual(reader.call_count,5)
            self.assertEqual({row['source_product_id'] for row in records},{'1','2','3','4','5'})
            self.assertEqual([call.args[1] for call in reader.call_args_list[:4]],['Ovens','Refrigerators','Ovens','Refrigerators'])

    def test_xml_vertical_index_is_normalized_without_losing_following_rows(self):
        xml=b'<ICECAT-interface><files.index><file path="export/freexml/EN/1.xml" Product_ID="1" Catid="2286" On_Market="1" Prod_ID="ONE" Updated="20261012000000"><EAN_UPCS><EAN_UPC Value="123"/></EAN_UPCS></file><file path="export/freexml/EN/2.xml" Product_ID="2" Catid="1322" On_Market="1" Prod_ID="TWO"/></files.index></ICECAT-interface>'
        with tempfile.TemporaryDirectory() as directory:
            index=Path(directory)/'vertical.gz';index.write_bytes(gzip.compress(xml))
            rows=list(sources.icecat_index_rows(index))
        self.assertEqual([row['product_id'] for row in rows],['1','2'])
        self.assertEqual(rows[0]['ean_upc'],'123')
        self.assertEqual(rows[1]['catid'],'1322')

    def test_post_search_payloads_have_separate_cache_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sources,'CACHE',Path(directory)),patch.object(sources,'validate_url'),patch.object(sources.urllib.request,'build_opener') as opener:
                opener.return_value.open.side_effect=[Response(b'one',3),Response(b'two',3)]
                self.assertEqual(sources.fetch('https://example.com/search','json_feed',data=b'first'),b'one')
                self.assertEqual(sources.fetch('https://example.com/search','json_feed',data=b'second'),b'two')
                self.assertEqual(sources.fetch('https://example.com/search','json_feed',data=b'first'),b'one')
                self.assertEqual(opener.return_value.open.call_count,2)

    def test_invalid_feed_identity_does_not_open_database(self):
        database=unittest.mock.Mock();service=sources.ImportService(database)
        try:
            result=service.store_record({}, {'name':'Test','brand':{'bad':'value'},'source_product_id':1,'release_date':'2025-01-01'})
            self.assertEqual(result,('skipped','invalid_identity'));database.assert_not_called()
        finally:service.close()

    def test_lg_dates_images_and_preorders_are_normalized(self):
        from backend.lg_catalog import normalize
        raw={'ec_model_name':'EXAMPLE','ec_model_url_path':'/in/test/','ec_model_release_date':1789948800000,
            'ec_model_status_code':'ACTIVE','ec_preorder_flag':'N','ec_medium_image_addr':'/in/test/image.jpg'}
        record=normalize(raw,'Ovens')
        self.assertEqual(record['release_date'],'2026-09-21')
        self.assertEqual(record['image_url'],'https://www.lg.com/content/dam/channel/wcms/in/test/image.jpg')
        self.assertTrue(record['on_market'])
        self.assertFalse(normalize({**raw,'ec_preorder_flag':'Y'},'Ovens')['on_market'])

    def test_removed_category_identity_is_retained_for_import_safety(self):
        from backend.catalog_importer import category_id
        cursor=unittest.mock.Mock();cursor.fetchone.return_value={'id':'existing-category'}
        self.assertEqual(category_id(cursor,'Ovens','parent'),'existing-category')
        self.assertEqual(cursor.execute.call_count,1)
        self.assertNotIn('AND deleted_at IS NULL',cursor.execute.call_args.args[0])


if __name__=='__main__':unittest.main()
