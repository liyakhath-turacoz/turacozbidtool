"""Fetch and attach verified catalogue product images, one category at a time.

Run from the repository root, for example:
    python backend/scripts/collect_product_images.py --category A
    python backend/scripts/collect_product_images.py --all

The script is resumable: products with an existing local image file are skipped.
It updates only the image_url field in products and the corresponding catalogue
CSV exports. Failed or ambiguous image matches are logged, not guessed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import uuid

import requests
from PIL import Image, ImageOps
from io import BytesIO

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
IMAGE_ROOT = BACKEND / "product_images"
LOG_PATH = ROOT / "product_catalog" / "image_collection_log.csv"
CATALOG_DIR = ROOT / "product_catalog"
NAMESPACE = uuid.UUID("3cdbf650-f7f2-4dbd-a90c-2dc89c6b67a1")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_DIMENSION = 1200
USER_AGENT = "TuracozProductCatalogue/1.0 (+official product image indexing; contact site administrator)"
CATEGORY_CODES = {
    "Mobile Phones & Tablets": "A",
    "Computers, Laptops & IT Equipment": "B",
    "TVs, Video & Home Entertainment": "C",
    "Audio, Headphones & Speakers": "D",
    "Large Home Appliances": "E",
    "Kitchen Appliances": "F",
    "Cleaning, Laundry & Floor Care": "G",
    "Air Conditioning, Cooling & Air Quality": "H",
    "Personal Care & Grooming Appliances": "I",
    "Cameras, Photography & Imaging": "J",
    "Gaming & Virtual Reality": "K",
    "Wearables & Smart Devices": "L",
    "Smart Home, Security & Surveillance": "M",
    "Networking, GPS & Communication": "N",
    "Printers, Scanners & Office Electronics": "O",
    "Power Backup, Batteries & Electrical Equipment": "P",
}
LOG_FIELDS = ["product_id", "category_code", "category", "brand", "product", "model", "status", "image_url", "image_source_url", "source_page", "detail"]


def stable_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{value}"))


def product_id_from_csv(row: dict[str, str]) -> str:
    identity = "|".join((row.get("category_code", ""), row.get("manufacturer", ""), row.get("brand", ""), row.get("model", ""), row.get("product_name", "")))
    return stable_id("product", identity)


class ProductPageParser(HTMLParser):
    """Collect image candidates and nearby labels without retaining full DOMs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: list[dict[str, str]] = []
        self.images: list[tuple[str, str]] = []
        self.page_text: list[str] = []
        self._title_depth = 0
        self._title: list[str] = []
        self._recent_text = ""
        self._jsonld_depth = 0
        self._jsonld: list[str] = []

    @property
    def title(self) -> str:
        return " ".join(self._title).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._title_depth += 1
        if tag == "meta":
            self.meta.append(values)
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._jsonld_depth += 1
        if tag in {"img", "source"}:
            label = " ".join(values.get(key, "") for key in ("alt", "title", "aria-label", "data-title"))
            context = (label + " " + self._recent_text[-500:]).strip()
            for key in ("src", "data-src", "data-original", "data-lazy-src", "srcset", "data-srcset"):
                raw = values.get(key, "").strip()
                if not raw:
                    continue
                urls = []
                if "srcset" in key:
                    for item in raw.split(","):
                        part = item.strip().split()
                        if part:
                            width = int(re.sub(r"\D", "", part[1]) or 0) if len(part) > 1 else 0
                            urls.append((width, part[0]))
                    urls.sort(reverse=True)
                    if urls:
                        self.images.append((urls[0][1], context))
                else:
                    self.images.append((raw, context))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if tag == "script" and self._jsonld_depth:
            self._jsonld_depth -= 1

    def handle_data(self, data: str) -> None:
        content = data.strip()
        if not content:
            return
        if self._title_depth:
            self._title.append(content)
        if self._jsonld_depth:
            self._jsonld.append(content)
        else:
            self._recent_text = (self._recent_text + " " + content)[-1500:]
            self.page_text.append(content)


def searchable(value: str) -> str:
    value = html.unescape(value).casefold()
    value = re.sub(r"https?://", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def tokens(value: str) -> set[str]:
    return {part for part in searchable(value).split() if len(part) > 1 and part not in {"the", "with", "and", "for", "series", "product", "official"}}


def images_from_jsonld(parser: ProductPageParser) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def walk(value: object, context: str = "") -> None:
        if isinstance(value, dict):
            local_context = " ".join([context, str(value.get("name", "")), str(value.get("model", "")), str(value.get("sku", ""))])
            for key, item in value.items():
                if key.casefold() in {"image", "images"}:
                    values = item if isinstance(item, list) else [item]
                    for image in values:
                        if isinstance(image, str):
                            found.append((image, local_context))
                        elif isinstance(image, dict) and image.get("url"):
                            found.append((str(image["url"]), local_context))
                elif isinstance(item, (dict, list)):
                    walk(item, local_context)
        elif isinstance(value, list):
            for item in value:
                walk(item, context)

    for raw in parser._jsonld:
        try:
            walk(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue
    return found


def meta_values(parser: ProductPageParser) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in parser.meta:
        key = (item.get("property") or item.get("name") or item.get("itemprop") or "").casefold()
        value = item.get("content", "").strip()
        if key and value:
            result.setdefault(key, value)
    return result


def model_match_score(product: dict[str, object], context: str, page_title: str, page_url: str) -> int:
    model = str(product.get("model") or "").strip()
    name = str(product.get("name") or "").strip()
    brand = str(product.get("brand") or "").strip()
    model_tokens = tokens(model)
    name_tokens = tokens(name) - tokens(brand)
    brand_tokens = tokens(brand)
    candidate_tokens = tokens(" ".join((context, page_title, page_url)))
    score = 0
    if model_tokens:
        overlap = model_tokens & candidate_tokens
        if model_tokens <= candidate_tokens:
            score += 8
        elif len(model_tokens) == 1 and overlap:
            score += 6
        elif overlap:
            score += min(7, 3 * len(overlap))
    name_overlap = name_tokens & candidate_tokens
    if name_tokens and len(name_overlap) >= min(2, len(name_tokens)):
        score += min(5, 2 * len(name_overlap))
    if brand_tokens & candidate_tokens:
        score += 1
    bad_words = {"logo", "icon", "banner", "avatar", "sprite", "placeholder", "social", "facebook", "instagram"}
    if bad_words & tokens(context):
        score -= 6
    return score


class Collector:
    def __init__(self, delay: float) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,image/avif,image/webp,image/apng,image/*,*/*;q=0.8", "Accept-Encoding": "gzip, deflate"})
        self.delay = max(0.0, delay)
        self.last_host_request: dict[str, float] = defaultdict(float)
        self.page_cache: dict[str, tuple[ProductPageParser, dict[str, str], str] | None] = {}
        self.image_cache: dict[str, str | None] = {}

    def _wait_for_host(self, url: str) -> None:
        host = urlsplit(url).netloc.casefold()
        remaining = self.delay - (time.monotonic() - self.last_host_request[host])
        if remaining > 0:
            time.sleep(remaining)
        self.last_host_request[host] = time.monotonic()

    def fetch(self, url: str, max_bytes: int) -> tuple[bytes, str, str]:
        if urlsplit(url).scheme not in {"http", "https"}:
            raise ValueError("Non-http image/page URL")
        self._wait_for_host(url)
        with self.session.get(url, timeout=(6, 10), stream=True, allow_redirects=True) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ValueError(f"Response exceeded {max_bytes} bytes")
            return bytes(body), response.headers.get("content-type", "").split(";", 1)[0].casefold(), response.url

    def page(self, url: str) -> tuple[ProductPageParser, dict[str, str], str] | None:
        if url in self.page_cache:
            return self.page_cache[url]
        try:
            body, content_type, final_url = self.fetch(url, MAX_PAGE_BYTES)
            if "html" not in content_type and not body.lstrip().startswith((b"<!", b"<html", b"<HTML")):
                raise ValueError(f"Not an HTML page ({content_type or 'unknown content type'})")
            parser = ProductPageParser()
            parser.feed(body.decode("utf-8", errors="replace"))
            meta = meta_values(parser)
            result = (parser, meta, final_url)
        except Exception as error:
            print(f"PAGE SKIP {url}: {error}", flush=True)
            result = None
        self.page_cache[url] = result
        return result

    def candidate_images(self, product: dict[str, object], page_url: str) -> list[tuple[int, str, str]]:
        loaded = self.page(page_url)
        if not loaded:
            return []
        parser, meta, final_url = loaded
        page_title = " ".join((parser.title, meta.get("og:title", ""), meta.get("twitter:title", ""), meta.get("description", "")))
        images: list[tuple[str, str, bool]] = [(url, context, False) for url, context in parser.images]
        images.extend((url, context, False) for url, context in images_from_jsonld(parser))
        for key in ("og:image", "og:image:url", "twitter:image", "twitter:image:src", "image"):
            if meta.get(key):
                images.append((meta[key], "", True))
        scored: list[tuple[int, str, str]] = []
        seen: set[str] = set()
        page_score = model_match_score(product, page_title, "", final_url)
        for raw, context, is_metadata_image in images:
            image_url = urljoin(final_url, html.unescape(raw.strip()))
            parts = urlsplit(image_url)
            if parts.scheme not in {"http", "https"} or not parts.netloc or image_url in seen:
                continue
            seen.add(image_url)
            image_words = tokens(image_url)
            if {"logo", "icon", "sprite", "banner", "avatar", "placeholder", "social"} & image_words or parts.path.casefold().endswith(".svg"):
                continue
            # Metadata images can inherit a match from a page title only when that
            # title identifies this product. Inline images must identify the model
            # in their own alt/context/URL so unrelated thumbnails cannot pass.
            score = page_score + 1 if is_metadata_image and page_score >= 6 else model_match_score(product, context, "", image_url)
            scored.append((score, image_url, final_url))
        scored.sort(reverse=True)
        return scored

    def to_webp(self, content: bytes) -> bytes:
        with Image.open(BytesIO(content)) as original:
            if original.width < 96 or original.height < 96 or original.width * original.height > 40_000_000:
                raise ValueError(f"Image dimensions unsuitable: {original.width}x{original.height}")
            image = ImageOps.exif_transpose(original)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, "WEBP", quality=82, method=5)
            return output.getvalue()

    def store_image(self, url: str) -> tuple[str, str]:
        if url in self.image_cache:
            cached = self.image_cache[url]
            if cached is None:
                raise ValueError("Image URL already failed during this run")
            return cached, url
        try:
            content, content_type, final_url = self.fetch(url, MAX_IMAGE_BYTES)
            data = self.to_webp(content)
            digest = hashlib.sha256(data).hexdigest()
            filename = f"{digest}.webp"
            IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
            target = IMAGE_ROOT / filename
            if not target.exists():
                temporary = target.with_suffix(".webp.tmp")
                temporary.write_bytes(data)
                temporary.replace(target)
            local_url = f"/product-images/{filename}"
            self.image_cache[url] = local_url
            return local_url, final_url
        except Exception:
            self.image_cache[url] = None
            raise

    def find_image(self, product: dict[str, object]) -> tuple[str, str, str]:
        original_url = str(product.get("image_url") or "").strip()
        failures: list[str] = []
        if original_url.startswith(("http://", "https://")):
            try:
                local_url, final_url = self.store_image(original_url)
                return local_url, final_url, "downloaded_existing_image_url"
            except Exception as error:
                failures.append(f"listed image: {error}")

        pages: list[str] = []
        for field in ("product_url", "source_url"):
            value = str(product.get(field) or "").strip()
            if value.startswith(("http://", "https://")) and value not in pages:
                pages.append(value)
        brand = str(product.get("brand") or "").strip()
        model = str(product.get("model") or "").strip()
        for page_url in pages:
            candidates = self.candidate_images(product, page_url)
            for score, image_url, final_page in candidates:
                # Require model/name evidence in the page or the specific image label.
                # Generic category hero images and company logos are deliberately skipped.
                if score < 6:
                    continue
                try:
                    local_url, final_image = self.store_image(image_url)
                    return local_url, final_image, f"matched_official_page_score_{score}"
                except Exception as error:
                    failures.append(f"candidate {image_url}: {error}")
        detail = " | ".join(failures[:3]) or ("No sufficiently specific product image found on linked pages" if pages else "No image or product/source URL available")
        raise ValueError(detail)


def database_rows(category_code: str | None) -> list[dict[str, object]]:
    sys.path.insert(0, str(BACKEND))
    from configuration import load_local_environment
    load_local_environment()
    from catalog_importer import connect

    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.name, p.brand, p.model, p.image_url, p.product_url,
                       p.source_url, COALESCE(parent.name, c.name, 'Uncategorised') AS category
                FROM products p
                LEFT JOIN categories c ON c.id=p.category_id
                LEFT JOIN categories parent ON parent.id=c.parent_id
                WHERE p.deleted_at IS NULL AND p.catalog_visible=1 AND p.status <> 'deleted'
                ORDER BY category, p.brand, p.name
            """)
            rows = list(cursor.fetchall())
    finally:
        connection.close()
    if category_code:
        category_name = next((name for name, code in CATEGORY_CODES.items() if code == category_code), None)
        if category_name is None:
            raise ValueError(f"Unknown category code: {category_code}. Choose A through P.")
        rows = [row for row in rows if row["category"] == category_name]
    return rows


def current_local_url(image_url: object) -> bool:
    raw = str(image_url or "")
    if not raw.startswith("/product-images/"):
        return False
    filename = raw.removeprefix("/product-images/")
    return Path(filename).name == filename and (IMAGE_ROOT / filename).is_file()


def save_result(product_id: str, image_url: str) -> None:
    sys.path.insert(0, str(BACKEND))
    from configuration import load_local_environment
    load_local_environment()
    from catalog_importer import connect

    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE products SET image_url=%s, updated_at=NOW() WHERE id=%s AND deleted_at IS NULL AND catalog_visible=1", (image_url, product_id))
            if cursor.rowcount != 1:
                raise RuntimeError(f"Product {product_id} is no longer visible; database row was not updated")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def append_log(row: dict[str, object]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not LOG_PATH.exists()
    with LOG_PATH.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LOG_FIELDS, extrasaction="ignore")
        if is_new:
            writer.writeheader()
        writer.writerow(row)
        stream.flush()


def sync_csv_exports(image_by_product_id: dict[str, str]) -> int:
    files = [CATALOG_DIR / "all_products.csv", *sorted(CATALOG_DIR.glob("[A-P]-*.csv"))]
    updates = 0
    for path in files:
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames or []
            rows = list(reader)
        if "image_url" not in fields:
            continue
        changed = False
        for row in rows:
            product_id = product_id_from_csv(row)
            image_url = image_by_product_id.get(product_id)
            if image_url and row.get("image_url", "") != image_url:
                row["image_url"] = image_url
                updates += 1
                changed = True
        if changed:
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
    return updates


def category_code_for(row: dict[str, object]) -> str:
    return CATEGORY_CODES.get(str(row.get("category") or ""), "?")


def process_category(code: str, collector: Collector) -> tuple[int, int, int]:
    rows = database_rows(code)
    print(f"\n=== Category {code}: {len(rows)} products ===", flush=True)
    success = missing = skipped = 0
    image_by_product_id: dict[str, str] = {}
    for index, product in enumerate(rows, start=1):
        product_id = str(product["id"])
        name = str(product.get("name") or "")
        if current_local_url(product.get("image_url")):
            skipped += 1
            image_by_product_id[product_id] = str(product["image_url"])
            append_log({"product_id": product_id, "category_code": code, "category": product["category"], "brand": product["brand"], "product": name, "model": product["model"], "status": "already_local", "image_url": product["image_url"]})
            continue
        try:
            local_url, image_source, status = collector.find_image(product)
            save_result(product_id, local_url)
            success += 1
            image_by_product_id[product_id] = local_url
            append_log({"product_id": product_id, "category_code": code, "category": product["category"], "brand": product["brand"], "product": name, "model": product["model"], "status": status, "image_url": local_url, "image_source_url": image_source, "source_page": product.get("product_url") or product.get("source_url")})
            print(f"[{code} {index}/{len(rows)}] OK {product.get('brand')} {name}", flush=True)
        except Exception as error:
            missing += 1
            append_log({"product_id": product_id, "category_code": code, "category": product["category"], "brand": product["brand"], "product": name, "model": product["model"], "status": "unresolved", "source_page": product.get("product_url") or product.get("source_url"), "detail": str(error)[:700]})
            print(f"[{code} {index}/{len(rows)}] UNRESOLVED {product.get('brand')} {name}: {str(error)[:220]}", flush=True)
        if index % 25 == 0:
            print(f"[{code}] checkpoint: {index}/{len(rows)} processed; {success} downloaded, {skipped} already local, {missing} unresolved", flush=True)
    csv_updates = sync_csv_exports(image_by_product_id)
    print(f"=== Category {code} complete: {success} downloaded, {skipped} already local, {missing} unresolved; {csv_updates} CSV row updates ===", flush=True)
    return success, skipped, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--category", choices=list(CATEGORY_CODES.values()), help="Process one category only (A-P)")
    group.add_argument("--all", action="store_true", help="Process categories A through P sequentially")
    parser.add_argument("--delay", type=float, default=0.35, help="Minimum seconds between requests to the same host")
    args = parser.parse_args()
    codes = list(CATEGORY_CODES.values()) if args.all else [args.category or "A"]
    collector = Collector(args.delay)
    total_success = total_skipped = total_missing = 0
    for code in codes:
        success, skipped, missing = process_category(code, collector)
        total_success += success
        total_skipped += skipped
        total_missing += missing
    print(f"\nImage collection complete: downloaded={total_success}, already_local={total_skipped}, unresolved={total_missing}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
