"""Read-only database diagnostics shared by startup, health checks and recovery."""

import pymysql


class DatabaseHealthError(RuntimeError):
    pass


def quote_identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def inspect_tables(conn) -> list[dict]:
    results = []
    with conn.cursor() as cursor:
        cursor.execute("SHOW FULL TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall() if list(row.values())[1] == "BASE TABLE"]
        for table in tables:
            try:
                cursor.execute(f"SELECT 1 FROM {quote_identifier(table)} LIMIT 1")
                cursor.fetchall()
                results.append({"table": table, "status": "ok"})
            except pymysql.MySQLError as exc:
                results.append({"table": table, "status": "unavailable", "code": exc.args[0], "error": str(exc.args[1])})
    return results


def assert_tables_readable(conn) -> None:
    failures = [row for row in inspect_tables(conn) if row["status"] != "ok"]
    if failures:
        details = "; ".join(f"{row['table']} (error {row['code']}: {row['error']})" for row in failures)
        raise DatabaseHealthError(
            f"Database tables are unavailable: {details}. "
            "Run python backend/scripts/check_database.py to diagnose. "
            "Missing InnoDB tablespaces require a backup restore or explicit recovery; startup will not delete tables."
        )
