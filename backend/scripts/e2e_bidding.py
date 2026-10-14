"""Run API/browser bidding scenarios using temporary accounts; clean them up afterward."""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import urllib.request
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from backend.main import db

BASE = os.getenv("E2E_API_URL", "http://127.0.0.1:8000")


def request(path, payload=None, token=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(urllib.request.Request(BASE + path, data=body, headers=headers, method=method), timeout=30) as response:
        return json.load(response)


def clean_up(accounts, country):
    if not accounts:
        return
    ids = [account["id"] for account in accounts.values()]
    placeholders = ",".join(["%s"] * len(ids))
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(f"SELECT id FROM users WHERE id IN ({placeholders}) AND LEFT(email,4)=%s", ids + ["e2e_"])
        if {row["id"] for row in cursor.fetchall()} != set(ids):
            raise RuntimeError("Refusing cleanup: fixture identity check failed")
        cursor.execute(f"SELECT id FROM bid_requests WHERE buyer_id IN ({placeholders})", ids)
        request_ids = [row["id"] for row in cursor.fetchall()]
        cursor.execute(f"SELECT id FROM reports WHERE reporter_id IN ({placeholders}) OR reported_user_id IN ({placeholders})", ids + ids)
        report_ids = [row["id"] for row in cursor.fetchall()]
        for identifier in report_ids:
            cursor.execute("DELETE FROM notifications WHERE target_report_id=%s", [identifier])
            cursor.execute("DELETE FROM reports WHERE id=%s", [identifier])
        cursor.execute(f"DELETE FROM invoices WHERE user_id IN ({placeholders})", ids)
        entities = [*ids, *request_ids, *report_ids]
        for identifier in request_ids:
            cursor.execute("SELECT id FROM bids WHERE bid_request_id=%s", [identifier])
            entities.extend(row["id"] for row in cursor.fetchall())
            cursor.execute("DELETE FROM notifications WHERE target_bid_id=%s", [identifier])
            cursor.execute("UPDATE bid_requests SET winning_bid_id=NULL WHERE id=%s", [identifier])
            cursor.execute("DELETE FROM bid_requests WHERE id=%s", [identifier])
        for identifier in entities:
            cursor.execute("DELETE FROM audit_logs WHERE entity_id=%s", [identifier])
            cursor.execute("DELETE FROM status_history WHERE entity_id=%s", [identifier])
        cursor.execute(f"DELETE FROM audit_logs WHERE actor_id IN ({placeholders})", ids)
        cursor.execute(f"DELETE FROM users WHERE id IN ({placeholders})", ids)
        cursor.execute("DELETE FROM locations WHERE country=%s", [country])
    print("Temporary accounts, requests, messages and locations cleaned up.", flush=True)


def run(suite="bidding"):
    run_id = uuid.uuid4().hex[:10]
    password = secrets.token_urlsafe(20)
    country = "E2E " + run_id
    accounts = {}
    state_path = PROJECT_ROOT / "web" / "tests" / ".state" / (run_id + ".json")
    try:
        admin = request("/auth/login", {"username": "admin@turacoz", "password": os.getenv("TURACOZ_ADMIN_PASSWORD", "")})
        admin['password']=os.getenv('TURACOZ_ADMIN_PASSWORD','')
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT p.id,p.name,p.brand,c.id AS category_id,c.name AS category,sc.id AS item_id,sc.name AS item FROM products p JOIN categories c ON c.id=p.category_id JOIN categories sc ON sc.id=p.subcategory_id WHERE p.deleted_at IS NULL AND p.status='active' AND c.status='active' AND sc.status='active' ORDER BY COALESCE(p.source_updated_at,p.created_at) DESC,p.id DESC LIMIT 1")
            product = cursor.fetchone()
            cursor.execute("SELECT id FROM categories WHERE parent_id=%s AND id<>%s AND status='active' AND deleted_at IS NULL LIMIT 1", [product["category_id"], product["item_id"]])
            other_item = cursor.fetchone()["id"]
        configurations = {
            "buyer": ("buyer", 12.9716, product["item_id"], False),
            "near1": ("dealer", 12.9716, product["item_id"], True),
            "near2": ("dealer", 12.9876, product["item_id"], True),
            "far": ("dealer", 13.0716, product["item_id"], True),
            "wrongItem": ("dealer", 12.9726, other_item, True),
            "unsubscribed": ("dealer", 12.9736, product["item_id"], False),
            "edgeInside": ("dealer", 12.9716 + 4.99 / 111.1949266, product["item_id"], True),
            "edgeOutside": ("dealer", 12.9716 + 5.01 / 111.1949266, product["item_id"], True),
            # Next to the buyer, subscribed and selling the item, but not in good standing: they get nothing.
            "flaggedNear": ("dealer", 12.9718, product["item_id"], True),
            "pendingNear": ("dealer", 12.9719, product["item_id"], True),
        }
        standing_overrides = {"flaggedNear": "flagged", "pendingNear": "pending"}
        for label, (role, latitude, item, subscribe) in configurations.items():
            username = f"e2e_{run_id}_{label.lower()}"
            request("/auth/register", {"name": "E2E " + label, "username": username, "password": password, "role": role})
            account = request("/auth/login", {"username": username, "password": password})
            account.update({"username": username, "password": password})
            accounts[label] = account
            if role == "dealer":
                profile = {"full_name": "E2E " + label, "business_name": "E2E " + label, "country": country, "state": "Karnataka", "city": "Bengaluru", "area": "Test area", "address": "Test shop", "latitude": latitude, "longitude": 77.5946, "service_radius_km": 5, "delivery_method": "radius", "categories": [item], "brands": []}
                request("/profile", profile, account["access_token"], "PUT")
                request(f"/admin/users/{account['id']}/status", {"status": standing_overrides.get(label, "verified"), "reason": "Temporary E2E fixture"}, admin["access_token"])
                with db() as conn, conn.cursor() as cursor:
                    cursor.execute("UPDATE dealer_profiles SET rating=5 WHERE user_id=%s", [account["id"]])
                if subscribe:
                    request("/dealer/subscription/activate", {}, account["access_token"])
        if suite=='admin':
            with db() as conn, conn.cursor() as cursor:
                cursor.execute('SELECT location_id FROM dealer_service_locations WHERE dealer_id=%s',[accounts['far']['id']])
                branch=cursor.fetchone()['location_id']
                cursor.execute("UPDATE locations SET city='Mysuru' WHERE id=%s AND country=%s",[branch,country])
                cursor.execute('INSERT INTO dealer_service_locations (dealer_id,location_id,radius_km,created_at) VALUES (%s,%s,5,NOW())',[accounts['near2']['id'],branch])
        settings = request("/settings", token=admin["access_token"])
        state = {"accounts": accounts, "admin": admin, "product": product, "country": country, "settings": settings, "apiUrl": BASE}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        print("Running browser/API scenarios with isolated temporary fixtures.", flush=True)
        test_file = {"live": "live_bidding.e2e.mjs", "mobile": "mobile_bidding.e2e.mjs", "profile": "business_profile.e2e.mjs", "admin":"admin.e2e.mjs"}.get(suite, "bidding.e2e.mjs")
        result = subprocess.run(["node", str(PROJECT_ROOT / "web" / "tests" / test_file), str(state_path)], cwd=PROJECT_ROOT)
        return result.returncode
    finally:
        clean_up(accounts, country)
        if suite=='admin' and state_path.exists():
            resources=json.loads(state_path.read_text(encoding='utf-8')).get('adminResources',{})
            with db() as conn, conn.cursor() as cursor:
                for identifier in resources.get('products',[]):
                    cursor.execute('SELECT name FROM products WHERE id=%s',[identifier])
                    record=cursor.fetchone()
                    if record and not record['name'].startswith(country+' admin'):
                        raise RuntimeError('Refusing non-fixture product cleanup')
                    cursor.execute('DELETE FROM products WHERE id=%s',[identifier])
                    cursor.execute('DELETE FROM audit_logs WHERE entity_id=%s',[identifier])
                for identifier in reversed(resources.get('categories',[])):
                    cursor.execute('SELECT name FROM categories WHERE id=%s',[identifier])
                    record=cursor.fetchone()
                    if record and not record['name'].startswith(country+' admin'):
                        raise RuntimeError('Refusing non-fixture category cleanup')
                    cursor.execute('DELETE FROM categories WHERE id=%s',[identifier])
                    cursor.execute('DELETE FROM audit_logs WHERE entity_id=%s',[identifier])
        state_path.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["bidding", "live", "mobile", "profile", "admin"], default="bidding")
    parser.add_argument("--revoke", help=argparse.SUPPRESS)
    parser.add_argument("--fixtures", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.revoke:
        state = json.loads(args.fixtures.read_text(encoding="utf-8"))
        fixture = next((value for value in state["accounts"].values() if value["id"] == args.revoke), None)
        if not fixture or not fixture["username"].startswith("e2e_"):
            raise RuntimeError("Subscription changes are limited to this test's fixtures")
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("UPDATE dealer_profiles dp JOIN users u ON u.id=dp.user_id SET dp.subscribed=FALSE WHERE dp.user_id=%s AND u.email=%s", [fixture["id"], fixture["username"]])
    else:
        sys.exit(run(args.suite))
