"""Keep bid and cart product identities valid after catalogue purges."""


REFERENCE_TABLES = {
    "bid_requests": "fk_bid_requests_product_registry",
    "cart_items": "fk_cart_items_product_registry",
}


def ensure_schema(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_identity_registry (
            product_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
            PRIMARY KEY (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    cursor.execute("""
        INSERT IGNORE INTO product_identity_registry (product_id)
        SELECT p.id FROM products p
        WHERE (p.catalog_visible=TRUE AND p.deleted_at IS NULL)
          OR EXISTS (SELECT 1 FROM bid_requests br WHERE br.product_id=p.id)
          OR EXISTS (SELECT 1 FROM cart_items ci WHERE ci.product_id=p.id)
    """)
    cursor.execute("""
        INSERT IGNORE INTO product_identity_registry (product_id)
        SELECT s.id FROM product_reference_snapshots s
    """)

    cursor.execute("""
        SELECT TABLE_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
          AND TABLE_NAME IN ('bid_requests','cart_items') AND COLUMN_NAME='product_id'
    """)
    for row in cursor.fetchall():
        if row["REFERENCED_TABLE_NAME"] == "products":
            table = row["TABLE_NAME"]
            constraint = row["CONSTRAINT_NAME"].replace("`", "``")
            cursor.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{constraint}`")

    for table, constraint in REFERENCE_TABLES.items():
        cursor.execute("""
            SELECT COUNT(*) AS count FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME='product_id'
              AND REFERENCED_TABLE_NAME='product_identity_registry'
        """, [table])
        if cursor.fetchone()["count"] == 0:
            cursor.execute(
                f"ALTER TABLE `{table}` ADD CONSTRAINT `{constraint}` "
                "FOREIGN KEY (`product_id`) REFERENCES `product_identity_registry` (`product_id`) ON DELETE RESTRICT"
            )


def register_product(cursor, product_id):
    cursor.execute(
        "INSERT IGNORE INTO product_identity_registry (product_id) VALUES (%s)",
        [product_id],
    )
