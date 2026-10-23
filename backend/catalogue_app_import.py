"""Import the reviewed, standalone A–P catalogue as the app's visible catalog.

Old product rows are hidden from product browsing but retained for bid, cart,
and audit references. Run with --apply to perform the transactional import.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

try:
    from .catalog_importer import connect
    from . import catalog_filters
    from .catalog_validation import validate_snapshot
except ImportError:
    from catalog_importer import connect
    import catalog_filters
    from catalog_validation import validate_snapshot

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "product_catalog" / "all_products.csv"
BACKUP_PATH = ROOT / "backend" / "recovery" / ("catalog-visibility-" + datetime.now().strftime('%Y%m%dT%H%M%S%f') + '.csv')
NAMESPACE = uuid.UUID("3cdbf650-f7f2-4dbd-a90c-2dc89c6b67a1")


def stable_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{value}"))


def rows_from_file() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    validate_snapshot(rows, ROOT / 'product_catalog' / 'images')
    keys = [(r["category_code"], r["manufacturer"], r["brand"], r["model"], r["product_name"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("The standalone catalogue contains duplicate import identities")
    for row in rows:
        if not all(row.get(key, "").strip() for key in ("department", "subcategory", "product_name", "brand")):
            raise ValueError(f"Incomplete category/product row: {row.get('product_name')}")
        specs = json.loads(row.get("specifications_json") or "{}")
        if not isinstance(specs, dict):
            raise ValueError(f"Specifications must be an object: {row['product_name']}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the new visible catalog to the configured database")
    args = parser.parse_args()
    products = rows_from_file()
    if not args.apply:
        print(json.dumps({"mode": "dry-run", "products": len(products), "departments": len({r['department'] for r in products}), "brands": len({r['brand'] for r in products}), "csv": str(CSV_PATH)}, indent=2))
        return 0
    catalog_filters.ensure_schema(connect)
    conn = connect()
    backup_created = False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) total FROM products WHERE deleted_at IS NULL")
            old_total = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(*) total FROM products p WHERE p.deleted_at IS NULL AND (EXISTS (SELECT 1 FROM bid_requests br WHERE br.product_id=p.id AND br.status='active' AND br.deleted_at IS NULL) OR EXISTS (SELECT 1 FROM cart_items ci JOIN carts ca ON ca.id=ci.cart_id WHERE ci.product_id=p.id AND ca.status='active' AND ca.deleted_at IS NULL))")
            linked_live = int(cursor.fetchone()["total"])
            if not BACKUP_PATH.exists():
                BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
                cursor.execute("SELECT id,catalog_visible FROM products")
                visibility = cursor.fetchall()
                with BACKUP_PATH.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=["product_id", "catalog_visible"])
                    writer.writeheader()
                    writer.writerows({"product_id": r["id"], "catalog_visible": int(r["catalog_visible"])} for r in visibility)
                backup_created = True

            category_ids: dict[tuple[str, str], tuple[str, str]] = {}
            for department, subcategory in sorted({(r["department"], r["subcategory"]) for r in products}):
                cursor.execute("SELECT id FROM categories WHERE parent_id IS NULL AND name=%s AND deleted_at IS NULL ORDER BY created_at LIMIT 1", [department])
                parent = cursor.fetchone()
                parent_id = parent["id"] if parent else stable_id("department", department)
                if not parent:
                    cursor.execute("INSERT INTO categories (id,parent_id,name,status,created_at,updated_at) VALUES (%s,NULL,%s,'active',NOW(),NOW())", [parent_id, department])
                cursor.execute("SELECT id FROM categories WHERE parent_id=%s AND name=%s AND deleted_at IS NULL ORDER BY created_at LIMIT 1", [parent_id, subcategory])
                child = cursor.fetchone()
                child_id = child["id"] if child else stable_id("subcategory", f"{department}|{subcategory}")
                if not child:
                    cursor.execute("INSERT INTO categories (id,parent_id,name,status,created_at,updated_at) VALUES (%s,%s,%s,'active',NOW(),NOW())", [child_id, parent_id, subcategory])
                category_ids[(department, subcategory)] = (parent_id, child_id)

            # This affects only the visibility marker; bid/cart/history rows and products remain intact.
            cursor.execute("UPDATE products SET catalog_visible=FALSE WHERE catalog_visible=TRUE")
            imported = 0
            for row in products:
                parent_id, child_id = category_ids[(row["department"], row["subcategory"])]
                identity = "|".join((row["category_code"], row["manufacturer"], row["brand"], row["model"], row["product_name"]))
                source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
                product_id = stable_id("product", identity)
                specs = json.loads(row.get("specifications_json") or "{}")
                release_year = int(row["release_year"]) if row.get("release_year", "").isdigit() else None
                raw_release_date = (row.get("release_date") or "").strip()
                try:
                    precision = (row.get("release_date_precision") or "unknown").strip().casefold()
                    release_date = date.fromisoformat(raw_release_date).isoformat() if len(raw_release_date) == 10 and precision in {"day", "date", "release_date"} else None
                except ValueError:
                    release_date = None
                min_price = max_price = 0
                official_price = None
                try:
                    official_price = Decimal((row.get("official_price") or "").replace(",", "").strip())
                    if official_price < 0 or official_price > Decimal("999999999999.99"):
                        official_price = None
                except (InvalidOperation, AttributeError):
                    official_price = None
                if official_price is not None and row.get("price_currency", "").upper() == "INR" and row.get("price_market", "").casefold() == "india":
                    min_price = max_price = official_price
                image = (row.get("image_url") or "").strip() or None
                if image and len(image) > 500:
                    image = None
                source_url = (row.get("product_source_url") or row.get("product_url") or "").strip() or None
                if source_url and len(source_url) > 1000:
                    source_url = source_url[:1000]
                product_url = (row.get("product_url") or "").strip() or None
                if product_url and len(product_url) > 1000:
                    product_url = product_url[:1000]
                price_source_url = (row.get("price_source_url") or "").strip() or None
                if price_source_url and len(price_source_url) > 1000:
                    price_source_url = price_source_url[:1000]
                cursor.execute("""
                    INSERT INTO products
                      (id,category_id,subcategory_id,name,brand,manufacturer,model,source,source_product_id,mpn,gtin,
                       release_year,release_date,release_date_precision,release_date_basis,catalog_added_at,
                       description,highlights,manual_specifications,price_min,price_max,image_url,source_url,product_url,price_source_url,
                       source_attribution,verification_status,catalog_notes,official_price,price_currency,price_type,price_market,
                       status,catalog_visible,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'review_catalog',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',TRUE,NOW(),NOW())
                    ON DUPLICATE KEY UPDATE category_id=VALUES(category_id),subcategory_id=VALUES(subcategory_id),name=VALUES(name),
                      brand=VALUES(brand),manufacturer=VALUES(manufacturer),model=VALUES(model),mpn=VALUES(mpn),gtin=VALUES(gtin),
                      release_year=VALUES(release_year),release_date=VALUES(release_date),release_date_precision=VALUES(release_date_precision),
                      release_date_basis=VALUES(release_date_basis),description=VALUES(description),highlights=VALUES(highlights),
                      manual_specifications=VALUES(manual_specifications),price_min=VALUES(price_min),price_max=VALUES(price_max),
                      image_url=VALUES(image_url),source_url=VALUES(source_url),product_url=VALUES(product_url),price_source_url=VALUES(price_source_url),
                      source_attribution=VALUES(source_attribution),verification_status=VALUES(verification_status),catalog_notes=VALUES(catalog_notes),
                      official_price=VALUES(official_price),price_currency=VALUES(price_currency),price_type=VALUES(price_type),price_market=VALUES(price_market),
                      status='active',catalog_visible=TRUE,deleted_at=NULL,updated_at=NOW()
                """, [product_id,parent_id,child_id,row["product_name"][:255],(row.get("brand") or "")[:190],(row.get("manufacturer") or "")[:190],(row.get("model") or "")[:190],source_key,(row.get("manufacturer_part_number") or "")[:190] or None,(row.get("gtin") or "")[:255] or None,release_year,release_date,(row.get("release_date_precision") or "unknown")[:12],"official_release_date" if release_date else "unknown",row.get("collected_on") or None,(row.get("description") or "")[:65000] or None,json.dumps(specs,ensure_ascii=False),json.dumps(specs,ensure_ascii=False),min_price,max_price,image,source_url,product_url,price_source_url,(row.get("source_attribution") or "")[:255] or None,(row.get("verification_status") or "")[:255] or None,(row.get("notes") or "")[:65000] or None,official_price,(row.get("price_currency") or "")[:8] or None,(row.get("price_type") or "")[:80] or None,(row.get("price_market") or "")[:80] or None])
                catalog_filters.index_product(cursor, {"id": product_id, "specifications": specs, "subcategory": row["subcategory"]})
                imported += 1
            cursor.execute("SELECT COUNT(*) total FROM products WHERE catalog_visible=TRUE AND deleted_at IS NULL")
            visible_total = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(DISTINCT COALESCE(NULLIF(manufacturer,''),brand)) total FROM products WHERE catalog_visible=TRUE AND deleted_at IS NULL")
            company_total = int(cursor.fetchone()["total"])
            if visible_total != len(products):
                raise RuntimeError(f"Expected {len(products)} visible rows after replacement, found {visible_total}")
        conn.commit()
        print(json.dumps({"status": "imported", "imported_rows": imported, "visible_total": visible_total, "companies": company_total, "old_active_rows_preserved_for_bids_or_cart": linked_live, "old_rows_total": old_total, "backup": str(BACKUP_PATH)}, indent=2))
    except Exception:
        conn.rollback()
        if backup_created and BACKUP_PATH.exists():
            BACKUP_PATH.unlink()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
