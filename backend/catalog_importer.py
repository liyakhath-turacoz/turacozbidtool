from __future__ import annotations

import argparse
from contextlib import suppress
import gzip
import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import pymysql

try:
    from .configuration import load_local_environment
    from .database_health import assert_tables_readable
except ImportError:
    from configuration import load_local_environment
    from database_health import assert_tables_readable


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRODUCTS_ROOT = ROOT / "products"
DB_HOST = os.getenv("TURACOZ_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("TURACOZ_DB_PORT", "3306"))
DB_USER = os.getenv("TURACOZ_DB_USER", "turacoz_app")
DB_PASSWORD = os.getenv("TURACOZ_DB_PASSWORD", "")
DB_NAME = os.getenv("TURACOZ_DB_NAME", "turacoz_bidtool")
CATALOG_NAMESPACE = uuid.UUID("b43f862d-c48e-49b4-89c6-e77e2779ad4e")


def connect():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def stable_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(CATALOG_NAMESPACE, f"{kind}:{value}"))


def json_text(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def parse_source_datetime(value: Any) -> datetime | None:
    raw = "".join(ch for ch in str(value or "") if ch.isdigit())
    for length, pattern in ((14, "%Y%m%d%H%M%S"), (8, "%Y%m%d")):
        if len(raw) >= length:
            try:
                return datetime.strptime(raw[:length], pattern)
            except ValueError:
                pass
    return None


def ensure_column(cursor, table: str, column: str, definition: str) -> None:
    cursor.execute(
        """
        SELECT COUNT(*) AS count FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
        """,
        (DB_NAME, table, column),
    )
    if cursor.fetchone()["count"] == 0:
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")


def index_exists(cursor, table: str, index: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS count FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND INDEX_NAME=%s
        """,
        (DB_NAME, table, index),
    )
    return cursor.fetchone()["count"] > 0


def index_columns(cursor, table: str, index: str) -> list[str]:
    cursor.execute(
        """
        SELECT COLUMN_NAME FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND INDEX_NAME=%s
        ORDER BY SEQ_IN_INDEX
        """,
        (DB_NAME, table, index),
    )
    return [row["COLUMN_NAME"] for row in cursor.fetchall()]


def ensure_catalog_schema(conn) -> None:
    with conn.cursor() as cursor:
        product_columns = {
            "source": "VARCHAR(40) NOT NULL DEFAULT 'manual' AFTER model",
            "source_product_id": "VARCHAR(80) NULL AFTER source",
            "mpn": "VARCHAR(190) NULL AFTER source_product_id",
            "gtin": "VARCHAR(255) NULL AFTER mpn",
            "release_year": "SMALLINT NULL AFTER gtin",
            "source_updated_at": "DATETIME NULL AFTER release_year",
            "icecat_quality": "VARCHAR(30) NULL AFTER source_updated_at",
            "summary_description": "TEXT NULL AFTER description",
            "highlights": "JSON NULL AFTER summary_description",
            "technical_specifications": "JSON NULL AFTER highlights",
            "software_specifications": "JSON NULL AFTER technical_specifications",
            "gallery": "JSON NULL AFTER software_specifications",
            "multimedia": "JSON NULL AFTER gallery",
        }
        for column, definition in product_columns.items():
            ensure_column(cursor, "products", column, definition)
        if not index_exists(cursor, "products", "uq_products_source_product"):
            cursor.execute(
                "ALTER TABLE products ADD UNIQUE KEY uq_products_source_product (source, source_product_id)"
            )
        if not index_exists(cursor, "products", "idx_products_release_source"):
            cursor.execute(
                "ALTER TABLE products ADD KEY idx_products_release_source (release_year, source, status)"
            )

        for column, definition in {
            "spec_group": "VARCHAR(120) NOT NULL DEFAULT 'Highlights' AFTER spec_name",
            "feature_id": "VARCHAR(80) NULL AFTER spec_group",
            "unit": "VARCHAR(40) NULL AFTER spec_value",
            "spec_type": "VARCHAR(40) NULL AFTER unit",
            "description": "TEXT NULL AFTER spec_type",
        }.items():
            ensure_column(cursor, "product_specifications", column, definition)
        cursor.execute(
            """
            SELECT DATA_TYPE AS data_type FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='product_specifications' AND COLUMN_NAME='spec_value'
            """,
            (DB_NAME,),
        )
        if cursor.fetchone()["data_type"].lower() != "text":
            if index_exists(cursor, "product_specifications", "idx_spec_search"):
                cursor.execute("ALTER TABLE product_specifications DROP INDEX idx_spec_search")
            cursor.execute("ALTER TABLE product_specifications MODIFY spec_value TEXT NOT NULL")
        if index_columns(cursor, "product_specifications", "uq_product_spec") != [
            "product_id",
            "spec_group",
            "spec_name",
        ]:
            if not index_exists(cursor, "product_specifications", "idx_specs_product"):
                cursor.execute(
                    "ALTER TABLE product_specifications ADD KEY idx_specs_product (product_id)"
                )
            if index_exists(cursor, "product_specifications", "uq_product_spec"):
                cursor.execute("ALTER TABLE product_specifications DROP INDEX uq_product_spec")
            cursor.execute(
                """
                ALTER TABLE product_specifications
                ADD UNIQUE KEY uq_product_spec (product_id, spec_group, spec_name)
                """
            )
        if not index_exists(cursor, "product_specifications", "idx_spec_search"):
            cursor.execute(
                "ALTER TABLE product_specifications ADD KEY idx_spec_search (spec_name, spec_value(100))"
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS product_assets (
              id CHAR(36) PRIMARY KEY,
              product_id CHAR(36) NOT NULL,
              asset_type VARCHAR(40) NOT NULL,
              url VARCHAR(1000) NOT NULL,
              thumbnail_url VARCHAR(1000) NULL,
              content_type VARCHAR(120) NULL,
              description VARCHAR(500) NULL,
              width INT NOT NULL DEFAULT 0,
              height INT NOT NULL DEFAULT 0,
              sort_order INT NOT NULL DEFAULT 0,
              created_at DATETIME NOT NULL,
              UNIQUE KEY uq_product_asset (product_id, asset_type, url(400)),
              KEY idx_product_assets_product_sort (product_id, asset_type, sort_order),
              CONSTRAINT fk_product_assets_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_imports (
              id CHAR(36) PRIMARY KEY,
              catalog_version VARCHAR(80) NOT NULL UNIQUE,
              manifest_hash CHAR(64) NOT NULL,
              status ENUM('importing','completed','failed') NOT NULL,
              product_count INT NOT NULL DEFAULT 0,
              imported_count INT NOT NULL DEFAULT 0,
              error_message TEXT NULL,
              started_at DATETIME NOT NULL,
              completed_at DATETIME NULL,
              updated_at DATETIME NOT NULL,
              KEY idx_catalog_import_status (status, updated_at)
            ) ENGINE=InnoDB
            """
        )
    conn.commit()


def iter_bundle_records(products_root: Path, manifest: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for relative_path in sorted(manifest.get("files") or {}):
        path = products_root / relative_path
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)


def validate_bundle(products_root: Path, manifest: dict[str, Any]) -> None:
    for relative_path, expected in (manifest.get("files") or {}).items():
        path = products_root / relative_path
        if not path.is_file():
            raise RuntimeError(f"Missing catalog shard: {relative_path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(f"Checksum mismatch for catalog shard: {relative_path}")


def category_id(cursor, name: str, parent_id: str | None) -> str:
    if parent_id is None:
        cursor.execute(
            "SELECT id FROM categories WHERE name=%s AND parent_id IS NULL AND deleted_at IS NULL LIMIT 1",
            (name,),
        )
    else:
        cursor.execute(
            "SELECT id FROM categories WHERE name=%s AND parent_id=%s AND deleted_at IS NULL LIMIT 1",
            (name, parent_id),
        )
    row = cursor.fetchone()
    if row:
        return row["id"]
    identifier = stable_id("category", f"{parent_id or 'root'}:{name}")
    cursor.execute(
        """
        INSERT INTO categories (id, parent_id, name, status, created_at, updated_at)
        VALUES (%s, %s, %s, 'active', NOW(), NOW())
        """,
        (identifier, parent_id, name),
    )
    return identifier


def flush_sample_catalog(cursor) -> None:
    # The local seed transaction data references the disposable sample products.
    cursor.execute("UPDATE bid_requests SET winning_bid_id=NULL")
    cursor.execute("DELETE FROM report_messages")
    cursor.execute("DELETE FROM reports")
    cursor.execute("UPDATE invoices SET bid_id=NULL")
    cursor.execute("DELETE FROM commissions")
    cursor.execute("DELETE FROM bids")
    cursor.execute("DELETE FROM bid_request_fields")
    cursor.execute("DELETE FROM bid_request_dealers")
    cursor.execute("DELETE FROM bid_requests")
    cursor.execute("DELETE FROM cart_items")
    cursor.execute("DELETE FROM product_assets")
    cursor.execute("DELETE FROM product_specifications")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM catalog_imports")


def upsert_product(cursor, record: dict[str, Any], electronics_id: str, subcategory_id: str) -> str:
    source_id = str(record["source_product_id"])
    product_id = stable_id("icecat-product", source_id)
    highlights = record.get("highlights") or {}
    cursor.execute(
        """
        INSERT INTO products (
          id, category_id, subcategory_id, location_id, name, brand, model,
          source, source_product_id, mpn, gtin, release_year, source_updated_at,
          icecat_quality, description, summary_description, highlights,
          technical_specifications, software_specifications, gallery, multimedia,
          price_min, price_max, image_url, status, created_by, created_at, updated_at, deleted_at
        ) VALUES (
          %s,%s,%s,NULL,%s,%s,%s,
          'icecat',%s,%s,%s,%s,%s,
          %s,%s,%s,%s,
          %s,%s,%s,%s,
          0,0,%s,'active',NULL,NOW(),NOW(),NULL
        )
        ON DUPLICATE KEY UPDATE
          category_id=VALUES(category_id), subcategory_id=VALUES(subcategory_id),
          name=VALUES(name), brand=VALUES(brand), model=VALUES(model), mpn=VALUES(mpn),
          gtin=VALUES(gtin), release_year=VALUES(release_year),
          source_updated_at=VALUES(source_updated_at), icecat_quality=VALUES(icecat_quality),
          description=VALUES(description), summary_description=VALUES(summary_description),
          highlights=VALUES(highlights), technical_specifications=VALUES(technical_specifications),
          software_specifications=VALUES(software_specifications), gallery=VALUES(gallery),
          multimedia=VALUES(multimedia), image_url=VALUES(image_url), status='active',
          deleted_at=NULL, updated_at=NOW()
        """,
        (
            product_id,
            electronics_id,
            subcategory_id,
            str(record.get("name") or "Unnamed product")[:190],
            str(record.get("brand") or "")[:120],
            str(record.get("model") or "")[:120],
            source_id,
            str(record.get("mpn") or "")[:190],
            ",".join(record.get("gtins") or [])[:255],
            record.get("release_year"),
            parse_source_datetime(record.get("source_updated_at")),
            str(record.get("quality") or "")[:30],
            str(record.get("description") or "")[:65_000],
            str(record.get("summary_description") or "")[:65_000],
            json_text(highlights),
            json_text(record.get("technical_specifications") or []),
            json_text(record.get("software_specifications") or []),
            json_text(record.get("gallery") or []),
            json_text(record.get("multimedia") or []),
            str(record.get("image_url") or "")[:500],
        ),
    )
    cursor.execute("DELETE FROM product_specifications WHERE product_id=%s", (product_id,))
    for order, (name, value) in enumerate(highlights.items()):
        cursor.execute(
            """
            INSERT INTO product_specifications
            (id, product_id, spec_name, spec_group, feature_id, spec_value, unit, spec_type,
             description, sort_order, created_at, updated_at)
            VALUES (%s,%s,%s,'Highlights',NULL,%s,NULL,NULL,NULL,%s,NOW(),NOW())
            """,
            (stable_id("highlight", f"{source_id}:{name}"), product_id, str(name)[:120], str(value), order),
        )
    cursor.execute("DELETE FROM product_assets WHERE product_id=%s", (product_id,))
    seen_urls: set[str] = set()
    for asset_type, assets in (
        ("image", record.get("gallery") or []),
        ("multimedia", record.get("multimedia") or []),
    ):
        for order, asset in enumerate(assets[:30]):
            url = str(asset.get("url") or "")[:1000]
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            cursor.execute(
                """
                INSERT INTO product_assets
                (id, product_id, asset_type, url, thumbnail_url, content_type, description,
                 width, height, sort_order, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                """,
                (
                    stable_id("asset", f"{source_id}:{asset_type}:{url}"),
                    product_id,
                    asset_type,
                    url,
                    str(asset.get("thumbnail_url") or "")[:1000],
                    str(asset.get("content_type") or "")[:120],
                    str(asset.get("description") or "")[:500],
                    int(asset.get("width") or 0),
                    int(asset.get("height") or 0),
                    order,
                ),
            )
    return product_id


def import_bundle_if_needed(
    products_root: Path = DEFAULT_PRODUCTS_ROOT,
    replace_existing: bool = False,
) -> dict[str, Any]:
    products_root = products_root.resolve()
    manifest_path = products_root / "manifest.json"
    if not manifest_path.is_file():
        return {"status": "skipped", "reason": "manifest_not_found"}
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    validate_bundle(products_root, manifest)
    version = str(manifest["catalog_version"])

    conn = connect()
    lock_acquired = False
    import_started = False
    try:
        assert_tables_readable(conn)
        ensure_catalog_schema(conn)
        with conn.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK('turacoz_catalog_import', 120) AS acquired")
            lock_acquired = cursor.fetchone()["acquired"] == 1
            if not lock_acquired:
                raise RuntimeError("Could not acquire the catalog import lock")
            cursor.execute(
                "SELECT status, manifest_hash, imported_count FROM catalog_imports WHERE catalog_version=%s",
                (version,),
            )
            existing = cursor.fetchone()
            if existing and existing["status"] == "completed" and existing["manifest_hash"] == manifest_hash:
                return {"status": "already_imported", "imported_count": existing["imported_count"]}
            if replace_existing:
                flush_sample_catalog(cursor)
            import_id = stable_id("catalog-import", version)
            cursor.execute(
                """
                INSERT INTO catalog_imports
                (id, catalog_version, manifest_hash, status, product_count, imported_count,
                 started_at, updated_at)
                VALUES (%s,%s,%s,'importing',%s,0,NOW(),NOW())
                ON DUPLICATE KEY UPDATE manifest_hash=VALUES(manifest_hash), status='importing',
                  product_count=VALUES(product_count), error_message=NULL, updated_at=NOW()
                """,
                (import_id, version, manifest_hash, int(manifest.get("product_count") or 0)),
            )
            electronics_id = category_id(cursor, "Electronics", None)
            subcategory_ids = {
                name: category_id(cursor, name, electronics_id)
                for name in (manifest.get("category_counts") or {})
            }
            conn.commit()
            import_started = True

        imported = 0
        with conn.cursor() as cursor:
            for record in iter_bundle_records(products_root, manifest):
                subcategory = str(record.get("subcategory") or "Other electronics")
                subcategory_identifier = subcategory_ids.get(subcategory)
                if not subcategory_identifier:
                    subcategory_identifier = category_id(cursor, subcategory, electronics_id)
                    subcategory_ids[subcategory] = subcategory_identifier
                upsert_product(cursor, record, electronics_id, subcategory_identifier)
                imported += 1
                if imported % 200 == 0:
                    cursor.execute(
                        "UPDATE catalog_imports SET imported_count=%s, updated_at=NOW() WHERE id=%s",
                        (imported, import_id),
                    )
                    conn.commit()
                    print(f"Imported {imported:,}/{manifest.get('product_count', 0):,} products")
            cursor.execute(
                """
                UPDATE catalog_imports SET status='completed', imported_count=%s,
                  completed_at=NOW(), updated_at=NOW() WHERE id=%s
                """,
                (imported, import_id),
            )
            conn.commit()
        return {"status": "completed", "imported_count": imported, "catalog_version": version}
    except Exception as exc:
        with suppress(pymysql.MySQLError):
            conn.rollback()
        if import_started:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE catalog_imports SET status='failed', error_message=%s, updated_at=NOW()
                        WHERE catalog_version=%s
                        """,
                        (str(exc)[:4000], version),
                    )
                    conn.commit()
            except Exception:
                with suppress(pymysql.MySQLError):
                    conn.rollback()
        raise
    finally:
        if lock_acquired:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT RELEASE_LOCK('turacoz_catalog_import')")
                conn.commit()
            except Exception:
                pass
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the generated Icecat bundle into MariaDB")
    parser.add_argument("--products-root", type=Path, default=DEFAULT_PRODUCTS_ROOT)
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete the disposable sample catalog and its dependent bid/cart data first",
    )
    args = parser.parse_args()
    print(import_bundle_if_needed(args.products_root, replace_existing=args.replace_existing))


if __name__ == "__main__":
    main()
