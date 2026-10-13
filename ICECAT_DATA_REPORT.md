# Icecat data and household appliance import report

As of 13 October 2026 (Asia/Kolkata).

The database contains **22,042 available products**: 21,676 electronics and 366 household appliances. The original bundled catalog contained 21,676 records across 29 electronics product types and no household appliances. Fourteen confirmed pre-2017 tablet variants were retired while preserving historical bids. The catalog totals and the household source breakdown are in [PRODUCT_CATALOG_REPORT.md](PRODUCT_CATALOG_REPORT.md) and [HOUSEHOLD_PRODUCTS_REPORT.md](HOUSEHOLD_PRODUCTS_REPORT.md).

## Icecat household index

The public [English household vertical index](https://data.icecat.biz/export/freexml/EN/1314.vertical.files.index.xml.gz) downloaded completely: **11,998,791 compressed bytes and 144,243 index entries**. It covers seven household types:

| Type | Index records | Marked on market |
|---|---:|---:|
| Ovens | 10,166 | 4,686 |
| Refrigerators | 18,535 | 9,361 |
| Freezers | 3,923 | 2,120 |
| Microwave ovens | 4,615 | 2,246 |
| Air conditioners | 3,537 | 1,407 |
| Washing machines | 18,719 | 8,886 |
| Dishwashers | 11,234 | 6,112 |

An Icecat index record does not guarantee an accessible product detail record or a usable recent release date. The importer requires actual product release evidence, excludes products older than the three-year cutoff, deduplicates models, and skips unchanged records. In the household import, most checked candidates lacked a release date or had a restricted/missing detail response; only **17** new records qualified. Icecat model detail availability can vary by account and product. A 404 is reported as unavailable; it does not by itself prove that a paid license is required.

The checked [Icecat vertical index documentation](https://iceclog.com/full-index-files-per-vertical-on-en-and-nl-locales-in-icecat-catalog/) lists 1314 as the household-appliance vertical. This is a vertical catalog subset, not all Icecat products.

## Why the appliance catalog was small

The local starter bundle was focused on electronics: its 29 types included laptops, SSDs, desktops, monitors, printers, phones and related hardware, with no appliance types. The daily Icecat index is only a change feed, and even the larger appliance vertical contains many older, unavailable or undated models. Records without first-release evidence are not assigned a fresh date from index-added or modified timestamps. LG's manufacturer catalog and EPREL's verified registry supplied more usable current appliance models.

The current minimum of 50 is met for air conditioners, dishwashers, freezers, ovens, refrigerators, tumble dryers and washing machines. Microwave ovens currently have **16** verified recent records. LG India's public catalog returned recent model dates, but its microwave set was limited; Icecat's broader index had many entries but few accessible records with usable release dates. The official [LG Korea microwave listing](https://www.lge.co.kr/m/category/microwaves-and-ovens?subCateId=CT50022013) also contains older models and several product families that are combination ovens, so its whole listing cannot safely be counted as 50 recent microwave models. Other current source coverage is described in [HOUSEHOLD_PRODUCTS_REPORT.md](HOUSEHOLD_PRODUCTS_REPORT.md).

## Full Icecat index download

The English general full index advertised **281,165,673 bytes** (about 268 MiB). The attempted download ended incomplete at roughly 160 MiB and was discarded; therefore its complete entry count is **not verified**. The successful household vertical is a separate, smaller file. It is also not valid to describe the accessible Open Icecat subset as the entire commercial Icecat database.

If you want to retry the general index from the project root, run:

```powershell
python backend\scripts\inspect_icecat_index.py --download-minutes 60
```

The command uses the private Icecat credentials already stored in `.env`, never prints them, and saves only a complete file. Network or account access may again limit the download. Review account access with Icecat if individual records return 401/403; a 404 can instead mean the record is absent at that path. See the [Open Catalog Interface guide](https://iceclog.com/wp-content/uploads/2018/12/Open-Catalog-Interface.pdf).

## Current verified totals

The database was audited on 13 October 2026. See [PRODUCT_CATALOG_REPORT.md](PRODUCT_CATALOG_REPORT.md) for product-type, year and brand counts. Legacy dates are not all verified launch dates: **21,644 legacy electronics records** have catalog-reported years whose exact release age cannot be certified. New imports use source release evidence and a strict cutoff of 13 October 2023.
