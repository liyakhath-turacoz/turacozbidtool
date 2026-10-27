# India product catalogue

Snapshot: 26 October 2026. **2,971 visible catalogue rows** (variant listings), including **518 additions** since the 2,453-row baseline. The catalogue has 83 canonical product-type definitions. The 16 legacy departments remain for existing shop category preferences and bid routing; buyer search uses product types and contextual facets.

Recent additions include **59 air-conditioner variants** and **11 device variants** from current India retailer listings: four Apple iPad Pro (M4, 2024) configurations and seven Microsoft Surface Laptop 15 (Snapdragon X2 Elite, 2026) configurations. Existing product IDs and historical bids/carts are retained. Every visible row has a local image; all 11 new images were downloaded and decoded before import.

The release-evidence pass added exact Samsung India TV lineup rules for 2025 and 2026; 12 matching candidates remain staged for other checks. Apple and Microsoft launch evidence enabled the 11 tablet/laptop variants above.

## Files and identity

`all_products.csv` is the import bundle. Department CSVs and `master_catalogue.xlsx` are generated views. Each row now carries an explicit immutable `product_id`; changing a name or correcting a brand must retain it. Never recompute an existing ID from its display fields.

`catalog_metadata.json` transports family, model, variant, type and offer metadata. `availability_evidence.json` retains publication evidence. `model_release_evidence.json` contains reviewed manufacturer launch rules and exact-model shared specifications. Variant-specific storage, colour and configuration must not be copied from another variant.

`source_registry.json` lists Indian retail/manufacturer sources. `bulk_ingestion_report.json` records coverage and validation results. `release_research_queue.json` is a compact research summary; complete candidate IDs and model queues live in SQL. Raw source documents, caches and recovery snapshots stay outside Git.

## Release-date research plan

1. Collect India-market product pages through public sitemaps, feeds and offers. A discovered URL is only a lead. Confirm the exact product/variant, a positive INR price and new condition. A listing on an India-specific retailer site is sufficient India-market evidence; stock levels are not collected.
2. Exclude accessories wrongly classified as devices, restricted promotions, used products and duplicate retailer parents. Group matching colours/capacities by exact hardware model so one research result can cover its variants.
3. Prioritise substantial product types with low live coverage, then models covering more variants. The current queue has **12,319 model groups covering 16,970 India-listed candidates** that still need release evidence; this is a research backlog, not a verified-product count.
4. Search exact brand/model identifiers in manufacturer newsrooms, launch archives, support specifications and manuals. The queue supplies focused search queries and source links. Process manufacturer feeds/archives in batches when possible. Use comparison sites to locate evidence, then verify the manufacturer model/generation.
5. Record the source URL, scope, date precision and review date. A current India retailer's explicit `Launch Year` or `Release Year` field can support a year-only value when it is on the exact product listing and its model identity matches. Keep the exact day blank; never turn 2025 into an invented 1 January date. Manufacturing/packing dates, store-listing timestamps, sitemap modification dates, certification dates and Icecat catalog-added dates are not release dates.
6. Apply evidence only to matching hardware generations and variants. Recheck identifiers, required specifications, exact images and current India offers. Keep unresolved or conflicting records pending.

The rolling release window is **26 October 2022 through 26 October 2026** for this snapshot. A year-only record qualifies only when its possible release interval fits the window. A current India store listing establishes India-market presence without any stock check; if it has no explicit release-year evidence, the model stays pending.

Icecat enriches exact verified brand/MPN or GTIN matches. It does not establish India availability. Manufacturer-confirmed models with unambiguous full variant names/options can be identified without inventing GTINs or treating retailer SKUs as MPNs. Matching exact GTINs across store offers can resolve existing catalogue duplicates; uncertain name-only matches stay pending.

## Current coverage and limitations

The pipeline has staged **37,154 candidate records** and discovered roughly **211,000 URL leads**. Current states: **1,958 published candidates, 34,851 pending, 28 eligible and 317 rejected**. Published candidates include existing products and multiple retailers; they are not counts of new products.

The current export has **1,264 exact release dates, 1,610 populated release years with accepted evidence, 70 populated GTINs and 2,971 local image references** (2,138 distinct referenced files). The audit still finds **1,361 rows without a verified release date/year, 2,890 without a GTIN, 750 missing required type attributes, 37 unmapped rows and 96 rows sharing purchase URLs**. Counts overlap. Existing records with incomplete research remain visible; new additions must pass release, variant, specification and image checks. Images and India listing evidence do not certify every legacy specification.

Croma's sitemap was inaccessible in this run. Some sources returned transfer/access errors; Vijay Sales now has an exact product-page parser, while some Sathya pages still need an adapter. iPlanet's public feed was collected to completion (3,428 parent listings); exact SKU matches supplied verified barcodes for some variants. Thousands of candidates still need verified release dates and fuller type-specific specifications. Do not publish the pending backlog merely to increase the count.

## Running the pipeline

Install `backend/requirements.txt` and `backend/scripts/requirements-catalog.txt`. Configure private database and optional Icecat credentials in `.env`.

Run commands from the repository root:

```powershell
python backend/scripts/ingest_india_catalog.py discover --sources reliance,croma --max-maps 25
python backend/scripts/ingest_india_catalog.py collect --sources iplanet --max-pages 20
python backend/scripts/ingest_india_catalog.py reprocess --sources iplanet
python backend/scripts/ingest_india_catalog.py verification-queue
python backend/scripts/ingest_india_catalog.py releases
python backend/scripts/ingest_india_catalog.py store-release-years
python backend/scripts/ingest_india_catalog.py model-specs
python backend/scripts/ingest_india_catalog.py variant-pages --limit 200
python backend/scripts/ingest_india_catalog.py manufacturer-pages --limit 100
python backend/scripts/ingest_india_catalog.py enrich --sources iplanet --limit 200
python backend/scripts/ingest_india_catalog.py publish --limit 200
python backend/scripts/ingest_india_catalog.py publish --limit 200 --apply
python backend/scripts/ingest_india_catalog.py search-index
```

Publication defaults to dry-run. Applied publication is append-only, snapshots recovery data, verifies downloaded images, and refreshes portable metadata. `audit --apply` updates classification only. `quarantine-invalid --apply` separately hides explicit used/restricted listings and preserves their IDs.

For a clean deployment, import the checked-in bundle with `python backend/catalogue_app_import.py --apply`. To add only missing IDs, use `--apply --append-only`. Configure the database privately; never distribute production credentials in catalogue files.

Exact release dates and years are hidden in buyer/dealer payloads by default. Set `TURACOZ_SHOW_PRODUCT_RELEASE_DATES=true` and restart the API to reveal them. Admins can distinguish manufacturer evidence from an India retailer's explicit launch-year field.

## Validation

The latest import passed the catalogue snapshot validator: all 2,960 rows have complete required fields, India price metadata, technical details and local image files. All 59 new product images were downloaded, opened and re-encoded before import; all 2,132 distinct current image files decoded successfully. The full export has been checked for duplicate product names, duplicate IDs and missing image paths by the same validator. Every exported GTIN matches the live database; two unverified barcodes that belonged to other colour variants were removed from the export.

The original target of 8,000–10,000 verified products is not reached. The 16,981-candidate date-research queue is not a verified-product count, and several categories still have low live coverage.

A synthetic 10,000-document Tantivy test used about 42 MB process RSS. Native search plus three facets measured about 2.2 ms at the 95th percentile; this excludes HTTP, database hydration and the full facet response. These measurements are local observations, not a total memory cap or production latency guarantee.
