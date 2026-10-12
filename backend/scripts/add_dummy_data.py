"""Add repeatable local demo accounts and one example bid without clearing data."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as server


HUBS = [
    ("India", "Delhi", "Delhi", "Demo Hub", "110001", 28.6139, 77.2090),
    ("India", "Maharashtra", "Mumbai", "Demo Hub", "400001", 19.0760, 72.8777),
    ("India", "Tamil Nadu", "Chennai", "Demo Hub", "600001", 13.0827, 80.2707),
    ("India", "West Bengal", "Kolkata", "Demo Hub", "700001", 22.5726, 88.3639),
    ("India", "Andhra Pradesh", "Ongole", "Demo Hub", "523001", 15.5050, 80.0450),
]


def ensure_role(cursor, name: str) -> str:
    cursor.execute("SELECT id FROM roles WHERE name=%s", [name])
    row = cursor.fetchone()
    if row:
        return row["id"]
    role_id = server.new_id()
    cursor.execute(
        "INSERT INTO roles (id, name, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
        [role_id, name],
    )
    return role_id


def ensure_location(cursor, hub: tuple) -> str:
    country, state, city, area, pincode, latitude, longitude = hub
    cursor.execute(
        """
        SELECT id FROM locations
        WHERE country=%s AND state=%s AND city=%s AND area=%s AND pincode=%s AND deleted_at IS NULL
        LIMIT 1
        """,
        [country, state, city, area, pincode],
    )
    row = cursor.fetchone()
    if row:
        return row["id"]
    location_id = server.new_id()
    cursor.execute(
        """
        INSERT INTO locations
          (id, country, state, city, area, address_line, pincode, latitude, longitude,
           service_radius_km, status, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,'Demo service location',%s,%s,%s,500,'active',NOW(),NOW())
        """,
        [location_id, country, state, city, area, pincode, latitude, longitude],
    )
    return location_id


def ensure_category(cursor, name: str, parent_id: str | None = None) -> str:
    cursor.execute(
        "SELECT id FROM categories WHERE name=%s AND parent_id <=> %s AND deleted_at IS NULL LIMIT 1",
        [name, parent_id],
    )
    row = cursor.fetchone()
    if row:
        return row["id"]
    category_id = server.new_id()
    cursor.execute(
        """
        INSERT INTO categories (id, name, parent_id, status, created_at, updated_at)
        VALUES (%s,%s,%s,'active',NOW(),NOW())
        """,
        [category_id, name, parent_id],
    )
    return category_id


def ensure_user(cursor, username: str, role_id: str, status: str, full_name: str, phone: str) -> str:
    cursor.execute("SELECT id FROM users WHERE email=%s", [username])
    row = cursor.fetchone()
    if row:
        user_id = row["id"]
        cursor.execute(
            """
            UPDATE users SET role_id=%s, password_hash=%s, full_name=%s, phone=%s,
              status=%s, deleted_at=NULL, updated_at=NOW()
            WHERE id=%s
            """,
            [role_id, server.hash_password(username), full_name, phone, status, user_id],
        )
        return user_id
    user_id = server.new_id()
    cursor.execute(
        """
        INSERT INTO users (id, role_id, email, password_hash, full_name, phone, status, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
        """,
        [user_id, role_id, username, server.hash_password(username), full_name, phone, status],
    )
    return user_id


def ensure_demo_products(cursor, admin_id: str, location_id: str, category_ids: dict[str, str]) -> None:
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM products p
        JOIN categories c ON c.id=p.category_id AND c.status='active' AND c.deleted_at IS NULL
        LEFT JOIN categories sc ON sc.id=p.subcategory_id
        WHERE p.status='active' AND p.deleted_at IS NULL
          AND (p.subcategory_id IS NULL OR (sc.status='active' AND sc.deleted_at IS NULL))
        """
    )
    if int(cursor.fetchone()["count"]):
        return
    demos = [
        ("Demo Lenovo Business Laptop", "Lenovo", "T14-Demo", 55000, 72000, "Laptops", {"RAM": "16 GB", "Storage": "512 GB SSD"}),
        ("Demo Samsung Smartphone", "Samsung", "S24-Demo", 45000, 65000, "Smartphones", {"Storage": "256 GB", "Display": "6.2 inch"}),
        ("Demo Dell Monitor", "Dell", "P2425-Demo", 15000, 22000, "Monitors", {"Size": "24 inch", "Resolution": "Full HD"}),
    ]
    for name, brand, model, price_min, price_max, subcategory, specs in demos:
        product_id = server.new_id()
        cursor.execute(
            """
            INSERT INTO products
              (id, category_id, subcategory_id, location_id, name, brand, model,
               price_min, price_max, status, created_by, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,NOW(),NOW())
            """,
            [
                product_id,
                category_ids["Electronics"],
                category_ids[subcategory],
                location_id,
                name,
                brand,
                model,
                price_min,
                price_max,
                admin_id,
            ],
        )
        for index, (key, value) in enumerate(specs.items()):
            cursor.execute(
                """
                INSERT INTO product_specifications
                  (id, product_id, spec_name, spec_value, sort_order, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,NOW(),NOW())
                """,
                [server.new_id(), product_id, key, value, index],
            )


def seed_sample_bid() -> None:
    with server.db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS count FROM bid_requests WHERE status='active' AND deleted_at IS NULL AND expires_at>NOW()")
        if int(cursor.fetchone()["count"]):
            return
        cursor.execute("SELECT id FROM users WHERE email='buyer1' AND deleted_at IS NULL")
        buyer = cursor.fetchone()
        cursor.execute(
            """
            SELECT p.id, p.price_min
            FROM products p
            JOIN categories c ON c.id=p.category_id AND c.status='active' AND c.deleted_at IS NULL
            LEFT JOIN categories sc ON sc.id=p.subcategory_id
            WHERE p.status='active' AND p.deleted_at IS NULL
              AND (p.subcategory_id IS NULL OR (sc.status='active' AND sc.deleted_at IS NULL))
            ORDER BY p.name LIMIT 1
            """
        )
        product = cursor.fetchone()
        cursor.execute("SELECT default_location_id FROM buyer_profiles WHERE user_id=%s", [buyer["id"] if buyer else ""])
        profile = cursor.fetchone() if buyer else None
        if not buyer or not product or not profile or not profile["default_location_id"]:
            return

        buyer_id = buyer["id"]
        product_id = product["id"]
        location_id = profile["default_location_id"]
        base_price = max(1000, float(product["price_min"] or 0))

    request_id = server.cart_repo.start_bid(
        buyer_id,
        product_id,
        location_id,
        25,
        1,
        {"Source": "local demo seed"},
        True,
        1440,
    )
    with server.db() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT dealer_id FROM bid_request_dealers WHERE bid_request_id=%s ORDER BY dealer_id LIMIT 2",
            [request_id],
        )
        dealer_ids = [row["dealer_id"] for row in cursor.fetchall()]

    for index, dealer_id in enumerate(dealer_ids):
        server.dealer_ops.submit_bid(
            dealer_id,
            server.BidIn(
                bid_request_id=request_id,
                amount=base_price + (index * 1500),
                warranty_text="1 year manufacturer warranty",
                delivery_time="5",
                installation_included=True,
                notes="Local demo offer",
            ),
        )


def populate() -> None:
    server.execute_sql_file()
    server.ensure_runtime_schema()
    server.seed_database()

    with server.db() as conn, conn.cursor() as cursor:
        roles = {name: ensure_role(cursor, name) for name in ("buyer", "dealer")}
        location_ids = [ensure_location(cursor, hub) for hub in HUBS]

        category_ids: dict[str, str] = {}
        root_id = ensure_category(cursor, "Electronics")
        category_ids["Electronics"] = root_id
        for name in ("Laptops", "Smartphones", "Monitors"):
            category_ids[name] = ensure_category(cursor, name, root_id)
        cursor.execute("SELECT id FROM categories WHERE deleted_at IS NULL AND status='active'")
        all_category_ids = [row["id"] for row in cursor.fetchall()]

        cursor.execute("SELECT id FROM users WHERE email='admin@turacoz' AND deleted_at IS NULL")
        admin = cursor.fetchone()
        if not admin:
            raise RuntimeError("Admin seed was not created")
        ensure_demo_products(cursor, admin["id"], location_ids[0], category_ids)

        for index in range(1, 21):
            hub_index = (index - 1) % len(location_ids)
            location_id = location_ids[hub_index]
            buyer_id = ensure_user(
                cursor,
                f"buyer{index}",
                roles["buyer"],
                "active",
                f"Demo Buyer {index}",
                f"+91 91111 {index:05d}",
            )
            cursor.execute(
                """
                INSERT INTO buyer_profiles
                  (id,user_id,phone,address,country,state,city,area,pincode,preferred_radius,default_location_id,created_at,updated_at)
                VALUES (%s,%s,%s,'Demo buyer address','India',%s,%s,'Demo Hub',%s,25,%s,NOW(),NOW())
                ON DUPLICATE KEY UPDATE phone=VALUES(phone), country=VALUES(country), state=VALUES(state),
                  city=VALUES(city), area=VALUES(area), pincode=VALUES(pincode), preferred_radius=25,
                  default_location_id=VALUES(default_location_id), updated_at=NOW()
                """,
                [server.new_id(), buyer_id, f"+91 91111 {index:05d}", HUBS[hub_index][1], HUBS[hub_index][2], HUBS[hub_index][4], location_id],
            )
            cursor.execute(
                "SELECT id FROM buyer_locations WHERE buyer_id=%s AND location_id=%s AND deleted_at IS NULL LIMIT 1",
                [buyer_id, location_id],
            )
            saved = cursor.fetchone()
            if saved:
                cursor.execute("UPDATE buyer_locations SET label='Demo location', is_default=TRUE, updated_at=NOW() WHERE id=%s", [saved["id"]])
            else:
                cursor.execute(
                    """
                    INSERT INTO buyer_locations (id,buyer_id,location_id,active_location_id,label,is_default,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,'Demo location',TRUE,NOW(),NOW())
                    """,
                    [server.new_id(), buyer_id, location_id, location_id],
                )
            cursor.execute("UPDATE buyer_locations SET is_default=FALSE, updated_at=NOW() WHERE buyer_id=%s AND location_id<>%s AND deleted_at IS NULL", [buyer_id, location_id])

        for index in range(1, 21):
            hub_index = (index - 1) % len(location_ids)
            dealer_id = ensure_user(
                cursor,
                f"dealer{index}",
                roles["dealer"],
                "verified",
                f"Demo Dealer {index}",
                f"+91 92222 {index:05d}",
            )
            cursor.execute(
                """
                INSERT INTO dealer_profiles
                  (id,user_id,business_name,owner_name,business_address,gst_number,rating,verification_status,
                   dynamic_fields,service_preferences,subscribed,subscribed_at,created_at,updated_at)
                VALUES (%s,%s,%s,%s,'Demo service address','07ABCDE1234F1Z9',4.5,'verified',%s,%s,TRUE,NOW(),NOW(),NOW())
                ON DUPLICATE KEY UPDATE business_name=VALUES(business_name), owner_name=VALUES(owner_name),
                  verification_status='verified', dynamic_fields=VALUES(dynamic_fields),
                  service_preferences=VALUES(service_preferences), subscribed=TRUE, updated_at=NOW()
                """,
                [
                    server.new_id(),
                    dealer_id,
                    f"Demo Dealer Supplies {index}",
                    f"Demo Dealer {index}",
                    '{"brands":[]}',
                    '{"method":"radius","states":[],"cities":[],"districts":[]}',
                ],
            )
            cursor.execute(
                """
                INSERT INTO dealer_service_locations (dealer_id,location_id,radius_km,created_at)
                VALUES (%s,%s,500,NOW())
                ON DUPLICATE KEY UPDATE radius_km=500, created_at=NOW()
                """,
                [dealer_id, location_ids[hub_index]],
            )
            for category_id in all_category_ids:
                cursor.execute(
                    "INSERT IGNORE INTO dealer_categories (dealer_id,category_id,created_at) VALUES (%s,%s,NOW())",
                    [dealer_id, category_id],
                )

    seed_sample_bid()
    print("Demo data is ready. Accounts buyer1..buyer20 and dealer1..dealer20 use matching passwords.")
    print("The seed is additive and repeatable; it does not truncate products, categories, or bid history.")


if __name__ == "__main__":
    populate()
