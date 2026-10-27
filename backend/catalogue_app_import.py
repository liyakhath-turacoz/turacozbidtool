"""Import the reviewed, standalone A–P catalogue into the app.

Old product rows are hidden from product browsing but retained for bid, cart,
and audit references in replacement mode. Use --apply --append-only to insert
new catalog rows while leaving existing product rows and visibility untouched.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

try:
    from .catalog_importer import connect
    from . import catalog_filters
    from . import catalog_metadata
    from .catalog_validation import validate_snapshot
except ImportError:
    from catalog_importer import connect
    import catalog_filters
    import catalog_metadata
    from catalog_validation import validate_snapshot

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "product_catalog" / "all_products.csv"
BACKUP_PATH = ROOT / "backend" / "recovery" / ("catalog-visibility-" + datetime.now().strftime('%Y%m%dT%H%M%S%f') + '.csv')
NAMESPACE = uuid.UUID("3cdbf650-f7f2-4dbd-a90c-2dc89c6b67a1")


def stable_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{value}"))


def specification_highlights(specs: dict) -> dict:
    """Keep the highlight panel concise while the technical panels hold full details."""
    highlights = {}
    non_highlight = re.compile(
        r"\b(os|operating system|software|firmware|update|ios|ipados|android|"
        r"apple intelligence|siri|store sku|model code)\b",
        re.IGNORECASE,
    )
    preferred = (
        "model", "processor", "cpu name", "capacity", "storage", "memory (gb)", "ram",
        "display", "display size", "size (main display)", "camera", "rear camera - resolution",
        "battery", "battery capacity (mah, typical)",
    )
    for wanted in preferred:
        match = next((key for key in specs if key.casefold() == wanted), None)
        if match and match not in highlights:
            highlights[match] = specs[match]
        if len(highlights) >= 6:
            break
    for name, value in specs.items():
        if len(highlights) >= 6:
            break
        if not non_highlight.search(name) and name not in highlights:
            highlights[name] = value
    return highlights


def specification_groups(specs: dict) -> tuple[list[dict], list[dict]]:
    """Shape the reviewed flat CSV attributes for the web product-detail panels."""
    software_pattern = re.compile(
        r"\b(os|operating system|os version|software|firmware|security update|update policy|"
        r"app compatibility|compatible apps|supported os|ios|ipados|android version|"
        r"apple intelligence|siri|security platform)\b",
        re.IGNORECASE,
    )
    technical, software = [], []
    for name, value in specs.items():
        if value is None or not str(value).strip():
            continue
        item = {
            "id": re.sub(r"[^a-z0-9]+", "_", str(name).casefold()).strip("_") or "specification",
            "name": str(name).strip(),
            "value": str(value).strip(),
        }
        (software if software_pattern.search(str(name)) else technical).append(item)

    def group(group_id: str, name: str, features: list[dict]) -> list[dict]:
        return [{"id": group_id, "name": name, "features": features}] if features else []

    return (
        group("catalog_technical", "Technical specifications", technical),
        group("catalog_software", "Software specifications", software),
    )


def row_product_id(row):
    explicit=str(row.get('product_id') or '').strip()
    if explicit:return str(uuid.UUID(explicit))
    return stable_id('product','|'.join(row[k] for k in ('category_code','manufacturer','brand','model','product_name')))


def release_evidence_by_product(path: Path = ROOT / "product_catalog" / "release_research_evidence.csv") -> dict[str, dict]:
    """Load normalized year evidence so store-listing dates are not called releases."""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {
            str(row.get("product_id") or "").strip(): row
            for row in csv.DictReader(stream)
            if str(row.get("product_id") or "").strip()
        }


def release_date_basis(row: dict, evidence: dict | None = None) -> str:
    """Classify the date source conservatively; page dates are not launch dates."""
    kind = str((evidence or {}).get("evidence_kind") or "").casefold().replace("-", "_").replace(" ", "_")
    attribution = str(row.get("source_attribution") or "").casefold()
    if kind:
        if "icecat_explicit_release" in kind:
            return "icecat_explicit_release"
        if "model_year" in kind:
            if kind.startswith("manufacturer"):
                return "manufacturer_model_year"
            if kind.startswith("retailer"):
                return "retailer_model_year"
            return "model_year"
        if any(token in kind for token in ("store_listing", "first_available")):
            return "india_store_listing_year"
        if any(token in kind for token in ("availability", "available_on_market", "first_seen", "documentation_year", "initial_firmware", "family_coverage", "family_launch")):
            return "availability_or_documentation_date"
        if any(token in kind for token in ("release", "launch", "announcement")):
            return "manufacturer_release" if "manufacturer" in kind else "official_release_date"
        return "other_unverified_evidence"
    if "icecat_explicit_release" in attribution:
        return "icecat_explicit_release"
    if "manufacturer_model_year" in attribution:
        return "manufacturer_model_year"
    if "india_store_launch_year" in attribution:
        return "india_store_launch_year"
    if "manufacturer_release" in attribution:
        return "manufacturer_release"
    if any(token in attribution for token in ("store listing", "store inventory", "first available")):
        return "india_store_listing_year"
    return "unknown"


def rows_from_file(path: Path = CSV_PATH) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    validate_snapshot(rows, ROOT / 'product_catalog' / 'images')
    keys = [(r["category_code"], r["manufacturer"], r["brand"], r["model"], r["product_name"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("The standalone catalogue contains duplicate import identities")
    ids=[row_product_id(row) for row in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate product IDs in catalogue')
    for row in rows:
        if not all(row.get(key, "").strip() for key in ("department", "subcategory", "product_name", "brand")):
            raise ValueError(f"Incomplete category/product row: {row.get('product_name')}")
        specs = json.loads(row.get("specifications_json") or "{}")
        if not isinstance(specs, dict):
            raise ValueError(f"Specifications must be an object: {row['product_name']}")
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the new visible catalog to the configured database")
    parser.add_argument("--append-only", action="store_true", help="Insert only catalogue products that do not already exist; preserve all existing product rows and visibility")
    parser.add_argument('--csv', type=Path, default=CSV_PATH, help='Validated additive batch or canonical catalogue CSV')
    args = parser.parse_args(argv)
    if args.append_only and not args.apply:
        parser.error("--append-only requires --apply")
    products = rows_from_file(args.csv)
    release_evidence = release_evidence_by_product()
    if not args.apply:
        print(json.dumps({"mode": "dry-run", "products": len(products), "departments": len({r['department'] for r in products}), "brands": len({r['brand'] for r in products}), "csv": str(CSV_PATH)}, indent=2))
        return 0
    catalog_filters.ensure_schema(connect)
    catalog_metadata.ensure_schema(connect)
    conn = connect()
    backup_created = False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) total FROM products WHERE deleted_at IS NULL")
            old_total = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(*) total FROM products WHERE catalog_visible=TRUE AND deleted_at IS NULL")
            old_visible_total = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(*) total FROM products p WHERE p.deleted_at IS NULL AND (EXISTS (SELECT 1 FROM bid_requests br WHERE br.product_id=p.id AND br.status='active' AND br.deleted_at IS NULL) OR EXISTS (SELECT 1 FROM cart_items ci JOIN carts ca ON ca.id=ci.cart_id WHERE ci.product_id=p.id AND ca.status='active' AND ca.deleted_at IS NULL))")
            linked_live = int(cursor.fetchone()["total"])
            if not args.append_only and not BACKUP_PATH.exists():
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

            # Replacement mode intentionally hides the old catalog. Append-only mode never
            # updates an existing product row, including its visibility or timestamps.
            if not args.append_only:
                cursor.execute("UPDATE products SET catalog_visible=FALSE WHERE catalog_visible=TRUE")
            imported = 0
            skipped_existing = 0
            for row in products:
                parent_id, child_id = category_ids[(row["department"], row["subcategory"])]
                identity = "|".join((row["category_code"], row["manufacturer"], row["brand"], row["model"], row["product_name"]))
                source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
                product_id = row_product_id(row)
                release_basis = release_date_basis(row, release_evidence.get(product_id))
                if args.append_only:
                    cursor.execute("SELECT id FROM products WHERE id=%s", [product_id])
                    if cursor.fetchone():
                        skipped_existing += 1
                        continue
                specs = json.loads(row.get("specifications_json") or "{}")
                highlights = specification_highlights(specs)
                technical, software = specification_groups(specs)
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
                       description,highlights,technical_specifications,software_specifications,manual_specifications,price_min,price_max,image_url,source_url,product_url,price_source_url,
                       source_attribution,verification_status,catalog_notes,official_price,price_currency,price_type,price_market,
                       status,catalog_visible,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'review_catalog',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',TRUE,NOW(),NOW())
                    ON DUPLICATE KEY UPDATE category_id=VALUES(category_id),subcategory_id=VALUES(subcategory_id),name=VALUES(name),
                      brand=VALUES(brand),manufacturer=VALUES(manufacturer),model=VALUES(model),mpn=VALUES(mpn),gtin=VALUES(gtin),
                      release_year=VALUES(release_year),release_date=VALUES(release_date),release_date_precision=VALUES(release_date_precision),
                      release_date_basis=VALUES(release_date_basis),description=VALUES(description),highlights=VALUES(highlights),
                      technical_specifications=VALUES(technical_specifications),software_specifications=VALUES(software_specifications),
                      manual_specifications=VALUES(manual_specifications),price_min=VALUES(price_min),price_max=VALUES(price_max),
                      image_url=VALUES(image_url),source_url=VALUES(source_url),product_url=VALUES(product_url),price_source_url=VALUES(price_source_url),
                      source_attribution=VALUES(source_attribution),verification_status=VALUES(verification_status),catalog_notes=VALUES(catalog_notes),
                      official_price=VALUES(official_price),price_currency=VALUES(price_currency),price_type=VALUES(price_type),price_market=VALUES(price_market),
                      status='active',catalog_visible=TRUE,deleted_at=NULL,updated_at=NOW()
                """, [product_id,parent_id,child_id,row["product_name"][:255],(row.get("brand") or "")[:190],(row.get("manufacturer") or "")[:190],(row.get("model") or "")[:190],source_key,(row.get("manufacturer_part_number") or "")[:190] or None,(row.get("gtin") or "")[:255] or None,release_year,release_date,(row.get("release_date_precision") or "unknown")[:12],release_basis if release_date or release_year else "unknown",row.get("collected_on") or None,(row.get("description") or "")[:65000] or None,json.dumps(highlights,ensure_ascii=False),json.dumps(technical,ensure_ascii=False),json.dumps(software,ensure_ascii=False),json.dumps(specs,ensure_ascii=False),min_price,max_price,image,source_url,product_url,price_source_url,(row.get("source_attribution") or "")[:255] or None,(row.get("verification_status") or "")[:255] or None,(row.get("notes") or "")[:65000] or None,official_price,(row.get("price_currency") or "")[:8] or None,(row.get("price_type") or "")[:80] or None,(row.get("price_market") or "")[:80] or None])
                catalog_filters.index_product(cursor, {"id": product_id, "specifications": specs, "subcategory": row["subcategory"]})
                imported += 1
            cursor.execute("SELECT COUNT(*) total FROM products WHERE catalog_visible=TRUE AND deleted_at IS NULL")
            visible_total = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(DISTINCT COALESCE(NULLIF(manufacturer,''),brand)) total FROM products WHERE catalog_visible=TRUE AND deleted_at IS NULL")
            company_total = int(cursor.fetchone()["total"])
            expected_visible = len(products) if not args.append_only else old_visible_total + imported
            if not args.append_only and visible_total != expected_visible:
                raise RuntimeError(f"Expected {len(products)} visible rows after replacement, found {visible_total}")
            if args.append_only and visible_total != expected_visible:
                raise RuntimeError(f"Expected {expected_visible} visible rows after append-only import, found {visible_total}")
        with conn.cursor() as cursor:catalog_metadata.restore_bundle(cursor)
        conn.commit()
        print(json.dumps({"status": "imported", "mode": "append-only" if args.append_only else "replacement", "imported_rows": imported, "skipped_existing_rows": skipped_existing, "visible_total": visible_total, "companies": company_total, "old_active_rows_preserved_for_bids_or_cart": linked_live, "old_rows_total": old_total, "backup": str(BACKUP_PATH) if backup_created else None}, indent=2))
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
