# Turacoz Product Catalog Bundle

This folder contains instructions for importing an optional Open Icecat catalog bundle. Downloaded manifests, shards and reports are local files excluded from Git; supply a bundle separately to import it into a fresh clone.

## Import into a database

From the project root:

```powershell
python backend\scripts\import_product_catalog.py --products-root products
```

Use `--replace-existing` only when intentionally replacing disposable/sample
catalog data and its dependent sample bids, carts, and reports:

```powershell
python backend\scripts\import_product_catalog.py --products-root products --replace-existing
```

The importer validates every shard checksum, uses stable Icecat-based product
IDs, acquires a MariaDB named lock, records the catalog version in
`catalog_imports`, and skips a version that has already imported successfully.

When `TURACOZ_IMPORT_PRODUCTS_ON_STARTUP=true` (the default), backend startup
also imports a present bundle once per catalog version. Production deployments
can instead run the explicit import command as a pre-start/release task.

## Format

- `manifest.json`: version, counts, filters, checksums, and attribution.
- `data/*.jsonl.gz`: gzip-compressed JSON Lines shards grouped by category.
- `reports/summary.json`: build summary.
- `reports/failures.jsonl`: inaccessible/rejected Icecat candidate report.

Temporary global indexes, per-product raw responses, and the discovery database
are deleted after a successful build.
