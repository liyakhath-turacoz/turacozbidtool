# India Product Catalogue

| Snapshot metric | Count |
| --- | --- |
| As of | 2026-10-27 |
| Visible product records / variants | 9,195 |
| Original records retained | 3,164 |
| New records added | 6,031 |
| Exact existing matches refreshed | 442 |
| Departments / product types | 16 / 99 |
| Normalized brands | 238 |
| Rows with verified image files | 9,195 / 9,195 |
| Rows with positive INR listed price | 9,195 / 9,195 |
| Rows with GTIN | 342 / 9,195 |
| Rows with release year | 4,133 / 9,195 |
| Newly imported rows with verified year at ingestion | 33 |
| Rows enriched in current exact-name research pass | 559 |

## Department coverage

| Department | Products |
| --- | --- |
| Air Conditioning, Cooling & Air Quality | 304 |
| Audio, Headphones & Speakers | 1,009 |
| Cameras, Photography & Imaging | 28 |
| Cleaning, Laundry & Floor Care | 88 |
| Computers, Laptops & IT Equipment | 3,502 |
| Gaming & Virtual Reality | 80 |
| Kitchen Appliances | 119 |
| Large Home Appliances | 683 |
| Mobile Phones & Tablets | 1,747 |
| Networking, GPS & Communication | 319 |
| Personal Care & Grooming Appliances | 61 |
| Power Backup, Batteries & Electrical Equipment | 227 |
| Printers, Scanners & Office Electronics | 370 |
| Smart Home, Security & Surveillance | 96 |
| TVs, Video & Home Entertainment | 225 |
| Wearables & Smart Devices | 337 |

## New additions by source

| Source | Products |
| --- | --- |
| tpstech | 3,389 |
| reliance | 1,348 |
| boat | 899 |
| vijaysales | 163 |
| portronics | 85 |
| whirlpool | 54 |
| industrybuying | 21 |
| iplanet | 21 |
| agaro | 16 |
| wonderchef | 10 |
| philips | 8 |
| sony | 7 |
| voltas | 7 |
| zebronics | 2 |
| imagine | 1 |

## Data rules

| Data | Rule |
| --- | --- |
| India listing | India-facing product/store listing with a positive INR price; stock status is not required. |
| Release year | Keep only explicitly supported release years; unknown years remain blank. |
| GTIN | Use a source-provided valid GTIN; it is optional. |
| Specifications | New rows require at least five structured specification fields and a detailed description. |
| Images | Product images are locally downloaded, decoded, and stored as content-hash WebP files. |
| Identity | Existing product IDs are preserved; additions are deduplicated by verified variant identity. |

## Canonical files

| Path | Role |
| --- | --- |
| all_products.csv | Canonical product import dataset. |
| master_catalogue.xlsx | Generated workbook view. |
| master_summary.csv; brand_summary.csv; category_coverage.csv; release_year_summary.csv | Generated summaries. |
| category_plan.csv | Active department and category mapping. |
| source_registry.json | Configured India source registry. |
| availability_evidence.json | Product listing, price, and image evidence. |
| release_research_evidence.csv | Verified release-year/date sources. |
| catalog_metadata.json | Family/model/variant and type metadata. |
| images/*.webp | Referenced product images plus images retained for hidden historical product rows. |

Department split CSV exports were removed; publication exporters use the canonical CSV and generated workbook/summary views.
