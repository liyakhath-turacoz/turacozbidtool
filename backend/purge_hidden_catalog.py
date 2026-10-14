"""Remove hidden legacy catalogue rows while retaining linked bid/cart snapshots.

Dry run by default. Run with --apply to purge rows from the live products table.
Snapshots are kept in product_reference_snapshots and exposed only through the
history-only product_reference_catalog view.
"""
from __future__ import annotations

import argparse

try:
    from .catalog_importer import connect
    from . import product_reference
except ImportError:
    from catalog_importer import connect
    import product_reference


LEGACY_WHERE = "p.catalog_visible=FALSE AND COALESCE(p.source,'') <> 'review_catalog'"


def counts(cursor):
    cursor.execute(f"SELECT COUNT(*) AS row_count FROM products p WHERE {LEGACY_WHERE}")
    total = cursor.fetchone()["row_count"]
    cursor.execute(f"""SELECT COUNT(DISTINCT p.id) AS row_count FROM products p
        WHERE {LEGACY_WHERE} AND (
          EXISTS(SELECT 1 FROM bid_requests br WHERE br.product_id=p.id)
          OR EXISTS(SELECT 1 FROM cart_items ci WHERE ci.product_id=p.id)
        )""")
    referenced = cursor.fetchone()["row_count"]
    cursor.execute(f"""SELECT COUNT(*) AS row_count FROM products p
        WHERE {LEGACY_WHERE} AND EXISTS(
          SELECT 1 FROM bid_requests br JOIN bids b ON b.bid_request_id=br.id
          WHERE br.product_id=p.id
        )""")
    with_bids = cursor.fetchone()["row_count"]
    cursor.execute(f"""SELECT COUNT(*) AS row_count FROM products p
        WHERE {LEGACY_WHERE} AND EXISTS(
          SELECT 1 FROM bid_requests br WHERE br.product_id=p.id AND br.status='active'
        )""")
    active_requests = cursor.fetchone()["row_count"]
    return {"legacy_rows": total, "referenced_product_snapshots": referenced,
            "products_with_bid_history": with_bids, "products_in_active_requests": active_requests}


def ensure_snapshot_schema(cursor):
    cursor.execute("CREATE TABLE IF NOT EXISTS product_reference_snapshots LIKE products")
    cursor.execute("""CREATE OR REPLACE VIEW product_reference_catalog AS
        SELECT p.* FROM products p WHERE (p.catalog_visible=TRUE AND p.deleted_at IS NULL)
          OR EXISTS (SELECT 1 FROM bid_requests br WHERE br.product_id=p.id)
          OR EXISTS (SELECT 1 FROM cart_items ci WHERE ci.product_id=p.id)
        UNION ALL SELECT s.* FROM product_reference_snapshots s
        WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.id=s.id)""")


def apply_purge(cursor, connection):
    ensure_snapshot_schema(cursor)
    cursor.execute(f"""INSERT IGNORE INTO product_reference_snapshots
        SELECT p.* FROM products p WHERE {LEGACY_WHERE} AND (
          EXISTS(SELECT 1 FROM bid_requests br WHERE br.product_id=p.id)
          OR EXISTS(SELECT 1 FROM cart_items ci WHERE ci.product_id=p.id)
        )""")
    product_reference.ensure_schema(cursor)
    cursor.execute("""DELETE source_row FROM product_source_records source_row
        JOIN products p ON p.id=source_row.product_id
        WHERE p.catalog_visible=FALSE AND COALESCE(p.source,'') <> 'review_catalog'""")
    cursor.execute(f"DELETE FROM products WHERE catalog_visible=FALSE AND COALESCE(source,'') <> 'review_catalog'")
    deleted=cursor.rowcount
    connection.commit()
    return deleted


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true",help="archive references and permanently purge hidden legacy products")
    args=parser.parse_args()
    with connect() as connection, connection.cursor() as cursor:
        before=counts(cursor)
        print("Before:",before)
        if not args.apply:
            print("Dry run only. Re-run with --apply to archive referenced history and delete hidden legacy products.")
            return
        deleted=apply_purge(cursor,connection)
        cursor.execute("SELECT COUNT(*) AS row_count FROM products WHERE catalog_visible=FALSE AND COALESCE(source,'') <> 'review_catalog'")
        remaining=cursor.fetchone()["row_count"]
        cursor.execute("SELECT COUNT(*) AS row_count FROM product_reference_snapshots")
        snapshots=cursor.fetchone()["row_count"]
        cursor.execute("""SELECT COUNT(*) AS row_count FROM bid_requests br
            LEFT JOIN product_reference_catalog p ON p.id=br.product_id
            WHERE p.id IS NULL""")
        broken_requests=cursor.fetchone()["row_count"]
        cursor.execute("""SELECT COUNT(*) AS row_count FROM cart_items ci
            LEFT JOIN product_reference_catalog p ON p.id=ci.product_id
            WHERE p.id IS NULL""")
        broken_cart_items=cursor.fetchone()["row_count"]
        print({"deleted_legacy_rows":deleted,"remaining_hidden_legacy_rows":remaining,
               "preserved_product_snapshots":snapshots,"broken_bid_request_products":broken_requests,
               "broken_cart_products":broken_cart_items})
        if remaining or broken_requests or broken_cart_items:
            raise RuntimeError("Legacy catalogue purge verification failed")


if __name__ == "__main__":
    main()
