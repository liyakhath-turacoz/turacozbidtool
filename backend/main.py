import asyncio
import atexit
import base64
import csv
import hashlib
import hmac
import io
import json
import logging
import math
import os
import secrets
import shutil
import time
import uuid
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from contextlib import contextmanager, suppress
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Literal

import pymysql
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

try:
    from .configuration import load_local_environment
    from .catalog_importer import import_bundle_if_needed
    from .connection_cache import ConnectionCache
    from .database_health import DatabaseHealthError, assert_tables_readable
    from . import geocoding
    from .logging_filters import install_token_filters
except ImportError:
    from configuration import load_local_environment
    from catalog_importer import import_bundle_if_needed
    from connection_cache import ConnectionCache
    from database_health import DatabaseHealthError, assert_tables_readable
    import geocoding
    from logging_filters import install_token_filters


DB_HOST = os.getenv("TURACOZ_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("TURACOZ_DB_PORT", "3306"))
DB_USER = os.getenv("TURACOZ_DB_USER", "turacoz_app")
DB_PASSWORD = os.getenv("TURACOZ_DB_PASSWORD", "")
DB_NAME = os.getenv("TURACOZ_DB_NAME", "turacoz_bidtool")
JWT_SECRET = os.getenv("TURACOZ_JWT_SECRET", "")
ADMIN_PASSWORD = os.getenv("TURACOZ_ADMIN_PASSWORD", "")
ROOT = Path(__file__).resolve().parent
SQL_FILE = ROOT / "deployment.sql"
WEB_BUILD = ROOT.parent / "web" / "dist"
UPLOAD_ROOT = ROOT / "local_uploads"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("turacozbidtool")
if JWT_SECRET == "change-this-before-production":
    logger.warning("TURACOZ_JWT_SECRET is using the development fallback; set a unique secret before deployment.")
if not ADMIN_PASSWORD:
    logger.warning("TURACOZ_ADMIN_PASSWORD must be configured before seeding a new database.")


class JsonEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000)
    return f"pbkdf2_sha256${salt}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, encoded = stored.split("$", 2)
        expected = hash_password(password, salt).split("$", 2)[2]
        return hmac.compare_digest(encoded, expected)
    except ValueError:
        return False


def account_status_blocks_access(status: str) -> bool:
    return status in {"held", "suspended", "banned", "deleted"}


def sign_token(payload: dict[str, Any], minutes: int) -> str:
    payload = {**payload, "exp": int(time.time()) + minutes * 60}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{body}.{sig}"


def parse_token(token: str) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
        expected = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if int(payload["exp"]) <= int(time.time()) or not isinstance(payload.get("sub"), str):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        return int(digits) if digits else 0


def open_database_connection(database=True):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME if database else None,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
        init_command="SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED",
    )


connection_cache = ConnectionCache(open_database_connection)
atexit.register(connection_cache.close)


@contextmanager
def db(database: bool = True):
    conn = connection_cache.acquire() if database else open_database_connection(False)
    reusable = True
    try:
        yield conn
        conn.commit()
    except pymysql.err.OperationalError as exc:
        reusable = False
        with suppress(pymysql.MySQLError):
            conn.rollback()
        if exc.args and exc.args[0] in {1205, 1213}:
            raise HTTPException(status_code=409, detail="This request is being changed by another action. Please try again") from exc
        raise
    except BaseException:
        try:
            conn.rollback()
        except Exception:
            reusable = False
        raise
    finally:
        if database and reusable:
            connection_cache.release(conn)
        else:
            connection_cache.discard(conn)


def check_database_storage() -> None:
    try:
        with db() as conn:
            assert_tables_readable(conn)
    except pymysql.MySQLError as exc:
        raise DatabaseHealthError(
            f"Database is unavailable (error {exc.args[0]}). Check the MariaDB/MySQL service and "
            "TURACOZ_DB_* settings, then run python backend/scripts/check_database.py."
        ) from exc


def execute_sql_file() -> None:
    sql = SQL_FILE.read_text(encoding="utf-8").replace("${DB_NAME}", DB_NAME)
    statements = []
    for statement in [item.strip() for item in sql.split(";") if item.strip()]:
        upper = statement.upper()
        if (upper.startswith("CREATE DATABASE") or
            upper.startswith("USE ") or
            upper.startswith("CREATE USER") or
            upper.startswith("ALTER USER") or
            upper.startswith("GRANT ") or
            upper.startswith("FLUSH ")):
            continue
        statements.append(statement)
    try:
        with db(database=True) as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    try:
                        cursor.execute(statement)
                    except pymysql.err.OperationalError as exc:
                        if exc.args and exc.args[0] in {1005, 1061, 1826} and "fk_bid_requests_winning_bid" in statement:
                            continue
                        raise
    except pymysql.err.OperationalError as exc:
        if exc.args and exc.args[0] in {1044, 1049, 1045, 2059}:
            raise RuntimeError(
                "MariaDB is not ready for Turacoz Bid Tool. Run database_setup.sql once with a MariaDB admin/root user, "
                "so the turacoz_app account is converted from GSSAPI/Windows auth to mysql_native_password, "
                "then start server.py again. Current app user is "
                f"'{DB_USER}' and database is '{DB_NAME}'."
            ) from exc
        raise


def ensure_runtime_schema() -> None:
    with db(database=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS count FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='bid_requests' AND COLUMN_NAME='skip_flagged_dealers'",
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE bid_requests ADD COLUMN skip_flagged_dealers BOOLEAN NOT NULL DEFAULT TRUE AFTER radius_km")
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='locations' AND COLUMN_NAME='address_line'
                """,
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE locations ADD COLUMN address_line VARCHAR(255) NULL AFTER area")
            # Places with the same postal address can have distinct immutable pins.
            cursor.execute("SELECT COUNT(*) AS count FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='locations' AND INDEX_NAME='uq_location'", [DB_NAME])
            if cursor.fetchone()["count"]:
                cursor.execute("ALTER TABLE locations DROP INDEX uq_location")
            cursor.execute("SELECT COUNT(*) AS count FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='locations' AND INDEX_NAME='idx_location_pin'", [DB_NAME])
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE locations ADD INDEX idx_location_pin (latitude, longitude)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS buyer_locations (
                  id CHAR(36) PRIMARY KEY,
                  buyer_id CHAR(36) NOT NULL,
                  location_id CHAR(36) NOT NULL,
                  label VARCHAR(120) NOT NULL DEFAULT 'Saved location',
                  is_default BOOLEAN NOT NULL DEFAULT FALSE,
                  created_at DATETIME NOT NULL,
                  updated_at DATETIME NOT NULL,
                  deleted_at DATETIME NULL,
                  active_location_id CHAR(36) NULL,
                  UNIQUE KEY uq_buyer_active_location (buyer_id, active_location_id),
                  KEY idx_buyer_locations_buyer_default (buyer_id, is_default, deleted_at),
                  CONSTRAINT fk_buyer_locations_buyer FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
                  CONSTRAINT fk_buyer_locations_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                """
            )
            cursor.execute("SELECT COUNT(*) AS count FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='buyer_locations' AND COLUMN_NAME='active_location_id'", [DB_NAME])
            if cursor.fetchone()["count"] == 0:
                # The previous nullable unique key allowed repeated active saves.
                # Saved row IDs have no references; retain one per buyer/location.
                cursor.execute("DELETE duplicate FROM buyer_locations duplicate JOIN buyer_locations retained ON retained.buyer_id=duplicate.buyer_id AND retained.location_id=duplicate.location_id AND retained.id<duplicate.id WHERE duplicate.deleted_at IS NULL AND retained.deleted_at IS NULL")
                cursor.execute("SELECT COUNT(*) AS count FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='buyer_locations' AND INDEX_NAME='uq_buyer_location'", [DB_NAME])
                if cursor.fetchone()["count"]:
                    cursor.execute("ALTER TABLE buyer_locations DROP INDEX uq_buyer_location")
                cursor.execute("ALTER TABLE buyer_locations ADD COLUMN active_location_id CHAR(36) NULL, ADD UNIQUE KEY uq_buyer_active_location (buyer_id, active_location_id)")
                cursor.execute("UPDATE buyer_locations SET active_location_id=IF(deleted_at IS NULL, location_id, NULL)")
                cursor.execute("SELECT DISTINCT buyer_id FROM buyer_locations WHERE deleted_at IS NULL")
                buyer_ids = [row["buyer_id"] for row in cursor.fetchall()]
                for buyer_id in buyer_ids:
                    cursor.execute("SELECT bl.id FROM buyer_locations bl JOIN buyer_profiles bp ON bp.user_id=bl.buyer_id AND bp.default_location_id=bl.location_id WHERE bl.buyer_id=%s AND bl.deleted_at IS NULL LIMIT 1", [buyer_id])
                    existing_default = cursor.fetchone()
                    synchronize_buyer_default(cursor, buyer_id, (existing_default or {}).get("id"))
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='notifications' AND COLUMN_NAME='target_bid_id'
                """,
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE notifications ADD COLUMN target_bid_id CHAR(36) NULL AFTER body")
                cursor.execute("ALTER TABLE notifications ADD KEY idx_notifications_target_bid (target_bid_id)")
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='notifications' AND COLUMN_NAME='target_report_id'
                """,
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE notifications ADD COLUMN target_report_id CHAR(36) NULL AFTER target_bid_id")
                cursor.execute("ALTER TABLE notifications ADD KEY idx_notifications_target_report (target_report_id)")
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='dealer_profiles' AND COLUMN_NAME='service_preferences'
                """,
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE dealer_profiles ADD COLUMN service_preferences JSON NULL AFTER dynamic_fields")
            # ── Subscription columns ─────────────────────────────────────────────
            for column_name, definition in (
                ("subscribed", "BOOLEAN NOT NULL DEFAULT FALSE AFTER rating"),
                ("subscribed_at", "DATETIME NULL AFTER subscribed"),
            ):
                cursor.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s AND TABLE_NAME='dealer_profiles' AND COLUMN_NAME=%s
                    """,
                    [DB_NAME, column_name],
                )
                if cursor.fetchone()["count"] == 0:
                    cursor.execute(f"ALTER TABLE dealer_profiles ADD COLUMN {column_name} {definition}")
            # ── notifications.is_read convenience column (mirrors read_at IS NOT NULL) ──
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='notifications' AND COLUMN_NAME='is_read'
                """,
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE notifications ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT FALSE AFTER read_at")
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='dealer_categories'
                  AND INDEX_NAME='idx_dealer_categories_category_dealer'
                """,
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE dealer_categories ADD KEY idx_dealer_categories_category_dealer (category_id, dealer_id)")
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='reports' AND COLUMN_NAME='closure_requested_by'
                """,
                [DB_NAME],
            )
            if cursor.fetchone()["count"] == 0:
                cursor.execute("ALTER TABLE reports ADD COLUMN closure_requested_by CHAR(36) NULL AFTER internal_notes")
                cursor.execute("ALTER TABLE reports ADD COLUMN closure_reason TEXT NULL AFTER closure_requested_by")
                cursor.execute(
                    "ALTER TABLE reports ADD COLUMN closure_requested_status ENUM('none','requested','approved','rejected') NOT NULL DEFAULT 'none' AFTER closure_reason"
                )
                cursor.execute("ALTER TABLE reports ADD KEY idx_reports_closure_request (closure_requested_status, updated_at)")
            cursor.execute(
                """
                SELECT COLUMN_TYPE AS column_type
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='report_messages' AND COLUMN_NAME='recipient_group'
                """,
                [DB_NAME],
            )
            recipient_column = cursor.fetchone()
            if recipient_column and "'admin'" not in recipient_column["column_type"]:
                cursor.execute(
                    "ALTER TABLE report_messages MODIFY recipient_group ENUM('admin','buyer','dealer','both') NOT NULL"
                )


def expire_due_bid_requests(cursor) -> None:
    # Find candidates without locking unrelated offers. A broad UPDATE JOIN
    # locked active bids even when nothing was due and deadlocked live readers.
    cursor.execute(
        """
        SELECT br.id FROM bid_requests br
        WHERE br.expires_at <= NOW() AND br.deleted_at IS NULL AND (
          br.status='active' OR (br.status='expired' AND (
            EXISTS (SELECT 1 FROM bids b WHERE b.bid_request_id=br.id AND b.status IN ('active','updated'))
            OR EXISTS (SELECT 1 FROM bid_request_dealers d WHERE d.bid_request_id=br.id AND d.status IN ('notified','viewed','bid','ignored'))
          ))) ORDER BY br.id
        """
    )
    candidates = cursor.fetchall()
    for candidate in candidates:
        request_id = candidate['id']
        cursor.execute("SELECT status, (expires_at<=NOW()) AS is_due FROM bid_requests WHERE id=%s FOR UPDATE", [request_id])
        current = cursor.fetchone()
        if not current or not current['is_due'] or current['status'] not in {'active', 'expired'}:
            continue
        cursor.execute("UPDATE bid_requests SET status='expired',updated_at=NOW() WHERE id=%s AND status='active'", [request_id])
        cursor.execute("UPDATE bids SET status='expired',updated_at=NOW() WHERE bid_request_id=%s AND status IN ('active','updated')", [request_id])
        cursor.execute("UPDATE bid_request_dealers SET status='expired' WHERE bid_request_id=%s AND status IN ('notified','viewed','bid','ignored')", [request_id])


def expire_bid_request_if_due(request_id: str) -> dict[str, Any] | None:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, buyer_id, status, expires_at, (expires_at <= NOW()) AS is_due
            FROM bid_requests
            WHERE id=%s AND deleted_at IS NULL
            FOR UPDATE
            """,
            [request_id],
        )
        req = cursor.fetchone()
        if not req or req["status"] not in {"active", "expired"} or not req.get("expires_at"):
            return None
        if not req["is_due"]:
            return None
        cursor.execute(
            """
            SELECT DISTINCT dealer_id FROM bid_request_dealers WHERE bid_request_id = %s
            UNION
            SELECT DISTINCT dealer_id FROM bids WHERE bid_request_id = %s AND deleted_at IS NULL
            """,
            [request_id, request_id],
        )
        dealer_ids = [row["dealer_id"] for row in cursor.fetchall()]
        if req["status"] == "active":
            cursor.execute("UPDATE bid_requests SET status='expired', updated_at=NOW() WHERE id=%s AND status='active'", [request_id])
            if cursor.rowcount != 1:
                return None
        cursor.execute(
            "UPDATE bids SET status='expired', updated_at=NOW() WHERE bid_request_id=%s AND status IN ('active','updated')",
            [request_id],
        )
        cursor.execute("UPDATE bid_request_dealers SET status='expired' WHERE bid_request_id=%s", [request_id])
        return {"buyer_id": req["buyer_id"], "dealer_ids": dealer_ids}


async def notify_bid_request_expiry(request_id: str, expires_at: datetime) -> None:
    # DATETIME has no timezone; use the same database clock as API mutations.
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT TIMESTAMPDIFF(SECOND, NOW(), expires_at) AS remaining FROM bid_requests WHERE id=%s AND status='active'", [request_id])
        row = cursor.fetchone()
    if not row:
        return
    await asyncio.sleep(max(float(row["remaining"] or 0), 0) + 1)
    result = expire_bid_request_if_due(request_id)
    if not result:
        return
    await publish_bid_snapshot(request_id)
    recipients = set([result["buyer_id"], *result["dealer_ids"]])
    for recipient_id in recipients:
        await manager.send_personal_message(
            {"type": "bid_expired", "request_id": request_id, "route": "bid_history"},
            recipient_id,
        )


bid_expiry_tasks: dict[str, asyncio.Task] = {}


def schedule_bid_request_expiry(request_id: str, expires_at: datetime | None) -> None:
    if not expires_at:
        return
    existing = bid_expiry_tasks.get(request_id)
    if existing and not existing.done():
        existing.cancel()
    task = asyncio.create_task(notify_bid_request_expiry(request_id, expires_at))
    task.add_done_callback(lambda completed, key=request_id: _cleanup_bid_expiry_task(key, completed))
    bid_expiry_tasks[request_id] = task


def _cleanup_bid_expiry_task(request_id: str, task: asyncio.Task) -> None:
    if bid_expiry_tasks.get(request_id) is task:
        bid_expiry_tasks.pop(request_id, None)
    if not task.cancelled():
        error = task.exception()
        if error:
            logger.error("Bid expiry task failed for %s: %s", request_id, error)


def schedule_existing_bid_expiries() -> None:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, expires_at
            FROM bid_requests
            WHERE status='active' AND expires_at IS NOT NULL AND deleted_at IS NULL
            """
        )
        rows = cursor.fetchall()
    for row in rows:
        schedule_bid_request_expiry(row["id"], row["expires_at"])


class AuthRepository:
    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.email, u.password_hash, u.full_name, u.status, r.name AS role
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.email = %s AND u.deleted_at IS NULL
                """,
                [email],
            )
            return cursor.fetchone()

    def store_refresh_token(self, user_id: str, token_hash: str, expires_at: datetime) -> None:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                [new_id(), user_id, token_hash, expires_at],
            )

    def write_login(self, user_id: str, success: bool, reason: str = "") -> None:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO login_history (id, user_id, success, reason, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                [new_id(), user_id, success, reason],
            )


def resolve_category_ids(cursor, cat_val: str, subcat_val: str | None) -> tuple[str, str | None]:
    category_id = None
    if len(cat_val) == 36 and "-" in cat_val:
        cursor.execute("SELECT id FROM categories WHERE id = %s AND parent_id IS NULL AND status='active' AND deleted_at IS NULL", [cat_val])
        row = cursor.fetchone()
        if row:
            category_id = row["id"]
        else:
            raise HTTPException(status_code=400, detail="Select an active parent category")

    if not category_id:
        cursor.execute("SELECT id FROM categories WHERE name = %s AND parent_id IS NULL AND deleted_at IS NULL", [cat_val])
        row = cursor.fetchone()
        if row:
            category_id = row["id"]
        else:
            category_id = new_id()
            cursor.execute(
                "INSERT INTO categories (id, name, parent_id, status, created_at, updated_at) VALUES (%s, %s, NULL, 'active', NOW(), NOW())",
                [category_id, cat_val]
            )

    subcategory_id = None
    if subcat_val:
        if len(subcat_val) == 36 and "-" in subcat_val:
            cursor.execute("SELECT id FROM categories WHERE id = %s AND parent_id=%s AND status='active' AND deleted_at IS NULL", [subcat_val, category_id])
            row = cursor.fetchone()
            if row:
                subcategory_id = row["id"]
            else:
                raise HTTPException(status_code=400, detail="The selected item must belong to the product category")

        if not subcategory_id:
            cursor.execute("SELECT id FROM categories WHERE name = %s AND parent_id = %s AND deleted_at IS NULL", [subcat_val, category_id])
            row = cursor.fetchone()
            if row:
                subcategory_id = row["id"]
            else:
                subcategory_id = new_id()
                cursor.execute(
                    "INSERT INTO categories (id, name, parent_id, status, created_at, updated_at) VALUES (%s, %s, %s, 'active', NOW(), NOW())",
                    [subcategory_id, subcat_val, category_id]
                )

    return category_id, subcategory_id


class CatalogRepository:
    def admin_catalog(self, q="", category="", brand="", status="", minimum=None, maximum=None, sort="Newest", limit=50, offset=0):
        where = """p.deleted_at IS NULL
          AND (%s='' OR p.id LIKE %s OR p.name LIKE %s OR p.brand LIKE %s OR p.model LIKE %s OR c.name LIKE %s OR sc.name LIKE %s OR p.highlights LIKE %s OR p.source_product_id LIKE %s OR p.mpn LIKE %s OR p.gtin LIKE %s)
          AND (%s='' OR c.name=%s OR sc.name=%s) AND (%s='' OR p.brand=%s)
          AND (%s='' OR p.status=%s) AND (%s IS NULL OR p.price_min >= %s) AND (%s IS NULL OR p.price_max <= %s)"""
        params = [q, *([f'%{q}%'] * 10), category, category, category, brand, brand, status, status, minimum, minimum, maximum, maximum]
        joins = "FROM products p JOIN categories c ON c.id=p.category_id LEFT JOIN categories sc ON sc.id=p.subcategory_id LEFT JOIN locations l ON l.id=p.location_id"
        ordering = {"Newest":"p.created_at DESC,p.id DESC", "Name":"p.name,p.id", "Lowest Price":"p.price_min,p.id", "Highest Price":"p.price_max DESC,p.id"}[sort]
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total {joins} WHERE {where}", params)
            total = cursor.fetchone()['total']
            cursor.execute(f"""SELECT p.id,p.name,c.name AS category,sc.name AS item,p.brand,p.model,p.price_min,p.price_max,p.status,p.created_at,p.image_url,p.source,p.release_year,p.source_product_id,p.mpn,p.gtin,
                CONCAT(l.city,', ',l.state) AS location,p.highlights AS specifications,
                EXISTS(SELECT 1 FROM bid_requests br WHERE br.product_id=p.id) AS has_bid_history
                {joins} WHERE {where} ORDER BY {ordering} LIMIT %s OFFSET %s""", params+[limit,offset])
            rows = cursor.fetchall()
            for row in rows:
                if isinstance(row['specifications'], str):
                    try:
                        row['specifications'] = json.loads(row['specifications'])
                    except ValueError:
                        row['specifications'] = {}
                if not isinstance(row['specifications'], dict):
                    row['specifications'] = {}
            self._merge_manual_specifications(cursor, rows)
            cursor.execute("SELECT COUNT(*) AS total FROM products WHERE deleted_at IS NULL")
            catalog_total = cursor.fetchone()['total']
            cursor.execute("SELECT DISTINCT brand FROM products WHERE deleted_at IS NULL ORDER BY brand")
            brands = [row['brand'] for row in cursor.fetchall() if row['brand']]
            return {'items':rows,'total':total,'catalog_total':catalog_total,'brands':brands}

    def list_products(
        self,
        query: str = "",
        limit: int = 100,
        offset: int = 0,
        category: str = "",
        brand: str = "",
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            pattern = f"%{query}%"
            cursor.execute(
                """
                SELECT p.id, p.name, c.name AS category, sc.name AS item, p.brand, p.model,
                       p.price_min, p.price_max, CONCAT(l.city, ', ', l.state) AS location,
                       p.status, p.description, p.summary_description, p.image_url,
                       p.release_year, p.source, p.source_product_id, p.mpn, p.gtin,
                       p.highlights AS specifications
                FROM products p
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN categories sc ON sc.id = p.subcategory_id
                LEFT JOIN locations l ON l.id = p.location_id
                WHERE p.deleted_at IS NULL
                  AND (%s = '' OR p.name LIKE %s OR p.brand LIKE %s OR p.model LIKE %s OR c.name LIKE %s OR sc.name LIKE %s)
                  AND (%s = '' OR c.name = %s OR sc.name = %s)
                  AND (%s = '' OR p.brand = %s)
                  AND (%s = TRUE OR p.status = 'active')
                  AND (%s = TRUE OR (c.status='active' AND c.deleted_at IS NULL AND (p.subcategory_id IS NULL OR (sc.status='active' AND sc.deleted_at IS NULL))))
                ORDER BY COALESCE(p.source_updated_at, p.created_at) DESC, p.id DESC
                LIMIT %s OFFSET %s
                """,
                [
                    query,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    category,
                    category,
                    category,
                    brand,
                    brand,
                    include_inactive,
                    include_inactive,
                    max(1, min(limit, 250)),
                    max(0, offset),
                ],
            )
            rows = cursor.fetchall()
            for row in rows:
                raw_specs = row.get("specifications")
                if isinstance(raw_specs, str):
                    try:
                        row["specifications"] = json.loads(raw_specs)
                    except json.JSONDecodeError:
                        row["specifications"] = {}
                elif not isinstance(raw_specs, dict):
                    row["specifications"] = {}
            self._merge_manual_specifications(cursor, rows)
            return rows

    @staticmethod
    def _merge_manual_specifications(cursor, rows: list[dict[str, Any]]) -> None:
        product_ids = [row["id"] for row in rows]
        if not product_ids:
            return
        placeholders = ",".join(["%s"] * len(product_ids))
        cursor.execute(
            f"SELECT product_id, spec_name, spec_value FROM product_specifications WHERE product_id IN ({placeholders}) ORDER BY sort_order, spec_name",
            product_ids,
        )
        by_product: dict[str, dict[str, str]] = {}
        for spec in cursor.fetchall():
            by_product.setdefault(spec["product_id"], {})[spec["spec_name"]] = spec["spec_value"]
        for row in rows:
            row["specifications"] = {**(row.get("specifications") or {}), **by_product.get(row["id"], {})}

    def product_detail(self, product_id: str, include_inactive: bool = False) -> dict[str, Any]:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.*, c.name AS category, sc.name AS item,
                       CONCAT(l.city, ', ', l.state) AS location
                FROM products p
                JOIN categories c ON c.id=p.category_id
                LEFT JOIN categories sc ON sc.id=p.subcategory_id
                LEFT JOIN locations l ON l.id=p.location_id
                WHERE p.id=%s AND p.deleted_at IS NULL
                  AND (%s=TRUE OR p.status='active')
                  AND (%s=TRUE OR (c.status='active' AND c.deleted_at IS NULL AND (p.subcategory_id IS NULL OR (sc.status='active' AND sc.deleted_at IS NULL))))
                """,
                [product_id, include_inactive, include_inactive],
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Product not found")
            for field, fallback in (
                ("highlights", {}),
                ("technical_specifications", []),
                ("software_specifications", []),
                ("gallery", []),
                ("multimedia", []),
            ):
                if isinstance(row.get(field), str):
                    try:
                        row[field] = json.loads(row[field])
                    except json.JSONDecodeError:
                        row[field] = fallback
                elif row.get(field) is None:
                    row[field] = fallback
            row["specifications"] = row.pop("highlights", {})
            cursor.execute(
                "SELECT spec_name, spec_value FROM product_specifications WHERE product_id=%s ORDER BY sort_order, spec_name",
                [product_id],
            )
            manual_specs = {spec["spec_name"]: spec["spec_value"] for spec in cursor.fetchall()}
            row["specifications"] = {**(row["specifications"] or {}), **manual_specs}
            cursor.execute(
                """
                SELECT asset_type, url, thumbnail_url, content_type, description,
                       width, height, sort_order
                FROM product_assets WHERE product_id=%s
                ORDER BY asset_type, sort_order
                """,
                [product_id],
            )
            row["assets"] = cursor.fetchall()
            return row

    def create_product(self, draft: "ProductIn", admin_id: str) -> str:
        product_id = new_id()
        with db() as conn, conn.cursor() as cursor:
            category_id, subcategory_id = resolve_category_ids(cursor, draft.category, draft.subcategory)
            cursor.execute("SELECT id FROM locations WHERE city = %s AND deleted_at IS NULL LIMIT 1", [draft.location])
            location = cursor.fetchone()
            location_id = location["id"] if location else None
            cursor.execute(
                """
                INSERT INTO products
                (id, category_id, subcategory_id, location_id, name, brand, model, price_min, price_max, status, created_by, highlights, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """,
                [product_id, category_id, subcategory_id, location_id, draft.name, draft.brand, draft.model, draft.price_min, draft.price_max, draft.status or "active", admin_id, json.dumps(draft.specifications)],
            )
            for index, (key, value) in enumerate(draft.specifications.items()):
                cursor.execute(
                    """
                    INSERT INTO product_specifications (id, product_id, spec_name, spec_value, sort_order, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    [new_id(), product_id, key, value, index],
                )
            audit(cursor, admin_id, "product.created", "products", product_id, {"name": draft.name})
        return product_id

    def update_product(self, product_id: str, draft: "ProductIn", admin_id: str) -> None:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT name,brand,model,category_id,subcategory_id FROM products WHERE id=%s AND deleted_at IS NULL FOR UPDATE", [product_id])
            current = cursor.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Product not found")
            category_id, subcategory_id = resolve_category_ids(cursor, draft.category, draft.subcategory)
            cursor.execute("SELECT id FROM bid_requests WHERE product_id=%s LIMIT 1", [product_id])
            if cursor.fetchone() and (current["name"], current["brand"] or "", current["model"] or "", current["category_id"], current["subcategory_id"]) != (draft.name, draft.brand, draft.model, category_id, subcategory_id):
                raise HTTPException(status_code=409, detail="This product has bidding history. Create a new product to change its identity or category")
            cursor.execute("SELECT id FROM locations WHERE deleted_at IS NULL AND (city=%s OR area=%s OR CONCAT(city, ', ', state)=%s) ORDER BY id LIMIT 1", [draft.location, draft.location, draft.location])
            location = cursor.fetchone()
            cursor.execute(
                """
                UPDATE products
                SET category_id=%s, subcategory_id=%s, location_id=%s, name=%s, brand=%s, model=%s, price_min=%s, price_max=%s, status=COALESCE(%s,status), highlights=%s, updated_at=NOW()
                WHERE id=%s AND deleted_at IS NULL
                """,
                [category_id, subcategory_id, location["id"] if location else None, draft.name, draft.brand, draft.model, draft.price_min, draft.price_max, draft.status, json.dumps(draft.specifications), product_id],
            )
            cursor.execute("DELETE FROM product_specifications WHERE product_id=%s", [product_id])
            for index, (key, value) in enumerate(draft.specifications.items()):
                cursor.execute(
                    """
                    INSERT INTO product_specifications (id, product_id, spec_name, spec_value, sort_order, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    [new_id(), product_id, key, value, index],
                )
            audit(cursor, admin_id, "product.updated", "products", product_id, {"name": draft.name})

    def soft_delete_product(self, product_id: str, admin_id: str) -> None:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE products SET status='deleted', deleted_at=NOW(), updated_at=NOW() WHERE id=%s AND deleted_at IS NULL",
                [product_id],
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Product not found")
            audit(cursor, admin_id, "product.deleted", "products", product_id, {})


class BidRepository:
    def list_bids(self, user_id: str, role: str, request_id: str | None = None) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            expire_due_bid_requests(cursor)
            query = """
                SELECT b.id, b.bid_request_id, b.dealer_id, br.product_id, br.location_id, br.quantity, br.radius_km, br.skip_flagged_dealers, p.name AS product, buyer.full_name AS buyer,
                       COALESCE(NULLIF(l.address_line, ''), bp.address) AS buyer_address, buyer.phone AS buyer_phone, buyer.email AS buyer_email,
                       dp.business_name AS dealer, dp.owner_name,
                       COALESCE(NULLIF(dl.address_line, ''), dp.business_address) AS business_address, dp.gst_number,
                       u.phone AS dealer_phone, u.email AS dealer_email,
                       b.amount, b.discount_amount, b.warranty_text, b.delivery_time, b.installation_included, b.free_gifts, b.extra_services, b.notes,
                       COALESCE(cm.amount, 0) AS commission,
                       COALESCE(cm.payment_status, 'not_due') AS commission_payment_status,
                       b.status, br.expires_at AS ends_at, UNIX_TIMESTAMP(br.expires_at) AS ends_at_epoch, br.status AS request_status,
                       l.area AS buyer_area, l.city AS buyer_city, l.state AS buyer_state, l.pincode AS buyer_pincode,
                       wb.amount AS winning_amount, wb.warranty_text AS winning_warranty_text,
                       wb.delivery_time AS winning_delivery_time, wb.free_gifts AS winning_free_gifts,
                       wb.extra_services AS winning_extra_services, wb.notes AS winning_notes,
                       CASE
                         WHEN b.status='lost' AND wb.amount IS NOT NULL THEN GREATEST(b.amount - wb.amount, 0)
                         ELSE 0
                       END AS price_difference
                FROM bids b
                JOIN bid_requests br ON br.id = b.bid_request_id
                JOIN products p ON p.id = br.product_id
                JOIN users buyer ON buyer.id = br.buyer_id
                LEFT JOIN buyer_profiles bp ON bp.user_id = buyer.id
                JOIN users u ON u.id = b.dealer_id
                LEFT JOIN dealer_profiles dp ON dp.user_id = b.dealer_id
                LEFT JOIN locations l ON l.id = br.location_id
                LEFT JOIN (
                    SELECT dsl.dealer_id, dsl.location_id
                    FROM dealer_service_locations dsl
                    JOIN (
                        SELECT dealer_id, MAX(created_at) AS created_at
                        FROM dealer_service_locations
                        GROUP BY dealer_id
                    ) latest ON latest.dealer_id = dsl.dealer_id AND latest.created_at = dsl.created_at
                ) dsl_current ON dsl_current.dealer_id = b.dealer_id
                LEFT JOIN locations dl ON dl.id = dsl_current.location_id
                LEFT JOIN bids wb ON wb.id = br.winning_bid_id
                LEFT JOIN commissions cm ON cm.bid_id = b.id
                WHERE b.deleted_at IS NULL AND br.deleted_at IS NULL
            """
            params = []
            if request_id:
                query += " AND br.id=%s"
                params.append(request_id)

            if role == "buyer":
                query += " AND br.buyer_id = %s"
                params.append(user_id)
            elif role == "dealer":
                query += """
                     AND (
                         b.dealer_id = %s
                         OR (
                             br.id IN (SELECT bid_request_id FROM bid_request_dealers WHERE dealer_id = %s)
                         )
                     )
                """
                params.extend([user_id, user_id])

            query += " ORDER BY b.created_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            eligible_cache: dict[str, set[str]] = {}
            for row in rows:
                row["is_mine"] = role == "dealer" and row["dealer_id"] == user_id
                request = {**row, "id": row["bid_request_id"]}
                is_live = row["status"] in {"active", "updated"} and row["request_status"] == "active"
                row["selectable"] = False
                if is_live:
                    key = row["bid_request_id"]
                    if key not in eligible_cache:
                        cursor.execute("SELECT dealer_id FROM bid_request_dealers WHERE bid_request_id=%s AND status IN ('notified','viewed','bid')", [key])
                        invited = {invitation["dealer_id"] for invitation in cursor.fetchall()}
                        eligible_cache[key] = invited.intersection(dealer_ops.matching_dealer_ids(cursor, row["product_id"], row["location_id"], float(row["radius_km"] or 0), bool(row["skip_flagged_dealers"])))
                    row["selectable"] = row["dealer_id"] in eligible_cache[key]

            # Anonymise active bids (before a winner is chosen) — no commission gating
            if role == "buyer":
                request_dealers: dict[str, set] = {}
                for row in rows:
                    req_id = row["bid_request_id"]
                    d_id = row["dealer_id"]
                    request_dealers.setdefault(req_id, set()).add(d_id)

                dealer_maps = {
                    req_id: {d_id: f"Dealer {i+1}" for i, d_id in enumerate(sorted(d_set))}
                    for req_id, d_set in request_dealers.items()
                }

                for row in rows:
                    if row["status"] != "won":
                        req_id = row["bid_request_id"]
                        d_id = row["dealer_id"]
                        row["dealer"] = dealer_maps[req_id].get(d_id, "Dealer")
                        row["owner_name"] = None
                        row["business_address"] = None
                        row["gst_number"] = None
                        row["dealer_phone"] = None
                        row["dealer_email"] = None
                    # Won bids: contact always visible (no commission gate)
            elif role == "dealer":
                request_dealers: dict[str, set] = {}
                for row in rows:
                    req_id = row["bid_request_id"]
                    d_id = row["dealer_id"]
                    request_dealers.setdefault(req_id, set()).add(d_id)

                dealer_maps = {
                    req_id: {d_id: ("My Shop" if d_id == user_id else f"Dealer {i+1}") for i, d_id in enumerate(sorted(d_set))}
                    for req_id, d_set in request_dealers.items()
                }

                for row in rows:
                    req_id = row["bid_request_id"]
                    d_id = row["dealer_id"]
                    contact_unlocked = (
                        row["status"] == "won"
                        and d_id == user_id
                    )
                    if not contact_unlocked:
                        row["buyer"] = None
                        row["buyer_phone"] = None
                        row["buyer_email"] = None
                        row["buyer_address"] = None
                        row["buyer_pincode"] = None
                    if d_id != user_id:
                        row["dealer"] = dealer_maps[req_id].get(d_id, "Dealer")
                        row["owner_name"] = None
                        row["business_address"] = None
                        row["gst_number"] = None
                        row["dealer_phone"] = None
                        row["dealer_email"] = None
                    else:
                        row["dealer"] = "My Shop"

            # Format datetime objects and compute lost_reason
            for row in rows:
                if row.get("status") == "lost":
                    # Terms differ, but they do not prove why the buyer chose it.
                    row["lost_reason"] = "buyer selected another offer"
                else:
                    row["lost_reason"] = ""
                epoch = row.pop("ends_at_epoch", None)
                if epoch is not None:
                    row["ends_at"] = datetime.fromtimestamp(float(epoch), timezone.utc).isoformat()

            return rows


class DealerRepository:
    def list_dealers(self) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, dp.business_name, GROUP_CONCAT(DISTINCT l.city ORDER BY l.city SEPARATOR ', ') AS city,
                       GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') AS category,
                       u.status, dp.rating,
                       CASE
                         WHEN SUM(CASE WHEN cm.payment_status IN ('pending','failed') THEN 1 ELSE 0 END) > 0 THEN 'pending'
                         WHEN SUM(CASE WHEN cm.payment_status = 'paid' THEN 1 ELSE 0 END) > 0 THEN 'paid'
                         WHEN SUM(CASE WHEN cm.payment_status = 'waived' THEN 1 ELSE 0 END) > 0 THEN 'waived'
                         ELSE 'not_due'
                       END AS commission_status
                FROM users u
                JOIN roles r ON r.id = u.role_id AND r.name = 'dealer'
                JOIN dealer_profiles dp ON dp.user_id = u.id
                LEFT JOIN dealer_service_locations dsl ON dsl.dealer_id = u.id
                LEFT JOIN locations l ON l.id = dsl.location_id
                LEFT JOIN dealer_categories dc ON dc.dealer_id = u.id
                LEFT JOIN categories c ON c.id = dc.category_id
                LEFT JOIN bids b ON b.dealer_id = u.id
                LEFT JOIN commissions cm ON cm.bid_id = b.id
                WHERE u.deleted_at IS NULL
                GROUP BY u.id, dp.business_name, u.status, dp.rating
                ORDER BY dp.business_name
                """
            )
            return cursor.fetchall()


class NotificationRepository:
    def list_notifications(self, user_id: str) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, body AS message, event_type, target_bid_id, target_report_id,
                       created_at, (read_at IS NOT NULL OR is_read = 1) AS is_read
                FROM notifications
                WHERE user_id = %s AND deleted_at IS NULL
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY created_at DESC
                LIMIT 50
                """,
                [user_id],
            )
            return cursor.fetchall()

    def mark_all_read(self, user_id: str) -> None:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE notifications SET read_at=NOW(), is_read=1 WHERE user_id=%s AND read_at IS NULL AND deleted_at IS NULL",
                [user_id],
            )

    def create(self, user_id: str, title: str, body: str, event_type: str = "system", target_bid_id: str | None = None) -> dict[str, Any]:
        item = {"id": new_id(), "title": title, "message": body, "created_at": now_utc()}
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, read_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NULL, NOW())
                """,
                [item["id"], user_id, event_type, title, body, target_bid_id],
            )
        return item


def create_notification(
    cursor,
    user_id: str,
    title: str,
    body: str,
    event_type: str = "system",
    target_bid_id: str | None = None,
    target_report_id: str | None = None,
) -> str:
    notification_id = new_id()
    cursor.execute(
        """
        INSERT INTO notifications
          (id, user_id, event_type, title, body, target_bid_id, target_report_id, read_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, NOW())
        """,
        [notification_id, user_id, event_type, title, body, target_bid_id, target_report_id],
    )
    return notification_id


def create_contact_reveal_notifications(cursor, bid_id: str) -> list[str]:
    cursor.execute(
        """
        SELECT b.dealer_id, br.buyer_id, p.name AS product
        FROM bids b
        JOIN bid_requests br ON br.id=b.bid_request_id
        JOIN products p ON p.id=br.product_id
        WHERE b.id=%s AND b.deleted_at IS NULL
        """,
        [bid_id],
    )
    row = cursor.fetchone()
    if not row:
        return []
    buyer_id = row["buyer_id"]
    dealer_id = row["dealer_id"]
    product = row["product"]
    cursor.execute(
        """
        INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, created_at)
        VALUES (%s, %s, 'commission_paid', 'Contact details unlocked',
                %s, %s, NOW())
        """,
        [
            new_id(),
            buyer_id,
            f"The commission for {product} is paid or waived. Open Bid History to view dealer contact details.",
            bid_id,
        ],
    )
    cursor.execute(
        """
        INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, created_at)
        VALUES (%s, %s, 'commission_paid', 'Buyer details unlocked',
                %s, %s, NOW())
        """,
        [
            new_id(),
            dealer_id,
            f"The commission for {product} is paid or waived. Open Bid History to view buyer contact details.",
            bid_id,
        ],
    )
    return [buyer_id, dealer_id]


def admin_user_ids(cursor) -> list[str]:
    cursor.execute(
        """
        SELECT u.id
        FROM users u
        JOIN roles r ON r.id=u.role_id AND r.name='admin'
        WHERE u.deleted_at IS NULL AND u.status IN ('active','verified')
        """
    )
    return [row["id"] for row in cursor.fetchall()]


def delete_user_account(cursor, user_id: str, actor_id: str) -> None:
    # Retain marketplace and financial history so an awarded request never loses
    # its winner, invoice, or commission when either participant leaves.
    cursor.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL FOR UPDATE", [user_id])
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")
    cursor.execute(
        """
        SELECT br.id, br.buyer_id FROM bid_requests br
        WHERE br.status='active' AND br.deleted_at IS NULL
          AND (br.buyer_id=%s OR EXISTS (SELECT 1 FROM bids b WHERE b.bid_request_id=br.id AND b.dealer_id=%s AND b.status IN ('active','updated')))
        ORDER BY br.id FOR UPDATE
        """,
        [user_id, user_id],
    )
    for request in cursor.fetchall():
        if request["buyer_id"] == user_id:
            cursor.execute("UPDATE bid_requests SET status='cancelled',updated_at=NOW() WHERE id=%s", [request["id"]])
            cursor.execute("UPDATE bids SET status='expired',updated_at=NOW() WHERE bid_request_id=%s AND status IN ('active','updated')", [request["id"]])
            cursor.execute("UPDATE bid_request_dealers SET status='expired' WHERE bid_request_id=%s", [request["id"]])
        else:
            cursor.execute("UPDATE bids SET status='withdrawn',updated_at=NOW() WHERE bid_request_id=%s AND dealer_id=%s AND status IN ('active','updated')", [request["id"],user_id])
    cursor.execute("UPDATE users SET status='deleted',deleted_at=NOW(),updated_at=NOW() WHERE id=%s", [user_id])
    cursor.execute("UPDATE dealer_profiles SET subscribed=FALSE,deleted_at=NOW(),updated_at=NOW() WHERE user_id=%s", [user_id])
    cursor.execute("DELETE FROM refresh_tokens WHERE user_id=%s", [user_id])
    audit(cursor, actor_id, "user.deleted", "users", user_id, {"history_retained": True})


def csv_response(filename: str, rows: list[dict[str, Any]]) -> Response:
    output = io.StringIO()
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["status"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    else:
        writer.writerow({"status": "No data"})
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lon / 2) ** 2
    a = min(1.0, max(0.0, a))
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def valid_coordinates(row: dict[str, Any], lat_key: str = "latitude", lon_key: str = "longitude") -> bool:
    try:
        lat = float(row.get(lat_key))
        lon = float(row.get(lon_key))
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0)


def normalize_place(value: Any) -> str:
    return str(value or "").strip().lower()


def geocode_address(country: str = "", state: str = "", city: str = "", area: str = "", pincode: str = "", address: str = "") -> tuple[float, float] | None:
    query = ", ".join(
        part
        for part in [address, area, city, state, pincode, country or "India"]
        if str(part or "").strip()
    )
    if not query.strip():
        return None
    try:
        params = urllib.parse.urlencode({"format": "json", "q": query, "limit": "1"})
        req = urllib.request.Request(
            f"https://nominatim.openstreetmap.org/search?{params}",
            headers={"User-Agent": "turacoz-bidtool-dev"},
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload:
            return None
        lat = float(payload[0]["lat"])
        lon = float(payload[0]["lon"])
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except Exception as exc:
        logger.info("OpenStreetMap geocode skipped/failed for %s: %s", query, exc)
    return None


def coordinates_or_geocode(latitude: float, longitude: float, **parts: str) -> tuple[float, float]:
    row = {"latitude": latitude, "longitude": longitude}
    if valid_coordinates(row):
        return float(latitude), float(longitude)
    geocoded = geocode_address(**parts)
    if geocoded:
        return geocoded
    return float(latitude or 0), float(longitude or 0)


def one_row(cursor, query: str, args: list[Any] | None = None) -> dict[str, Any]:
    cursor.execute(query, args or [])
    return cursor.fetchone() or {}


class DashboardRepository:
    def admin_dashboard(self) -> dict[str, Any]:
        with db() as conn, conn.cursor() as cursor:
            expire_due_bid_requests(cursor)
            metrics = {
                "dealers": one_row(cursor, "SELECT COUNT(*) AS value FROM users u JOIN roles r ON r.id=u.role_id WHERE r.name='dealer' AND u.deleted_at IS NULL")["value"],
                "buyers": one_row(cursor, "SELECT COUNT(*) AS value FROM users u JOIN roles r ON r.id=u.role_id WHERE r.name='buyer' AND u.deleted_at IS NULL")["value"],
                "products": one_row(cursor, "SELECT COUNT(*) AS value FROM products WHERE deleted_at IS NULL")["value"],
                "completed_bids": one_row(cursor, "SELECT COUNT(*) AS value FROM bids WHERE status='won' AND deleted_at IS NULL")["value"],
                "pending_reports": one_row(cursor, "SELECT COUNT(*) AS value FROM reports WHERE status IN ('open','investigating','escalated') AND deleted_at IS NULL")["value"],
                "revenue": one_row(cursor, "SELECT COALESCE(SUM(amount),0) AS value FROM commissions WHERE payment_status='paid'")["value"],
                "commission_due": one_row(cursor, "SELECT COALESCE(SUM(amount),0) AS value FROM commissions WHERE payment_status IN ('pending','failed')")["value"],
                "banned_dealers": one_row(cursor, "SELECT COUNT(*) AS value FROM users u JOIN roles r ON r.id=u.role_id WHERE r.name='dealer' AND u.status='banned'")["value"],
                "held_dealers": one_row(cursor, "SELECT COUNT(*) AS value FROM users u JOIN roles r ON r.id=u.role_id WHERE r.name='dealer' AND u.status IN ('held','flagged','suspended')")["value"],
            }
            cursor.execute(
                """
                SELECT action, entity_type, entity_id, created_at
                FROM audit_logs
                ORDER BY created_at DESC
                LIMIT 8
                """
            )
            activity = cursor.fetchall()

            # Chart 1: Revenue by Month
            cursor.execute(
                """
                SELECT DATE_FORMAT(COALESCE(c.paid_at,c.created_at), '%b %Y') AS label, COALESCE(SUM(c.amount), 0) AS value
                FROM commissions c
                WHERE c.payment_status = 'paid'
                GROUP BY DATE_FORMAT(COALESCE(c.paid_at,c.created_at), '%b %Y'), YEAR(COALESCE(c.paid_at,c.created_at)), MONTH(COALESCE(c.paid_at,c.created_at))
                ORDER BY YEAR(COALESCE(c.paid_at,c.created_at)) ASC, MONTH(COALESCE(c.paid_at,c.created_at)) ASC
                """
            )
            revenue_by_month = cursor.fetchall()

            # Chart 2: Dealers by State
            cursor.execute(
                """
                SELECT COALESCE(l.state, 'Unknown') AS label, COUNT(DISTINCT u.id) AS value
                FROM users u
                JOIN roles r ON r.id = u.role_id AND r.name = 'dealer'
                LEFT JOIN dealer_service_locations dsl ON dsl.dealer_id = u.id
                LEFT JOIN locations l ON l.id = dsl.location_id
                WHERE u.deleted_at IS NULL
                GROUP BY label
                """
            )
            dealers_by_state = cursor.fetchall()

            # Chart 3: Dealers by Category
            cursor.execute(
                """
                SELECT c.name AS label, COUNT(DISTINCT dc.dealer_id) AS value
                FROM categories c
                LEFT JOIN dealer_categories dc ON dc.category_id = c.id
                WHERE c.deleted_at IS NULL
                GROUP BY c.name
                """
            )
            dealers_by_category = cursor.fetchall()

            # Chart 4: Buyers by State
            cursor.execute(
                """
                SELECT COALESCE(l.state, 'Maharashtra') AS label, COUNT(DISTINCT u.id) AS value
                FROM users u
                JOIN roles r ON r.id = u.role_id AND r.name = 'buyer'
                LEFT JOIN bid_requests br ON br.buyer_id = u.id AND br.deleted_at IS NULL
                LEFT JOIN locations l ON l.id = br.location_id
                WHERE u.deleted_at IS NULL
                GROUP BY label
                """
            )
            buyers_by_state = cursor.fetchall()

            # Chart 5: Products by Category
            cursor.execute(
                """
                SELECT c.name AS label, COUNT(p.id) AS value
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id AND p.deleted_at IS NULL
                WHERE c.deleted_at IS NULL
                GROUP BY c.name
                """
            )
            products_by_category = cursor.fetchall()

            # Chart 6: Bid Success Rate
            cursor.execute(
                """
                SELECT status AS label, COUNT(*) AS value
                FROM bid_requests
                WHERE deleted_at IS NULL
                GROUP BY status
                """
            )
            bid_success_rate = cursor.fetchall()

            # Chart 7: Top Categories
            cursor.execute(
                """
                SELECT c.name AS label, COUNT(p.id) AS value
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id AND p.deleted_at IS NULL
                WHERE c.deleted_at IS NULL
                GROUP BY c.name
                ORDER BY value DESC
                LIMIT 6
                """
            )
            top_categories = cursor.fetchall()

            # Chart 8: Top Cities
            cursor.execute(
                """
                SELECT COALESCE(l.city, 'Unknown') AS label, COUNT(br.id) AS value
                FROM locations l
                JOIN bid_requests br ON br.location_id = l.id AND br.deleted_at IS NULL
                GROUP BY label
                ORDER BY value DESC
                LIMIT 5
                """
            )
            top_cities = cursor.fetchall()

            # Chart 9: Recent Reports
            cursor.execute(
                """
                SELECT r.id, ru.full_name AS reporter, tu.full_name AS reported_party, r.reason, r.status, r.created_at
                FROM reports r
                JOIN users ru ON ru.id = r.reporter_id
                JOIN users tu ON tu.id = r.reported_user_id
                WHERE r.deleted_at IS NULL
                ORDER BY r.created_at DESC
                LIMIT 8
                """
            )
            recent_reports = cursor.fetchall()

            return {
                "metrics": metrics,
                "activity": activity,
                "charts": {
                    "revenue_by_month": revenue_by_month,
                    "dealers_by_state": dealers_by_state,
                    "dealers_by_category": dealers_by_category,
                    "buyers_by_state": buyers_by_state,
                    "products_by_category": products_by_category,
                    "bid_success_rate": bid_success_rate,
                    "top_categories": top_categories,
                    "top_cities": top_cities,
                    "recent_reports": recent_reports,
                }
            }

    def buyer_dashboard(self, buyer_id: str) -> dict[str, Any]:
        with db() as conn, conn.cursor() as cursor:
            expire_due_bid_requests(cursor)
            metrics = {
                "active_bids": one_row(cursor, "SELECT COUNT(*) AS value FROM bid_requests WHERE buyer_id=%s AND status='active'", [buyer_id])["value"],
                "orders": one_row(cursor, "SELECT COUNT(*) AS value FROM bid_requests WHERE buyer_id=%s AND status='awarded'", [buyer_id])["value"],
                "cart_items": one_row(cursor, "SELECT COUNT(*) AS value FROM carts c JOIN cart_items ci ON ci.cart_id=c.id WHERE c.buyer_id=%s AND c.status='active'", [buyer_id])["value"],
                "notifications": one_row(cursor, "SELECT COUNT(*) AS value FROM notifications WHERE user_id=%s AND read_at IS NULL AND deleted_at IS NULL", [buyer_id])["value"],
            }
            return {"metrics": metrics, "products": catalog_repo.list_products("")[:5], "notifications": notification_repo.list_notifications(buyer_id)}

    def dealer_dashboard(self, dealer_id: str) -> dict[str, Any]:
        requests = dealer_ops.incoming_requests(dealer_id)
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT subscribed FROM dealer_profiles WHERE user_id=%s", [dealer_id])
            sub_row = cursor.fetchone()
            is_sub = sub_row["subscribed"] if sub_row else False

            metrics = {
                "incoming_requests": len(requests),
                "submitted_bids": one_row(cursor, "SELECT COUNT(*) AS value FROM bids WHERE dealer_id=%s AND deleted_at IS NULL", [dealer_id])["value"],
                "won_bids": one_row(cursor, "SELECT COUNT(*) AS value FROM bids WHERE dealer_id=%s AND status='won'", [dealer_id])["value"],
                "lost_bids": one_row(cursor, "SELECT COUNT(*) AS value FROM bids WHERE dealer_id=%s AND status='lost'", [dealer_id])["value"],
                "subscription_status": "Subscribed ✓" if is_sub else "Not Active",
                "revenue": one_row(cursor, "SELECT COALESCE(SUM(b.amount),0) AS value FROM bids b WHERE b.dealer_id=%s AND b.status='won'", [dealer_id])["value"],
            }
            return {"metrics": metrics, "requests": requests[:5], "notifications": notification_repo.list_notifications(dealer_id)}


class AdminRepository:
    def list_users(self, role: str, query: str = "") -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        with db() as conn, conn.cursor() as cursor:
            if role == "dealer":
                cursor.execute(
                    """
                    SELECT u.id, u.email, u.full_name, u.phone, u.status, u.created_at,
                           dp.business_name, dp.owner_name, dp.business_address, dp.gst_number, dp.rating, dp.subscribed, dp.verification_status, dp.service_preferences, dp.dynamic_fields,
                           GROUP_CONCAT(DISTINCT l.country ORDER BY l.country SEPARATOR ', ') AS country,
                           GROUP_CONCAT(DISTINCT l.state ORDER BY l.state SEPARATOR ', ') AS state,
                           GROUP_CONCAT(DISTINCT l.city ORDER BY l.city SEPARATOR ', ') AS city,
                           GROUP_CONCAT(DISTINCT l.area ORDER BY l.area SEPARATOR ', ') AS area,
                           GROUP_CONCAT(DISTINCT l.pincode ORDER BY l.pincode SEPARATOR ', ') AS pincode,
                           GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') AS categories
                    FROM users u
                    JOIN roles r ON r.id=u.role_id AND r.name='dealer'
                    LEFT JOIN dealer_profiles dp ON dp.user_id=u.id
                    LEFT JOIN dealer_service_locations dsl ON dsl.dealer_id=u.id
                    LEFT JOIN locations l ON l.id=dsl.location_id
                    LEFT JOIN dealer_categories dc ON dc.dealer_id=u.id
                    LEFT JOIN categories c ON c.id=dc.category_id
                    WHERE u.deleted_at IS NULL
                      AND (%s='' OR u.email LIKE %s OR u.full_name LIKE %s OR u.phone LIKE %s OR dp.business_name LIKE %s OR dp.gst_number LIKE %s OR l.city LIKE %s OR l.pincode LIKE %s OR c.name LIKE %s OR u.id LIKE %s OR l.state LIKE %s OR l.area LIKE %s OR dp.service_preferences LIKE %s OR dp.dynamic_fields LIKE %s)
                    GROUP BY u.id, u.email, u.full_name, u.phone, u.status, u.created_at,
                             dp.business_name, dp.owner_name, dp.business_address, dp.gst_number, dp.rating, dp.subscribed, dp.verification_status, dp.service_preferences, dp.dynamic_fields
                    ORDER BY u.created_at DESC
                    """,
                    [query]+[pattern]*13,
                )
            else:
                cursor.execute(
                    """
                    SELECT u.id, u.email, u.full_name, u.phone, u.status, u.created_at,
                           COUNT(DISTINCT br.id) AS bid_count,
                           COUNT(DISTINCT CASE WHEN br.status = 'awarded' THEN br.id END) AS purchase_count,
                           GROUP_CONCAT(DISTINCT l.city SEPARATOR ', ') AS cities,
                           GROUP_CONCAT(DISTINCT l.state SEPARATOR ', ') AS states,
                           GROUP_CONCAT(DISTINCT l.country SEPARATOR ', ') AS countries,
                           GROUP_CONCAT(DISTINCT l.pincode SEPARATOR ', ') AS pincodes
                    FROM users u
                    JOIN roles r ON r.id=u.role_id AND r.name='buyer'
                    LEFT JOIN bid_requests br ON br.buyer_id=u.id AND br.deleted_at IS NULL
                    LEFT JOIN buyer_locations bl ON bl.buyer_id=u.id AND bl.deleted_at IS NULL
                    LEFT JOIN locations l ON l.id=bl.location_id AND l.deleted_at IS NULL
                    WHERE u.deleted_at IS NULL
                      AND (%s='' OR u.email LIKE %s OR u.full_name LIKE %s OR u.phone LIKE %s OR l.city LIKE %s OR l.state LIKE %s OR l.pincode LIKE %s OR u.id LIKE %s)
                    GROUP BY u.id, u.email, u.full_name, u.phone, u.status, u.created_at
                    ORDER BY u.created_at DESC
                    """,
                    [query]+[pattern]*7,
                )
            rows=cursor.fetchall()
            if role=='dealer':
                for row in rows:
                    for field in ('service_preferences','dynamic_fields'):
                        value=row.get(field) or {}
                        value=json.loads(value) if isinstance(value,str) else value
                        row[field]=value if isinstance(value,dict) else {}
                    preferences=row['service_preferences']
                    location=preferences.get('location') or {}
                    for key in ('country','state','city','area','pincode'):
                        row[key]=row.get(key) or location.get(key) or (preferences.get('country') if key=='country' else '')
                    row['brands']=', '.join(row['dynamic_fields'].get('brands') or [])
            return rows

    def set_user_status(self, actor_id: str, user_id: str, status: str, reason: str = "") -> None:
        allowed = {"active", "verified", "pending", "held", "flagged", "suspended", "banned", "deleted"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail="Invalid status")
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT u.status, r.name AS role FROM users u JOIN roles r ON r.id=u.role_id WHERE u.id=%s AND u.deleted_at IS NULL FOR UPDATE", [user_id])
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            if row['role'] not in {'buyer','dealer'}:
                raise HTTPException(status_code=400, detail="Only buyer and dealer accounts can be moderated here")
            cursor.execute("UPDATE users SET status=%s, updated_at=NOW() WHERE id=%s", [status, user_id])
            if row["role"] == "dealer" and status in {"active", "verified", "pending"}:
                # Admin approval must also update the profile used for matching.
                cursor.execute("UPDATE dealer_profiles SET verification_status=%s, updated_at=NOW() WHERE user_id=%s", ["pending" if status == "pending" else "verified", user_id])
            cursor.execute(
                """
                INSERT INTO status_history (id, entity_type, entity_id, old_status, new_status, changed_by, reason, created_at)
                VALUES (%s, 'user', %s, %s, %s, %s, %s, NOW())
                """,
                [new_id(), user_id, row["status"], status, actor_id, reason],
            )
            audit(cursor, actor_id, "user.status_changed", "users", user_id, {"status": status, "reason": reason})

    def list_logs(self) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.id, u.email AS actor, a.action, a.entity_type, a.entity_id, a.metadata_json, a.created_at
                FROM audit_logs a
                LEFT JOIN users u ON u.id=a.actor_id
                ORDER BY a.created_at DESC
                LIMIT 300
                """
            )
            return cursor.fetchall()

    def list_commissions(self) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id, c.amount, c.rate_percent, c.payment_status, c.paid_at, c.created_at,
                       b.id AS bid_id, dp.business_name AS dealer, p.name AS product
                FROM commissions c
                JOIN bids b ON b.id=c.bid_id
                JOIN dealer_profiles dp ON dp.user_id=b.dealer_id
                JOIN bid_requests br ON br.id=b.bid_request_id
                JOIN products p ON p.id=br.product_id
                ORDER BY c.created_at DESC
                """
            )
            return cursor.fetchall()

    def set_commission_status(self, actor_id: str, commission_id: str, status: str) -> tuple[str | None, list[str]]:
        allowed = {"pending", "paid", "failed", "waived", "refunded"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail="Invalid payment status")
        bid_id = None
        recipients: list[str] = []
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT bid_id, payment_status FROM commissions WHERE id=%s FOR UPDATE", [commission_id])
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Commission not found")
            bid_id = existing["bid_id"]
            if existing["payment_status"] == status:
                return bid_id, []
            transitions = {
                "pending": {"paid", "failed", "waived"},
                "failed": {"pending", "paid", "waived"},
                "paid": {"refunded"},
                "waived": set(),
                "refunded": set(),
            }
            if status not in transitions.get(existing["payment_status"], set()):
                raise HTTPException(status_code=409, detail="Invalid commission payment transition")
            paid_at = "NOW()" if status == "paid" else "paid_at" if status == "refunded" else "NULL"
            cursor.execute(
                f"UPDATE commissions SET payment_status=%s, paid_at={paid_at}, updated_at=NOW() WHERE id=%s",
                [status, commission_id],
            )
            invoice_status = "paid" if status == "paid" else "cancelled" if status in {"waived", "refunded"} else "issued"
            cursor.execute(
                "UPDATE invoices SET status=%s, updated_at=NOW() WHERE bid_id=%s",
                [invoice_status, bid_id],
            )
            was_unlocked = existing["payment_status"] in {"paid", "waived"}
            is_unlocked = status in {"paid", "waived"}
            if is_unlocked and not was_unlocked:
                recipients = create_contact_reveal_notifications(cursor, bid_id)
            audit(cursor, actor_id, "commission.status_changed", "commissions", commission_id, {"status": status})
        return bid_id, recipients


class CartRepository:
    def get_cart(self, buyer_id: str) -> dict[str, Any]:
        with db() as conn, conn.cursor() as cursor:
            cart_id = self._active_cart(cursor, buyer_id)
            cursor.execute(
                """
                SELECT ci.id, ci.product_id, ci.quantity, p.name, p.brand, p.model, p.price_min, p.price_max
                FROM cart_items ci JOIN products p ON p.id=ci.product_id
                WHERE ci.cart_id=%s AND p.status='active' AND p.deleted_at IS NULL
                ORDER BY ci.created_at DESC
                """,
                [cart_id],
            )
            return {"id": cart_id, "items": cursor.fetchall()}

    def add_item(self, buyer_id: str, product_id: str, quantity: int) -> None:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM products WHERE id=%s AND status='active' AND deleted_at IS NULL",
                [product_id],
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Active product not found")
            cart_id = self._active_cart(cursor, buyer_id)
            cursor.execute(
                """
                INSERT INTO cart_items (id, cart_id, product_id, quantity, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE quantity=LEAST(100000, quantity+VALUES(quantity)), updated_at=NOW()
                """,
                [new_id(), cart_id, product_id, max(1, quantity)],
            )
            audit(cursor, buyer_id, "cart.item_added", "products", product_id, {"quantity": quantity})

    def remove_item(self, buyer_id: str, item_id: str) -> None:
        with db() as conn, conn.cursor() as cursor:
            cart_id = self._active_cart(cursor, buyer_id)
            cursor.execute("DELETE FROM cart_items WHERE id=%s AND cart_id=%s", [item_id, cart_id])
            audit(cursor, buyer_id, "cart.item_removed", "cart_items", item_id, {})

    def start_bid(self, buyer_id: str, product_id: str, location_id: str | None, radius_km: float, quantity: int, fields: dict[str, str], skip_flagged_dealers: bool = True, expiry_minutes: int | None = None) -> str:
        request_id = new_id()
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL FOR UPDATE", [buyer_id])
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Buyer not found")
            rules = SettingsRepository.read_setting(cursor, "bid_rules")
            expiry_minutes = int(expiry_minutes if expiry_minutes is not None else round(float(rules["expiry_hours"]) * 60))
            if not float(rules["min_time_hours"]) * 60 - 1e-9 <= expiry_minutes <= float(rules["max_time_hours"]) * 60 + 1e-9:
                raise HTTPException(status_code=400, detail="Request duration is outside the configured bidding limits")
            cursor.execute("SELECT p.id FROM products p JOIN categories c ON c.id=p.category_id LEFT JOIN categories sc ON sc.id=p.subcategory_id WHERE p.id=%s AND p.status='active' AND p.deleted_at IS NULL AND c.status='active' AND c.deleted_at IS NULL AND (p.subcategory_id IS NULL OR (sc.status='active' AND sc.deleted_at IS NULL)) FOR UPDATE", [product_id])
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Active product not found")
            if not location_id:
                cursor.execute(
                    """
                    SELECT location_id
                    FROM buyer_locations
                    WHERE buyer_id=%s AND deleted_at IS NULL
                    ORDER BY is_default DESC, updated_at DESC
                    LIMIT 1
                    """,
                    [buyer_id],
                )
                location_id = (cursor.fetchone() or {}).get("location_id")
            if not location_id:
                cursor.execute("SELECT default_location_id FROM buyer_profiles WHERE user_id=%s", [buyer_id])
                location_id = (cursor.fetchone() or {}).get("default_location_id")
            if not location_id:
                raise HTTPException(status_code=400, detail="Add a saved buyer location in Profile before starting a bid")
            cursor.execute(
                """
                SELECT l.id, l.latitude, l.longitude
                FROM locations l
                LEFT JOIN buyer_locations bl ON bl.location_id=l.id AND bl.buyer_id=%s AND bl.deleted_at IS NULL
                LEFT JOIN buyer_profiles bp ON bp.default_location_id=l.id AND bp.user_id=%s
                WHERE l.id=%s AND l.deleted_at IS NULL AND (bl.id IS NOT NULL OR bp.user_id IS NOT NULL)
                """,
                [buyer_id, buyer_id, location_id],
            )
            selected_location = cursor.fetchone()
            if not selected_location:
                raise HTTPException(status_code=403, detail="Select one of your saved locations")
            if not valid_coordinates(selected_location):
                raise HTTPException(status_code=400, detail="Selected saved location needs a valid map pin")
            # Zero means no additional buyer distance limit. Dealer coverage
            # always applies; a saved profile preference must not override this request.
            buyer_radius_km = float(radius_km or 0)
            location_rules = SettingsRepository.read_setting(cursor, "location_rules")
            if buyer_radius_km > float(location_rules["max_radius_km"]):
                raise HTTPException(status_code=400, detail="Buyer radius exceeds the configured maximum")

            eligible = dealer_ops.matching_dealer_ids(cursor, product_id, location_id, buyer_radius_km, skip_flagged_dealers)
            maximum_dealers = int(rules["max_dealers"])
            if maximum_dealers > 0:
                eligible = eligible[:maximum_dealers]
            if not eligible:
                raise HTTPException(status_code=400, detail="No subscribed dealers match this saved location and product category/item")

            cursor.execute(
                """
                INSERT INTO bid_requests (id, buyer_id, product_id, location_id, quantity, radius_km, skip_flagged_dealers, status, expires_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', DATE_ADD(NOW(), INTERVAL %s MINUTE), NOW(), NOW())
                """,
                [request_id, buyer_id, product_id, location_id, max(1, quantity), buyer_radius_km, skip_flagged_dealers, expiry_minutes],
            )
            for key, value in fields.items():
                cursor.execute(
                    "INSERT INTO bid_request_fields (id, bid_request_id, field_name, field_value, created_at) VALUES (%s, %s, %s, %s, NOW())",
                    [new_id(), request_id, key, value],
                )

            cursor.execute("SELECT name FROM products WHERE id=%s", [product_id])
            prod_name = (cursor.fetchone() or {}).get("name", "Product")

            notified_count = 0
            for dealer_id in eligible:
                # Always record in bid_request_dealers so matching is tracked
                cursor.execute(
                    "INSERT IGNORE INTO bid_request_dealers (bid_request_id, dealer_id, notified_at, status) VALUES (%s, %s, NOW(), 'notified')",
                    [request_id, dealer_id],
                )
                cursor.execute(
                    """
                    INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, created_at)
                    VALUES (%s, %s, 'new_bid_request', 'New bid request',
                           'A matching buyer request is available in your service area.', %s, NOW())
                    """,
                    [new_id(), dealer_id, request_id],
                )
                notified_count += 1

            logger.info(
                "Bid %s: %d matching dealers, %d subscribed/notified",
                request_id, len(eligible), notified_count,
            )

            # Insert buyer confirmation notification
            cursor.execute(
                """
                INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, created_at)
                VALUES (%s, %s, 'bid_request_created', 'Bid Broadcasted Successfully', %s, %s, NOW())
                """,
                [
                    new_id(), buyer_id,
                    f"Your bid request for {prod_name} has been broadcasted. {notified_count} subscribed dealer(s) notified. You will receive offers soon.",
                    request_id,
                ]
            )
            audit(cursor, buyer_id, "bid_request.created", "bid_requests", request_id, {"dealers_matched": len(eligible), "dealers_notified": notified_count})
        return request_id

    def accept_bid(self, buyer_id: str, bid_id: str) -> dict[str, Any]:
        with db() as conn, conn.cursor() as cursor:
            expire_due_bid_requests(cursor)
            cursor.execute(
                """
                SELECT bid_request_id FROM bids
                WHERE id=%s AND deleted_at IS NULL
                """,
                [bid_id],
            )
            bid_ref = cursor.fetchone()
            if not bid_ref:
                raise HTTPException(status_code=400, detail="Bid not found, expired, or no longer selectable")
            cursor.execute(
                """
                SELECT id, buyer_id, product_id, location_id, radius_km, skip_flagged_dealers, winning_bid_id, status, expires_at, (expires_at > NOW()) AS is_open
                FROM bid_requests WHERE id=%s AND deleted_at IS NULL FOR UPDATE
                """,
                [bid_ref["bid_request_id"]],
            )
            request = cursor.fetchone()
            if request and request["buyer_id"] == buyer_id and request["status"] == "awarded" and request["winning_bid_id"] == bid_id:
                cursor.execute("SELECT dealer_id FROM bids WHERE id=%s AND status='won'", [bid_id])
                winner = cursor.fetchone()
                if winner:
                    return {"buyer_id": buyer_id, "winner_id": winner["dealer_id"], "loser_ids": [], "bid_id": bid_id, "request_id": request["id"]}
            if not request or request["buyer_id"] != buyer_id or request["status"] != "active" or not request["is_open"]:
                raise HTTPException(status_code=400, detail="Bid not found, expired, or no longer selectable")
            cursor.execute(
                """
                SELECT b.bid_request_id, b.amount, b.dealer_id, p.name AS product, c.name AS category, c.id AS category_id
                FROM bids b JOIN products p ON p.id=%s
                JOIN categories c ON c.id=p.category_id
                WHERE b.id=%s AND b.bid_request_id=%s AND b.status IN ('active','updated')
                  AND b.deleted_at IS NULL AND b.created_at <= %s
                FOR UPDATE
                """,
                [request["product_id"], bid_id, request["id"], request["expires_at"]],
            )
            bid = cursor.fetchone()
            if not bid:
                raise HTTPException(status_code=400, detail="Bid not found, expired, or no longer selectable")
            if not dealer_ops.request_dealer_is_eligible(cursor, request, bid["dealer_id"], lock=True):
                raise HTTPException(status_code=400, detail="This dealer is no longer eligible for this request")
            cursor.execute(
                "SELECT id, dealer_id FROM bids WHERE bid_request_id=%s AND id<>%s AND deleted_at IS NULL AND status IN ('active','updated') FOR UPDATE",
                [bid["bid_request_id"], bid_id],
            )
            losing_bids = cursor.fetchall()
            loser_ids = [row["dealer_id"] for row in losing_bids]
            cursor.execute("UPDATE bids SET status='lost', updated_at=NOW() WHERE bid_request_id=%s AND id<>%s AND deleted_at IS NULL AND status IN ('active','updated')", [bid["bid_request_id"], bid_id])
            cursor.execute("UPDATE bids SET status='won', updated_at=NOW() WHERE id=%s AND status IN ('active','updated')", [bid_id])
            if cursor.rowcount != 1:
                raise HTTPException(status_code=400, detail="Bid is no longer selectable")
            cursor.execute("UPDATE bid_requests SET status='awarded', winning_bid_id=%s, updated_at=NOW() WHERE id=%s AND status='active' AND expires_at > NOW()", [bid_id, bid["bid_request_id"]])
            if cursor.rowcount != 1:
                raise HTTPException(status_code=400, detail="Bid request is no longer active")

            # Subscription covers participation; no commission or invoice is created.
            # Notify buyer — contact immediately visible (no commission)
            cursor.execute(
                """
                INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, created_at)
                VALUES (%s, %s, 'bid_accepted', 'Winning dealer selected', %s, %s, NOW())
                """,
                [
                    new_id(),
                    buyer_id,
                    f"You selected the winning dealer for {bid['product']}. Open Bid History to view dealer contact details.",
                    bid_id,
                ]
            )
            # The subscription covers bidding; contacts unlock on selection.
            cursor.execute(
                """
                INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, created_at)
                VALUES (%s, %s, 'bid_accepted', 'Congratulations, you won this bid!', %s, %s, NOW())
                """,
                [
                    new_id(),
                    bid["dealer_id"],
                    f"Your offer for {bid['product']} was selected. Open Bid History for buyer contacts and your private bid conversation.",
                    bid_id,
                ]
            )
            for loser in losing_bids:
                cursor.execute(
                    """
                    INSERT INTO notifications (id, user_id, event_type, title, body, target_bid_id, created_at)
                    VALUES (%s, %s, 'bid_lost', 'Bid closed', %s, %s, NOW())
                    """,
                    [
                        new_id(),
                        loser["dealer_id"],
                        f"The buyer selected another dealer for {bid['product']}. This bid is now closed.",
                        loser["id"],
                    ],
                )

            audit(cursor, buyer_id, "bid.accepted", "bids", bid_id, {})
            return {
                "buyer_id": buyer_id,
                "winner_id": bid["dealer_id"],
                "loser_ids": loser_ids,
                "bid_id": bid_id,
                "request_id": bid["bid_request_id"],
            }

    def _active_cart(self, cursor, buyer_id: str) -> str:
        # Serialize creation, since carts has no unique constraint for active carts.
        cursor.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", [buyer_id])
        cursor.execute("SELECT id FROM carts WHERE buyer_id=%s AND status='active' AND deleted_at IS NULL ORDER BY created_at, id FOR UPDATE", [buyer_id])
        rows = cursor.fetchall()
        if rows:
            cart_id = rows[0]["id"]
            for duplicate in rows[1:]:
                cursor.execute("SELECT product_id,quantity FROM cart_items WHERE cart_id=%s", [duplicate["id"]])
                for item in cursor.fetchall():
                    cursor.execute("INSERT INTO cart_items (id,cart_id,product_id,quantity,created_at,updated_at) VALUES (%s,%s,%s,%s,NOW(),NOW()) ON DUPLICATE KEY UPDATE quantity=LEAST(100000,quantity+VALUES(quantity)),updated_at=NOW()", [new_id(),cart_id,item["product_id"],item["quantity"]])
                cursor.execute("DELETE FROM cart_items WHERE cart_id=%s", [duplicate["id"]])
                cursor.execute("UPDATE carts SET status='abandoned',updated_at=NOW() WHERE id=%s", [duplicate["id"]])
            return cart_id
        cart_id = new_id()
        cursor.execute("INSERT INTO carts (id, buyer_id, status, created_at, updated_at) VALUES (%s, %s, 'active', NOW(), NOW())", [cart_id, buyer_id])
        return cart_id


class DealerOpsRepository:
    def request_dealer_is_eligible(self, cursor, request: dict[str, Any], dealer_id: str, lock: bool = False) -> bool:
        if lock:
            # Profile edits and admin status changes lock this same user row.
            cursor.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", [dealer_id])
            cursor.fetchone()
            cursor.execute("SELECT user_id FROM dealer_profiles WHERE user_id=%s FOR UPDATE", [dealer_id])
            cursor.fetchone()
        cursor.execute("SELECT status FROM bid_request_dealers WHERE bid_request_id=%s AND dealer_id=%s", [request["id"], dealer_id])
        row = cursor.fetchone()
        if not row or row["status"] not in {"notified", "viewed", "bid"}:
            return False
        return dealer_id in self.matching_dealer_ids(
            cursor, request["product_id"], request["location_id"], float(request["radius_km"] or 0),
            bool(request["skip_flagged_dealers"]), dealer_id,
        )

    def matching_dealer_ids(self, cursor, product_id: str, location_id: str, radius_km: float, skip_flagged_dealers: bool = True, dealer_id: str | None = None) -> list[str]:
        rules = SettingsRepository.read_setting(cursor, "dealer_rules")
        location_rules = SettingsRepository.read_setting(cursor, "location_rules")
        cursor.execute(
            """
            SELECT p.category_id, p.subcategory_id, p.brand FROM products p
            JOIN categories c ON c.id=p.category_id AND c.status='active' AND c.deleted_at IS NULL
            LEFT JOIN categories sc ON sc.id=p.subcategory_id
            WHERE p.id=%s AND p.status='active' AND p.deleted_at IS NULL
              AND (p.subcategory_id IS NULL OR (sc.parent_id=p.category_id AND sc.status='active' AND sc.deleted_at IS NULL))
            """,
            [product_id],
        )
        product = cursor.fetchone()
        if not product:
            logger.debug("matching_dealer_ids: product %s not found", product_id)
            return []
        cursor.execute("SELECT id AS location_id, country, area, city, state, pincode, latitude, longitude FROM locations WHERE id=%s AND deleted_at IS NULL", [location_id])
        origin = cursor.fetchone()
        if not origin or not valid_coordinates(origin):
            logger.debug("matching_dealer_ids: buyer location %s has invalid coordinates", location_id)
            return []
        # Regional coverage can match without a dealer map pin. Radius coverage
        # validates the dealer pin after the coverage method is read.
        cursor.execute(
            """
            SELECT u.id, l.country, l.area, l.city, l.state, l.pincode,
                   l.latitude, l.longitude, dsl.radius_km,
                   dp.service_preferences, dp.dynamic_fields
            FROM users u
            JOIN roles r ON r.id=u.role_id AND r.name='dealer'
            JOIN dealer_categories dc_parent ON dc_parent.dealer_id=u.id AND dc_parent.category_id=%s
            LEFT JOIN dealer_categories dc_item ON dc_item.dealer_id=u.id AND dc_item.category_id=%s
            LEFT JOIN (
                SELECT dealer_id,
                       location_id,
                       radius_km
                FROM dealer_service_locations
                WHERE dealer_id IN (
                    SELECT user_id FROM dealer_profiles
                )
                AND (dealer_id, created_at) IN (
                    SELECT dealer_id, MAX(created_at)
                    FROM dealer_service_locations
                    GROUP BY dealer_id
                )
            ) dsl ON dsl.dealer_id=u.id
            LEFT JOIN locations l ON l.id=dsl.location_id AND l.deleted_at IS NULL
            JOIN dealer_profiles dp ON dp.user_id=u.id AND dp.subscribed=TRUE AND dp.deleted_at IS NULL
            WHERE u.status IN ('active','verified','flagged','pending') AND u.deleted_at IS NULL
              AND (u.status <> 'pending' OR %s = FALSE)
              AND (%s = FALSE OR dp.verification_status='verified')
              AND dp.verification_status <> 'rejected' AND dp.rating >= %s
              AND (%s IS NULL OR u.id=%s)
              AND (
                  %s IS NULL OR dc_item.category_id IS NOT NULL OR NOT EXISTS (
                      SELECT 1
                      FROM dealer_categories dc_config
                      JOIN categories configured_item ON configured_item.id=dc_config.category_id
                      WHERE dc_config.dealer_id=u.id
                        AND configured_item.parent_id=%s
                        AND configured_item.deleted_at IS NULL
                  )
              )
              AND (%s = FALSE OR u.status <> 'flagged')
            """,
            [
                product["category_id"],
                product["subcategory_id"],
                bool(rules["verification_required"]),
                bool(rules["verification_required"]),
                float(rules["min_rating_threshold"]),
                dealer_id, dealer_id,
                product["subcategory_id"],
                product["category_id"],
                skip_flagged_dealers,
            ],
        )
        candidates = cursor.fetchall()
        logger.debug(
            "matching_dealer_ids: product=%s origin=%s/%s — %d candidate dealer(s)",
            product_id, origin.get("city"), origin.get("state"), len(candidates),
        )
        matched = []
        buyer_state = normalize_place(origin.get("state"))
        buyer_city = normalize_place(origin.get("city"))
        buyer_area = normalize_place(origin.get("area"))
        for row in candidates:
            if row.get("country") and normalize_place(row["country"]) != normalize_place(origin["country"]):
                continue

            preferences = row.get("service_preferences") or {}
            if isinstance(preferences, str):
                try:
                    preferences = json.loads(preferences)
                except json.JSONDecodeError:
                    preferences = {}
            if not isinstance(preferences, dict):
                preferences = {}
            service_country = preferences.get("country") or row.get("country") or "India"
            if normalize_place(service_country) != normalize_place(origin.get("country")):
                continue
            method = normalize_place(preferences.get("method") or "radius")
            method = {"state": "states", "district": "districts", "city": "cities"}.get(method, method)
            if method not in {"radius", "states", "districts", "cities"}:
                continue

            def normalized_values(*keys: str) -> set[str]:
                values: set[str] = set()
                for key in keys:
                    raw = preferences.get(key) or []
                    if isinstance(raw, str):
                        raw = raw.split(",")
                    if isinstance(raw, (list, tuple, set)):
                        values.update(normalize_place(value) for value in raw if normalize_place(value))
                return values

            if method == "states":
                coverage = normalized_values("states", "service_states")
                is_match = bool(buyer_state and buyer_state in coverage)
                detail = f"state={origin.get('state')}"
            elif method == "districts":
                coverage = normalized_values("districts", "service_districts")
                is_match = bool(coverage.intersection({buyer_city, buyer_area} - {""}))
                detail = f"district={origin.get('city')}/{origin.get('area')}"
            elif method == "cities":
                coverage = normalized_values("cities", "service_cities")
                is_match = bool(buyer_city and buyer_city in coverage)
                detail = f"city={origin.get('city')}"
            else:
                # Radius coverage uses the dealer's pinned service location and their configured range.
                dealer_radius = min(float(row["radius_km"] or 0), float(location_rules["max_radius_km"]))
                if dealer_radius <= 0 or not valid_coordinates(row):
                    logger.debug("  dealer %s skipped: invalid pin or service radius", row["id"])
                    continue
                distance = haversine_km(
                    float(origin["latitude"]),
                    float(origin["longitude"]),
                    float(row["latitude"]),
                    float(row["longitude"]),
                )
                is_match = distance <= dealer_radius
                detail = f"radius={dealer_radius:.1f}km distance={distance:.1f}km"
            # Disambiguate identically named cities/districts using selected states
            # (or the pinned state when no explicit state list is configured).
            if method in {"cities", "districts"}:
                states = normalized_values("states", "service_states")
                shop_state = row.get("state") or (preferences.get("location") or {}).get("state")
                if not states and shop_state:
                    states = {normalize_place(shop_state)}
                if states and buyer_state not in states:
                    is_match = False
            distance = float("inf")
            if valid_coordinates(row):
                distance = haversine_km(float(origin["latitude"]), float(origin["longitude"]), float(row["latitude"]), float(row["longitude"]))
            if radius_km > 0 and distance > radius_km:
                is_match = False
            logger.debug("  dealer %s %s → %s", row["id"], detail, "MATCH" if is_match else "SKIP")
            if is_match:
                matched.append((distance, row["id"]))
        logger.debug("matching_dealer_ids: %d matched out of %d candidates", len(matched), len(candidates))
        return list(dict.fromkeys(dealer for _, dealer in sorted(matched)))

    def incoming_requests(self, dealer_id: str) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            expire_due_bid_requests(cursor)
            cursor.execute(
                """
                SELECT br.id, br.product_id, br.location_id, br.skip_flagged_dealers, p.name AS product, c.name AS category, br.quantity, br.radius_km, br.status, br.expires_at,
                       UNIX_TIMESTAMP(br.expires_at) AS expires_at_epoch,
                       CONCAT(l.area, ', ', l.city) AS buyer_area
                FROM bid_request_dealers brd
                JOIN bid_requests br ON br.id=brd.bid_request_id
                JOIN products p ON p.id=br.product_id
                JOIN categories c ON c.id=p.category_id
                JOIN locations l ON l.id=br.location_id
                JOIN users u ON u.id=brd.dealer_id
                JOIN dealer_profiles dp ON dp.user_id=u.id AND dp.subscribed=TRUE
                WHERE brd.dealer_id=%s AND u.status IN ('active','verified','flagged','pending')
                  AND u.deleted_at IS NULL AND br.status='active' AND br.expires_at > NOW()
                  AND br.deleted_at IS NULL AND dp.deleted_at IS NULL
                  AND brd.status IN ('notified','viewed','bid')
                  AND NOT EXISTS (
                    SELECT 1 FROM bids b
                    WHERE b.bid_request_id=br.id AND b.dealer_id=brd.dealer_id
                      AND b.deleted_at IS NULL AND b.status IN ('active','updated','won','lost')
                  )
                ORDER BY br.expires_at ASC
                LIMIT 100
                """,
                [dealer_id],
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                if self.request_dealer_is_eligible(cursor, row, dealer_id):
                    row["expires_at"] = datetime.fromtimestamp(float(row.pop("expires_at_epoch")), timezone.utc).isoformat()
                    result.append(row)
            return result

    def submit_bid(self, dealer_id: str, payload: "BidIn") -> str:
        with db() as conn, conn.cursor() as cursor:
            expire_due_bid_requests(cursor)
            cursor.execute("SELECT status FROM users WHERE id=%s", [dealer_id])
            dealer = cursor.fetchone()
            rules = SettingsRepository.read_setting(cursor, "dealer_rules")
            allowed_statuses = {"active", "verified", "flagged"} | ({"pending"} if not rules["verification_required"] else set())
            if not dealer or dealer["status"] not in allowed_statuses:
                raise HTTPException(status_code=403, detail="Dealer status blocks bidding")
            cursor.execute("SELECT subscribed FROM dealer_profiles WHERE user_id=%s AND deleted_at IS NULL", [dealer_id])
            profile = cursor.fetchone()
            if not profile or not profile["subscribed"]:
                raise HTTPException(status_code=403, detail="Activate a dealer subscription before bidding")
            cursor.execute(
                "SELECT id, product_id, location_id, radius_km, skip_flagged_dealers, status, expires_at, (expires_at > NOW()) AS is_open FROM bid_requests WHERE id=%s AND deleted_at IS NULL FOR UPDATE",
                [payload.bid_request_id],
            )
            request = cursor.fetchone()
            if not request or request["status"] != "active" or not request["is_open"]:
                raise HTTPException(status_code=400, detail="Bid request has expired")
            cursor.execute(
                """
                SELECT brd.status, br.expires_at, br.status AS request_status, (br.expires_at > NOW()) AS is_open
                FROM bid_request_dealers brd
                JOIN bid_requests br ON br.id=brd.bid_request_id
                WHERE brd.bid_request_id=%s AND brd.dealer_id=%s
                """,
                [payload.bid_request_id, dealer_id],
            )
            eligibility = cursor.fetchone()
            if not eligibility or not self.request_dealer_is_eligible(cursor, request, dealer_id, lock=True):
                raise HTTPException(status_code=403, detail="Bid request is outside dealer eligibility")
            if eligibility["request_status"] != "active" or not eligibility["is_open"]:
                raise HTTPException(status_code=400, detail="Bid request has expired")
            cursor.execute(
                """
                SELECT id, status, amount FROM bids
                WHERE bid_request_id=%s AND dealer_id=%s
                FOR UPDATE
                """,
                [payload.bid_request_id, dealer_id],
            )
            existing = cursor.fetchone()
            if existing:
                if existing["status"] not in {"active", "updated", "withdrawn"}:
                    raise HTTPException(status_code=400, detail="This offer cannot be reopened")
                step = Decimal(str(SettingsRepository.read_setting(cursor, "bid_rules")["min_bidding_increment"]))
                previous = Decimal(str(existing["amount"]))
                current = Decimal(str(payload.amount))
                if existing["status"] != "withdrawn" and current != previous and step > 0 and previous - current < step:
                    raise HTTPException(status_code=400, detail=f"A revised price must decrease by at least {step} (terms may change at the same price)")
                cursor.execute(
                    """
                    UPDATE bids b JOIN bid_requests br ON br.id=b.bid_request_id
                    SET b.amount=%s, b.discount_amount=%s, b.warranty_text=%s, b.delivery_time=%s,
                        b.installation_included=%s, b.free_gifts=%s, b.extra_services=%s,
                        b.notes=%s, b.status='updated', b.deleted_at=NULL, b.updated_at=NOW()
                    WHERE b.id=%s AND br.status='active' AND br.expires_at > NOW()
                    """,
                    [
                        payload.amount,
                        payload.discount_amount,
                        payload.warranty_text,
                        payload.delivery_time,
                        payload.installation_included,
                        payload.free_gifts,
                        payload.extra_services,
                        payload.notes,
                        existing["id"],
                    ],
                )
                if cursor.rowcount == 0:
                    cursor.execute("SELECT (expires_at > NOW()) AS is_open FROM bid_requests WHERE id=%s", [request["id"]])
                    if not cursor.fetchone()["is_open"]:
                        raise HTTPException(status_code=400, detail="Bid request has expired")
                cursor.execute("UPDATE bid_request_dealers SET status='bid' WHERE bid_request_id=%s AND dealer_id=%s", [payload.bid_request_id, dealer_id])
                audit(cursor, dealer_id, "bid.updated", "bids", existing["id"], {"amount": payload.amount})
                return existing["id"]
            bid_id = new_id()
            cursor.execute(
                """
                INSERT INTO bids (id, bid_request_id, dealer_id, amount, discount_amount, warranty_text, delivery_time, installation_included, free_gifts, extra_services, notes, status, created_at, updated_at)
                SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW()
                FROM bid_requests WHERE id=%s AND status='active' AND expires_at > NOW()
                """,
                [bid_id, payload.bid_request_id, dealer_id, payload.amount, payload.discount_amount, payload.warranty_text, payload.delivery_time, payload.installation_included, payload.free_gifts, payload.extra_services, payload.notes, payload.bid_request_id],
            )
            if cursor.rowcount != 1:
                raise HTTPException(status_code=400, detail="Bid request has expired")
            cursor.execute("UPDATE bid_request_dealers SET status='bid' WHERE bid_request_id=%s AND dealer_id=%s", [payload.bid_request_id, dealer_id])
            audit(cursor, dealer_id, "bid.submitted", "bid_requests", payload.bid_request_id, {"amount": payload.amount})
            return bid_id


class ReportRepository:
    def list_reports(self, viewer_id: str = None, viewer_role: str = None) -> list[dict[str, Any]]:
        with db() as conn, conn.cursor() as cursor:
            query = """
                SELECT r.id, r.reporter_id, r.reported_user_id, ru.full_name AS reporter, tu.full_name AS reported_party,
                       r.bid_id, p.name AS product, p.brand AS product_brand, b.amount AS bid_amount,
                       br.quantity AS quantity, b.warranty_text AS warranty, b.delivery_time AS delivery,
                       r.reason, r.description, r.status, r.created_at,
                       r.closure_requested_by, cu.full_name AS closure_requested_by_name,
                       r.closure_reason, r.closure_requested_status,
                       b.status AS bid_status,
                       (br.status='awarded' AND br.winning_bid_id=b.id) AS contacts_unlocked,
                       COALESCE(c.payment_status, 'not_due') AS commission_payment_status
                FROM reports r
                JOIN users ru ON ru.id=r.reporter_id
                JOIN users tu ON tu.id=r.reported_user_id
                JOIN bids b ON b.id=r.bid_id
                JOIN bid_requests br ON br.id=b.bid_request_id
                JOIN products p ON p.id=br.product_id
                LEFT JOIN users cu ON cu.id=r.closure_requested_by
                LEFT JOIN commissions c ON c.bid_id=b.id
                WHERE r.deleted_at IS NULL
            """
            params = []
            if viewer_role and viewer_role != "admin":
                query += " AND (r.reporter_id = %s OR r.reported_user_id = %s)"
                params.extend([viewer_id, viewer_id])

            query += " ORDER BY r.created_at DESC LIMIT 200"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if viewer_role and viewer_role != "admin":
                for r in rows:
                    if not r["contacts_unlocked"]:
                        if viewer_role == "buyer":
                            if r["reporter_id"] != viewer_id:
                                r["reporter"] = "Dealer"
                            if r["reported_user_id"] != viewer_id:
                                r["reported_party"] = "Dealer"
                            if r["closure_requested_by"] and r["closure_requested_by"] != viewer_id:
                                r["closure_requested_by_name"] = "Dealer"
                        elif viewer_role == "dealer":
                            if r["reporter_id"] != viewer_id:
                                r["reporter"] = "Buyer"
                            if r["reported_user_id"] != viewer_id:
                                r["reported_party"] = "Buyer"
                            if r["closure_requested_by"] and r["closure_requested_by"] != viewer_id:
                                r["closure_requested_by_name"] = "Buyer"
            return rows

    def request_closure(self, actor_id: str, report_id: str, reason: str) -> list[str]:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT reporter_id, reported_user_id, bid_id
                FROM reports
                WHERE id=%s AND deleted_at IS NULL
                """,
                [report_id],
            )
            report = cursor.fetchone()
            if not report:
                raise HTTPException(status_code=404, detail="Report not found")
            if actor_id != report["reporter_id"]:
                raise HTTPException(status_code=403, detail="Only the user who created the report can cancel it")
            cursor.execute(
                """
                UPDATE reports
                SET status='closed',
                    closure_requested_by=%s,
                    closure_reason=%s,
                    closure_requested_status='approved',
                    updated_at=NOW()
                WHERE id=%s
                """,
                [actor_id, reason, report_id],
            )
            cursor.execute(
                """
                INSERT INTO report_messages (id, report_id, sender_id, recipient_group, message, created_at)
                VALUES (%s, %s, %s, 'both', %s, NOW())
                """,
                [new_id(), report_id, actor_id, "Report cancelled by reporter."],
            )
            recipients = list({report["reporter_id"], report["reported_user_id"]})
            for recipient in recipients:
                create_notification(
                    cursor,
                    recipient,
                    "Report cancelled",
                    "The report linked to your bid has been cancelled by the reporter.",
                    "report_cancelled",
                    target_bid_id=report["bid_id"],
                    target_report_id=report_id,
                )
            audit(cursor, actor_id, "report.cancelled", "reports", report_id, {"reason": reason})
            return recipients

    def decide_closure(self, actor_id: str, report_id: str, approve: bool, note: str = "") -> list[str]:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT reporter_id, reported_user_id, bid_id, closure_requested_by
                FROM reports
                WHERE id=%s AND deleted_at IS NULL AND closure_requested_status='requested'
                """,
                [report_id],
            )
            report = cursor.fetchone()
            if not report:
                raise HTTPException(status_code=404, detail="Closure request not found")
            if approve:
                cursor.execute(
                    """
                    UPDATE reports
                    SET status='resolved', closure_requested_status='approved',
                        internal_notes=CONCAT(COALESCE(internal_notes,''), %s),
                        updated_at=NOW()
                    WHERE id=%s
                    """,
                    [f"\n{now_utc().isoformat()} Closure approved. {note}" if note else f"\n{now_utc().isoformat()} Closure approved.", report_id],
                )
                title = "Report closure approved"
                body = "Admin approved the closure request. The report is marked resolved."
            else:
                cursor.execute(
                    """
                    UPDATE reports
                    SET closure_requested_status='rejected',
                        internal_notes=CONCAT(COALESCE(internal_notes,''), %s),
                        updated_at=NOW()
                    WHERE id=%s
                    """,
                    [f"\n{now_utc().isoformat()} Closure rejected. {note}" if note else f"\n{now_utc().isoformat()} Closure rejected.", report_id],
                )
                title = "Report closure rejected"
                body = "Admin rejected the closure request. The report remains open for review."
            recipients = [report["reporter_id"], report["reported_user_id"]]
            for recipient in recipients:
                create_notification(
                    cursor,
                    recipient,
                    title,
                    body,
                    "report_updated",
                    target_bid_id=report["bid_id"],
                    target_report_id=report_id,
                )
            audit(cursor, actor_id, "report.closure_decided", "reports", report_id, {"approved": approve, "note": note})
            return recipients

    def create_report(self, reporter_id: str, payload: "ReportIn") -> str:
        if not payload.bid_id:
            raise HTTPException(status_code=400, detail="Reports must be created from a specific bid")
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT b.id, b.dealer_id, br.id AS request_id, br.buyer_id, p.name AS product
                FROM bids b
                JOIN bid_requests br ON br.id = b.bid_request_id
                JOIN products p ON p.id = br.product_id
                WHERE b.id = %s AND b.deleted_at IS NULL
                """,
                [payload.bid_id],
            )
            bid_info = cursor.fetchone()
            if not bid_info:
                raise HTTPException(status_code=404, detail="Bid not found")
            if reporter_id == bid_info["buyer_id"]:
                reported_user_id = bid_info["dealer_id"]
            elif reporter_id == bid_info["dealer_id"]:
                reported_user_id = bid_info["buyer_id"]
            else:
                raise HTTPException(status_code=403, detail="Only the bid buyer or dealer can report this bid")

            # Check if a report already exists for this bid
            # Serialize the two participants so simultaneous reports cannot
            # create duplicate threads or overwrite a counter-dispute.
            cursor.execute("SELECT id FROM bid_requests WHERE id=%s FOR UPDATE", [bid_info['request_id']])
            cursor.execute("SELECT id, description FROM reports WHERE bid_id = %s AND deleted_at IS NULL LIMIT 1", [payload.bid_id])
            existing_report = cursor.fetchone()
            if existing_report:
                report_id = existing_report["id"]
                new_desc = f"{existing_report['description'] or ''}\n\n[Counter-dispute by {reporter_id}]: {payload.reason} - {payload.description}"
                cursor.execute(
                    """
                    UPDATE reports
                    SET status='open', description=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    [new_desc, report_id]
                )
                create_notification(
                    cursor,
                    reported_user_id,
                    "Counter-dispute Filed",
                    f"The other party filed a counter-dispute for {bid_info['product']}.",
                    "report_filed",
                    target_bid_id=payload.bid_id,
                    target_report_id=report_id,
                )
                cursor.execute(
                    """
                    INSERT INTO report_messages (id, report_id, sender_id, recipient_group, message, created_at)
                    VALUES (%s, %s, %s, 'both', %s, NOW())
                    """,
                    [new_id(), report_id, reporter_id, f"{payload.reason}: {payload.description}".strip(": ")],
                )
                audit(cursor, reporter_id, "report.counter_filed", "reports", report_id, {"reason": payload.reason})
            else:
                report_id = new_id()
                cursor.execute(
                    """
                    INSERT INTO reports (id, reporter_id, reported_user_id, bid_id, reason, description, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'open', NOW(), NOW())
                    """,
                    [report_id, reporter_id, reported_user_id, payload.bid_id, payload.reason, payload.description],
                )
                create_notification(
                    cursor,
                    reported_user_id,
                    "Dispute Filed against you",
                    f"A dispute has been filed regarding the bid for {bid_info['product']}.",
                    "report_filed",
                    target_bid_id=payload.bid_id,
                    target_report_id=report_id,
                )
                cursor.execute(
                    """
                    INSERT INTO report_messages (id, report_id, sender_id, recipient_group, message, created_at)
                    VALUES (%s, %s, %s, 'both', %s, NOW())
                    """,
                    [new_id(), report_id, reporter_id, f"{payload.reason}: {payload.description}".strip(": ")],
                )
                audit(cursor, reporter_id, "report.created", "reports", report_id, {"reason": payload.reason})

            # Always notify admins
            for admin in admin_user_ids(cursor):
                create_notification(
                    cursor,
                    admin,
                    "New bid report",
                    f"A report was filed/updated for {bid_info['product']}.",
                    "report_created",
                    target_bid_id=payload.bid_id,
                    target_report_id=report_id,
                )
        return report_id

    def update_report(self, actor_id: str, report_id: str, status: str, note: str = "") -> list[str]:
        allowed = {"open", "investigating", "resolved", "rejected", "escalated", "closed"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail="Invalid report status")
        with db() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE reports SET status=%s, internal_notes=CONCAT(COALESCE(internal_notes,''), %s), updated_at=NOW() WHERE id=%s",
                [status, f"\n{now_utc().isoformat()} {note}" if note else "", report_id],
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Report not found")
            cursor.execute("SELECT reporter_id, reported_user_id, bid_id FROM reports WHERE id=%s", [report_id])
            report = cursor.fetchone()
            recipients = []
            if report:
                recipients = [report["reporter_id"], report["reported_user_id"]]
                for recipient in recipients:
                    create_notification(
                        cursor,
                        recipient,
                        "Report status updated",
                        f"Your bid report is now {status}.",
                        "report_updated",
                        target_bid_id=report["bid_id"],
                        target_report_id=report_id,
                    )
            audit(cursor, actor_id, "report.status_changed", "reports", report_id, {"status": status, "note": note})
            return recipients


class SettingsRepository:
    defaults = {
        "commission": {
            "global_percent": 5.0,
            "category_overrides": {"Electronics": 6.0, "Healthcare": 4.5, "Furniture": 5.0},
            "dealer_overrides": {}
        },
        "bid_rules": {
            "min_time_hours": 1 / 60,
            "max_time_hours": 72.0,
            "expiry_hours": 24.0,
            "auto_cancel": True,
            "max_dealers": 10,
            "min_bidding_increment": 0.0
        },
        "location_rules": {
            "default_radius": 15.0,
            "max_radius_km": 5000.0,
            "cities": ["Mumbai", "Pune", "Delhi", "Bangalore", "Hyderabad"],
            "states": ["Maharashtra", "Delhi", "Karnataka", "Telangana"],
            "countries": ["India"],
            "pincode_matching": True
        },
        "dealer_rules": {
            "verification_required": True,
            "min_rating_threshold": 0.0,
            "max_categories": 5,
            "max_branches": 3,
            "ban_rules": "Banned on 3 consecutive reports",
            "flag_rules": "Flagged on any report under investigation"
        },
        "notification_rules": {
            "enable": True,
            "timing_minutes": 5,
            "reminder_time_hours": 2
        },
        "categories": ["Electronics", "Healthcare", "Furniture", "Office", "Medical"]
    }

    @classmethod
    def read_setting(cls, cursor, key: str) -> dict[str, Any]:
        cursor.execute("SELECT setting_value FROM platform_settings WHERE setting_key=%s AND status='active'", [key])
        row = cursor.fetchone()
        value = (row or {}).get("setting_value") or {}
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = {}
        defaults = cls.defaults.get(key, {})
        result = {**defaults, **value} if isinstance(defaults, dict) and isinstance(value, dict) else {}
        if key == "bid_rules" and isinstance(value, dict) and "bid_expiry_hours" in value:
            result["expiry_hours"] = value["bid_expiry_hours"]
        if key == "commission" and isinstance(value, dict) and "global_percent" not in value and "percentage" in value:
            result["global_percent"] = value["percentage"]
        # Earlier clients could save unvalidated strings or invalid durations.
        numeric_ranges = {
            "bid_rules": {"min_time_hours": (1 / 60, 72), "max_time_hours": (1 / 60, 72), "expiry_hours": (1 / 60, 72), "max_dealers": (0, 10000), "min_bidding_increment": (0, 9999999999.99)},
            "location_rules": {"max_radius_km": (0, 5000)},
            "dealer_rules": {"min_rating_threshold": (0, 5)},
        }
        for field, (minimum, maximum) in numeric_ranges.get(key, {}).items():
            try:
                number = float(result[field])
                if not math.isfinite(number) or not minimum <= number <= maximum or (field == "max_dealers" and not number.is_integer()):
                    raise ValueError("Invalid rule")
                result[field] = int(number) if field == "max_dealers" else number
            except (TypeError, ValueError):
                result[field] = defaults[field]
        if key == "bid_rules":
            if result["min_time_hours"] > result["max_time_hours"]:
                result["min_time_hours"], result["max_time_hours"] = defaults["min_time_hours"], defaults["max_time_hours"]
            result["expiry_hours"] = min(result["max_time_hours"], max(result["min_time_hours"], result["expiry_hours"]))
        if key == "dealer_rules" and not isinstance(result["verification_required"], bool):
            result["verification_required"] = defaults["verification_required"]
        return result

    def list_settings(self) -> dict[str, Any]:
        with db() as conn, conn.cursor() as cursor:
            settings = {key: self.read_setting(cursor, key) for key in self.defaults if key != "categories"}
            cursor.execute("SELECT name FROM categories WHERE parent_id IS NULL AND status='active' AND deleted_at IS NULL ORDER BY name")
            settings["categories"] = [row["name"] for row in cursor.fetchall()]
            return settings

    def save_setting(self, actor_id: str, key: str, value: dict[str, Any]) -> None:
        if key not in self.defaults:
            raise HTTPException(status_code=400, detail="Unknown setting")
        if key == "categories":
            raise HTTPException(status_code=400, detail="Use the category endpoints to edit the product taxonomy")
        with db() as conn, conn.cursor() as cursor:
            # Forms edit a subset of fields; preserve the other configured rules.
            merged = {**self.read_setting(cursor, key), **value}
            if key == "bid_rules" and "bid_expiry_hours" in value:
                merged["expiry_hours"] = merged.pop("bid_expiry_hours")
            merged.pop("bid_expiry_hours", None)
            if key == "commission" and "percentage" in value and "global_percent" not in value:
                merged["global_percent"] = value["percentage"]
            if key == "commission":
                merged.pop("percentage", None)
            ranges = {
                "bid_rules": {"min_time_hours": (1 / 60, 72), "max_time_hours": (1 / 60, 72), "expiry_hours": (1 / 60, 72), "max_dealers": (0, 10000), "min_bidding_increment": (0, 9999999999.99)},
                "location_rules": {"default_radius": (0, 5000), "max_radius_km": (0, 5000)},
                "dealer_rules": {"min_rating_threshold": (0, 5)},
                "commission": {"global_percent": (0, 100)},
            }
            try:
                for field, (minimum, maximum) in ranges.get(key, {}).items():
                    number = float(merged[field])
                    if not math.isfinite(number) or not minimum <= number <= maximum:
                        raise ValueError(f"{field} must be between {minimum:g} and {maximum:g}")
                    if field == "max_dealers" and not number.is_integer():
                        raise ValueError("max_dealers must be a whole number")
                    merged[field] = int(number) if field == "max_dealers" else number
                if key == "bid_rules" and not merged["min_time_hours"] <= merged["expiry_hours"] <= merged["max_time_hours"]:
                    raise ValueError("Default expiry must be within the minimum and maximum duration")
                if key == "dealer_rules" and not isinstance(merged["verification_required"], bool):
                    raise ValueError("verification_required must be true or false")
                if key == "commission":
                    for field in ("category_overrides", "dealer_overrides"):
                        overrides = merged[field]
                        if not isinstance(overrides, dict):
                            raise ValueError(f"{field} must be a mapping")
                        for override, rate in overrides.items():
                            number = float(rate)
                            if not math.isfinite(number) or not 0 <= number <= 100:
                                raise ValueError("Commission rates must be between 0 and 100")
                            overrides[override] = number
            except (TypeError, ValueError, KeyError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cursor.execute(
                """
                INSERT INTO platform_settings (id, setting_key, setting_value, status, created_at, updated_at)
                VALUES (%s, %s, %s, 'active', NOW(), NOW())
                ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value), status='active', updated_at=NOW()
                """,
                [new_id(), key, json.dumps(merged, allow_nan=False)],
            )
            audit(cursor, actor_id, "setting.updated", "platform_settings", None, {"key": key})


class AuthService:
    def __init__(self, repo: AuthRepository):
        self.repo = repo

    def login(self, username: str, password: str) -> dict[str, Any]:
        user = self.repo.find_user_by_email(username)
        if not user or not verify_password(password, user["password_hash"]):
            if user:
                self.repo.write_login(user["id"], False, "bad_password")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if account_status_blocks_access(user["status"]):
            self.repo.write_login(user["id"], False, user["status"])
            raise HTTPException(status_code=403, detail="Account is blocked")
        access = sign_token({"sub": user["id"], "role": user["role"], "email": user["email"]}, 24 * 60)
        refresh = secrets.token_urlsafe(48)
        self.repo.store_refresh_token(
            user["id"],
            hashlib.sha256(refresh.encode()).hexdigest(),
            now_utc() + timedelta(days=30),
        )
        self.repo.write_login(user["id"], True)
        subscribed = False
        if user["role"] == "dealer":
            with db() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT subscribed FROM dealer_profiles WHERE user_id=%s AND deleted_at IS NULL", [user["id"]])
                profile = cursor.fetchone()
                subscribed = bool(profile and profile["subscribed"])
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["full_name"],
            "role": user["role"],
            "status": user["status"],
            "subscribed": subscribed,
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }


def audit(cursor, actor_id: str, action: str, entity: str, entity_id: str, metadata: dict[str, Any]) -> None:
    cursor.execute(
        """
        INSERT INTO audit_logs (id, actor_id, action, entity_type, entity_id, metadata_json, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """,
        [new_id(), actor_id, action, entity, entity_id, json.dumps(metadata, cls=JsonEncoder)],
    )


def seed_database() -> None:
    if not ADMIN_PASSWORD:
        raise RuntimeError("Configure TURACOZ_ADMIN_PASSWORD in the private .env file before seeding admin credentials")
    with db() as conn, conn.cursor() as cursor:
        for name in ["admin", "buyer", "dealer"]:
            cursor.execute(
                """
                INSERT INTO roles (id, name, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE updated_at=updated_at
                """,
                [new_id(), name],
            )
        cursor.execute("SELECT id FROM roles WHERE name='admin'")
        admin_role = cursor.fetchone()
        if admin_role:
            cursor.execute(
                """
                INSERT INTO users (id, role_id, email, password_hash, full_name, phone, status, created_at, updated_at, deleted_at)
                VALUES (%s, %s, 'admin@turacoz', %s, 'Turacoz Bid Tool Admin', '', 'active', NOW(), NOW(), NULL)
                ON DUPLICATE KEY UPDATE email=email
                """,
                [new_id(), admin_role["id"], hash_password(ADMIN_PASSWORD)],
            )


class LoginIn(BaseModel):
    username: str = Field(max_length=190)
    password: str = Field(max_length=1024)


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    username: str = Field(min_length=2, max_length=190)
    password: str = Field(min_length=6, max_length=1024)
    role: str

    @model_validator(mode="after")
    def validate_identity(self):
        self.name, self.username = self.name.strip(), self.username.strip()
        if len(self.name) < 2 or len(self.username) < 2:
            raise ValueError("Name and username must contain at least two non-space characters")
        return self


class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    category: str = Field(min_length=2, max_length=120)
    subcategory: str | None = Field(default=None, max_length=120)
    brand: str = Field(min_length=1, max_length=190)
    model: str = Field(default="", max_length=190)
    price_min: float = Field(default=0, ge=0, le=9999999999.99)
    price_max: float = Field(default=0, ge=0, le=9999999999.99)
    location: str = Field(default="Mumbai", max_length=120)
    specifications: dict[str, str] = Field(default_factory=dict)
    status: Literal["active", "inactive", "archived"] | None = None

    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_price_range(self):
        if self.price_max < self.price_min:
            raise ValueError("price_max must be greater than or equal to price_min")
        return self


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    parent_id: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class StatusIn(BaseModel):
    status: str
    reason: str = ""


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=100000)


class StartBidIn(BaseModel):
    product_id: str
    location_id: str | None = None
    radius_km: float = Field(default=0, ge=0, le=5000)
    quantity: int = Field(default=1, ge=1, le=100000)
    skip_flagged_dealers: bool = True
    expiry_minutes: int | None = Field(
        default=None,
        ge=1,
        le=4320,
        validation_alias=AliasChoices("expiry_minutes", "expiry_hours"),
        description="Request lifetime in minutes (legacy clients may send this as expiry_hours).",
    )
    notes: str = ""
    fields: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_fields(self):
        seen = set()
        if len(self.fields) > 50:
            raise ValueError("A request can include at most 50 custom fields")
        for key, value in self.fields.items():
            normalized = key.strip().casefold()
            if not normalized or len(key) > 120 or normalized in seen:
                raise ValueError("Request field names must be unique, nonempty, and at most 120 characters")
            if len(value.encode("utf-8")) > 65535:
                raise ValueError("Request field value is too long")
            seen.add(normalized)
        if len(self.notes.encode("utf-8")) > 65535:
            raise ValueError("Request notes are too long")
        return self


class BuyerLocationIn(BaseModel):
    label: str = Field(default="Saved location", min_length=1, max_length=120)
    address: str = Field(default="", max_length=255)
    country: str = Field(default="India", max_length=80)
    state: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    area: str = Field(default="", max_length=120)
    pincode: str = Field(default="", max_length=20)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    is_default: bool = False

    model_config = ConfigDict(allow_inf_nan=False)


class BidIn(BaseModel):
    bid_request_id: str
    amount: Decimal = Field(gt=0, le=Decimal("9999999999.99"), max_digits=12, decimal_places=2, description="Final total for the full request quantity, after discount")
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("9999999999.99"), max_digits=12, decimal_places=2, description="Savings already included in amount; never subtract this again")
    warranty_text: str = Field(default="", max_length=255)
    delivery_time: str = Field(default="", max_length=120)
    installation_included: bool = False
    notes: str = Field(default="", max_length=65000)
    free_gifts: str = Field(default="", max_length=65000)
    extra_services: str = Field(default="", max_length=65000)

    model_config = ConfigDict(allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_text_sizes(self):
        if any(len(getattr(self, field).encode("utf-8")) > 65535 for field in ("notes", "free_gifts", "extra_services")):
            raise ValueError("Offer text is too long")
        return self

class ReportIn(BaseModel):
    reported_user_id: str | None = None
    bid_id: str | None = None
    reason: str
    description: str = ""


class ReportUpdateIn(BaseModel):
    status: str
    note: str = ""


class ReportClosureRequestIn(BaseModel):
    reason: str = Field(min_length=3)


class ReportMessageIn(BaseModel):
    recipient_group: str
    message: str



class SettingIn(BaseModel):
    value: dict[str, Any]


class ProfileUpdateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(default="", max_length=32)
    address: str = Field(default="", max_length=255)
    country: str = Field(default="", max_length=80)
    state: str = Field(default="", max_length=100)
    city: str = Field(default="", max_length=100)
    area: str = Field(default="", max_length=120)
    pincode: str = Field(default="", max_length=20)
    preferred_radius: float = Field(default=15.0, gt=0, le=5000)
    business_name: str = Field(default="", max_length=190)
    gst_number: str = Field(default="", max_length=32)
    service_radius_km: float = Field(default=25.0, gt=0, le=5000)
    description: str = ""
    brands: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    delivery_method: Literal['radius', 'city', 'cities', 'state', 'states', 'district', 'districts'] = "radius"
    service_states: list[str] = Field(default_factory=list)
    service_cities: list[str] = Field(default_factory=list)
    service_districts: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)

    model_config = ConfigDict(allow_inf_nan=False)


auth_service = AuthService(AuthRepository())
catalog_repo = CatalogRepository()
bid_repo = BidRepository()
dealer_repo = DealerRepository()
notification_repo = NotificationRepository()
dashboard_repo = DashboardRepository()
admin_repo = AdminRepository()
cart_repo = CartRepository()
dealer_ops = DealerOpsRepository()
report_repo = ReportRepository()


def normalize_report_recipient_group(role: str, requested_group: str) -> str:
    group = (requested_group or "").lower().strip()
    if group in {"public", "everyone"}:
        group = "both"
    if role == "admin":
        return group if group in {"buyer", "dealer", "both"} else "both"
    return "both" if group == "both" else "admin"


def report_message_visible_to(row: dict[str, Any], user: dict[str, Any]) -> bool:
    if user["role"] == "admin" or row["sender_id"] == user["sub"]:
        return True
    group = (row.get("recipient_group") or "").lower()
    if group == "both":
        return True
    return group == user["role"]
settings_repo = SettingsRepository()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    if not DB_PASSWORD or not JWT_SECRET or not ADMIN_PASSWORD:
        raise RuntimeError("Configure TURACOZ_DB_PASSWORD, TURACOZ_JWT_SECRET and TURACOZ_ADMIN_PASSWORD in the private .env file before starting the backend")
    install_token_filters()
    check_database_storage()
    execute_sql_file()
    ensure_runtime_schema()
    seed_database()
    if os.getenv("TURACOZ_IMPORT_PRODUCTS_ON_STARTUP", "true").lower() in {"1", "true", "yes", "on"}:
        import_result = import_bundle_if_needed(ROOT.parent / "products")
        logger.info("Product catalog startup import: %s", import_result)
    check_database_storage()
    schedule_existing_bid_expiries()
    if WEB_BUILD.exists():
        app_instance.mount("/assets", StaticFiles(directory=WEB_BUILD / "assets"), name="assets")
    try:
        yield
    finally:
        for task in list(bid_expiry_tasks.values()):
            if not task.done():
                task.cancel()
        connection_cache.close()


app = FastAPI(title="Turacoz Bid Tool API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(DatabaseHealthError)
async def database_health_error_handler(request, exc: DatabaseHealthError):
    logger.error("Database readiness failed: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "Database storage is unavailable. Run backend/scripts/check_database.py and restore the affected table."})


@app.exception_handler(pymysql.MySQLError)
async def database_error_handler(request, exc: pymysql.MySQLError):
    code = exc.args[0] if exc.args else None
    if code == 1062:
        return JSONResponse(status_code=409, content={"detail": "This record already exists. Refresh and try again."})
    logger.error("Database request failed (error %s): %s", code, exc)
    if code in {1016, 1030, 1034, 1044, 1045, 1049, 1146, 1812, 1932, 2002, 2003, 2006, 2013}:
        return JSONResponse(status_code=503, content={"detail": "Database is unavailable. Check the database service and run backend/scripts/check_database.py."})
    return JSONResponse(status_code=500, content={"detail": "Database operation failed. Check the backend log."})


cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "TURACOZ_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5000,http://127.0.0.1:5000,http://localhost:5180,http://127.0.0.1:5180",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket | None = None):
        connections = self.active_connections.get(user_id)
        if connections is None:
            return
        if websocket is None:
            self.active_connections.pop(user_id, None)
            return
        connections.discard(websocket)
        if not connections:
            self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: str):
        for connection in list(self.active_connections.get(user_id, set())):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(user_id, connection)

    async def broadcast(self, message: dict):
        for user_id in list(self.active_connections):
            await self.send_personal_message(message, user_id)


manager = ConnectionManager()

_bid_publication_lock = asyncio.Lock()


def request_snapshot(request_id: str, recipient: dict) -> dict:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("""SELECT br.id,br.product_id,br.quantity,br.status,br.winning_bid_id,
            UNIX_TIMESTAMP(br.expires_at) AS expires_at_epoch,p.name AS product,
            l.area AS buyer_area,l.city AS buyer_city,l.state AS buyer_state
            FROM bid_requests br JOIN products p ON p.id=br.product_id
            JOIN locations l ON l.id=br.location_id WHERE br.id=%s AND br.deleted_at IS NULL""", [request_id])
        request = cursor.fetchone()
    if not request:
        return {}
    request["expires_at"] = datetime.fromtimestamp(float(request.pop("expires_at_epoch")), timezone.utc).isoformat()
    bids = bid_repo.list_bids(recipient["id"], recipient["role"], request_id)
    request["offers_count"] = len([bid for bid in bids if bid["status"] != "withdrawn"])
    incoming = None
    if recipient["role"] == "dealer" and request["status"] == "active":
        incoming = next((row for row in dealer_ops.incoming_requests(recipient["id"]) if row["id"] == request_id), None)
    return {"request_id": request_id, "request": request, "bids": bids, "dealer_request": incoming}


async def publish_bid_snapshot(request_id: str):
    """Push committed, personalized offers to participants without an HTTP refresh."""
    async with _bid_publication_lock:
        with db() as conn, conn.cursor() as cursor:
            cursor.execute("""SELECT DISTINCT u.id,r.name AS role FROM users u JOIN roles r ON r.id=u.role_id
                WHERE u.deleted_at IS NULL AND u.status IN ('active','verified','flagged','pending') AND (
                  u.id IN (SELECT buyer_id FROM bid_requests WHERE id=%s)
                  OR u.id IN (SELECT dealer_id FROM bid_request_dealers WHERE bid_request_id=%s)
                  OR u.id IN (SELECT dealer_id FROM bids WHERE bid_request_id=%s)
                  OR r.name='admin')""", [request_id, request_id, request_id])
            recipients = [row for row in cursor.fetchall() if row["id"] in manager.active_connections]
        version = str(time.time_ns())
        async def deliver(recipient):
            try:
                snapshot = await asyncio.to_thread(request_snapshot, request_id, recipient)
                if snapshot:
                    await manager.send_personal_message(jsonable_encoder({"type": "bid_snapshot", "version": version, **snapshot}), recipient["id"])
            except Exception:
                logger.exception("Unable to publish bid snapshot for request %s", request_id)
                await manager.send_personal_message({"type": "bid_updated", "request_id": request_id, "refresh_required": True}, recipient["id"])
        await asyncio.gather(*(deliver(recipient) for recipient in recipients))


async def publish_user_requests(user_id: str):
    await manager.send_personal_message({"type": "profile_updated"}, user_id)
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT br.id FROM bid_requests br JOIN bid_request_dealers brd ON brd.bid_request_id=br.id WHERE brd.dealer_id=%s AND br.status='active' AND br.deleted_at IS NULL", [user_id])
        request_ids = [row["id"] for row in cursor.fetchall()]
    for request_id in request_ids:
        await publish_bid_snapshot(request_id)


class BidMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def bid_conversation_participants(cursor, bid_id: str, user: dict, writing=False):
    cursor.execute("""SELECT br.buyer_id,b.dealer_id FROM bids b JOIN bid_requests br ON br.id=b.bid_request_id
        WHERE b.id=%s AND br.winning_bid_id=b.id AND br.status='awarded'
          AND b.status IN ('won','completed') AND b.deleted_at IS NULL AND br.deleted_at IS NULL""", [bid_id])
    participants = cursor.fetchone()
    if not participants:
        raise HTTPException(status_code=409, detail="A private conversation opens when the buyer selects the winning bid")
    if user["sub"] not in participants.values() and (writing or user["role"] != "admin"):
        raise HTTPException(status_code=403, detail="Only the buyer and winning dealer can use this conversation")
    return participants


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    token = websocket.query_params.get("token", "")
    try:
        token_user = authenticate_token(token)
        if token_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="WebSocket user mismatch")
    except HTTPException:
        await websocket.close(code=4401, reason="Authentication required")
        return
    except pymysql.MySQLError:
        await websocket.close(code=1013, reason="Database temporarily unavailable")
        return
    await manager.connect(user_id, websocket)
    try:
        while True:
            try:
                text_message = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if text_message == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
            try:
                authenticate_token(token)
            except HTTPException:
                await websocket.close(code=4401, reason="Session expired or account blocked")
                break
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        manager.disconnect(user_id, websocket)
    finally:
        manager.disconnect(user_id, websocket)


def authenticate_token(token: str) -> dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = parse_token(token)
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT u.status, u.email, r.name AS role FROM users u JOIN roles r ON r.id=u.role_id WHERE u.id=%s AND u.deleted_at IS NULL", [payload["sub"]])
        user_row = cursor.fetchone()
        if not user_row or account_status_blocks_access(user_row["status"]):
            raise HTTPException(status_code=403, detail="Account is inactive or blocked")
    return {**payload, **user_row, "raw_token": token}


def current_user(authorization: str = Header(default="")) -> dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authenticate_token(authorization.removeprefix("Bearer ").strip())


def require_role(*roles: str):
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return dependency


@app.get("/bids/{bid_id}/messages")
def bid_messages(bid_id: str, user: dict = Depends(current_user)):
    with db() as conn, conn.cursor() as cursor:
        bid_conversation_participants(cursor, bid_id, user)
        cursor.execute("""SELECT m.id,m.bid_id,m.sender_id,m.message,m.created_at,u.full_name AS sender_name,r.name AS sender_role
            FROM bid_messages m JOIN users u ON u.id=m.sender_id JOIN roles r ON r.id=u.role_id
            WHERE m.bid_id=%s ORDER BY m.created_at,m.id""", [bid_id])
        return cursor.fetchall()


@app.post("/bids/{bid_id}/messages")
async def send_bid_message(bid_id: str, payload: BidMessageIn, user: dict = Depends(current_user)):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Enter a message")
    with db() as conn, conn.cursor() as cursor:
        participants = bid_conversation_participants(cursor, bid_id, user, writing=True)
        message_id = new_id()
        cursor.execute("INSERT INTO bid_messages(id,bid_id,sender_id,message,created_at) VALUES (%s,%s,%s,%s,NOW(6))", [message_id,bid_id,user["sub"],message])
        cursor.execute("""SELECT m.id,m.bid_id,m.sender_id,m.message,m.created_at,u.full_name AS sender_name,r.name AS sender_role
            FROM bid_messages m JOIN users u ON u.id=m.sender_id JOIN roles r ON r.id=u.role_id WHERE m.id=%s""", [message_id])
        sent = cursor.fetchone()
    await asyncio.gather(*(manager.send_personal_message(jsonable_encoder({"type": "bid_message", "bid_id": bid_id, "message": sent}), identifier) for identifier in set(participants.values())))
    return sent


@app.get("/health")
def health() -> dict[str, str]:
    check_database_storage()
    return {"status": "ok", "database": DB_NAME}


@app.get("/locations/search")
def search_locations(q: str = Query(min_length=3, max_length=240), user: dict[str, Any] = Depends(current_user)):
    return geocoding.search(q.strip())


@app.get("/locations/reverse")
def reverse_location(latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180), user: dict[str, Any] = Depends(current_user)):
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise HTTPException(status_code=400, detail="Choose a valid map pin")
    return geocoding.reverse(latitude, longitude)


@app.post("/auth/login")
def login(payload: LoginIn) -> dict[str, Any]:
    return auth_service.login(payload.username.lower().strip(), payload.password)


@app.post("/auth/register")
def register(payload: RegisterIn) -> dict[str, Any]:
    username = payload.username.lower().strip()
    role_name = payload.role.lower().strip()
    if role_name not in ["buyer", "dealer"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'buyer' or 'dealer'")

    with db() as conn, conn.cursor() as cursor:
        # Check if username exists
        cursor.execute("SELECT id FROM users WHERE email = %s", [username])
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")

        # Get role ID
        cursor.execute("SELECT id FROM roles WHERE name = %s", [role_name])
        role_row = cursor.fetchone()
        if not role_row:
            raise HTTPException(status_code=500, detail="System role configuration error")
        role_id = role_row["id"]

        # Insert user
        user_id = new_id()
        status = "active" if role_name == "buyer" else "pending"
        cursor.execute(
            """
            INSERT INTO users (id, role_id, email, password_hash, full_name, phone, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, '', %s, NOW(), NOW())
            """,
            [user_id, role_id, username, hash_password(payload.password), payload.name, status]
        )

        # Create empty profile
        if role_name == "buyer":
            cursor.execute(
                """
                INSERT INTO buyer_profiles (id, user_id, phone, address, country, state, city, area, pincode, preferred_radius, default_location_id, dynamic_fields, created_at, updated_at)
                VALUES (%s, %s, '', '', '', '', '', '', '', 15.0, NULL, NULL, NOW(), NOW())
                """,
                [new_id(), user_id]
            )
        elif role_name == "dealer":
            cursor.execute(
                """
                INSERT INTO dealer_profiles (id, user_id, business_name, owner_name, business_address, gst_number, rating, verification_status, warning_message, dynamic_fields, created_at, updated_at)
                VALUES (%s, %s, %s, %s, '', '', 0.0, 'pending', NULL, NULL, NOW(), NOW())
                """,
                [new_id(), user_id, payload.name, payload.name]
            )

        audit(cursor, user_id, "auth.registered", "users", user_id, {"role": role_name, "username": username})

    return {"status": "registered", "user_id": user_id}


@app.get("/profile")
def get_profile(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id, email, full_name, phone, status FROM users WHERE id = %s AND deleted_at IS NULL", [user["sub"]])
        u = cursor.fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")

        profile_data = {
            "id": u["id"],
            "email": u["email"],
            "full_name": u["full_name"],
            "phone": u["phone"] or "",
            "role": user["role"],
            "status": u["status"]
        }

        if user["role"] == "buyer":
            cursor.execute(
                """
                SELECT bp.address, bp.country, bp.state, bp.city, bp.area, bp.pincode, bp.preferred_radius,
                       bp.default_location_id, l.latitude, l.longitude
                FROM buyer_profiles bp
                LEFT JOIN locations l ON l.id=bp.default_location_id
                WHERE bp.user_id = %s
                """,
                [user["sub"]]
            )
            bp_row = cursor.fetchone()
            if bp_row:
                profile_data.update({
                    "address": bp_row["address"] or "",
                    "country": bp_row["country"] or "",
                    "state": bp_row["state"] or "",
                    "city": bp_row["city"] or "",
                    "area": bp_row["area"] or "",
                    "pincode": bp_row["pincode"] or "",
                    "preferred_radius": float(bp_row["preferred_radius"]),
                    "default_location_id": bp_row["default_location_id"] or "",
                    "latitude": float(bp_row["latitude"] or 0),
                    "longitude": float(bp_row["longitude"] or 0)
                })
            else:
                profile_data.update({
                    "address": "", "country": "", "state": "", "city": "", "area": "", "pincode": "", "preferred_radius": 15.0,
                    "default_location_id": "", "latitude": 0.0, "longitude": 0.0
                })
            cursor.execute(
                """
                SELECT bl.id, bl.location_id, bl.label, bl.is_default,
                       l.address_line AS address, l.country, l.state, l.city, l.area, l.pincode,
                       l.latitude, l.longitude
                FROM buyer_locations bl
                JOIN locations l ON l.id=bl.location_id
                WHERE bl.buyer_id=%s AND bl.deleted_at IS NULL AND l.deleted_at IS NULL
                ORDER BY bl.is_default DESC, bl.updated_at DESC
                """,
                [user["sub"]],
            )
            profile_data["locations"] = cursor.fetchall()

        elif user["role"] == "dealer":
            cursor.execute(
                """
                SELECT dp.business_name, dp.business_address, dp.gst_number, dp.rating,
                       dp.subscribed, dp.subscribed_at,
                       dp.dynamic_fields, dp.service_preferences,
                       dsl.radius_km, l.address_line, l.country, l.state, l.city, l.area, l.pincode, l.latitude, l.longitude
                FROM dealer_profiles dp
                LEFT JOIN (
                    SELECT dealer_id, location_id, radius_km
                    FROM dealer_service_locations
                    WHERE (dealer_id, created_at) IN (
                        SELECT dealer_id, MAX(created_at)
                        FROM dealer_service_locations
                        GROUP BY dealer_id
                    )
                ) dsl ON dsl.dealer_id = dp.user_id
                LEFT JOIN locations l ON l.id = dsl.location_id
                WHERE dp.user_id = %s
                """,
                [user["sub"]]
            )
            dp_row = cursor.fetchone()
            if dp_row:
                dynamic_fields = {}
                if dp_row["dynamic_fields"]:
                    try:
                        dynamic_fields = json.loads(dp_row["dynamic_fields"]) if isinstance(dp_row["dynamic_fields"], str) else dp_row["dynamic_fields"]
                    except Exception:
                        dynamic_fields = {}
                service_preferences = {}
                if dp_row.get("service_preferences"):
                    try:
                        service_preferences = json.loads(dp_row["service_preferences"]) if isinstance(dp_row["service_preferences"], str) else dp_row["service_preferences"]
                    except Exception:
                        service_preferences = {}
                profile_data.update({
                    "business_name": dp_row["business_name"] or "",
                    "address": dp_row["address_line"] or dp_row["business_address"] or "",
                    "gst_number": dp_row["gst_number"] or "",
                    "rating": float(dp_row["rating"]),
                    "subscribed": bool(dp_row["subscribed"]),
                    "subscribed_at": dp_row["subscribed_at"].isoformat() if dp_row["subscribed_at"] else None,
                    "service_radius_km": float(dp_row["radius_km"] or service_preferences.get("radius_km") or 25.0),
                    "max_service_radius_km": float(SettingsRepository.read_setting(cursor, "location_rules")["max_radius_km"]),
                    "country": dp_row["country"] or service_preferences.get("country") or "India",
                    "state": dp_row["state"] or (service_preferences.get("location") or {}).get("state", ""),
                    "city": dp_row["city"] or (service_preferences.get("location") or {}).get("city", ""),
                    "area": dp_row["area"] or (service_preferences.get("location") or {}).get("area", ""),
                    "pincode": dp_row["pincode"] or (service_preferences.get("location") or {}).get("pincode", ""),
                    "latitude": float(dp_row["latitude"] or 0),
                    "longitude": float(dp_row["longitude"] or 0),
                    "description": dynamic_fields.get("description", ""),
                    "brands": dynamic_fields.get("brands", []),
                    "branches": dynamic_fields.get("branches", []),
                    "delivery_method": {
                        "states": "state",
                        "districts": "district",
                        "cities": "city",
                    }.get(service_preferences.get("method", "radius"), service_preferences.get("method", "radius")),
                    "service_states": service_preferences.get("states", []),
                    "service_cities": service_preferences.get("cities", dynamic_fields.get("branches", [])),
                    "service_districts": service_preferences.get("districts", [])
                })
            else:
                profile_data.update({
                    "business_name": "", "address": "", "gst_number": "", "rating": 0.0,
                    "subscribed": False, "subscribed_at": None,
                    "service_radius_km": 25.0,
                    "country": "", "state": "", "city": "", "area": "", "pincode": "", "description": "", "brands": [], "branches": []
                })

            cursor.execute(
                """
                SELECT c.id, c.name FROM dealer_categories dc
                JOIN categories c ON c.id = dc.category_id
                WHERE dc.dealer_id = %s AND c.status='active' AND c.deleted_at IS NULL
                """,
                [user["sub"]]
            )
            selected_categories = cursor.fetchall()
            profile_data["categories"] = [cat["name"] for cat in selected_categories]
            profile_data["category_ids"] = [cat["id"] for cat in selected_categories]

        return profile_data


@app.put("/profile")
def update_profile(payload: ProfileUpdateIn, background_tasks: BackgroundTasks, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    full_name = payload.full_name.strip()
    phone = payload.phone.strip()
    if len(full_name) < 2:
        raise HTTPException(status_code=400, detail="Name must contain at least two non-space characters")

    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", [user["sub"]])
        if user["role"] == "dealer" and payload.delivery_method == "radius":
            maximum_radius = float(SettingsRepository.read_setting(cursor, "location_rules")["max_radius_km"])
            if payload.service_radius_km > maximum_radius:
                raise HTTPException(status_code=400, detail="Dealer service radius exceeds the configured maximum")
            if not payload.city.strip() or not payload.state.strip() or not valid_coordinates({"latitude": payload.latitude, "longitude": payload.longitude}):
                raise HTTPException(status_code=400, detail="Radius coverage needs a shop city, state and confirmed map pin")
        cursor.execute(
            """
            UPDATE users
            SET full_name = %s, phone = %s, updated_at = NOW()
            WHERE id = %s AND deleted_at IS NULL
            """,
            [full_name, phone, user["sub"]]
        )

        location_id = None
        regional_without_pin = user["role"] == "dealer" and payload.delivery_method != "radius" and not valid_coordinates({"latitude": payload.latitude, "longitude": payload.longitude})
        if payload.city.strip() and not regional_without_pin:
            if not payload.state.strip():
                raise HTTPException(status_code=400, detail="State is required for a saved location")
            if not valid_coordinates({"latitude": payload.latitude, "longitude": payload.longitude}):
                raise HTTPException(status_code=400, detail="Search the address, place/confirm the map pin, then save")
            latitude, longitude = coordinates_or_geocode(
                payload.latitude,
                payload.longitude,
                country=payload.country,
                state=payload.state,
                city=payload.city,
                area=payload.area,
                pincode=payload.pincode,
                address=payload.address,
            )
            country = payload.country.strip() or "India"
            state = payload.state.strip()
            city = payload.city.strip()
            area = payload.area.strip()
            pincode = payload.pincode.strip()
            radius = payload.preferred_radius if user["role"] == "buyer" else payload.service_radius_km
            location_payload = BuyerLocationIn(
                label="Dealer service location",
                address=payload.address,
                country=country,
                state=state,
                city=city,
                area=area,
                pincode=pincode,
                latitude=latitude,
                longitude=longitude,
            )
            location_id = upsert_location_from_payload(cursor, location_payload, radius)

        if user["role"] == "buyer":
            cursor.execute(
                """
                INSERT INTO buyer_profiles (id, user_id, phone, address, country, state, city, area, pincode, preferred_radius, default_location_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    phone = VALUES(phone), address = VALUES(address), country = VALUES(country),
                    state = VALUES(state), city = VALUES(city), area = VALUES(area), pincode = VALUES(pincode),
                    preferred_radius = VALUES(preferred_radius), default_location_id = COALESCE(VALUES(default_location_id), default_location_id), updated_at = NOW()
                """,
                [new_id(), user["sub"], phone, payload.address, payload.country, payload.state, payload.city, payload.area, payload.pincode, payload.preferred_radius, location_id]
            )
            if location_id:
                cursor.execute("SELECT id FROM buyer_locations WHERE buyer_id=%s AND deleted_at IS NULL ORDER BY is_default DESC, updated_at DESC LIMIT 1", [user["sub"]])
                saved = cursor.fetchone()
                save_buyer_location(cursor, user["sub"], location_id, payload.address.strip() or "Default location", True, (saved or {}).get("id"))
            else:
                synchronize_buyer_default(cursor, user["sub"])

        elif user["role"] == "dealer":
            dynamic_data = {
                "description": payload.description,
                "brands": payload.brands,
                "branches": payload.branches
            }
            service_cities = (
                payload.service_cities
                if "service_cities" in payload.model_fields_set
                else payload.branches
            )
            service_preferences = {
                "country": payload.country.strip() or "India",
                "method": {
                    "state": "states",
                    "district": "districts",
                    "city": "cities",
                }.get(payload.delivery_method, payload.delivery_method)
                if payload.delivery_method in {"radius", "state", "states", "district", "districts", "city", "cities"}
                else "radius",
                "states": payload.service_states,
                "cities": service_cities,
                "districts": payload.service_districts,
                "radius_km": payload.service_radius_km,
                "location": {"country": payload.country.strip() or "India", "state": payload.state.strip(), "city": payload.city.strip(), "area": payload.area.strip(), "pincode": payload.pincode.strip()},
            }
            coverage_key = {"states": "states", "cities": "cities", "districts": "districts"}.get(service_preferences["method"])
            if coverage_key and not any(str(value).strip() for value in service_preferences[coverage_key]):
                raise HTTPException(status_code=400, detail=f"Add at least one service {coverage_key} entry for this delivery method")
            cursor.execute(
                """
                INSERT INTO dealer_profiles (id, user_id, business_name, owner_name, business_address, gst_number, rating, verification_status, dynamic_fields, service_preferences, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 0.0, 'pending', %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    business_name = VALUES(business_name), owner_name = VALUES(owner_name),
                    business_address = VALUES(business_address), gst_number = VALUES(gst_number),
                    dynamic_fields = VALUES(dynamic_fields), service_preferences = VALUES(service_preferences), updated_at = NOW()
                """,
                [new_id(), user["sub"], payload.business_name or full_name, full_name, payload.address, payload.gst_number, json.dumps(dynamic_data), json.dumps(service_preferences)]
            )

            if location_id:
                # Remove all previous service locations for this dealer — one location only
                cursor.execute("DELETE FROM dealer_service_locations WHERE dealer_id = %s", [user["sub"]])
                cursor.execute(
                    """
                    INSERT INTO dealer_service_locations (dealer_id, location_id, radius_km, created_at)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    [user["sub"], location_id, payload.service_radius_km]
                )
            else:
                cursor.execute("DELETE FROM dealer_service_locations WHERE dealer_id = %s", [user["sub"]])

            cursor.execute("DELETE FROM dealer_categories WHERE dealer_id = %s", [user["sub"]])
            for cat_id in resolve_dealer_category_ids(cursor, payload.categories):
                cursor.execute("INSERT INTO dealer_categories (dealer_id, category_id, created_at) VALUES (%s, %s, NOW())", [user["sub"], cat_id])

        audit(cursor, user["sub"], "profile.updated", "users", user["sub"], {})
        cursor.execute("SELECT status FROM users WHERE id = %s", [user["sub"]])
        u_row = cursor.fetchone()
        user_status = u_row["status"] if u_row else "active"

    background_tasks.add_task(publish_user_requests, user["sub"])
    return {
        "id": user["sub"],
        "email": user["email"],
        "name": full_name,
        "role": user["role"],
        "status": user_status,
        "access_token": user["raw_token"],
    }


def resolve_dealer_category_ids(cursor, selections: list[str]) -> list[str]:
    cursor.execute("SELECT c.id,c.name,c.parent_id FROM categories c LEFT JOIN categories parent ON parent.id=c.parent_id WHERE c.status='active' AND c.deleted_at IS NULL AND (c.parent_id IS NULL OR (parent.status='active' AND parent.deleted_at IS NULL))")
    rows = cursor.fetchall()
    by_id = {row["id"]: row for row in rows}
    parent_ids = {row["id"] for row in rows if row["parent_id"] is None and (row["id"] in selections or row["name"] in selections)}
    resolved = set()
    for selection in dict.fromkeys(selections):
        selection = selection.strip()
        row = by_id.get(selection)
        if not row:
            candidates = [row for row in rows if row["name"].casefold() == selection.casefold()]
            if len(candidates) > 1 and parent_ids:
                candidates = [row for row in candidates if row["id"] in parent_ids or row["parent_id"] in parent_ids]
            if len(candidates) != 1:
                raise HTTPException(status_code=400, detail="Select active categories/items by ID; a category name is missing or ambiguous")
            row = candidates[0]
        resolved.add(row["id"])
        if row["parent_id"]:
            resolved.add(row["parent_id"])
    return sorted(resolved)


def upsert_location_from_payload(cursor, payload: BuyerLocationIn, radius: float = 0) -> str:
    """Reuse an identical location; preserve rows referenced by bidding history."""
    if not valid_coordinates({"latitude": payload.latitude, "longitude": payload.longitude}):
        raise HTTPException(status_code=400, detail="Confirm an exact map pin before saving this location")
    if not payload.state.strip() or not payload.city.strip():
        raise HTTPException(status_code=400, detail="Saved locations need state and city from the confirmed map pin")

    # Reuse the same pin at the database's seven-decimal coordinate precision.
    cursor.execute(
        """
        SELECT id FROM locations
        WHERE ABS(latitude - %s) < 0.0000001 AND ABS(longitude - %s) < 0.0000001
          AND country=%s AND state=%s AND city=%s
          AND COALESCE(area,'')=%s AND COALESCE(address_line,'')=%s AND COALESCE(pincode,'')=%s
          AND deleted_at IS NULL
        LIMIT 1
        """,
        [
            payload.latitude,
            payload.longitude,
            payload.country.strip() or "India",
            payload.state.strip(),
            payload.city.strip(),
            payload.area.strip(), payload.address.strip(), payload.pincode.strip(),
        ],
    )
    row = cursor.fetchone()
    if row:
        return row["id"]

    # No matching coords row — create a brand new one
    # A matching written address may represent a different pin. Create a separate
    # row rather than changing coordinates another buyer or dealer may reference.
    location_id = new_id()
    cursor.execute(
        """
        INSERT INTO locations (id, country, state, city, area, address_line, pincode, latitude, longitude, service_radius_km, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
        """,
        [
            location_id,
            payload.country.strip() or "India",
            payload.state.strip(),
            payload.city.strip(),
            payload.area.strip(),
            payload.address.strip(),
            payload.pincode.strip(),
            payload.latitude,
            payload.longitude,
            max(0, radius),
        ],
    )
    return location_id


def synchronize_buyer_default(cursor, buyer_id: str, saved_id: str | None = None) -> None:
    cursor.execute("SELECT id, location_id FROM buyer_locations WHERE buyer_id=%s AND deleted_at IS NULL ORDER BY is_default DESC, updated_at DESC, id", [buyer_id])
    rows = cursor.fetchall()
    selected = next((row for row in rows if row["id"] == saved_id), rows[0] if rows else None)
    cursor.execute("UPDATE buyer_locations SET is_default=(id=%s) WHERE buyer_id=%s AND deleted_at IS NULL", [(selected or {}).get("id", ""), buyer_id])
    location_id = (selected or {}).get("location_id")
    cursor.execute(
        "INSERT INTO buyer_profiles (id,user_id,default_location_id,created_at,updated_at) VALUES (%s,%s,%s,NOW(),NOW()) ON DUPLICATE KEY UPDATE default_location_id=VALUES(default_location_id),updated_at=NOW()",
        [new_id(), buyer_id, location_id],
    )
    if location_id:
        cursor.execute("UPDATE buyer_profiles bp JOIN locations l ON l.id=bp.default_location_id SET bp.address=l.address_line,bp.country=l.country,bp.state=l.state,bp.city=l.city,bp.area=l.area,bp.pincode=l.pincode WHERE bp.user_id=%s", [buyer_id])
    else:
        cursor.execute("UPDATE buyer_profiles SET address='',country='',state='',city='',area='',pincode='' WHERE user_id=%s", [buyer_id])


def save_buyer_location(cursor, buyer_id: str, location_id: str, label: str, make_default: bool, saved_id: str | None = None) -> str:
    # Caller holds the buyer user row lock, serializing the cap and default updates.
    cursor.execute("SELECT id, location_id, is_default FROM buyer_locations WHERE buyer_id=%s AND deleted_at IS NULL ORDER BY is_default DESC, updated_at DESC", [buyer_id])
    rows = cursor.fetchall()
    previous = next((row for row in rows if row["id"] == saved_id), None)
    if saved_id and not previous:
        raise HTTPException(status_code=404, detail="Saved location not found")
    duplicate = next((row for row in rows if row["location_id"] == location_id), None)
    target_id = (duplicate or previous or {}).get("id")
    if not target_id:
        if len(rows) >= 3:
            raise HTTPException(status_code=400, detail="A buyer can save up to 3 locations")
        target_id = new_id()
        cursor.execute("INSERT INTO buyer_locations (id,buyer_id,location_id,active_location_id,label,is_default,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,FALSE,NOW(),NOW())", [target_id,buyer_id,location_id,location_id,label])
    else:
        cursor.execute("UPDATE buyer_locations SET location_id=%s,active_location_id=%s,label=%s,updated_at=NOW() WHERE id=%s", [location_id,location_id,label,target_id])
    if previous and previous["id"] != target_id:
        cursor.execute("UPDATE buyer_locations SET deleted_at=NOW(),active_location_id=NULL,is_default=FALSE,updated_at=NOW() WHERE id=%s", [previous["id"]])
    preserve_default = bool((previous or {}).get("is_default") or (duplicate or {}).get("is_default"))
    synchronize_buyer_default(cursor, buyer_id, target_id if make_default or preserve_default else None)
    return target_id


@app.get("/buyer/locations")
def buyer_locations(user: dict[str, Any] = Depends(require_role("buyer"))) -> list[dict[str, Any]]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
                SELECT bl.id, bl.location_id, bl.label, bl.is_default,
                   l.address_line AS address, l.country, l.state, l.city, l.area, l.pincode, l.latitude, l.longitude
            FROM buyer_locations bl
            JOIN locations l ON l.id=bl.location_id
            WHERE bl.buyer_id=%s AND bl.deleted_at IS NULL AND l.deleted_at IS NULL
            ORDER BY bl.is_default DESC, bl.updated_at DESC
            """,
            [user["sub"]],
        )
        return cursor.fetchall()


@app.post("/buyer/locations")
def add_buyer_location(payload: BuyerLocationIn, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", [user["sub"]])
        location_id = upsert_location_from_payload(cursor, payload)
        saved_id = save_buyer_location(cursor, user["sub"], location_id, payload.label.strip() or "Saved location", payload.is_default)
        audit(cursor, user["sub"], "buyer_location.saved", "locations", location_id, {"label": payload.label})
        return {"id": saved_id, "location_id": location_id, "status": "saved"}


@app.put("/buyer/locations/{saved_id}")
def update_buyer_location(saved_id: str, payload: BuyerLocationIn, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", [user["sub"]])
        location_id = upsert_location_from_payload(cursor, payload)
        saved_id = save_buyer_location(cursor, user["sub"], location_id, payload.label.strip() or "Saved location", payload.is_default, saved_id)
        audit(cursor, user["sub"], "buyer_location.updated", "locations", location_id, {"label": payload.label})
        return {"id": saved_id, "location_id": location_id, "status": "updated"}


@app.post("/buyer/locations/{saved_id}/default")
def set_default_buyer_location(saved_id: str, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", [user["sub"]])
        cursor.execute("SELECT location_id FROM buyer_locations WHERE id=%s AND buyer_id=%s AND deleted_at IS NULL", [saved_id, user["sub"]])
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Saved location not found")
        synchronize_buyer_default(cursor, user["sub"], saved_id)
        audit(cursor, user["sub"], "buyer_location.default_set", "locations", row["location_id"], {})
        return {"status": "default_set"}


@app.delete("/buyer/locations/{saved_id}")
def delete_buyer_location(saved_id: str, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", [user["sub"]])
        cursor.execute("SELECT location_id, is_default FROM buyer_locations WHERE id=%s AND buyer_id=%s AND deleted_at IS NULL", [saved_id, user["sub"]])
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Saved location not found")
        cursor.execute("UPDATE buyer_locations SET deleted_at=NOW(), active_location_id=NULL, updated_at=NOW(), is_default=FALSE WHERE id=%s", [saved_id])
        synchronize_buyer_default(cursor, user["sub"])
        audit(cursor, user["sub"], "buyer_location.deleted", "locations", row["location_id"], {})
        return {"status": "deleted"}


def validate_category_parent(cursor, category_id: str, parent_id: str | None) -> None:
    if not parent_id:
        return
    if parent_id == category_id:
        raise HTTPException(status_code=400, detail="A category cannot be its own parent")
    cursor.execute("SELECT id FROM categories WHERE id=%s AND parent_id IS NULL AND status='active' AND deleted_at IS NULL", [parent_id])
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="Items must belong to an active top-level category")
    cursor.execute("SELECT id FROM categories WHERE parent_id=%s AND deleted_at IS NULL LIMIT 1", [category_id])
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="A category with items cannot become an item")


@app.get("/categories")
def get_categories() -> list[dict[str, Any]]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id, name, parent_id, status FROM categories WHERE deleted_at IS NULL ORDER BY name")
        rows = cursor.fetchall()

    parent_map = {}
    for r in rows:
        if r["parent_id"] is None:
            r["items"] = []
            parent_map[r["id"]] = r

    for r in rows:
        if r["parent_id"] is not None:
            parent = parent_map.get(r["parent_id"])
            if parent:
                parent["items"].append(r)

    return list(parent_map.values())


@app.post("/admin/categories")
def add_category(payload: CategoryIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cat_id = new_id()
        validate_category_parent(cursor, cat_id, payload.parent_id)
        cursor.execute("SELECT id FROM categories WHERE name=%s AND parent_id <=> %s AND deleted_at IS NULL LIMIT 1", [payload.name, payload.parent_id])
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="This category/item already exists under the selected parent")
        cursor.execute(
            """
            INSERT INTO categories (id, name, parent_id, status, created_at, updated_at)
            VALUES (%s, %s, %s, 'active', NOW(), NOW())
            """,
            [cat_id, payload.name.strip(), payload.parent_id]
        )
        audit(cursor, user["sub"], "category.created", "categories", cat_id, {"name": payload.name, "parent_id": payload.parent_id})
    return {"status": "created", "id": cat_id}


@app.put("/admin/categories/{cat_id}")
def update_category(cat_id: str, payload: CategoryIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT parent_id FROM categories WHERE id=%s AND deleted_at IS NULL FOR UPDATE", [cat_id])
        current = cursor.fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Category not found")
        validate_category_parent(cursor, cat_id, payload.parent_id)
        cursor.execute("SELECT id FROM categories WHERE name=%s AND parent_id <=> %s AND id<>%s AND deleted_at IS NULL LIMIT 1", [payload.name, payload.parent_id, cat_id])
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="This category/item already exists under the selected parent")
        if current["parent_id"] != payload.parent_id:
            cursor.execute("SELECT id FROM products WHERE category_id=%s OR subcategory_id=%s LIMIT 1", [cat_id, cat_id])
            has_products = bool(cursor.fetchone())
            cursor.execute("SELECT dealer_id FROM dealer_categories WHERE category_id=%s LIMIT 1", [cat_id])
            if has_products or cursor.fetchone():
                raise HTTPException(status_code=409, detail="A category used by products or dealers cannot be moved; create a new category")
        cursor.execute(
            """
            UPDATE categories
            SET name = %s, parent_id = %s, updated_at = NOW()
            WHERE id = %s AND deleted_at IS NULL
            """,
            [payload.name.strip(), payload.parent_id, cat_id]
        )
        audit(cursor, user["sub"], "category.updated", "categories", cat_id, {"name": payload.name, "parent_id": payload.parent_id})
    return {"status": "updated"}


@app.delete("/admin/categories/{cat_id}")
def delete_category(cat_id: str, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM categories WHERE (id=%s OR parent_id=%s) AND deleted_at IS NULL FOR UPDATE", [cat_id,cat_id])
        affected = [row['id'] for row in cursor.fetchall()]
        if not affected or cat_id not in affected:
            raise HTTPException(status_code=404, detail="Category not found")
        marks=','.join(['%s']*len(affected))
        cursor.execute(f"SELECT id FROM products WHERE (category_id IN ({marks}) OR subcategory_id IN ({marks})) AND deleted_at IS NULL LIMIT 1",affected+affected)
        products_exist = cursor.fetchone()
        cursor.execute(f"SELECT dc.dealer_id FROM dealer_categories dc JOIN users u ON u.id=dc.dealer_id WHERE dc.category_id IN ({marks}) AND u.deleted_at IS NULL LIMIT 1",affected)
        if products_exist or cursor.fetchone():
            raise HTTPException(status_code=409, detail="This category is used by products or dealer profiles. Reassign them before deleting it")
        cursor.execute(
            "UPDATE categories SET deleted_at = NOW(), updated_at = NOW() WHERE id = %s AND deleted_at IS NULL",
            [cat_id]
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        cursor.execute(
            "UPDATE categories SET deleted_at = NOW(), updated_at = NOW() WHERE parent_id = %s AND deleted_at IS NULL",
            [cat_id]
        )
        audit(cursor, user["sub"], "category.deleted", "categories", cat_id, {})
    return {"status": "deleted"}


@app.get("/admin/products")
def admin_catalog(q: str="", category: str="", brand: str="", status: Literal['','active','inactive','archived']="", minimum: float | None=Query(default=None,ge=0), maximum: float | None=Query(default=None,ge=0), sort: Literal['Newest','Name','Lowest Price','Highest Price']='Newest', limit:int=Query(default=50,ge=1,le=250), offset:int=Query(default=0,ge=0), user:dict=Depends(require_role('admin'))):
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(status_code=400,detail="Minimum price must not exceed maximum price")
    return catalog_repo.admin_catalog(q,category,brand,status,minimum,maximum,sort,limit,offset)


@app.get("/products")
def products(
    q: str = "",
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    category: str = "",
    brand: str = "",
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    return catalog_repo.list_products(
        q,
        limit=limit,
        offset=offset,
        category=category,
        brand=brand,
        include_inactive=user["role"] == "admin",
    )


@app.get("/products/{product_id}")
def product_detail(product_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return catalog_repo.product_detail(product_id, include_inactive=user["role"] == "admin")


@app.post("/products")
def create_product(payload: ProductIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    product_id = catalog_repo.create_product(payload, user["sub"])
    return {"id": product_id, "status": "created"}


@app.put("/products/{product_id}")
def update_product(product_id: str, payload: ProductIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    catalog_repo.update_product(product_id, payload, user["sub"])
    return {"status": "updated"}


@app.delete("/products/{product_id}")
def delete_product(product_id: str, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    catalog_repo.soft_delete_product(product_id, user["sub"])
    return {"status": "deleted"}


@app.get("/bids")
def bids(user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    return bid_repo.list_bids(user["sub"], user["role"])


@app.get("/notifications")
def notifications(user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    return notification_repo.list_notifications(user["sub"])


@app.post("/notifications/mark-read")
def mark_notifications_read(user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    notification_repo.mark_all_read(user["sub"])
    return {"status": "ok"}


@app.post("/notifications/{notification_id}/mark-read")
def mark_single_notification_read(notification_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE notifications
            SET read_at=NOW(), is_read=1
            WHERE id=%s AND user_id=%s AND read_at IS NULL AND deleted_at IS NULL
            """,
            [notification_id, user["sub"]],
        )
    return {"status": "ok"}


@app.post("/dealer/subscription/activate")
async def activate_dealer_subscription(user: dict[str, Any] = Depends(require_role("dealer"))) -> dict[str, Any]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT subscribed FROM dealer_profiles WHERE user_id=%s",
            [user["sub"]],
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dealer profile not found")
        if row["subscribed"]:
            return {"status": "already_subscribed", "subscribed": True}
        cursor.execute(
            "UPDATE dealer_profiles SET subscribed=TRUE, subscribed_at=NOW(), updated_at=NOW() WHERE user_id=%s",
            [user["sub"]],
        )
        create_notification(
            cursor,
            user["sub"],
            "Subscription Activated",
            "Your dealer subscription is now active. You will receive new bid request alerts matching your service area.",
            "subscription_activated",
        )
        audit(cursor, user["sub"], "dealer.subscribed", "dealer_profiles", user["sub"], {})
    await manager.send_personal_message(
        {"type": "subscription_activated", "route": "profile"},
        user["sub"],
    )
    return {"status": "subscribed", "subscribed": True}


@app.get("/admin/dealers")
def admin_dealers(user: dict[str, Any] = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    return dealer_repo.list_dealers()


@app.get("/admin/dashboard")
def admin_dashboard(user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    return dashboard_repo.admin_dashboard()


@app.get("/buyer/dashboard")
def buyer_dashboard(user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, Any]:
    return dashboard_repo.buyer_dashboard(user["sub"])


@app.get("/dealer/dashboard")
def dealer_dashboard(user: dict[str, Any] = Depends(require_role("dealer"))) -> dict[str, Any]:
    return dashboard_repo.dealer_dashboard(user["sub"])


@app.get("/admin/buyers")
def admin_buyers(q: str = "", user: dict[str, Any] = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    return admin_repo.list_users("buyer", q)


@app.get("/admin/dealers/search")
def admin_dealers_search(q: str = "", user: dict[str, Any] = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    return admin_repo.list_users("dealer", q)


@app.get("/admin/dealers/{dealer_id}/details")
def admin_dealer_details(dealer_id: str, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT u.id, u.email, u.full_name, u.phone, u.status, u.created_at,
                   dp.business_name, dp.owner_name, dp.business_address, dp.gst_number, dp.rating, dp.subscribed, dp.verification_status, dp.service_preferences
            FROM users u
            LEFT JOIN dealer_profiles dp ON dp.user_id = u.id
            WHERE u.id = %s AND u.deleted_at IS NULL AND u.role_id=(SELECT id FROM roles WHERE name='dealer')
            """,
            [dealer_id]
        )
        basic = cursor.fetchone()
        if not basic:
            raise HTTPException(status_code=404, detail="Dealer not found")

        preferences=basic.get('service_preferences') or {}
        basic['service_preferences']=json.loads(preferences) if isinstance(preferences,str) else preferences
        cursor.execute(
            """
            SELECT l.id, l.country, l.state, l.city, l.area, l.pincode, l.latitude, l.longitude, dsl.radius_km
            FROM dealer_service_locations dsl
            JOIN locations l ON l.id = dsl.location_id
            WHERE dsl.dealer_id = %s
            """,
            [dealer_id]
        )
        locations = cursor.fetchall()

        cursor.execute(
            """
            SELECT c.id, c.name
            FROM dealer_categories dc
            JOIN categories c ON c.id = dc.category_id
            WHERE dc.dealer_id = %s
            """,
            [dealer_id]
        )
        categories = cursor.fetchall()

        cursor.execute(
            """
            SELECT b.id, p.name AS product, b.amount, b.status, b.created_at
            FROM bids b
            JOIN bid_requests br ON br.id = b.bid_request_id
            JOIN products p ON p.id = br.product_id
            WHERE b.dealer_id = %s AND b.deleted_at IS NULL
            ORDER BY b.created_at DESC
            """,
            [dealer_id]
        )
        bids = cursor.fetchall()

        cursor.execute(
            """
            SELECT c.id, c.amount, c.payment_status, c.created_at, p.name AS product
            FROM commissions c
            JOIN bids b ON b.id = c.bid_id
            JOIN bid_requests br ON br.id = b.bid_request_id
            JOIN products p ON p.id = br.product_id
            WHERE b.dealer_id = %s
            ORDER BY c.created_at DESC
            """,
            [dealer_id]
        )
        commissions = cursor.fetchall()

        cursor.execute(
            """
            SELECT r.id, ru.full_name AS reporter, r.reason, r.description, r.status, r.created_at
            FROM reports r
            JOIN users ru ON ru.id = r.reporter_id
            WHERE (r.reported_user_id=%s OR r.reporter_id=%s) AND r.deleted_at IS NULL
            ORDER BY r.created_at DESC
            """,
            [dealer_id,dealer_id]
        )
        reports = cursor.fetchall()

        cursor.execute(
            """
            SELECT id, original_name, storage_path, content_type, size_bytes, created_at
            FROM uploaded_files
            WHERE owner_id = %s AND status = 'active'
            ORDER BY created_at DESC
            """,
            [dealer_id]
        )
        documents = cursor.fetchall()

        cursor.execute(
            """
            SELECT sh.old_status, sh.new_status, sh.reason, sh.created_at, u.full_name AS changed_by
            FROM status_history sh
            LEFT JOIN users u ON u.id = sh.changed_by
            WHERE sh.entity_type = 'user' AND sh.entity_id = %s
            ORDER BY sh.created_at DESC
            """,
            [dealer_id]
        )
        timeline = cursor.fetchall()

        return {
            "basic": basic,
            "locations": locations,
            "categories": categories,
            "bids": bids,
            "commissions": commissions,
            "reports": reports,
            "documents": documents,
            "timeline": timeline
        }


@app.get("/admin/buyers/{buyer_id}/details")
def admin_buyer_details(buyer_id: str, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT u.id, u.email, u.full_name, u.phone, u.status, u.created_at, bp.address, bp.country, bp.state, bp.city, bp.area, bp.pincode, bp.preferred_radius
            FROM users u LEFT JOIN buyer_profiles bp ON bp.user_id=u.id
            WHERE u.id = %s AND u.deleted_at IS NULL AND u.role_id=(SELECT id FROM roles WHERE name='buyer')
            """,
            [buyer_id]
        )
        basic = cursor.fetchone()
        if not basic:
            raise HTTPException(status_code=404, detail="Buyer not found")

        cursor.execute(
            """
            SELECT bl.id, bl.label, bl.is_default, l.id AS location_id, l.country, l.state, l.city, l.area, l.pincode, l.latitude, l.longitude
            FROM buyer_locations bl JOIN locations l ON l.id=bl.location_id
            WHERE bl.buyer_id=%s AND bl.deleted_at IS NULL AND l.deleted_at IS NULL ORDER BY bl.is_default DESC,bl.updated_at DESC
            """,
            [buyer_id]
        )
        addresses = cursor.fetchall()

        cursor.execute(
            """
            SELECT br.id, p.name AS product, br.quantity, br.status, br.expires_at, br.created_at,
                   b.amount AS winning_amount, dp.business_name AS dealer
            FROM bid_requests br
            JOIN products p ON p.id = br.product_id
            LEFT JOIN bids b ON b.id = br.winning_bid_id
            LEFT JOIN dealer_profiles dp ON dp.user_id = b.dealer_id
            WHERE br.buyer_id = %s AND br.deleted_at IS NULL
            ORDER BY br.created_at DESC
            """,
            [buyer_id]
        )
        bids = cursor.fetchall()
        basic["bid_count"]=len(bids)
        basic["purchase_count"]=sum(bid["status"]=="awarded" for bid in bids)

        cursor.execute(
            """
            SELECT r.id, tu.full_name AS reported_party, r.reason, r.description, r.status, r.created_at
            FROM reports r
            JOIN users tu ON tu.id = r.reported_user_id
            WHERE (r.reporter_id=%s OR r.reported_user_id=%s) AND r.deleted_at IS NULL
            ORDER BY r.created_at DESC
            """,
            [buyer_id,buyer_id]
        )
        reports = cursor.fetchall()

        cursor.execute(
            """
            SELECT action, entity_type, entity_id, metadata_json, created_at
            FROM audit_logs
            WHERE actor_id = %s OR (entity_type = 'users' AND entity_id = %s)
            ORDER BY created_at DESC
            LIMIT 50
            """,
            [buyer_id, buyer_id]
        )
        timeline = cursor.fetchall()

        return {
            "basic": basic,
            "addresses": addresses,
            "locations": addresses,
            "bids": bids,
            "reports": reports,
            "timeline": timeline
        }


@app.get("/reports/{report_id}/messages")
def list_report_messages(report_id: str, user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with db() as conn, conn.cursor() as cursor:
        # Winning participants share identities immediately after selection.
        cursor.execute(
            """
            SELECT r.reporter_id, r.reported_user_id,
                   (br.status='awarded' AND br.winning_bid_id=b.id) AS contacts_unlocked
            FROM reports r
            JOIN bids b ON b.id=r.bid_id
            JOIN bid_requests br ON br.id=b.bid_request_id
            WHERE r.id = %s
            """,
            [report_id]
        )
        report = cursor.fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if user["role"] != "admin" and user["sub"] not in {report["reporter_id"], report["reported_user_id"]}:
            raise HTTPException(status_code=403, detail="Report is not linked to your account")

        cursor.execute(
            """
            SELECT rm.id, rm.report_id, rm.sender_id, rm.recipient_group, rm.message, rm.created_at,
                   u.full_name AS sender_name, r.name AS sender_role
            FROM report_messages rm
            JOIN users u ON u.id = rm.sender_id
            JOIN roles r ON r.id = u.role_id
            WHERE rm.report_id = %s
            ORDER BY rm.created_at ASC
            """,
            [report_id]
        )
        rows = cursor.fetchall()

        # Unselected offers retain anonymous participant names.
        if user["role"] != "admin" and not report["contacts_unlocked"]:
            for r in rows:
                if r["sender_id"] != user["sub"]:
                    if r["sender_role"] == "dealer":
                        r["sender_name"] = "Dealer"
                    elif r["sender_role"] == "buyer":
                        r["sender_name"] = "Buyer"

        if user["role"] == "admin":
            return rows
        return [row for row in rows if report_message_visible_to(row, user)]


@app.post("/reports/{report_id}/messages")
async def create_report_message(report_id: str, payload: ReportMessageIn, user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    msg_id = new_id()
    notify_user_ids: list[str] = []
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("""SELECT r.reporter_id,r.reported_user_id,r.bid_id,
            (br.status='awarded' AND br.winning_bid_id=b.id) AS contacts_unlocked
            FROM reports r JOIN bids b ON b.id=r.bid_id JOIN bid_requests br ON br.id=b.bid_request_id
            WHERE r.id=%s AND r.deleted_at IS NULL""", [report_id])
        report = cursor.fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if user["role"] != "admin" and user["sub"] not in {report["reporter_id"], report["reported_user_id"]}:
            raise HTTPException(status_code=403, detail="Report is not linked to your account")
        recipient_group = normalize_report_recipient_group(user["role"], payload.recipient_group)
        cursor.execute(
            """
            INSERT INTO report_messages (id, report_id, sender_id, recipient_group, message, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            [msg_id, report_id, user["sub"], recipient_group, payload.message]
        )
        audit(cursor, user["sub"], "report.message_sent", "reports", report_id, {"recipient_group": recipient_group})
        cursor.execute("""SELECT m.id,m.report_id,m.sender_id,m.message,m.recipient_group,m.created_at,
            u.full_name AS sender_name,r.name AS sender_role FROM report_messages m
            JOIN users u ON u.id=m.sender_id JOIN roles r ON r.id=u.role_id WHERE m.id=%s""", [msg_id])
        sent_message = cursor.fetchone()

        if user["role"] == "admin":
            if recipient_group == "both":
                notify_user_ids = [report["reporter_id"], report["reported_user_id"]]
            else:
                cursor.execute(
                    """
                    SELECT u.id
                    FROM users u
                    JOIN roles r ON r.id = u.role_id
                    WHERE u.id IN (%s, %s) AND r.name=%s
                    """,
                    [report["reporter_id"], report["reported_user_id"], recipient_group],
                )
                notify_user_ids = [row["id"] for row in cursor.fetchall()]
            for recipient_id in notify_user_ids:
                create_notification(
                    cursor,
                    recipient_id,
                    "Admin replied to report",
                    "Open the report to view the admin reply.",
                    "report_reply",
                    target_bid_id=report["bid_id"],
                    target_report_id=report_id,
                )
        elif recipient_group == "both":
            notify_user_ids = [uid for uid in [report["reporter_id"], report["reported_user_id"]] if uid != user["sub"]]
            for admin_id in admin_user_ids(cursor):
                notify_user_ids.append(admin_id)
            for recipient_id in notify_user_ids:
                create_notification(
                    cursor,
                    recipient_id,
                    "New public report message",
                    "Open the report to view the new message.",
                    "report_reply",
                    target_bid_id=report["bid_id"],
                    target_report_id=report_id,
                )
        else:
            notify_user_ids = admin_user_ids(cursor)
            for admin_id in notify_user_ids:
                create_notification(
                    cursor,
                    admin_id,
                    "Private report message",
                    "A buyer/dealer sent a private message to admin.",
                    "report_private_message",
                    target_bid_id=report["bid_id"],
                    target_report_id=report_id,
                )

    with db() as conn, conn.cursor() as cursor:
        admins = set(admin_user_ids(cursor))
    for recipient_id in set(notify_user_ids + [user["sub"]]):
        visible_message = dict(sent_message)
        if not report['contacts_unlocked'] and recipient_id != user['sub'] and recipient_id not in admins and user['role'] in {'buyer','dealer'}:
            visible_message['sender_name'] = user['role'].title()
        await manager.send_personal_message(
            jsonable_encoder({"type": "new_message", "report_id": report_id, "route": "reports", "message": visible_message}),
            recipient_id,
        )
    return {"id": msg_id, "status": "sent"}



@app.post("/admin/users/{user_id}/status")
def admin_user_status(user_id: str, payload: StatusIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT r.name AS role FROM users u JOIN roles r ON r.id=u.role_id WHERE u.id=%s AND u.deleted_at IS NULL",[user_id])
        target=cursor.fetchone()
        if not target:
            raise HTTPException(status_code=404,detail="User not found")
        if target['role'] not in {'buyer','dealer'}:
            raise HTTPException(status_code=400,detail="Only buyer and dealer accounts can be moderated here")
    if payload.status == "deleted":
        with db() as conn, conn.cursor() as cursor:
            delete_user_account(cursor, user_id, user["sub"])
        return {"status": "deleted"}
    admin_repo.set_user_status(user["sub"], user_id, payload.status, payload.reason)
    return {"status": "updated"}


@app.delete("/profile")
def delete_own_profile(user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    if user['role'] == 'admin':
        raise HTTPException(status_code=403, detail="Admin accounts cannot be deleted through the marketplace profile")
    with db() as conn, conn.cursor() as cursor:
        delete_user_account(cursor, user["sub"], user["sub"])
    return {"status": "deleted"}


@app.get("/admin/logs")
def admin_logs(user: dict[str, Any] = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    return admin_repo.list_logs()


@app.get("/admin/payments")
def admin_payments(user: dict[str, Any] = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    return admin_repo.list_commissions()


@app.post("/admin/payments/{commission_id}/status")
async def admin_payment_status(commission_id: str, payload: StatusIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    bid_id, recipients = admin_repo.set_commission_status(user["sub"], commission_id, payload.status)
    if payload.status == "paid" and bid_id:
        for recipient_id in recipients:
            await manager.send_personal_message(
                {"type": "commission_paid", "bid_id": bid_id, "route": "bid_history"},
                recipient_id,
            )
    return {"status": "updated"}


@app.get("/reports")
def reports(user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    if user["role"] == "admin":
        return report_repo.list_reports(user["sub"], user["role"])
    rows = report_repo.list_reports(user["sub"], user["role"])
    return [row for row in rows if row.get("reporter_id") == user["sub"] or row.get("reported_user_id") == user["sub"]]


@app.get("/reports/{report_id}")
def report_detail(report_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    rows = report_repo.list_reports(user["sub"], user["role"])
    report = next((row for row in rows if row.get("id") == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if user["role"] != "admin" and user["sub"] not in {report.get("reporter_id"), report.get("reported_user_id")}:
        raise HTTPException(status_code=403, detail="Report is not linked to your account")
    return report


@app.post("/reports")
async def create_report(payload: ReportIn, user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    report_id = report_repo.create_report(user["sub"], payload)
    with db() as conn, conn.cursor() as cursor:
        admins = admin_user_ids(cursor)
    for admin_id in admins:
        await manager.send_personal_message(
            {"type": "report_created", "report_id": report_id, "route": "reports"},
            admin_id,
        )
    return {"id": report_id, "status": "created"}


@app.post("/reports/{report_id}/status")
async def update_report(report_id: str, payload: ReportUpdateIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    recipients = report_repo.update_report(user["sub"], report_id, payload.status, payload.note)
    for recipient_id in recipients:
        await manager.send_personal_message(
            {"type": "report_updated", "report_id": report_id, "route": "reports"},
            recipient_id,
        )
    return {"status": "updated"}


@app.post("/reports/{report_id}/closure-request")
async def request_report_closure(report_id: str, payload: ReportClosureRequestIn, user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    recipients = report_repo.request_closure(user["sub"], report_id, payload.reason)
    for recipient_id in recipients:
        await manager.send_personal_message(
            {"type": "report_cancelled", "report_id": report_id, "route": "reports"},
            recipient_id,
        )
    return {"status": "closed"}


@app.post("/reports/{report_id}/closure-decision")
async def decide_report_closure(report_id: str, payload: StatusIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    decision = payload.status.lower().strip()
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Status must be approved or rejected")
    recipients = report_repo.decide_closure(user["sub"], report_id, decision == "approved", payload.reason)
    for recipient_id in recipients:
        await manager.send_personal_message(
            {"type": "report_updated", "report_id": report_id, "route": "reports"},
            recipient_id,
        )
    return {"status": decision}


@app.get("/settings")
def settings(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return settings_repo.list_settings()


@app.post("/settings/{key}")
def save_setting(key: str, payload: SettingIn, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    settings_repo.save_setting(user["sub"], key, payload.value)
    return {"status": "saved"}


@app.get("/cart")
def cart(user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, Any]:
    return cart_repo.get_cart(user["sub"])


@app.post("/cart/items")
def add_cart_item(payload: CartItemIn, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    cart_repo.add_item(user["sub"], payload.product_id, payload.quantity)
    return {"status": "added"}


@app.delete("/cart/items/{item_id}")
def remove_cart_item(item_id: str, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    cart_repo.remove_item(user["sub"], item_id)
    return {"status": "removed"}


@app.post("/buyer/bids")
async def buyer_start_bid(payload: StartBidIn, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    fields = {key.strip(): value for key, value in payload.fields.items()}
    if payload.notes.strip() and not any(key.casefold() == "notes" for key in fields):
        fields["Notes"] = payload.notes.strip()
    request_id = await asyncio.to_thread(cart_repo.start_bid,
        user["sub"],
        payload.product_id,
        payload.location_id,
        payload.radius_km,
        payload.quantity,
        fields,
        payload.skip_flagged_dealers,
        payload.expiry_minutes,
    )
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT expires_at FROM bid_requests WHERE id = %s", [request_id])
        request_row = cursor.fetchone()
        expires_at = request_row["expires_at"] if request_row else None
        # Only wake up subscribed dealers via WebSocket
        cursor.execute(
            """
            SELECT brd.dealer_id
            FROM bid_request_dealers brd
            JOIN dealer_profiles dp ON dp.user_id = brd.dealer_id AND dp.subscribed = TRUE
            WHERE brd.bid_request_id = %s
            """,
            [request_id],
        )
        dealers = [row["dealer_id"] for row in cursor.fetchall()]
    schedule_bid_request_expiry(request_id, expires_at)
    await publish_bid_snapshot(request_id)
    for dealer_id in dealers:
        await manager.send_personal_message({"type": "new_request", "request_id": request_id}, dealer_id)
    # Wake up buyer too so their notifications tab updates immediately
    await manager.send_personal_message({"type": "bid_created", "request_id": request_id}, user["sub"])
    return {"id": request_id, "status": "created"}


@app.post("/buyer/bids/{bid_id}/accept")
async def buyer_accept_bid(bid_id: str, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    result = await asyncio.to_thread(cart_repo.accept_bid, user["sub"], bid_id)
    await publish_bid_snapshot(result["request_id"])
    await manager.send_personal_message(
        {"type": "bid_accepted", "bid_id": bid_id, "request_id": result["request_id"], "route": "bid_history"},
        result["buyer_id"],
    )
    await manager.send_personal_message(
        {"type": "bid_won", "bid_id": bid_id, "request_id": result["request_id"], "route": "bid_history"},
        result["winner_id"],
    )
    for dealer_id in result["loser_ids"]:
        await manager.send_personal_message(
            {"type": "bid_lost", "request_id": result["request_id"], "route": "bid_history"},
            dealer_id,
        )
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT dealer_id FROM bid_request_dealers WHERE bid_request_id=%s", [result["request_id"]])
        observers = {row["dealer_id"] for row in cursor.fetchall()} - {result["winner_id"], *result["loser_ids"]}
    for dealer_id in observers:
        await manager.send_personal_message({"type": "bid_accepted", "request_id": result["request_id"]}, dealer_id)
    return {"status": "accepted"}


@app.post("/dealer/bids/{bid_id}/pay")
async def dealer_pay_bid(bid_id: str, user: dict[str, Any] = Depends(require_role("dealer"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT b.id, b.status, br.buyer_id, br.status AS request_status, br.winning_bid_id, c.id AS commission_id, c.payment_status
            FROM bids b
            JOIN bid_requests br ON br.id = b.bid_request_id
            LEFT JOIN commissions c ON c.bid_id = b.id
            WHERE b.id = %s AND b.dealer_id = %s
            FOR UPDATE
            """,
            [bid_id, user["sub"]]
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bid not found or not owned by you")
        if row["status"] != "won" or row["request_status"] != "awarded" or row["winning_bid_id"] != bid_id:
            raise HTTPException(status_code=400, detail="Only a winning bid has a commission to pay")
        if not row["commission_id"]:
            raise HTTPException(status_code=404, detail="Commission record not found")
        if row["payment_status"] in {"paid", "waived"}:
            return {"status": row["payment_status"]}
        if row["payment_status"] not in {"pending", "failed"}:
            raise HTTPException(status_code=400, detail="Commission is not payable in its current state")

        cursor.execute(
            """
            UPDATE invoices SET status = 'paid', updated_at = NOW()
            WHERE bid_id = %s
            """,
            [bid_id]
        )
        cursor.execute(
            """
            UPDATE commissions SET payment_status = 'paid', paid_at = NOW(), updated_at = NOW()
            WHERE bid_id = %s
            """,
            [bid_id]
        )
        audit(cursor, user["sub"], "commission.paid", "bids", bid_id, {})
        recipients = create_contact_reveal_notifications(cursor, bid_id)
    for recipient_id in recipients:
        await manager.send_personal_message(
            {"type": "commission_paid", "bid_id": bid_id, "route": "bid_history"},
            recipient_id,
        )

    return {"status": "paid"}


@app.get("/buyer/requests")
def buyer_requests(include_closed: bool = False, user: dict[str, Any] = Depends(require_role("buyer"))) -> list[dict[str, Any]]:
    with db() as conn, conn.cursor() as cursor:
        expire_due_bid_requests(cursor)
        cursor.execute(
            """
            SELECT br.id, br.product_id, p.name AS product, br.quantity, br.expires_at, br.status,
                   UNIX_TIMESTAMP(br.expires_at) AS expires_at_epoch,
                   l.address_line AS buyer_address, l.city AS buyer_city, l.area AS buyer_area,
                   l.state AS buyer_state, l.pincode AS buyer_pincode,
                   (SELECT COUNT(*) FROM bids b WHERE b.bid_request_id = br.id AND b.deleted_at IS NULL AND b.status IN ('active','updated','won','lost','expired')) AS offers_count
            FROM bid_requests br
            JOIN products p ON p.id = br.product_id
            LEFT JOIN locations l ON l.id = br.location_id
            WHERE br.buyer_id = %s AND br.deleted_at IS NULL
              AND (%s=TRUE OR (br.status='active' AND br.expires_at > NOW()))
            ORDER BY br.created_at DESC
            """,
            [user["sub"], include_closed]
        )
        rows = cursor.fetchall()
        for r in rows:
            if r["expires_at"]:
                r["expires_at"] = datetime.fromtimestamp(float(r.pop("expires_at_epoch")), timezone.utc).isoformat()
        return rows


@app.delete("/buyer/requests/{request_id}")
async def cancel_buyer_request(request_id: str, user: dict[str, Any] = Depends(require_role("buyer"))) -> dict[str, str]:
    with db() as conn, conn.cursor() as cursor:
        expire_due_bid_requests(cursor)
        cursor.execute("SELECT id, status FROM bid_requests WHERE id = %s AND buyer_id = %s AND deleted_at IS NULL FOR UPDATE", [request_id, user["sub"]])
        req = cursor.fetchone()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req["status"] in {"expired", "cancelled"}:
            return {"status": req["status"]}
        if req["status"] != "active":
            raise HTTPException(status_code=400, detail="Only active bid requests can be cancelled")
        cursor.execute(
            """
            SELECT DISTINCT dealer_id FROM bid_request_dealers WHERE bid_request_id = %s
            UNION
            SELECT DISTINCT dealer_id FROM bids WHERE bid_request_id = %s AND deleted_at IS NULL
            """,
            [request_id, request_id],
        )
        dealer_ids = [row["dealer_id"] for row in cursor.fetchall()]
        cursor.execute("UPDATE bid_requests SET status = 'cancelled', updated_at = NOW() WHERE id = %s", [request_id])
        cursor.execute("UPDATE bids SET status = 'expired', updated_at = NOW() WHERE bid_request_id = %s AND status IN ('active','updated')", [request_id])
        cursor.execute("UPDATE bid_request_dealers SET status = 'expired' WHERE bid_request_id = %s", [request_id])
        for dealer_id in dealer_ids:
            create_notification(
                cursor,
                dealer_id,
                "Closed by Customer",
                "The buyer closed this bid request.",
                "bid_cancelled",
                target_bid_id=None,
            )
        audit(cursor, user["sub"], "bid_request.cancelled", "bid_requests", request_id, {})
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM audit_logs
            WHERE actor_id=%s AND action='bid_request.cancelled'
            """,
            [user["sub"]],
        )
        if int(cursor.fetchone()["count"]) > 3:
            cursor.execute("UPDATE users SET status='flagged', updated_at=NOW() WHERE id=%s AND status IN ('active','verified','flagged')", [user["sub"]])
    await publish_bid_snapshot(request_id)
    for dealer_id in dealer_ids:
        await manager.send_personal_message(
            {"type": "bid_cancelled", "request_id": request_id, "route": "bid_history"},
            dealer_id,
        )
    return {"status": "cancelled"}


@app.get("/dealer/requests")
def dealer_requests(user: dict[str, Any] = Depends(require_role("dealer"))) -> list[dict[str, Any]]:
    return dealer_ops.incoming_requests(user["sub"])


@app.post("/dealer/bids")
async def dealer_submit_bid(payload: BidIn, user: dict[str, Any] = Depends(require_role("dealer"))) -> dict[str, str]:
    bid_id = await asyncio.to_thread(dealer_ops.submit_bid, user["sub"], payload)
    recipients = [user["sub"]]
    with db() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT buyer_id FROM bid_requests WHERE id = %s", [payload.bid_request_id])
        row = cursor.fetchone()
        if row:
            buyer_id = row["buyer_id"]
            create_notification(
                cursor,
                buyer_id,
                "New Offer Received",
                "A dealer has submitted an offer for your bid request.",
                "new_bid",
                target_bid_id=payload.bid_request_id,
            )
            recipients.append(buyer_id)

            cursor.execute("SELECT dealer_id FROM bid_request_dealers WHERE bid_request_id = %s", [payload.bid_request_id])
            for d_row in cursor.fetchall():
                other_dealer_id = d_row["dealer_id"]
                if other_dealer_id != user["sub"]:
                    recipients.append(other_dealer_id)
    await publish_bid_snapshot(payload.bid_request_id)
    # Events must follow commit so clients cannot refresh an older DB snapshot.
    for recipient_id in recipients:
        await manager.send_personal_message({"type": "new_bid", "bid_request_id": payload.bid_request_id}, recipient_id)
    return {"id": bid_id, "status": "submitted"}


@app.post("/dealer/bids/{bid_id}/withdraw")
async def withdraw_dealer_bid(bid_id: str, user: dict[str, Any] = Depends(require_role("dealer"))) -> dict[str, Any]:
    recipients = [user["sub"]]
    with db() as conn, conn.cursor() as cursor:
        expire_due_bid_requests(cursor)
        cursor.execute(
            "SELECT bid_request_id FROM bids WHERE id=%s AND dealer_id=%s AND deleted_at IS NULL",
            [bid_id, user["sub"]],
        )
        bid_ref = cursor.fetchone()
        if not bid_ref:
            raise HTTPException(status_code=404, detail="Bid not found")
        cursor.execute("SELECT id, status, (expires_at > NOW()) AS is_open FROM bid_requests WHERE id=%s AND deleted_at IS NULL FOR UPDATE", [bid_ref["bid_request_id"]])
        request = cursor.fetchone()
        if not request or request["status"] != "active" or not request["is_open"]:
            raise HTTPException(status_code=400, detail="Cannot withdraw a bid after its request has closed")
        # The request row lock serializes withdrawal with bid acceptance and new offers.
        cursor.execute("SELECT id, status, bid_request_id FROM bids WHERE id = %s AND dealer_id = %s AND deleted_at IS NULL FOR UPDATE", [bid_id, user["sub"]])
        bid = cursor.fetchone()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
        if bid["status"] not in {"active", "updated"}:
            raise HTTPException(status_code=400, detail=f"Cannot withdraw bid with status: {bid['status']}")

        # Withdraw the bid
        cursor.execute("UPDATE bids SET status = 'withdrawn', updated_at = NOW() WHERE id = %s", [bid_id])
        cursor.execute("UPDATE bid_request_dealers SET status='notified' WHERE bid_request_id=%s AND dealer_id=%s", [bid["bid_request_id"], user["sub"]])

        # Check how many bids this dealer has withdrawn/cancelled in total!
        cursor.execute("SELECT COUNT(*) AS count FROM audit_logs WHERE actor_id=%s AND action='bid.withdrawn'", [user["sub"]])
        withdrawn_count = int(cursor.fetchone()["count"]) + 1

        flagged = False
        if withdrawn_count > 3:
            cursor.execute("UPDATE users SET status = 'flagged', updated_at = NOW() WHERE id = %s AND status IN ('active','verified','flagged')", [user["sub"]])
            cursor.execute(
                """
                UPDATE dealer_profiles
                SET warning_message = 'Your profile is flagged for exceeding the maximum limit of 3 bid withdrawals.', updated_at = NOW()
                WHERE user_id = %s
                """,
                [user["sub"]]
            )
            for admin in admin_user_ids(cursor):
                create_notification(
                    cursor,
                    admin,
                    "Dealer Auto-Flagged",
                    f"Dealer {user['email']} was automatically flagged for exceeding 3 bid withdrawals.",
                    "dealer_flagged"
                )
            flagged = True

        audit(cursor, user["sub"], "bid.withdrawn", "bids", bid_id, {"withdrawn_count": withdrawn_count, "auto_flagged": flagged})

        # Notify buyer and other dealers of withdrawal
        cursor.execute("SELECT buyer_id FROM bid_requests WHERE id = %s", [bid["bid_request_id"]])
        req_row = cursor.fetchone()
        if req_row:
            buyer_id = req_row["buyer_id"]
            recipients.append(buyer_id)

            cursor.execute("SELECT dealer_id FROM bid_request_dealers WHERE bid_request_id = %s", [bid["bid_request_id"]])
            for d_row in cursor.fetchall():
                other_dealer_id = d_row["dealer_id"]
                if other_dealer_id != user["sub"]:
                    recipients.append(other_dealer_id)
    await publish_bid_snapshot(bid["bid_request_id"])
    for recipient_id in recipients:
        await manager.send_personal_message({"type": "bid_withdrawn", "bid_request_id": bid["bid_request_id"]}, recipient_id)

    return {"status": "withdrawn", "flagged": flagged}


@app.get("/export/{kind}.csv")
def export_csv(kind: str, user: dict[str, Any] = Depends(current_user)) -> Response:
    if kind == "products":
        rows = []
        offset = 0
        while True:
            batch = catalog_repo.list_products(
                "",
                limit=250,
                offset=offset,
                include_inactive=user["role"] == "admin",
            )
            rows.extend(batch)
            if len(batch) < 250:
                break
            offset += len(batch)
        return csv_response("products.csv", rows)
    if kind == "bids":
        return csv_response("bids.csv", bid_repo.list_bids(user["sub"], user["role"]))
    if kind == "dealers" and user["role"] == "admin":
        return csv_response("dealers.csv", admin_repo.list_users("dealer", ""))
    if kind == "buyers" and user["role"] == "admin":
        return csv_response("buyers.csv", admin_repo.list_users("buyer", ""))
    if kind == "payments" and user["role"] == "admin":
        return csv_response("payments.csv", admin_repo.list_commissions())
    if kind == "logs" and user["role"] == "admin":
        return csv_response("logs.csv", admin_repo.list_logs())
    if kind == "reports":
        rows = report_repo.list_reports()
        if user["role"] != "admin":
            rows = [
                row
                for row in rows
                if row.get("reporter_id") == user["sub"] or row.get("reported_user_id") == user["sub"]
            ]
        return csv_response("reports.csv", rows)
    raise HTTPException(status_code=404, detail="Unknown export")


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".txt", ".csv"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@app.post("/uploads")
def upload_file(file: UploadFile = File(...), user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    safe_name = Path(file.filename or "upload.bin").name
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension '{ext}' is not permitted.")

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit.")

    UPLOAD_ROOT.mkdir(exist_ok=True)
    file_id = new_id()
    target = UPLOAD_ROOT / f"{file_id}-{safe_name}"
    with target.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO uploaded_files (id, owner_id, original_name, storage_path, content_type, size_bytes, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'active', NOW())
            """,
            [file_id, user["sub"], safe_name, str(target.relative_to(ROOT)), file.content_type, size],
        )
        audit(cursor, user["sub"], "file.uploaded", "uploaded_files", file_id, {"name": safe_name, "size": size})
    return {"id": file_id, "name": safe_name, "size_bytes": size, "storage": "local"}


@app.get("/{path:path}")
def react_web(path: str):
    if not WEB_BUILD.exists():
        raise HTTPException(status_code=404, detail="Run npm run build in the web directory first")
    requested = (WEB_BUILD / path).resolve()
    if not requested.is_relative_to(WEB_BUILD.resolve()):
        raise HTTPException(status_code=404, detail="File not found")
    if path and requested.exists() and requested.is_file():
        return FileResponse(requested)
    return FileResponse(WEB_BUILD / "index.html")


if __name__ == "__main__":
    import uvicorn

    logger.info("Backend API running at http://127.0.0.1:8000/")
    logger.info("Do not open http://0.0.0.0:8000/ in a browser; 0.0.0.0 is only the server bind address.")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
