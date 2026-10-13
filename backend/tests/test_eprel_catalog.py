import json
import unittest
from unittest.mock import patch
from backend import eprel_catalog as eprel
from backend.product_sources import is_recent


class EprelCatalogTests(unittest.TestCase):
    def fixture(self,**changes):
        return {'modelIdentifier':'TEST MODEL','supplierOrTrademark':'Test manufacturer','eprelRegistrationNumber':'1',
            'onMarketFirstStartDate':[2025,1,1],'onMarketStartDate':[2026,1,1],'status':'PUBLISHED','blocked':False,
            'orgVerificationStatus':'VERIFIED',**changes}

    def test_first_market_date_prevents_an_old_model_looking_new(self):
        product=eprel.normalize(self.fixture(onMarketFirstStartDate=[2015,1,1]),'Ovens')
        self.assertEqual(product['release_date'],'2015-01-01')
        self.assertFalse(is_recent(product)[0])

    def test_future_first_market_date_is_rejected(self):
        product=eprel.normalize(self.fixture(onMarketFirstStartDate=[2030,1,1]),'Ovens')
        self.assertEqual(is_recent(product),(False,'future_release'))

    def test_ended_market_period_is_not_imported(self):
        product=eprel.normalize(self.fixture(onMarketEndDate=[2025,3,1]),'Ovens')
        self.assertEqual(is_recent(product),(False,'discontinued'))

    def test_freezer_filter_excludes_refrigerator_freezer_combinations(self):
        mixed=self.fixture(capRefrNet=175,capFreezeNet=75)
        freezer=self.fixture(modelIdentifier='PURE FREEZER',eprelRegistrationNumber='2',capRefrNet=0,capFreezeNet=75)
        source={'categories':['Freezers']}
        with patch.object(eprel,'fetch',return_value=json.dumps({'hits':[mixed,freezer]}).encode()):
            records=list(eprel.category_records(source,'Freezers',lambda *args:None))
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['model'],'PURE FREEZER')

    def test_energy_label_is_not_presented_as_a_product_photo(self):
        product=eprel.normalize(self.fixture(energyLabelId=123),'Ovens')
        self.assertEqual(product['image_url'],'')
        self.assertEqual(product['release_date_basis'],'eprel_first_eu_market_date')
        self.assertIn('EU / EEA',product['highlights'].values())


if __name__=='__main__':unittest.main()
