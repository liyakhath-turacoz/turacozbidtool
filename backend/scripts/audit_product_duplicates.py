"""Report products in the common database that look like the same product (read-only).

Run from the project root:

    python backend/scripts/audit_product_duplicates.py
    python backend/scripts/audit_product_duplicates.py --csv duplicates.csv

Two products are listed together when they share a barcode, a brand + part number, a brand + model number,
or the same brand and product name (ignoring case, punctuation, word order and spacing of units).
Nothing is changed; an administrator decides which copy to keep and archives the others.
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend import product_identity as identity  # noqa: E402
from backend.main import db  # noqa: E402


def find_groups() -> list[dict]:
    with db() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, brand, model, mpn, gtin, source, status FROM products WHERE deleted_at IS NULL AND status IN ('active','inactive')"
        )
        products = cursor.fetchall()
    owners: dict[str, set[str]] = defaultdict(set)
    by_id = {product["id"]: product for product in products}
    for product in products:
        for _, key in identity.identity_keys(product["name"], product["brand"], product["model"], product["mpn"], product["gtin"]):
            owners[key].add(product["id"])
    # Merge products linked by any shared key into one group.
    parent = {pid: pid for pid in by_id}

    def root(pid: str) -> str:
        while parent[pid] != pid:
            parent[pid] = parent[parent[pid]]
            pid = parent[pid]
        return pid

    shared_keys: dict[str, str] = {}
    for key, ids in owners.items():
        if len(ids) > 1:
            first, *rest = sorted(ids)
            for other in rest:
                parent[root(other)] = root(first)
            shared_keys[key] = key
    groups: dict[str, list[str]] = defaultdict(list)
    for pid in by_id:
        groups[root(pid)].append(pid)
    result = []
    for members in groups.values():
        if len(members) > 1:
            kinds = sorted({key.split(":", 1)[0].rstrip("0123456789") for key, ids in owners.items() if len(ids) > 1 and ids & set(members)})
            result.append({"matched_on": ",".join(kinds), "products": [by_id[m] for m in sorted(members, key=lambda m: by_id[m]["name"])]})
    result.sort(key=lambda group: (-len(group["products"]), group["products"][0]["name"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", help="also write the groups to this CSV file")
    args = parser.parse_args()
    groups = find_groups()
    total = sum(len(group["products"]) for group in groups)
    print(f"{len(groups)} group(s) of likely duplicates, {total} products involved.")
    for number, group in enumerate(groups[:40], start=1):
        print(f"\nGroup {number} (same {group['matched_on']}):")
        for product in group["products"]:
            print(f"  {product['id']}  {product['name']}  [{product['brand']} / {product['model'] or '-'}]  source={product['source']}")
    if len(groups) > 40:
        print(f"\n... and {len(groups) - 40} more groups. Use --csv to see all of them.")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["group", "matched_on", "product_id", "name", "brand", "model", "mpn", "gtin", "source", "status"])
            for number, group in enumerate(groups, start=1):
                for p in group["products"]:
                    writer.writerow([number, group["matched_on"], p["id"], p["name"], p["brand"], p["model"], p["mpn"], p["gtin"], p["source"], p["status"]])
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
