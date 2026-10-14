# Category A — Mobile Phones & Tablets

Status: **in progress**. This folder contains a separate, normalized CSV staging catalogue. It is not joined to, imported into, or used to update the existing product database. No application code or live product rows were changed.

## Ordered product types

1. **Smartphones** — Android phones, iPhones, foldable phones (active)
2. **Feature Phones** — keypad phones, basic mobile phones
3. **Tablets** — Android tablets, iPads, Windows tablets
4. **E-readers** — Kindle-type devices
5. **Telephone Devices** — cordless phones, landline phones, video phones
6. **Mobile Accessories** — phone cases, screen protectors, mobile chargers, power banks, phone holders, styluses

Department B remains queued until every product type in A has been researched, deduplicated within this staging catalogue, and validated.

## Current smartphone tranche

- `products.csv`: 11 Apple models with official availability dates from 2023-10-13 through 2026-10-13: iPhone 16/16 Plus/16 Pro/16 Pro Max/16e, iPhone 17/17 Pro/17 Pro Max, iPhone Air, iPhone 18 Pro/18 Pro Max.
- `needs_review.csv`: 201 entries: 200 manufacturer-catalogue candidates whose release dates or product details still need verification, plus iPhone Duo, whose official availability date is 2026-10-23 (after the 2026-10-13 as-of date). Review entries are not included in the eligible product export.
- `sources.csv` tracks manufacturer sources, extraction status, and known gaps. Catalog presence alone is not treated as proof of release date.

The release cutoff is **2023-10-13** and the as-of date is **2026-10-13**. Missing dates remain blank; dates are not inferred from crawl time, image filenames, or catalog order. Deduplication applies only within these new staging files, using normalized brand plus model/MPN. Distinct SKUs are retained only when official identifiers distinguish them.

## CSV columns and later import

The CSVs use normalized product fields: department/type, product name, brand, model, MPN/GTIN, description, specifications JSON, product/image URLs, release date/year and precision, release evidence URL, source attribution, staging dedup key, eligibility, and validation notes. They contain no legacy database IDs or database-match fields. Map these columns to the target database only during a separately authorized import. HTML and unrelated page markup are excluded.

## Resuming

Use `progress.json`, `sources.csv`, and each row's `dedup_key`. Finish smartphone date and specification checks and resolve duplicates within this staging catalogue before starting Feature Phones. Do not start the next product type or department early. Firecrawl scrape outputs are temporary research artifacts under the ignored `.firecrawl/` directory; these clean CSV exports are the deliverables.
