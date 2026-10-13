# Household appliance catalog report

Audited 13 October 2026. The marketplace contains **22,042 available records**: **21,676 electronics** and **366 household appliances**. The household catalog grew from 44 to 366 in this import pass: **322 products added** and **2 existing product records updated**.

## Household product types

| Household type | Available records | Meets 50 minimum? |
|---|---:|:---:|
| Air conditioners | 50 | Yes |
| Dishwashers | 50 | Yes |
| Freezers | 50 | Yes |
| Microwave ovens | 16 | No |
| Ovens | 50 | Yes |
| Refrigerators | 50 | Yes |
| Tumble dryers | 50 | Yes |
| Washing machines | 50 | Yes |
| **Total** | **366** | — |

These are product/SKU records, which can include regional and configuration variants. They do not necessarily equal distinct global model families. Recent new imports were limited to products with an explicit recent release/market date, identifiable brand and model, and no indication that the product was discontinued. The import cutoff was 13 October 2023.

## Where the new products came from

| Source | Added | Existing records updated | Date evidence and scope |
|---|---:|---:|---|
| [LG India catalog](https://www.lg.com/in/air-conditioners/all-air-conditioners/) | 134 | 0 | LG model release date, model/SKU and product page; India catalog |
| [Open Icecat household vertical](https://data.icecat.biz/export/freexml/EN/1314.vertical.files.index.xml.gz) | 17 | 0 | Product XML release date; publicly accessible English household vertical |
| [EU EPREL registry](https://eprel.ec.europa.eu/screen/product/ovens) | 171 | 2 | Manufacturer-declared first EU/EEA market date; verified supplier records |
| **Total** | **322** | **2** | |

For the 171 EPREL additions, the stored date indicates the manufacturer's first declared EU/EEA market date. It is not presented as the product's first worldwide launch. EPREL does not provide product photos through these records, so the app uses its unavailable-image placeholder instead of showing an energy label as a product image. LG and Icecat records retain source attribution and source links in the database.

## Why microwaves remain below 50

The original catalog bundle contained **21,676 electronics products across 29 types and zero household appliance types**. Its source coverage explains why the home-appliance total began at just 44; it was not evidence that the marketplace already had thousands of hidden appliances.

The Icecat household index is large—**144,243 index entries**—but entries are not equivalent to accessible, recent products. In the import, most candidate appliance entries either lacked a release date, were too old, were unchanged, or could not be fetched. Index-added dates are not used as release dates. The Icecat and LG India data only raised microwave ovens to 16 with qualifying recent dates. LG Korea's live listing contains a mixture of older products, microwaves and combination ovens; counting the whole listing as 50 recent microwave models would misclassify products and release ages. The category is reported as 16 rather than padded with old or unverified records.

There are also no current database categories for vacuum cleaners, air purifiers or cooktops in this audited household type list. This does not mean those products do not exist. They were not added in this pass because the reviewed feed coverage/import schema did not produce a date-verified set for those product types. The category counts in [PRODUCT_CATALOG_REPORT.md](PRODUCT_CATALOG_REPORT.md) show the complete existing product-type breakdown.

## The existing 21,676 electronics records

The electronics catalog is not a hidden household appliance stock. It is made up of 29 electronics types. The largest product/SKU counts are:

| Electronics type | Records |
|---|---:|
| Laptops | 2,754 |
| SSDs | 2,754 |
| Desktop computers | 2,298 |
| Monitors | 2,206 |
| Printers | 1,838 |
| Smartphones | 1,396 |
| Signage displays | 1,230 |
| Servers | 909 |
| Televisions | 772 |
| Enterprise network switches | 727 |

The remaining electronics types include storage servers, graphics cards, motherboards, projectors, CPUs, cameras, tablets, networking and audio/video equipment. [PRODUCT_CATALOG_REPORT.md](PRODUCT_CATALOG_REPORT.md) lists all 29 types, reported release years and brands. Many original Icecat year values are unverified catalog years, not independently checked launch years; the report marks the distinction.

## Source and import references

- [Product source setup and adapters](PRODUCT_SOURCES_GUIDE.md)
- [Icecat index and access details](ICECAT_DATA_REPORT.md)
- Local database detail: ignored private files under `products/reports/`, including `product-statistics.csv` and `product-statistics.json`
