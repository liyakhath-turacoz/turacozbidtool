import unittest

from backend.main import DealerOpsRepository


class PreferenceRoutingCursor:
    """Small cursor fixture for exercising the real dealer routing method."""

    def __init__(self):
        self.category_parent = {
            "electronics": None,
            "home": None,
            "laptops": "electronics",
            "phones": "electronics",
            "refrigerators": "home",
        }
        self.product = {"category_id": "electronics", "subcategory_id": "laptops", "brand": "Asus", "manufacturer": "Asus"}
        self.origin = {"location_id": "buyer-pin", "country": "India", "area": "Ameerpet", "city": "Hyderabad", "state": "Telangana", "pincode": "500016", "latitude": 17.4375, "longitude": 78.4483}
        self.dealers = {
            "dealer1": self.dealer([], [], 17.4375, 78.4483),
            "dealer2": self.dealer(["electronics", "laptops"], ["LG"], 17.4375, 78.4483),
            "dealer3": self.dealer(["electronics"], ["Samsung"], 17.4375, 78.4483),
        }
        self.one = None
        self.many = []

    @staticmethod
    def dealer(categories, brands, latitude, longitude):
        return {
            "categories": categories,
            "row": {
                "id": "dealer",
                "country": "India",
                "area": "Ameerpet",
                "city": "Hyderabad",
                "state": "Telangana",
                "pincode": "500016",
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": 25,
                "service_preferences": {"country": "India", "method": "radius", "radius_km": 25},
                "dynamic_fields": {"brands": brands},
            },
        }

    def execute(self, statement, args=None):
        args = args or []
        sql = " ".join(statement.split())
        self.one, self.many = None, []
        if "FROM platform_settings" in sql:
            self.one = {"setting_value": {}} if args[0] not in {"dealer_rules", "location_rules"} else {
                "setting_value": {"verification_required": True, "min_rating_threshold": 0, "max_radius_km": 5000}
            }
        elif "FROM product_reference_catalog p" in sql:
            self.one = self.product
        elif "FROM locations WHERE id=%s" in sql:
            self.one = self.origin
        elif "FROM users u" in sql and "JOIN dealer_profiles dp" in sql:
            self.many = []
            for dealer_id, profile in self.dealers.items():
                row = dict(profile["row"])
                row["id"] = dealer_id
                self.many.append(row)
        elif "FROM dealer_categories dc" in sql:
            for dealer_id, profile in self.dealers.items():
                for category_id in profile["categories"]:
                    self.many.append({
                        "dealer_id": dealer_id,
                        "category_id": category_id,
                        "parent_id": self.category_parent.get(category_id),
                    })
        else:
            raise AssertionError(f"Unexpected routing SQL: {sql}")

    def fetchone(self):
        if self.one is not None:
            result, self.one = self.one, None
            return result
        if self.many:
            return self.many.pop(0)
        return None

    def fetchall(self):
        result, self.many = self.many, []
        return result


class DealerMatchingTests(unittest.TestCase):
    def setUp(self):
        self.cursor = PreferenceRoutingCursor()
        self.repo = DealerOpsRepository()

    def matches(self, brand, category="electronics", product_type="laptops", buyer_radius=0):
        self.cursor.product = {
            "category_id": category,
            "subcategory_id": product_type,
            "brand": brand,
            "manufacturer": brand,
        }
        return self.repo.matching_dealer_ids(self.cursor, "product", "buyer-pin", buyer_radius, False)

    def test_unchecked_company_means_any_brand_but_selected_company_stays_strict(self):
        self.assertEqual(self.matches("Asus"), ["dealer1"])
        self.assertEqual(self.matches("LG"), ["dealer1", "dealer2"])
        self.assertEqual(self.matches("Samsung"), ["dealer1", "dealer3"])

    def test_parent_category_means_all_children_and_selected_child_is_narrow(self):
        self.assertIn("dealer3", self.matches("Samsung", product_type="phones"))
        self.assertNotIn("dealer2", self.matches("LG", product_type="phones"))
        self.cursor.dealers["dealer3"]["categories"] = ["electronics", "laptops"]
        self.assertNotIn("dealer3", self.matches("Samsung", product_type="phones"))

    def test_product_type_without_company_filter_accepts_every_brand(self):
        self.cursor.dealers["dealer1"]["categories"] = ["electronics", "laptops"]
        self.assertIn("dealer1", self.matches("Asus"))
        self.assertIn("dealer1", self.matches("Lenovo"))
        self.assertNotIn("dealer1", self.matches("Asus", product_type="phones"))

    def test_company_only_profile_matches_that_company_across_categories(self):
        self.cursor.dealers["dealer2"]["categories"] = []
        self.assertIn("dealer2", self.matches("LG", category="home", product_type="refrigerators"))
        self.assertNotIn("dealer2", self.matches("Samsung", category="home", product_type="refrigerators"))

    def test_category_product_type_and_company_preferences_intersect(self):
        self.cursor.dealers["dealer1"]["categories"] = ["electronics", "laptops"]
        self.cursor.dealers["dealer1"]["row"]["dynamic_fields"]["brands"] = ["Samsung"]
        self.assertIn("dealer1", self.matches("Samsung", product_type="laptops"))
        self.assertNotIn("dealer1", self.matches("Samsung", product_type="phones"))
        self.assertNotIn("dealer1", self.matches("LG", product_type="laptops"))

    def test_radius_coverage_excludes_dealer_outside_its_service_circle(self):
        self.cursor.dealers["dealer2"]["row"]["latitude"] = 18.4375
        self.assertNotIn("dealer2", self.matches("LG"))

    def test_buyer_radius_is_an_additional_limit_on_dealer_coverage(self):
        self.cursor.dealers["dealer1"]["row"]["latitude"] = 17.4875
        self.assertIn("dealer1", self.matches("Asus"))
        self.assertNotIn("dealer1", self.matches("Asus", buyer_radius=1))

    def test_state_service_area_matches_only_the_selected_state(self):
        dealer = self.cursor.dealers["dealer1"]["row"]
        self.cursor.dealers["dealer1"]["categories"] = []
        dealer["service_preferences"] = {
            "country": "India", "method": "states", "states": ["Telangana"]
        }
        self.assertIn("dealer1", self.matches("Asus"))
        self.cursor.origin["state"] = "Andhra Pradesh"
        self.assertNotIn("dealer1", self.matches("Asus"))

    def test_city_service_area_requires_city_and_configured_state(self):
        dealer = self.cursor.dealers["dealer1"]["row"]
        self.cursor.dealers["dealer1"]["categories"] = []
        dealer["service_preferences"] = {
            "country": "India", "method": "cities",
            "cities": ["Ongole"], "states": ["Andhra Pradesh"],
        }
        self.cursor.origin.update(city="Ongole", state="Andhra Pradesh")
        self.assertIn("dealer1", self.matches("Asus"))
        self.cursor.origin["state"] = "Telangana"
        self.assertNotIn("dealer1", self.matches("Asus"))
        self.cursor.origin.update(city="Hyderabad", state="Telangana")
        self.assertNotIn("dealer1", self.matches("Asus"))

    def test_district_service_area_matches_city_or_area_within_state(self):
        dealer = self.cursor.dealers["dealer1"]["row"]
        self.cursor.dealers["dealer1"]["categories"] = []
        dealer["service_preferences"] = {
            "country": "India", "method": "districts",
            "districts": ["RTC Bus Stand"], "states": ["Andhra Pradesh"],
        }
        self.cursor.origin.update(city="Ongole", area="RTC Bus Stand", state="Andhra Pradesh")
        self.assertIn("dealer1", self.matches("Asus"))
        self.cursor.origin["state"] = "Telangana"
        self.assertNotIn("dealer1", self.matches("Asus"))


if __name__ == "__main__":
    unittest.main()
