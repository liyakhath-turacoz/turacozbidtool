"""Optionally reset a local database and add the repeatable demo marketplace."""

from __future__ import annotations

import argparse
import getpass
import re
import sys
from pathlib import Path

import pymysql

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_ROOT))
import main as server


def validate_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"{label} must contain only letters, numbers, and underscores")
    return value


def reset_database(root_password: str) -> None:
    database_name = validate_identifier(server.DB_NAME, "Database name")
    app_user = validate_identifier(server.DB_USER, "Database user")
    connection = pymysql.connect(
        host=server.DB_HOST,
        port=server.DB_PORT,
        user="root",
        password=root_password,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database_name}`")
            cursor.execute(
                f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            for host in ("localhost", "127.0.0.1"):
                cursor.execute(
                    f"CREATE USER IF NOT EXISTS '{app_user}'@'{host}' IDENTIFIED BY %s",
                    [server.DB_PASSWORD],
                )
                cursor.execute(
                    f"ALTER USER '{app_user}'@'{host}' IDENTIFIED BY %s",
                    [server.DB_PASSWORD],
                )
                cursor.execute(
                    f"GRANT ALL PRIVILEGES ON `{database_name}`.* TO '{app_user}'@'{host}'"
                )
            cursor.execute("FLUSH PRIVILEGES")
    finally:
        connection.close()


def populate() -> None:
    server.execute_sql_file()
    server.ensure_runtime_schema()
    server.seed_database()
    from add_dummy_data import populate as seed_demo_marketplace

    seed_demo_marketplace()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the configured database. This permanently deletes all data in it.",
    )
    parser.add_argument(
        "--root-password",
        help="Database admin password (prompted securely when --reset is used).",
    )
    args = parser.parse_args()
    if not server.DB_PASSWORD or not server.ADMIN_PASSWORD or not server.JWT_SECRET:
        parser.error("Configure TURACOZ_DB_PASSWORD, TURACOZ_ADMIN_PASSWORD and TURACOZ_JWT_SECRET in the private .env file before seeding")
    if args.reset:
        root_password = args.root_password or getpass.getpass("MariaDB/MySQL root password: ")
        if not root_password:
            parser.error("A root password is required to reset the database")
        reset_database(root_password)
    populate()


if __name__ == "__main__":
    main()
