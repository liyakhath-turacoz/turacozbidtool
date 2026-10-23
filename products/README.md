# Optional Open Icecat Catalog Bundle

This directory can contain an Open Icecat product bundle. Downloaded manifests and shards are supplied separately and are excluded from Git. The current India buyer catalog is documented in [product_catalog/README.md](../product_catalog/README.md).

## Import

From the repository root, run:

```powershell
python backend\scripts\import_product_catalog.py --products-root products
```

Use `--replace-existing` only when intentionally replacing catalog data and its dependent records. Review the importer options before running it against a database with production data.

The importer validates shard checksums, uses stable Icecat product IDs, acquires a MariaDB named lock, and records successful catalog versions. Backend startup does not import this bundle unless `TURACOZ_IMPORT_PRODUCTS_ON_STARTUP=true` is set.

## Bundle format

- `manifest.json`: version, counts, filters, checksums, and attribution.
- `data/*.jsonl.gz`: gzip-compressed JSON Lines shards grouped by category.
- `reports/`: importer/build summaries when present.
