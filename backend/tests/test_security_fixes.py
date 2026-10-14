import unittest
from decimal import Decimal

from fastapi import HTTPException

from backend.main import LoginThrottle, bid_terms_token, csv_response, csv_safe_cell


class CsvSafetyTests(unittest.TestCase):
    def test_formula_prefixes_are_neutralised(self):
        for value in ("=SUM(A1)", "+1", "-2+3", "@cmd", "\tcell", "\rcell"):
            self.assertEqual(csv_safe_cell(value), "'" + value)

    def test_plain_text_and_numbers_are_untouched(self):
        self.assertEqual(csv_safe_cell("Samsung TV"), "Samsung TV")
        self.assertEqual(csv_safe_cell(-5), -5)
        self.assertIsNone(csv_safe_cell(None))

    def test_export_escapes_cells(self):
        body = csv_response("x.csv", [{"name": "=HYPERLINK(\"http://evil\")", "qty": 2}]).body.decode()
        self.assertIn("'=HYPERLINK", body)


class LoginThrottleTests(unittest.TestCase):
    def test_blocks_after_repeated_failures_and_resets(self):
        throttle = LoginThrottle(max_failures=3, window_seconds=60)
        for _ in range(3):
            throttle.check("shop@example.com")
            throttle.record_failure("shop@example.com")
        with self.assertRaises(HTTPException) as caught:
            throttle.check("shop@example.com")
        self.assertEqual(caught.exception.status_code, 429)
        throttle.check("someone-else")
        throttle.reset("shop@example.com")
        throttle.check("shop@example.com")

    def test_failures_expire(self):
        throttle = LoginThrottle(max_failures=1, window_seconds=0)
        throttle.record_failure("a")
        throttle.check("a")


class BidTermsTokenTests(unittest.TestCase):
    base = {
        "amount": Decimal("15000.00"),
        "discount_amount": Decimal("500.00"),
        "warranty_text": "1 year",
        "delivery_time": "2 days",
        "installation_included": 1,
        "free_gifts": "",
        "extra_services": "",
        "notes": "",
    }

    def test_same_terms_give_same_token(self):
        self.assertEqual(bid_terms_token(self.base), bid_terms_token({**self.base, "amount": "15000"}))

    def test_any_commercial_change_changes_token(self):
        original = bid_terms_token(self.base)
        for key, value in (
            ("amount", Decimal("15500.00")),
            ("warranty_text", "3 years"),
            ("delivery_time", "9 days"),
            ("installation_included", 0),
            ("free_gifts", "Bag"),
        ):
            self.assertNotEqual(original, bid_terms_token({**self.base, key: value}), key)


if __name__ == "__main__":
    unittest.main()
