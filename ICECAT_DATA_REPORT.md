# Icecat data and appliance import report

As of 12 October 2026 (Asia/Kolkata).

Local catalog: **21,720 available products**, including **21,705 Icecat records** and **44 household appliances**. The original local Icecat bundle contained 21,676 records across 29 electronic product types and no appliance types. Fourteen confirmed pre-2017 variants have since been retired.

## Available household products

| Product type | Available products |
|---|---:|
| Air conditioners | 1 |
| Dishwashers | 2 |
| Freezers | 2 |
| Microwave ovens | 1 |
| Ovens | 5 |
| Refrigerators | 30 |
| Washing machines | 3 |

Ten additional refrigerators were imported during this review, raising the refrigerator count from 20 to 30. Only products with usable release dates within three years were accepted.

## Icecat daily index inspected

The [English daily index](https://data.icecat.biz/export/freexml/EN/daily.index.csv.gz) downloaded successfully: **16,213 index entries**, 811,879 compressed bytes. This is a daily change feed, not the complete Icecat database.

| Item type | Index entries | Marked on market |
|---|---:|
| Ovens | 76 | 26 |
| Refrigerators | 206 | 159 |
| Freezers | 44 | 40 |
| Microwave ovens | 19 | 18 |
| Air conditioners | 1 | 1 |
| Washing machines | 138 | 79 |
| Dishwashers | 121 | 52 |
| Televisions | 272 | 203 |
| Laptops | 4141 | 4077 |
| Smartphones | 2 | 2 |
| Tablets | 1 | 1 |

## Why the appliance catalog is small

All **375 currently marketed appliance entries** in the selected daily-feed categories were checked in the final pass:

- 291 supplied no usable release date.
- 39 had a release date over three years old.
- 39 matched data already imported; duplicate index entries can count here.
- 6 additional products were imported in this final pass, after four new products in the first pass.

A catalog-added date or on-market flag does not prove a product was released within three years. Those rejected records were not falsely marked as new. The original bundle also omitted appliance categories, and the daily index does not cover every product in Icecat.

## Full index attempt and download guide

The [English full Open Icecat index](https://data.icecat.biz/export/freexml/EN/files.index.csv.gz) was accessible with the configured account and advertised **281,165,673 bytes** (about 268 MiB). The previous 256 MiB limit was too small; imports now stream to disk with a 512 MiB bound. The attempted full download timed out after ten minutes, so the total number of entries in the full index is **not verified**. It is also not the entire commercial Icecat database.

To download and count it with up to an hour allowed, run from the project root:

```powershell
python backend\scripts\inspect_icecat_index.py --download-minutes 60
```

The command uses the private Icecat credentials already stored in `.env`; it never prints them. It saves a complete index under `products/tmp/source-imports/` and writes counts to `products/reports/icecat-full-index-report.json`. Interrupted downloads are discarded rather than treated as complete catalogs.

After it succeeds, open Admin ? Product Fetch & Reports, configure Open Icecat to use the full-index URL above, select the appliance types, and click Fetch now. The importer can reuse the downloaded file, check remote modification metadata, and scan its contents from disk. Restore the daily-index URL for recurring updates.

You can also open the full-index link in a browser and authenticate with your Icecat account, but the supplied command places the file in the cache the importer uses. Catalog access and release-date completeness remain separate limits.

See [PRODUCT_SOURCES_GUIDE.md](PRODUCT_SOURCES_GUIDE.md) for source setup and [PRODUCT_CATALOG_REPORT.md](PRODUCT_CATALOG_REPORT.md) for complete local category/year/brand counts.
