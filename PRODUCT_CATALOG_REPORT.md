# Current India store catalogue

Verified on **2026-10-23**: **1,492 purchasable variants**, **70 brands**, **16 departments**.

Every visible row has an in-stock store variant, positive INR selling price, technical details, a purchase URL and a decoded, locally stored product photograph. Prices and stock are point-in-time store claims. Reconfirm delivery pincode, stock and price before purchase.

## Coverage

| Department | Products |
|---|---:|
| Mobile Phones & Tablets | 80 |
| Computers, Laptops & IT Equipment | 416 |
| TVs, Video & Home Entertainment | 74 |
| Audio, Headphones & Speakers | 232 |
| Large Home Appliances | 66 |
| Kitchen Appliances | 45 |
| Cleaning, Laundry & Floor Care | 23 |
| Air Conditioning, Cooling & Air Quality | 95 |
| Personal Care & Grooming Appliances | 40 |
| Cameras, Photography & Imaging | 12 |
| Gaming & Virtual Reality | 20 |
| Wearables & Smart Devices | 7 |
| Smart Home, Security & Surveillance | 83 |
| Networking, GPS & Communication | 81 |
| Printers, Scanners & Office Electronics | 88 |
| Power Backup, Batteries & Electrical Equipment | 130 |

## Evidence and files

- all_products.csv, A–P exports, master_catalogue.xlsx and the root product_inventory.xlsx contain the same replacement records.
- availability_evidence.json records the exact store variant/SKU, stock-check date, selling price, original photo URL and downloaded image SHA-256.
- verification_report.json records scan totals, rejected inventory and coverage limitations.
- images/ contains the product photos served at /catalog-images/. Web and mobile use the same assets.

## Acceptance rules

Store inventory must have a positive INR price and an available exact variant. Storefront currency is independently checked. Store listings created before 2025-04-23 are excluded. Samsung variants use explicit new-condition, InStock Offers from current India buy pages instead of a listing-age estimate.

Store listing dates are NOT manufacturer release dates. Unknown release dates and years remain blank. Coverage is a verified subset of the configured stores; it does not claim every Indian store or every latest launch.

Refurbished, renewed, pre-owned, preorder, gift/bundle, incomplete, unmatched-colour-image and known legacy-generation records are excluded. Exact name and SKU duplicates are removed. Missing metadata is not invented.

## Refresh and deployment

Install backend/scripts/requirements-catalog.txt. Run rebuild_india_catalog.py with the current India verification date and desired listing cutoff, then inspect .firecrawl/india-catalog-staged/verification_report.json. Run publish_india_catalog.py without flags to validate; --apply publishes and imports.

Publication rejects empty/suspiciously small snapshots, inventory evidence older than seven days, missing details, duplicate identities or mismatched/missing downloaded photos. An imported snapshot does not reserve stock or refresh itself.

Backups are private under backend/recovery/ and excluded from Git. Unreferenced old products are deleted; historical products remain hidden for bid/cart references. Legacy import schedules and automatic startup bundle imports are disabled by default.

Deploy product_catalog/images with the backend. Restart a backend running without reload to enable the /catalog-images/ route.
