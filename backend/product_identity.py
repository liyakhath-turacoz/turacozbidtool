"""Decide whether two product descriptions are the same product, so the common database never holds a product twice.

A product can be recognised by several independent signals. Each signal becomes an *identity key*; the
database allows each key to belong to exactly one product, which makes duplicates impossible even when two
people add the same product at the same moment.

Strong signals, strongest first:

* ``g:`` a valid barcode (GTIN / EAN / UPC)
* ``m:`` brand + manufacturer part number
* ``b:`` brand + model number
* ``n:`` brand + the words of the product name, normalised (case, punctuation, word order and spacing of
  units such as "55 inch" and "55inch" do not matter)

Descriptions that are only *similar* are never merged automatically: ``similar_products`` ranks them so a
person can decide.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Iterable

STOP_WORDS = {"the", "a", "an", "with", "for", "and", "of", "in", "by", "new", "original", "genuine"}
BRAND_SUFFIXES = {"ltd", "limited", "pvt", "private", "inc", "incorporated", "llc", "llp", "co", "corp", "corporation", "india", "industries", "electronics"}
KEY_LIMIT = 240
# Bump this whenever the rules above change. Keys written under an older version are dropped and rebuilt
# automatically (see dealer_catalogue.sync_identities), so a rule change can never leave wrong matches behind.
KEY_VERSION = 2
KEY_KINDS = ("g", "m", "b", "n")


def current_prefixes() -> tuple[str, ...]:
    return tuple(f"{kind}{KEY_VERSION}" for kind in KEY_KINDS)
GTIN_LENGTHS = (8, 12, 13, 14)

_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(inches|inch|in|gb|tb|mb|kg|g|w|kw|v|mah|hz|l|ltr|litre|liter|ml|mm|cm|m|ton|tons|star)\b")
_UNIT_ALIASES = {"inches": "inch", "in": "inch", "ltr": "l", "litre": "l", "liter": "l", "tons": "ton"}


def _ascii(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def norm_text(value: Any) -> str:
    """Lower-case words separated by single spaces; '&' becomes 'and'; punctuation disappears."""
    text = _ascii(value).casefold().replace("&", " and ").replace("+", " plus ")
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    text = re.sub(r"(?<![0-9])\.|\.(?![0-9])", " ", text)
    return " ".join(text.split())


def norm_brand(value: Any) -> str:
    words = [word for word in norm_text(value).split() if word not in BRAND_SUFFIXES]
    return "".join(words)


def norm_code(value: Any) -> str:
    """Model and part numbers: upper-case letters and digits only (so 'NA352/00' equals 'na-352-00')."""
    return re.sub(r"[^A-Z0-9]", "", _ascii(value).upper().replace("+", "PLUS"))


def model_code(model: Any, brand: Any = "") -> str:
    """A model number as a code. Feeds often repeat the brand inside the model ("Samsung Galaxy S26"), so a
    leading brand name is dropped before the code is made."""
    words = norm_text(model).split()
    brand_words = norm_text(brand).split()
    if brand_words and words[: len(brand_words)] == brand_words:
        words = words[len(brand_words):]
    return norm_code(" ".join(words))


def gtin_checksum_ok(digits: str) -> bool:
    if len(digits) not in GTIN_LENGTHS or not digits.isdigit():
        return False
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(d) * (3 if index % 2 == 0 else 1) for index, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def gtins(value: Any) -> list[str]:
    """Every valid barcode found in a cell. Cells may hold several, separated by commas or semicolons."""
    found: list[str] = []
    for part in re.split(r"[^0-9]+", str(value or "")):
        if part and part not in found and gtin_checksum_ok(part):
            found.append(part)
    return found


def name_tokens(name: Any, brand: Any = "") -> list[str]:
    text = norm_text(name)
    text = _UNIT.sub(lambda m: m.group(1) + _UNIT_ALIASES.get(m.group(2), m.group(2)), text)
    brand_words = set(norm_text(brand).split())
    tokens = [token for token in text.split() if token not in STOP_WORDS and token not in brand_words]
    return tokens


def _key(prefix: str, *parts: str) -> str:
    key = f"{prefix}{KEY_VERSION}:" + "|".join(parts)
    if len(key) > KEY_LIMIT:
        key = key[: KEY_LIMIT - 41] + "#" + hashlib.sha1(key.encode("utf-8")).hexdigest()
    return key


def identity_keys(name: Any, brand: Any = "", model: Any = "", mpn: Any = "", gtin: Any = "") -> list[tuple[str, str]]:
    """(kind, key) pairs describing this product, strongest first. Missing information simply yields fewer keys."""
    brand_key = norm_brand(brand)
    keys: list[tuple[str, str]] = []
    for code in gtins(gtin):
        keys.append(("gtin", _key("g", code)))
    mpn_code = norm_code(mpn)
    model_id = model_code(model, brand)
    if brand_key and len(mpn_code) >= 3:
        keys.append(("mpn", _key("m", brand_key, mpn_code)))
    if brand_key and len(model_id) >= 2 and model_id != mpn_code:
        keys.append(("model", _key("b", brand_key, model_id)))
    elif brand_key and len(model_id) >= 2 and not mpn_code:
        keys.append(("model", _key("b", brand_key, model_id)))
    tokens = name_tokens(name, brand)
    if len(tokens) >= 2:
        # The model number is part of the key: two products with the same name but different models are different.
        keys.append(("name", _key("n", brand_key, " ".join(sorted(tokens)), model_id or mpn_code)))
    return keys


def similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    """0..1 closeness of two product descriptions that share a brand. Different model numbers never match."""
    model_a, model_b = model_code(a.get("model"), a.get("brand")), model_code(b.get("model"), b.get("brand"))
    if model_a and model_b and model_a != model_b:
        return 0.0
    tokens_a = set(name_tokens(a.get("name"), a.get("brand")))
    tokens_b = set(name_tokens(b.get("name"), b.get("brand")))
    if not tokens_a or not tokens_b:
        return 0.0
    jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    ordered_a, ordered_b = sorted(tokens_a), sorted(tokens_b)
    spaced = SequenceMatcher(None, " ".join(ordered_a), " ".join(ordered_b)).ratio()
    # "Air Fryer" and "Airfryer" differ only in a space, so also compare with the spaces removed.
    joined = SequenceMatcher(None, "".join(ordered_a), "".join(ordered_b)).ratio()
    return round(0.4 * jaccard + 0.6 * max(spaced, joined), 3)


def similar_products(row: dict[str, Any], candidates: Iterable[dict[str, Any]], threshold: float = 0.7, limit: int = 3) -> list[dict[str, Any]]:
    scored = []
    for candidate in candidates:
        score = similarity(row, candidate)
        if score >= threshold:
            scored.append({**candidate, "score": score})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]
