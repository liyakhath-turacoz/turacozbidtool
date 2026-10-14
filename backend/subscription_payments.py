"""Paid dealer subscriptions: gateway access, signature checks and subscription period maths.

Three modes, chosen with TURACOZ_PAYMENT_MODE:

* ``razorpay`` - real payments through Razorpay (needs RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET;
  RAZORPAY_WEBHOOK_SECRET is needed to accept webhooks).
* ``test``     - a built-in fake gateway that follows the same order -> payment -> signature steps, for
  local development and automated checks. It never moves money.
* ``demo``     - the old behaviour: one click activates the subscription for free.

When TURACOZ_PAYMENT_MODE is not set, Razorpay is used if both keys are present, otherwise ``demo``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("turacozbidtool.payments")

MODES = ("razorpay", "test", "demo")
RAZORPAY_API = "https://api.razorpay.com/v1"
TEST_GATEWAY_SECRET = "turacoz-test-gateway-secret"


class PaymentError(Exception):
    """Raised for gateway failures; the message is safe to show to the person paying."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def payment_mode(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    chosen = (env.get("TURACOZ_PAYMENT_MODE") or "").strip().lower()
    if chosen in MODES:
        return chosen
    if env.get("RAZORPAY_KEY_ID") and env.get("RAZORPAY_KEY_SECRET"):
        return "razorpay"
    return "demo"


def payment_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Plan and gateway settings. Never includes any secret."""
    env = os.environ if env is None else env
    mode = payment_mode(env)

    def number(name: str, default: int, low: int, high: int) -> int:
        try:
            value = int(float(env.get(name, default)))
        except (TypeError, ValueError):
            value = default
        return min(max(value, low), high)

    price = number("TURACOZ_SUBSCRIPTION_PRICE_RUPEES", 999, 1, 1_000_000)
    days = number("TURACOZ_SUBSCRIPTION_DAYS", 30, 1, 366)
    return {
        "mode": mode,
        "amount_paise": price * 100,
        "price_rupees": price,
        "period_days": days,
        "currency": "INR",
        "key_id": env.get("RAZORPAY_KEY_ID", "") if mode == "razorpay" else "",
        "configured": mode != "razorpay" or bool(env.get("RAZORPAY_KEY_ID") and env.get("RAZORPAY_KEY_SECRET")),
    }


def _hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def checkout_signature(order_id: str, payment_id: str, secret: str) -> str:
    """The signature Razorpay (and the test gateway) returns to the browser after a payment."""
    return _hmac_hex(secret, f"{order_id}|{payment_id}".encode("utf-8"))


def checkout_signature_valid(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    if not (order_id and payment_id and signature and secret):
        return False
    return hmac.compare_digest(checkout_signature(order_id, payment_id, secret), str(signature))


def webhook_signature_valid(raw_body: bytes, signature: str, secret: str) -> bool:
    if not (raw_body is not None and signature and secret):
        return False
    return hmac.compare_digest(_hmac_hex(secret, raw_body), str(signature))


def gateway_secrets(mode: str, env: dict[str, str] | None = None) -> dict[str, str]:
    """Secrets for checking signatures in the given mode."""
    env = os.environ if env is None else env
    if mode == "razorpay":
        return {"checkout": env.get("RAZORPAY_KEY_SECRET", ""), "webhook": env.get("RAZORPAY_WEBHOOK_SECRET", "")}
    if mode == "test":
        return {"checkout": TEST_GATEWAY_SECRET, "webhook": TEST_GATEWAY_SECRET}
    return {"checkout": "", "webhook": ""}


def extend_subscription(current_end: datetime | None, now: datetime, days: int) -> tuple[datetime, datetime]:
    """Paying early keeps the days already bought; paying after expiry starts from now."""
    start = current_end if current_end and current_end > now else now
    return start, start + timedelta(days=days)


def parse_webhook_event(raw_body: bytes) -> dict[str, Any] | None:
    """Pull the order, payment and amount out of a Razorpay payment.captured or order.paid event."""
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(event, dict) or event.get("event") not in {"payment.captured", "order.paid"}:
        return None
    payload = event.get("payload") or {}
    payment = ((payload.get("payment") or {}).get("entity")) or {}
    order = ((payload.get("order") or {}).get("entity")) or {}
    order_id = payment.get("order_id") or order.get("id")
    payment_id = payment.get("id")
    amount = payment.get("amount") if payment.get("amount") is not None else order.get("amount_paid")
    if not (order_id and payment_id):
        return None
    if payment.get("status") not in (None, "captured"):
        return None
    return {"order_id": str(order_id), "payment_id": str(payment_id), "amount_paise": int(amount) if amount is not None else None}


def create_razorpay_order(amount_paise: int, receipt: str, notes: dict[str, str], env: dict[str, str] | None = None, opener=None) -> dict[str, Any]:
    """Create an order with Razorpay. The amount always comes from the server, never from the browser."""
    env = os.environ if env is None else env
    key_id, key_secret = env.get("RAZORPAY_KEY_ID", ""), env.get("RAZORPAY_KEY_SECRET", "")
    if not (key_id and key_secret):
        raise PaymentError("Online payments are not set up yet. Please contact support.", 503)
    body = json.dumps({"amount": amount_paise, "currency": "INR", "receipt": receipt[:40], "notes": notes}).encode("utf-8")
    token = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        RAZORPAY_API + "/orders",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {token}"},
    )
    try:
        with (opener or urllib.request.urlopen)(request, timeout=15) as response:
            order = json.load(response)
    except urllib.error.HTTPError as error:
        # Log the gateway's reason for us; show the payer something they can act on.
        logger.error("Razorpay refused the order: HTTP %s %s", error.code, error.read()[:300])
        raise PaymentError("The payment service could not start this payment. Please try again in a moment.") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        logger.error("Razorpay order request failed: %s", error)
        raise PaymentError("The payment service is not reachable right now. Please try again in a moment.") from error
    if not order.get("id"):
        raise PaymentError("The payment service returned an unexpected answer. Please try again.")
    return order
