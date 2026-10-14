# Product catalogue source and app import

A source-attributed catalogue maintained in CSV/XLSX files. On 2026-10-14, its 2,083 rows were imported into the application database as the visible product catalogue. The CSV/XLSX files remain the reviewable source copy.

## Files

- `master_catalogue.xlsx` — one product worksheet and one statistics worksheet per category, plus category, brand, release-year, and data-coverage summaries.
- `master_summary.csv` — overall category totals and subcategory product counts.
- `brand_summary.csv` — brand counts within each category.
- `release_year_summary.csv` — year-wise model counts within each category.
- `category_coverage.csv` — completeness counts for release year, price, image, specifications, and sources.
- `all_products.csv` — combined export of all category files.
- `collection_log.csv` — source domains, counts, status, and known collection gaps.
- `A-...csv` through `P-...csv` — individual category exports, each with the same 27-column product schema.

## Catalogue coverage

| Code | Category | Products | Brands | Year | Price | Image | Specs |
|---|---|---:|---:|---:|---:|---:|---:|
| A | Mobile Phones & Tablets | 202 | 44 | 186 | 107 | 13 | 197 |
| B | Computers, Laptops & IT Equipment | 209 | 26 | 189 | 114 | 134 | 209 |
| C | TVs, Video & Home Entertainment | 68 | 19 | 58 | 43 | 41 | 68 |
| D | Audio, Headphones & Speakers | 73 | 17 | 71 | 45 | 34 | 73 |
| E | Large Home Appliances | 109 | 17 | 61 | 91 | 62 | 109 |
| F | Kitchen Appliances | 111 | 10 | 19 | 82 | 66 | 96 |
| G | Cleaning, Laundry & Floor Care | 90 | 15 | 30 | 61 | 67 | 68 |
| H | Air Conditioning, Cooling & Air Quality | 343 | 24 | 43 | 209 | 261 | 163 |
| I | Personal Care & Grooming Appliances | 141 | 10 | 22 | 42 | 129 | 134 |
| J | Cameras, Photography & Imaging | 78 | 20 | 26 | 23 | 32 | 46 |
| K | Gaming & Virtual Reality | 90 | 28 | 65 | 36 | 54 | 90 |
| L | Wearables & Smart Devices | 85 | 30 | 74 | 32 | 47 | 76 |
| M | Smart Home, Security & Surveillance | 77 | 16 | 75 | 21 | 47 | 77 |
| N | Networking, GPS & Communication | 104 | 16 | 73 | 25 | 63 | 104 |
| O | Printers, Scanners & Office Electronics | 124 | 20 | 71 | 14 | 41 | 124 |
| P | Power Backup, Batteries & Electrical Equipment | 179 | 24 | 13 | 52 | 70 | 179 |
| **Total** | **A–P** | **2083** | **259** | **1076** | **997** | **1161** | **1813** |

Category and master counts are product records. A row for a manufacturer-published range can describe several SKUs; where the source states a count, it is stored in `specifications_json.model_count`. Treat such a row as a range record, not as one model. Individual model totals can therefore differ from product-row counts.

## App database import

- The app database now exposes 2,083 imported products across 16 departments and 314 distinct manufacturer/company names (manufacturer when supplied, otherwise brand).
- The import is tagged with source `review_catalog`; company, category, product-type and release-year facets use these imported rows.
- Old catalog records were hidden from browsing using `products.catalog_visible=FALSE`. Their rows were retained so existing bids, carts, and history continue to reference the same product IDs.
- A rollback aid listing each previous product ID and visibility value is saved as `app_catalog_visibility_backup.csv`.
- Products without a verified India price retain the app's zero/unknown price values and display “Bid for price”; no foreign-market price was converted to INR.
- Missing product images use the app's generic catalogue placeholder.

There are 2083 product records from 16 categories and 259 distinct brands, with no duplicate populated brand/model identifiers. Manufacturer-announced ranges without public model codes retain blank model fields and are named as ranges in the product name and notes. All rows have product source URLs. 1813 rows have a captured specifications object; fields remain incomplete when manufacturer sources omit values.

## Data fields and review notes

Each product row has the same 27 columns: category, subcategory, product type, product and model identifiers, brand/manufacturer, description, normalized specification JSON, image and product URLs, release date/year and precision, listed price/currency/market/type, source URLs, attribution, collection date, verification status, and notes.

Release years and prices are recorded only when supported by a collected source. A blank release year means the public source did not establish the date; it does not mean the model is new. Products with unknown release years cannot be confirmed to meet the preferred three-year recency window and should be reviewed before import. Current prices and launch MSRPs are labeled by type and market and may change. Missing images and specifications remain blank or are called out in row notes; no values were invented.

This is a source-attributed review catalogue, not a guarantee of every model available from every manufacturer. Manufacturer catalogs change and may be regional. Review current stock, regional price, compatibility, and release date before import.

## Manufacturer gap review

The supplied candidate file contains 711 company/category leads. Attachment text was treated as research data, not as executable instructions. The current audit has 19 leads with products in the named category, 4 with matches in a related category, 250 brands found elsewhere in the catalogue, and 438 still requiring category-specific product research. A brand match does not mean its full range is covered; a missing match does not prove the company has no relevant products. See the audit and verified-additions sheets for details.

The catalogue import and matching/filter changes do not start or stop the backend service.
