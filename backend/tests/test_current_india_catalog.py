import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.catalog_validation import validate_snapshot
from backend.scripts.rebuild_india_catalog import classify, make_row


class InventoryGatesTests(unittest.TestCase):
    def test_compatibility_does_not_make_power_bank_a_laptop(self):
        self.assertEqual(classify({'product_type': '', 'title': 'Impulse 20000 mAh Power Bank, Compatible with Laptop and iPhone'}), ('P', 'Power banks'))
        self.assertIsNone(classify({'product_type': 'Laptop Battery', 'title': 'Battery for HP Laptop'}))

    def test_lenses_and_security_cameras_have_the_right_categories(self):
        self.assertEqual(classify({'product_type': 'Digital Imaging', 'title': 'Sony FE 50mm F1.4 GM Lens'}), ('J', 'Camera lenses'))
        self.assertEqual(classify({'product_type': 'Security Camera', 'title': 'Wireless camera'}), ('M', 'Security cameras'))

    def test_empty_stale_future_and_missing_photo_snapshots_fail(self):
        with TemporaryDirectory() as folder:
            image_dir = Path(folder)
            row = dict.fromkeys(('product_name','brand','model','department','subcategory','description','product_url','product_source_url','price_source_url'), 'Example')
            row.update(price_currency='INR', price_market='India', verification_status='india_store_in_stock_image_verified', official_price='1000', collected_on='2026-10-23', specifications_json=json.dumps({'Power':'20W','Capacity':'10000mAh'}), image_url='/catalog-images/'+'a'*24+'.webp')
            with self.assertRaises(ValueError): validate_snapshot([], image_dir, date(2026,10,23))
            with self.assertRaisesRegex(ValueError, 'Missing downloaded'): validate_snapshot([row], image_dir, date(2026,10,23))
            (image_dir / ('a'*24+'.webp')).write_bytes(b'photo'*200)
            validate_snapshot([row], image_dir, date(2026,10,23))
            with self.assertRaisesRegex(ValueError, 'older than seven'): validate_snapshot([row], image_dir, date(2026,11,1))
            with self.assertRaisesRegex(ValueError, 'future'): validate_snapshot([row], image_dir, date(2026,10,22))
            with self.assertRaisesRegex(ValueError, 'Duplicate'): validate_snapshot([row,row], image_dir, date(2026,10,23))
            row['image_url']='/catalog-images/../../.env'
            with self.assertRaisesRegex(ValueError, 'unsafe'): validate_snapshot([row], image_dir, date(2026,10,23))

    def test_sold_out_old_and_refurbished_inventory_is_never_accepted(self):
        product = {'title':'Modern Wireless Headphones', 'product_type':'Headphones', 'created_at':'2026-10-10', 'published_at':'2026-10-10', 'variants':[{'available':False,'price':'1999'}]}
        row, reason = make_row('https://example.com','Sony',product,[],{},'2026-10-23','2025-04-23')
        self.assertIsNone(row)
        self.assertEqual(reason,'out_of_stock_or_invalid_price')
        product['created_at']='2020-01-01'
        self.assertEqual(make_row('https://example.com','Sony',product,[],{},'2026-10-23','2025-04-23')[1], 'not_recent_store_listing')
        product['title']='Refurbished Wireless Headphones'
        self.assertEqual(make_row('https://example.com','Sony',product,[],{},'2026-10-23','2025-04-23')[1], 'used_bundle_accessory_or_non_product')


if __name__ == '__main__': unittest.main()
