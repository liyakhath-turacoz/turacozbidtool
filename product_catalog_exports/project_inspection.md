# Existing product catalogue inspection (read-only)

## Product bundle

The existing `products/` directory contains 32 gzip-compressed JSONL data shards under `products/data/`, a `manifest.json`, `catalog-state.json`, report files under `products/reports/`, and source-import work files under `products/tmp/source-imports/`. It has no nested `products/products` directory. The bundle README describes it as a product data bundle; its importer is separate from the application database.

## Live product table

Read-only inspection found 22,060 rows in the application product table: 22,042 active and 18 soft-deleted. The table keeps department/category IDs and product type IDs, manufacturer name, model, MPN/GTIN, source identifiers, release date/year and precision, descriptions and specifications, image/gallery links, source attribution, and audit/status fields. The existing unique source key is `(source, source_product_id)`; this staging export additionally uses normalized brand+model dedup keys.

Relevant columns observed: `id`, `category_id`, `subcategory_id`, `name`, `brand`, `model`, `source`, `source_product_id`, `mpn`, `gtin`, `release_year`, `release_date`, `release_date_precision`, `release_date_basis`, `description`, `technical_specifications`, `image_url`, `gallery`, `source_url`, `source_attribution`, `status`, `created_at`, `updated_at`, and `deleted_at`. The exact table also has other catalogue metadata fields. No schema changes were made.

## Existing phone records

The earlier read-only category aggregation returned 1,396 active smartphone products and 189 active tablets. Smartphone brand counts: Samsung 1,138; Motorola 142; HONOR 50; OPPO 28; reseller/refurbisher label ?upcycle it? 28; TCL 10. Tablet counts: Samsung 119; Lenovo 52; Zebra 6; Acer 5; HONOR 3; TCL 3; OPPO 1. These are existing database records and are not the new manufacturer-verified staging totals.

For the current smartphone tranche, a read-only query scanned 22,042 active product names/models against 212 staging entries; 17 catalogue candidates have possible overlap with existing rows. Those candidates are marked in `needs_review.csv`. The 11 Apple records with verified qualifying release dates had no exact normalized match in the active product rows. This matching pass is a staging safeguard, not an import.

## Change boundary

No application code, schema, or product rows were changed. The only live database activity was SELECT metadata/product reads inside a read-only transaction. New manufacturer research is staged under `product_catalog_staging/` as CSV and supporting documentation for later review and import instructions. No server was started or stopped.
