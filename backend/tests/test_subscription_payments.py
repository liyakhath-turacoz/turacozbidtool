import base64
import hashlib
import hmac
import io
import json
import unittest
import urllib.error
from datetime import datetime, timedelta

from pydantic import ValidationError

from backend import subscription_payments as payments
from backend.main import PaymentDetailsIn


def hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class PaymentModeTests(unittest.TestCase):
    def test_explicit_mode_wins(self):
        self.assertEqual(payments.payment_mode({"TURACOZ_PAYMENT_MODE": "test"}), "test")
        self.assertEqual(payments.payment_mode({"TURACOZ_PAYMENT_MODE": " DEMO "}), "demo")

    def test_keys_switch_on_razorpay_when_no_mode_is_set(self):
        keys = {"RAZORPAY_KEY_ID": "rzp_test_1", "RAZORPAY_KEY_SECRET": "secret"}
        self.assertEqual(payments.payment_mode(keys), "razorpay")
        self.assertEqual(payments.payment_mode({"RAZORPAY_KEY_ID": "rzp_test_1"}), "demo")
        self.assertEqual(payments.payment_mode({}), "demo")

    def test_unknown_mode_falls_back(self):
        self.assertEqual(payments.payment_mode({"TURACOZ_PAYMENT_MODE": "free-for-all"}), "demo")


class PaymentConfigTests(unittest.TestCase):
    def test_defaults_are_999_rupees_for_30_days(self):
        config = payments.payment_config({})
        self.assertEqual((config["price_rupees"], config["amount_paise"], config["period_days"]), (999, 99900, 30))
        self.assertEqual(config["currency"], "INR")

    def test_values_are_read_and_bounded(self):
        config = payments.payment_config({"TURACOZ_SUBSCRIPTION_PRICE_RUPEES": "1500", "TURACOZ_SUBSCRIPTION_DAYS": "9999"})
        self.assertEqual((config["amount_paise"], config["period_days"]), (150000, 366))
        broken = payments.payment_config({"TURACOZ_SUBSCRIPTION_PRICE_RUPEES": "abc", "TURACOZ_SUBSCRIPTION_DAYS": "-4"})
        self.assertEqual((broken["price_rupees"], broken["period_days"]), (999, 1))

    def test_secret_is_never_part_of_the_config(self):
        env = {"RAZORPAY_KEY_ID": "rzp_test_1", "RAZORPAY_KEY_SECRET": "top-secret", "RAZORPAY_WEBHOOK_SECRET": "hook-secret"}
        config = payments.payment_config(env)
        self.assertEqual(config["key_id"], "rzp_test_1")
        self.assertNotIn("top-secret", json.dumps(config))
        self.assertNotIn("hook-secret", json.dumps(config))

    def test_razorpay_without_keys_is_flagged_unconfigured(self):
        self.assertFalse(payments.payment_config({"TURACOZ_PAYMENT_MODE": "razorpay"})["configured"])


class SignatureTests(unittest.TestCase):
    def test_checkout_signature_matches_razorpays_scheme(self):
        expected = hmac_hex("key-secret", b"order_A|pay_B")
        self.assertEqual(payments.checkout_signature("order_A", "pay_B", "key-secret"), expected)
        self.assertTrue(payments.checkout_signature_valid("order_A", "pay_B", expected, "key-secret"))

    def test_checkout_signature_rejects_tampering(self):
        good = payments.checkout_signature("order_A", "pay_B", "key-secret")
        self.assertFalse(payments.checkout_signature_valid("order_A", "pay_OTHER", good, "key-secret"))
        self.assertFalse(payments.checkout_signature_valid("order_OTHER", "pay_B", good, "key-secret"))
        self.assertFalse(payments.checkout_signature_valid("order_A", "pay_B", good, "wrong-secret"))
        self.assertFalse(payments.checkout_signature_valid("order_A", "pay_B", "", "key-secret"))
        self.assertFalse(payments.checkout_signature_valid("order_A", "pay_B", good, ""))

    def test_webhook_signature_covers_the_raw_body(self):
        body = b'{"event":"payment.captured"}'
        signature = hmac_hex("hook", body)
        self.assertTrue(payments.webhook_signature_valid(body, signature, "hook"))
        self.assertFalse(payments.webhook_signature_valid(body + b" ", signature, "hook"))
        self.assertFalse(payments.webhook_signature_valid(body, signature, "other"))
        self.assertFalse(payments.webhook_signature_valid(body, "", "hook"))


class PeriodTests(unittest.TestCase):
    now = datetime(2026, 10, 14, 12, 0, 0)

    def test_first_payment_starts_now(self):
        start, end = payments.extend_subscription(None, self.now, 30)
        self.assertEqual((start, end), (self.now, self.now + timedelta(days=30)))

    def test_lapsed_subscription_restarts_from_now(self):
        start, end = payments.extend_subscription(self.now - timedelta(days=3), self.now, 30)
        self.assertEqual(start, self.now)
        self.assertEqual(end, self.now + timedelta(days=30))

    def test_renewing_early_keeps_the_days_already_paid_for(self):
        current_end = self.now + timedelta(days=5)
        start, end = payments.extend_subscription(current_end, self.now, 30)
        self.assertEqual(start, current_end)
        self.assertEqual(end, current_end + timedelta(days=30))


class WebhookEventTests(unittest.TestCase):
    def event(self, name="payment.captured", **payment):
        entity = {"id": "pay_1", "order_id": "order_1", "amount": 99900, "status": "captured", **payment}
        return json.dumps({"event": name, "payload": {"payment": {"entity": entity}}}).encode()

    def test_captured_payment_is_understood(self):
        self.assertEqual(
            payments.parse_webhook_event(self.event()),
            {"order_id": "order_1", "payment_id": "pay_1", "amount_paise": 99900},
        )

    def test_other_events_and_uncaptured_payments_are_ignored(self):
        self.assertIsNone(payments.parse_webhook_event(self.event("payment.failed")))
        self.assertIsNone(payments.parse_webhook_event(self.event(status="failed")))
        self.assertIsNone(payments.parse_webhook_event(b"not json"))
        self.assertIsNone(payments.parse_webhook_event(json.dumps({"event": "payment.captured", "payload": {}}).encode()))


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class RazorpayOrderTests(unittest.TestCase):
    env = {"RAZORPAY_KEY_ID": "rzp_test_1", "RAZORPAY_KEY_SECRET": "shh"}

    def test_order_request_uses_server_amount_and_basic_auth(self):
        seen = {}

        def opener(request, timeout):
            seen["url"], seen["auth"], seen["body"], seen["timeout"] = request.full_url, request.headers["Authorization"], json.loads(request.data), timeout
            return FakeResponse(json.dumps({"id": "order_X", "amount": 99900}).encode())

        order = payments.create_razorpay_order(99900, "receipt-1", {"dealer_id": "d1"}, self.env, opener)
        self.assertEqual(order["id"], "order_X")
        self.assertEqual(seen["url"], "https://api.razorpay.com/v1/orders")
        self.assertEqual(seen["auth"], "Basic " + base64.b64encode(b"rzp_test_1:shh").decode())
        self.assertEqual((seen["body"]["amount"], seen["body"]["currency"]), (99900, "INR"))
        self.assertLessEqual(seen["timeout"], 30)

    def test_missing_keys_give_a_service_unavailable_error(self):
        with self.assertRaises(payments.PaymentError) as caught:
            payments.create_razorpay_order(99900, "r", {}, {})
        self.assertEqual(caught.exception.status_code, 503)

    def test_gateway_failures_do_not_leak_details(self):
        def refuse(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 400, "Bad", {}, io.BytesIO(b'{"error":{"description":"internal detail"}}'))

        with self.assertRaises(payments.PaymentError) as caught:
            payments.create_razorpay_order(99900, "r", {}, self.env, refuse)
        self.assertNotIn("internal detail", str(caught.exception))

        def offline(request, timeout):
            raise urllib.error.URLError("no route")

        with self.assertRaises(payments.PaymentError):
            payments.create_razorpay_order(99900, "r", {}, self.env, offline)


class PaymentDetailsTests(unittest.TestCase):
    def test_empty_details_are_allowed(self):
        self.assertEqual(PaymentDetailsIn().upi_id, "")

    def test_valid_upi_and_bank_details_are_normalised(self):
        details = PaymentDetailsIn(upi_id=" shop.name@okhdfc ", account_holder="  A  Shopkeeper ", bank_name="HDFC Bank",
                                   account_number="1234 5678 9012", ifsc="hdfc0001234")
        self.assertEqual(details.upi_id, "shop.name@okhdfc")
        self.assertEqual(details.account_holder, "A Shopkeeper")
        self.assertEqual(details.account_number, "123456789012")
        self.assertEqual(details.ifsc, "HDFC0001234")

    def test_bad_upi_is_rejected(self):
        for value in ("no-at-sign", "a@", "@bank", "two@@bank", "x y@bank"):
            with self.assertRaises(ValidationError):
                PaymentDetailsIn(upi_id=value)

    def test_bank_details_must_be_complete_and_well_formed(self):
        with self.assertRaises(ValidationError):
            PaymentDetailsIn(account_number="123456789")
        with self.assertRaises(ValidationError):
            PaymentDetailsIn(account_holder="A", bank_name="B", account_number="12ab56", ifsc="HDFC0001234")
        with self.assertRaises(ValidationError):
            PaymentDetailsIn(account_holder="A", bank_name="B", account_number="123456789", ifsc="HDFC1001234")


if __name__ == "__main__":
    unittest.main()
