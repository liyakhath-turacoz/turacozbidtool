"""Diagnose tables, or explicitly rebuild lost catalog specifications from retained highlights."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import socket
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.catalog_importer import connect, stable_id
from backend.database_health import inspect_tables, quote_identifier
import pymysql


def restore_catalog_specs(conn, failures: list[dict]) -> None:
    if len(failures) != 1 or failures[0]["table"] != "product_specifications":
        raise RuntimeError("Recovery supports only a missing product_specifications tablespace. Restore other tables from a database backup.")
    failure = failures[0]
    if failure["code"] not in {1030, 1812} or "tablespace" not in failure["error"].lower() or "missing" not in failure["error"].lower():
        raise RuntimeError("Refusing to replace a table with an error other than a missing tablespace.")
    with socket.socket() as probe:
        probe.settimeout(2)
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            raise RuntimeError("Stop the backend before restoring specifications.")
    with conn.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK('turacoz_catalog_import', 0) AS acquired")
        if cursor.fetchone()["acquired"] != 1:
            raise RuntimeError("A catalog import is in progress. Stop it before recovery.")
        cursor.execute("SELECT TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME='product_specifications'")
        if cursor.fetchall():
            raise RuntimeError("Other tables reference specifications; use a database backup restore instead.")
        cursor.execute("SELECT id, source, source_product_id, highlights, created_at, updated_at FROM products ORDER BY id")
        products = cursor.fetchall()
        if not products or any(row["source"] != "icecat" or not row["source_product_id"] for row in products):
            raise RuntimeError("This database contains manual/unknown products. Their lost specifications cannot be reconstructed safely by this tool.")
        recovered = []
        for product in products:
            highlights = json.loads(product["highlights"]) if isinstance(product["highlights"], str) else product["highlights"]
            if not isinstance(highlights, dict):
                raise RuntimeError(f"Product {product['id']} has no recoverable highlights object.")
            for order, (name, value) in enumerate(highlights.items()):
                recovered.append((stable_id("highlight", f"{product['source_product_id']}:{name}"), product["id"], str(name)[:120], "Highlights", str(value), order, product["created_at"], product["updated_at"]))
        if not recovered:
            raise RuntimeError("No specifications were recovered; the damaged table was left intact.")

        backup = PROJECT_ROOT / "backend" / "recovery" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
        backup.mkdir(parents=True)
        (backup / "product_highlights.json").write_text(json.dumps(products, default=str, ensure_ascii=False), encoding="utf-8")
        metadata = {}
        for catalog in ("COLUMNS", "STATISTICS", "KEY_COLUMN_USAGE", "TABLE_CONSTRAINTS"):
            cursor.execute(f"SELECT * FROM information_schema.{catalog} WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='product_specifications'")
            metadata[catalog] = cursor.fetchall()
        (backup / "table_metadata.json").write_text(json.dumps(metadata, default=str), encoding="utf-8")
        cursor.execute("SELECT @@datadir AS data_dir, DATABASE() AS database_name")
        server = cursor.fetchone()
        frm = Path(server["data_dir"]) / server["database_name"] / "product_specifications.frm"
        if frm.is_file():
            shutil.copy2(frm, backup / frm.name)

        schema = (PROJECT_ROOT / "backend" / "deployment.sql").read_text(encoding="utf-8")
        ddl = next(statement.strip() for statement in schema.split(";") if statement.strip().startswith("CREATE TABLE IF NOT EXISTS product_specifications ("))
        (backup / "restore_schema.sql").write_text(ddl + ";\n", encoding="utf-8")
        staged = "product_specifications_recovery_" + uuid.uuid4().hex[:8]
        staged_ddl = ddl.replace("CREATE TABLE IF NOT EXISTS product_specifications (", f"CREATE TABLE {quote_identifier(staged)} (").replace("fk_specs_product", "fk_specs_" + staged[-8:])
        cursor.execute(staged_ddl)
        for offset in range(0, len(recovered), 500):
            cursor.executemany(
                f"INSERT INTO {quote_identifier(staged)} (id,product_id,spec_name,spec_group,spec_value,sort_order,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                recovered[offset:offset + 500],
            )
        conn.commit()
        cursor.execute(f"SELECT COUNT(*) AS count FROM {quote_identifier(staged)}")
        if cursor.fetchone()["count"] != len(recovered):
            raise RuntimeError(f"Recovery verification failed; the original table is intact. Staged data: {staged}")
        # All recoverable data is backed up and verified in a separate table before
        # removing the unusable dictionary entry. No healthy table is dropped.
        current = [row for row in inspect_tables(conn) if row["table"] == "product_specifications"][0]
        if current["status"] == "ok" or current.get("code") not in {1030, 1812}:
            raise RuntimeError("The original table's state changed; refusing replacement.")
        (backup / "recovery_plan.json").write_text(json.dumps({"staged_table": staged, "products": len(products), "specifications": len(recovered)}), encoding="utf-8")
        cursor.execute("DROP TABLE product_specifications")
        cursor.execute(f"RENAME TABLE {quote_identifier(staged)} TO product_specifications")
        conn.commit()
        print(f"Recovered {len(recovered):,} specifications for {len(products):,} catalog products.")
        print(f"Recovery source and metadata: {backup}")
        print("Edits stored only in the lost tablespace cannot be recovered from retained highlights.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore-catalog-specs", action="store_true", help="Explicitly replace only a missing catalog specifications tablespace, after backing up retained highlights and verifying a staged replacement. Stop the backend first.")
    args = parser.parse_args()
    conn = connect()
    try:
        results = inspect_tables(conn)
        failures = [row for row in results if row["status"] != "ok"]
        for row in results:
            print(f"{row['status'].upper()}: {row['table']}" + (f" ({row['code']}: {row['error']})" if "code" in row else ""))
        if failures and args.restore_catalog_specs:
            restore_catalog_specs(conn, failures)
            failures = [row for row in inspect_tables(conn) if row["status"] != "ok"]
        print(f"{len(results)} tables checked; {len(failures)} unavailable.")
        return 1 if failures else 0
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, pymysql.MySQLError) as exc:
        print(f"Database check/recovery failed: {exc}", file=sys.stderr)
        sys.exit(1)
