# India Product Catalogue

| Snapshot metric | Count |
| --- | ---: |
| As of | 2026-10-29 |
| Visible product records / variants | 9,211 |
| Original records retained | 3,164 |
| New records added | 6,047 |
| Departments / product types | 16 / 99 |
| Normalized brands | 243 |
| Rows with verified local images | 9,211 / 9,211 |
| Rows with positive INR listed price | 9,211 / 9,211 |
| Rows with GTIN | 342 / 9,211 |
| Rows with release year | 5,429 / 9,211 |
| Rows with blank release year | 3,782 / 9,211 |
| Release research evidence rows | 3,606 |

## Department coverage

| Department | Products |
| --- | ---: |
| Mobile Phones & Tablets | 1,757 |
| Computers, Laptops & IT Equipment | 3,503 |
| TVs, Video & Home Entertainment | 225 |
| Audio, Headphones & Speakers | 1,009 |
| Large Home Appliances | 686 |
| Kitchen Appliances | 119 |
| Cleaning, Laundry & Floor Care | 88 |
| Air Conditioning, Cooling & Air Quality | 306 |
| Personal Care & Grooming Appliances | 61 |
| Cameras, Photography & Imaging | 28 |
| Gaming & Virtual Reality | 80 |
| Wearables & Smart Devices | 337 |
| Smart Home, Security & Surveillance | 96 |
| Networking, GPS & Communication | 319 |
| Printers, Scanners & Office Electronics | 370 |
| Power Backup, Batteries & Electrical Equipment | 227 |

## Data rules

| Data | Rule |
| --- | --- |
| India listing | India-facing product/store page with a positive INR price; stock status is not required. |
| Release year | Store only years supported by exact-model or product-family evidence; unknown years remain blank. |
| GTIN | A source-provided valid GTIN is optional. |
| Specifications | New records contain detailed descriptions and structured technical fields. |
| Images | Downloaded product images are stored as content-hash WebP files in the images directory. |
| Identity | Existing product IDs are preserved; additions are checked against product and variant identities. |

## Canonical files

| Path | Role |
| --- | --- |
| all_products.csv | Canonical product import dataset. |
| master_catalogue.xlsx | Generated workbook view. |
| catalog_metadata.json | Product family, model, variant and taxonomy assignments. |
| release_research_evidence.csv | Product-level release-year/date evidence. |
| Summary CSV files | Generated category, brand, year and coverage summaries. |
