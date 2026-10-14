import unittest

from backend.catalog_preferences import company_preference_matches, dealer_category_preference_matches, product_type_preference_matches
from backend.catalog_filters import conditions, explicit_ram_capacity, public_catalog_data, relevance_order, regex_prefix, search_terms, search_variants
from backend.catalog_search_engine import _python_rank


class CatalogPreferenceTests(unittest.TestCase):
    def test_category_only_selects_every_product_type_in_the_category(self):
        self.assertTrue(product_type_preference_matches(True, [], "refrigerators"))
        self.assertTrue(product_type_preference_matches(True, [], "dishwashers"))
        self.assertFalse(product_type_preference_matches(False, [], "refrigerators"))

    def test_partial_product_type_selection_excludes_unchecked_types(self):
        selected = ["refrigerators", "dishwashers"]
        self.assertTrue(product_type_preference_matches(True, selected, "refrigerators"))
        self.assertTrue(product_type_preference_matches(True, selected, "dishwashers"))
        self.assertFalse(product_type_preference_matches(True, selected, "vacuum-cleaners"))

    def test_company_filter_is_optional_and_matches_manufacturer_or_brand(self):
        self.assertTrue(company_preference_matches([], "LG Electronics India Ltd.", "LG"))
        self.assertTrue(company_preference_matches(["lg"], "LG Electronics India Ltd.", "LG"))
        self.assertTrue(company_preference_matches(["LG Electronics India Ltd."], "LG Electronics India Ltd.", "ACME"))
        self.assertFalse(company_preference_matches(["Samsung"], "LG Electronics India Ltd.", "LG"))

    def test_combined_company_and_product_type_preferences(self):
        def eligible(item, manufacturer, brand):
            return product_type_preference_matches(True, ["refrigerators"], item) and company_preference_matches(["LG"], manufacturer, brand)

        self.assertTrue(eligible("refrigerators", "LG Electronics India Ltd.", "LG"))
        self.assertFalse(eligible("dishwashers", "LG Electronics India Ltd.", "LG"))
        self.assertFalse(eligible("refrigerators", "Samsung India", "Samsung"))

    def test_no_company_preference_allows_selected_products_from_any_brand(self):
        self.assertTrue(company_preference_matches([], "LG Electronics", "LG"))
        self.assertTrue(company_preference_matches([], "Samsung India", "Samsung"))

    def test_category_parent_means_all_product_types_and_child_checks_are_narrow(self):
        parents = {"appliances": None, "refrigerators": "appliances", "dishwashers": "appliances"}
        self.assertTrue(dealer_category_preference_matches([], "computers", "laptops", parents))
        self.assertTrue(dealer_category_preference_matches(["appliances"], "appliances", "refrigerators", parents))
        self.assertTrue(dealer_category_preference_matches(["appliances", "refrigerators"], "appliances", "refrigerators", parents))
        self.assertFalse(dealer_category_preference_matches(["appliances", "refrigerators"], "appliances", "dishwashers", parents))
        self.assertFalse(dealer_category_preference_matches(["appliances", "refrigerators"], "appliances", None, parents))
        self.assertTrue(dealer_category_preference_matches(["refrigerators"], "appliances", "refrigerators", parents))

    def test_company_only_preference_is_global_but_still_restricts_company(self):
        parents = {"electronics": None, "laptops": "electronics", "appliances": None, "refrigerators": "appliances"}
        def eligible(categories, companies, category, item, manufacturer, brand):
            return dealer_category_preference_matches(categories, category, item, parents) and company_preference_matches(companies, manufacturer, brand)
        self.assertTrue(eligible([], ["LG"], "appliances", "refrigerators", "LG Electronics", "LG"))
        self.assertFalse(eligible([], ["LG"], "electronics", "laptops", "Dell Inc.", "Dell"))
        self.assertTrue(eligible(["electronics", "laptops"], [], "electronics", "laptops", "Dell Inc.", "Dell"))

    def test_product_search_uses_partial_terms_and_specification_keys(self):
        terms = search_terms("16 GB RAM")
        self.assertEqual(terms, ["16", "gb", "ram"])
        where, args = conditions({"q": "16 GB RAM"})
        self.assertEqual(where.count("fs.spec_key) REGEXP"), 3)
        self.assertEqual(args[:9], [regex_prefix("16")]*3 + [regex_prefix("gb")]*3 + [regex_prefix("ram")]*3)
        self.assertIn("rf.spec_key='ram'", where)
        self.assertEqual(args[-3], r"(^|[^[:alnum:]])16[^[:alnum:]]*gb([^[:alnum:]]|$)")
        self.assertIn('"(?:memory_storage|memory)"', args[-1])
        self.assertIn('"(?:ram|ram capacity|installed ram|system ram)"', args[-1])

    def test_ram_capacity_is_only_constrained_when_query_labels_it_as_ram(self):
        self.assertEqual(explicit_ram_capacity("16GB RAM"), ("16", "gb"))
        self.assertEqual(explicit_ram_capacity("RAM 1.5 TB"), ("1.5", "tb"))
        self.assertIsNone(explicit_ram_capacity("16GB storage"))
        self.assertIsNone(explicit_ram_capacity("RAM"))
        where, args = conditions({"q": "ram"})
        self.assertIn("LOWER(p.highlights) REGEXP %s", where)
        self.assertIn('"(?:memory_storage|memory)"', args[-1])

    def test_catalog_search_combines_category_type_brand_and_facets(self):
        where, args = conditions({
            "categories": ["Large Home Appliances"],
            "product_types": ["Refrigerators"],
            "brands": ["LG"],
            "specs": {"capacity": ["300 L"]},
        })
        self.assertIn("c.name IN (%s)", where)
        self.assertIn("sc.name IN (%s)", where)
        self.assertIn("COALESCE(NULLIF(p.manufacturer", where)
        self.assertIn("f.spec_key=%s AND f.spec_value IN (%s)", where)
        self.assertEqual(args, ["Large Home Appliances", "Refrigerators", "LG", "LG", "capacity", "300 L"])

    def test_public_product_specs_remove_provenance_fields_recursively(self):
        source = {
            "RAM": "8 GB",
            "specifications_source_url": "https://vendor.example/specs",
            "nested": {"source_attribution": "Catalog", "display": "6.1 inch", "product_page_url": "https://vendor.example/product"},
            "features": [{"name": "Source URL", "value": "https://vendor.example"},
                         {"name": "Water resistance", "value": "IP68"}],
        }
        self.assertEqual(public_catalog_data(source), {
            "RAM": "8 GB",
            "nested": {"display": "6.1 inch"},
            "features": [{"name": "Water resistance", "value": "IP68"}],
        })

    def test_search_ranks_exact_and_prefix_matches_ahead_of_spec_mentions(self):
        ordering, args = relevance_order("Samsung Galaxy")
        self.assertIn("LOWER(p.name)=LOWER(%s)", ordering)
        self.assertIn("LOWER(p.model) REGEXP %s", ordering)
        self.assertEqual(len(args), 7 + 7 * 2)

    def test_search_escapes_like_wildcards_and_limits_token_count(self):
        self.assertEqual(regex_prefix("ram_%"), r"(^|[^[:alnum:]])ram_%")
        self.assertEqual(len(search_terms("a b c d e f g h i")), 8)

    def test_search_has_bidirectional_category_synonyms(self):
        self.assertIn("notebook", search_variants("laptop"))
        self.assertIn("laptop", search_variants("notebook"))
        self.assertIn("fridge", search_variants("refrigerator"))

    def test_fuzzy_fallback_recovers_typos_and_uses_category_and_specs(self):
        records = [
            {"id": "laptop", "name": "Zenbook 14", "brand": "Asus", "model": "UX3405", "category": "Computers", "item": "Laptops", "searchable_specs": "16 GB RAM OLED"},
            {"id": "phone", "name": "Galaxy S25", "brand": "Samsung", "model": "SM-S931", "category": "Mobile Phones & Tablets", "item": "Smartphones", "searchable_specs": "12 GB RAM"},
            {"id": "washer", "name": "Front Load Washer", "brand": "LG", "model": "FHM", "category": "Home Appliances", "item": "Washing Machines", "searchable_specs": "10 kg"},
        ]
        self.assertEqual([row["id"] for row, _score in _python_rank("laptpo", records)], ["laptop"])
        self.assertEqual([row["id"] for row, _score in _python_rank("16 GB RAM", records)], ["laptop"])
        self.assertEqual(_python_rank("refrigerator", records), [])
        self.assertEqual([row["id"] for row, _score in _python_rank("smart phone", records)], ["phone"])


if __name__ == "__main__":
    unittest.main()
