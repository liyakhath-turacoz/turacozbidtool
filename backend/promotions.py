"""Promotional offers that dealers publish for products they sell. Rules and wording only; storage is in main.py."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

OFFER_TYPES = ("percent", "amount", "special_price", "gift", "other")
MAX_PRODUCTS_PER_OFFER = 200
MAX_LIVE_OFFERS = 50
MAX_DAYS = 180

TYPE_LABELS = {
    "percent": "Percentage off",
    "amount": "Amount off",
    "special_price": "Special price",
    "gift": "Free gift",
    "other": "Other offer",
}


class OfferProblem(ValueError):
    """A rule the offer breaks. The message is written for the shop that is filling the form in."""


def _rupees(value: Decimal) -> str:
    """Rupees with Indian digit grouping, like the rest of the app: 150000 becomes ₹1,50,000."""
    whole = value == value.to_integral_value()
    text = f"{value:.0f}" if whole else f"{value:.2f}"
    integer, _, fraction = text.partition(".")
    if len(integer) > 3:
        head, tail = integer[:-3], integer[-3:]
        integer = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head) + "," + tail
    return "₹" + integer + ("." + fraction if fraction else "")


def headline(offer: dict[str, Any]) -> str:
    """The short phrase buyers read first."""
    kind = offer.get("offer_type")
    value = Decimal(str(offer.get("offer_value") or 0))
    if kind == "percent":
        percent = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{percent}% off"
    if kind == "amount":
        return f"{_rupees(value)} off"
    if kind == "special_price":
        return f"Special price {_rupees(value)}"
    if kind == "gift":
        return f"Free gift: {offer.get('gift_text', '')}"
    return offer.get("title", "")


def validate_offer(data: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Return a cleaned copy of the offer, or raise OfferProblem with a plain-language reason.

    `starts_at` and `ends_at` are timezone-aware datetimes; `now` must be aware too.
    """
    offer = dict(data)
    title = " ".join(str(offer.get("title") or "").split())
    if not 3 <= len(title) <= 120:
        raise OfferProblem("Give the offer a short title, between 3 and 120 characters.")
    offer["title"] = title

    kind = offer.get("offer_type")
    if kind not in OFFER_TYPES:
        raise OfferProblem("Choose what kind of offer this is.")
    value = offer.get("offer_value")
    offer["offer_value"] = None
    offer["gift_text"] = " ".join(str(offer.get("gift_text") or "").split())
    details = str(offer.get("details") or "").strip()
    if len(details) > 2000:
        raise OfferProblem("The offer details are longer than 2,000 characters.")
    offer["details"] = details

    if kind in {"percent", "amount", "special_price"}:
        try:
            amount = Decimal(str(value))
        except Exception as error:  # Decimal raises several error types for bad text
            raise OfferProblem("Enter the offer value as a number.") from error
        if not amount.is_finite() or amount <= 0:
            raise OfferProblem("The offer value must be greater than 0.")
        if kind == "percent" and amount > 90:
            raise OfferProblem("A percentage offer can be at most 90%.")
        if kind != "percent" and amount > Decimal("100000000"):
            raise OfferProblem("The offer value is too large.")
        offer["offer_value"] = amount.quantize(Decimal("0.01"))
        offer["gift_text"] = ""
    elif kind == "gift":
        if not 2 <= len(offer["gift_text"]) <= 200:
            raise OfferProblem("Say what the free gift is, in up to 200 characters.")
    elif len(details) < 10:
        raise OfferProblem("Describe the offer in the details, so buyers know what they get.")

    code = str(offer.get("promo_code") or "").strip().upper()
    if code and not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{1,39}", code):
        raise OfferProblem("A promo code can use letters, numbers, dashes and underscores, up to 40 characters.")
    offer["promo_code"] = code

    starts, ends = offer.get("starts_at"), offer.get("ends_at")
    if not isinstance(ends, datetime) or ends.tzinfo is None:
        raise OfferProblem("Choose when the offer ends.")
    if not isinstance(starts, datetime) or starts.tzinfo is None:
        starts = now
    if ends <= now:
        raise OfferProblem("The end date must be in the future.")
    if ends <= starts:
        raise OfferProblem("The offer must end after it starts.")
    if ends - starts > timedelta(days=MAX_DAYS):
        raise OfferProblem(f"An offer can run for at most {MAX_DAYS} days. Create a new one to extend it.")
    offer["starts_at"], offer["ends_at"] = starts, ends

    product_ids = list(dict.fromkeys(str(item) for item in (offer.get("product_ids") or []) if str(item).strip()))
    if not product_ids:
        raise OfferProblem("Choose at least one product this offer applies to.")
    if len(product_ids) > MAX_PRODUCTS_PER_OFFER:
        raise OfferProblem(f"An offer can cover at most {MAX_PRODUCTS_PER_OFFER} products.")
    offer["product_ids"] = product_ids
    return offer


def phase(status: str, starts_epoch: float, ends_epoch: float, now_epoch: float) -> str:
    """live, scheduled, ended or paused: what a shop sees next to each of its offers."""
    if status == "paused":
        return "paused"
    if ends_epoch <= now_epoch:
        return "ended"
    if starts_epoch > now_epoch:
        return "scheduled"
    return "live"
