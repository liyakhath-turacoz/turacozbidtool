import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend import promotions

NOW = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)


def offer(**changes):
    base = {
        "title": "Diwali sale",
        "offer_type": "percent",
        "offer_value": Decimal("10"),
        "details": "",
        "starts_at": NOW,
        "ends_at": NOW + timedelta(days=7),
        "product_ids": ["p1"],
    }
    base.update(changes)
    return base


def problem(**changes):
    with_error = None
    try:
        promotions.validate_offer(offer(**changes), NOW)
    except promotions.OfferProblem as error:
        with_error = str(error)
    return with_error


class ValidationTests(unittest.TestCase):
    def test_a_good_offer_is_cleaned(self):
        cleaned = promotions.validate_offer(offer(title="  Diwali   sale ", promo_code=" diwali-10 ", offer_value="10"), NOW)
        self.assertEqual(cleaned["title"], "Diwali sale")
        self.assertEqual(cleaned["promo_code"], "DIWALI-10")
        self.assertEqual(cleaned["offer_value"], Decimal("10.00"))

    def test_title_is_required(self):
        self.assertIn("title", problem(title="  "))
        self.assertIn("title", problem(title="x" * 121))

    def test_value_rules_depend_on_the_kind_of_offer(self):
        self.assertIn("greater than 0", problem(offer_value=Decimal("0")))
        self.assertIn("number", problem(offer_value="lots"))
        self.assertIn("90%", problem(offer_value=Decimal("95")))
        self.assertIsNone(problem(offer_type="amount", offer_value=Decimal("95")))
        self.assertIsNone(problem(offer_type="special_price", offer_value=Decimal("38990")))

    def test_gift_needs_a_description_and_other_needs_details(self):
        self.assertIn("free gift", problem(offer_type="gift", offer_value=None, gift_text=""))
        self.assertIsNone(problem(offer_type="gift", offer_value=None, gift_text="Carry case"))
        self.assertIn("details", problem(offer_type="other", offer_value=None, details="short"))
        self.assertIsNone(problem(offer_type="other", offer_value=None, details="Free installation worth Rs. 1500 on every purchase"))

    def test_unknown_kind_is_refused(self):
        self.assertIn("kind", problem(offer_type="mystery"))

    def test_dates_must_make_sense(self):
        self.assertIn("future", problem(ends_at=NOW - timedelta(hours=1)))
        self.assertIn("after it starts", problem(starts_at=NOW + timedelta(days=10), ends_at=NOW + timedelta(days=9)))
        self.assertIn("180 days", problem(ends_at=NOW + timedelta(days=181)))
        self.assertIn("ends", problem(ends_at=None))
        # A date without a time zone is refused rather than guessed.
        self.assertIn("ends", problem(ends_at=datetime(2026, 12, 1)))

    def test_missing_start_means_now(self):
        cleaned = promotions.validate_offer(offer(starts_at=None), NOW)
        self.assertEqual(cleaned["starts_at"], NOW)

    def test_products_are_required_unique_and_limited(self):
        self.assertIn("at least one", problem(product_ids=[]))
        self.assertEqual(promotions.validate_offer(offer(product_ids=["a", "a", "b"]), NOW)["product_ids"], ["a", "b"])
        self.assertIn("at most", problem(product_ids=[str(i) for i in range(201)]))

    def test_promo_codes_are_restricted(self):
        self.assertIn("promo code", problem(promo_code="no spaces allowed"))
        self.assertIsNone(problem(promo_code="SAVE_10"))


class WordingTests(unittest.TestCase):
    def test_headlines_read_naturally(self):
        self.assertEqual(promotions.headline({"offer_type": "percent", "offer_value": Decimal("10.00")}), "10% off")
        self.assertEqual(promotions.headline({"offer_type": "percent", "offer_value": Decimal("12.50")}), "12.5% off")
        self.assertEqual(promotions.headline({"offer_type": "amount", "offer_value": Decimal("2000.00")}), "₹2,000 off")
        self.assertEqual(promotions.headline({"offer_type": "amount", "offer_value": Decimal("1500.50")}), "₹1,500.50 off")
        self.assertEqual(promotions.headline({"offer_type": "special_price", "offer_value": Decimal("150000")}), "Special price ₹1,50,000")
        self.assertEqual(promotions.headline({"offer_type": "gift", "gift_text": "Carry case"}), "Free gift: Carry case")
        self.assertEqual(promotions.headline({"offer_type": "other", "title": "Free installation"}), "Free installation")

    def test_phase_tells_a_shop_where_each_offer_stands(self):
        self.assertEqual(promotions.phase("active", 100, 200, 150), "live")
        self.assertEqual(promotions.phase("active", 300, 400, 150), "scheduled")
        self.assertEqual(promotions.phase("active", 100, 200, 250), "ended")
        self.assertEqual(promotions.phase("paused", 100, 200, 150), "paused")
        self.assertEqual(promotions.phase("paused", 100, 200, 250), "paused")


if __name__ == "__main__":
    unittest.main()
