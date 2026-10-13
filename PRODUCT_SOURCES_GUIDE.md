# Product fetching and catalog dates

## Admin operation

Restart the backend after installing these changes. In either app, open **Admin → Product Fetch & Reports**.

1. Configure a source, select its product types and set the maximum accepted products per run.
2. Use **Fetch now**, or enable an hourly interval, daily local time, or one fixed local date/time. The default timezone is `Asia/Kolkata`.
3. Keep the backend running for scheduled work. Schedules, import history, counts and source identities are stored in MariaDB. Interrupted imports can be fetched again safely; unchanged records are skipped.
4. Check job errors and review links. An article without an identifiable product and release evidence is a review lead. It is not turned into a made-up SKU.

Schedules start disabled. Downloads are bounded, jobs run in a worker thread, and the page shows progress. A fixed schedule runs once. Fetching does not restore products an admin removed or disabled, change existing auction identities, or overwrite manual specification edits.

## Thirteen official manufacturer sources

These listings returned article links during inspection on 12 October 2026. The registry is in `backend/manufacturer_sources.py`; HTML structures can change, and not every press release supplies importable product data. LG India is also queried through its official product catalog API, which publishes model release dates and product SKUs.

| Manufacturer | Official source | Observed structure | Relevant products |
|---|---|---|---|
| Samsung | [India press resources](https://news.samsung.com/in/category/press-resources) | WordPress article links; `og:title`, `date` metadata | Phones, tablets, TVs, appliances |
| OPPO | [India newsroom](https://www.oppo.com/in/newsroom/) | Embedded news JSON with `page_url`, `title`, `sort_date` | Phones, tablets |
| Apple | [Newsroom feed](https://www.apple.com/newsroom/rss-feed.rss) | Atom entries, alternate article links, publication dates | Phones, tablets, laptops, watches |
| Lenovo | [Newsroom](https://news.lenovo.com/) | WordPress press-release links and JSON-LD dates | Laptops, tablets, monitors |
| HP | [Newsroom](https://www.hp.com/us-en/newsroom.html) | AEM links to dated press-release pages | Laptops, monitors, printers |
| ASUS | [Press RSS](https://press.asus.com/rss.xml) | RSS items and linked press releases | Laptops, tablets, phones, monitors |
| Acer | [News feed](https://news.acer.com/feed) | RSS items and article HTML/JSON-LD | Laptops, tablets, monitors |
| Midea | [Global news](https://www.midea.com/global/news) | AEM article links | Air conditioners, refrigerators, kitchen/laundry appliances |
| TCL | [Global news](https://www.tcl.com/global/en/news) | AEM article links | TVs, phones, tablets, appliances |
| Panasonic | [Global press](https://news.panasonic.com/global/press/) | Public newsroom JSON API with article URL, title, publication timestamp | TVs, air conditioners, kitchen/laundry appliances |
| Whirlpool | [Latest news](https://www.whirlpoolcorp.com/latest-news.html) | AEM newsroom article links | Kitchen/laundry appliances |
| Bosch | [Press portal](https://www.bosch-presse.de/pressportal/de/en/news/) | Numbered HTML press articles | Kitchen/laundry appliances |
| LG | [India catalog](https://www.lg.com/in/air-conditioners/all-air-conditioners/) | Official catalog search API with model SKU, image, status and model release date | Air conditioners, refrigerators, microwave ovens, washers, freezers, dishwashers |

Manufacturer adapters accept structured `Product` records with release dates and supported named launch models with availability evidence. Stated sale dates take priority over publication dates; a future availability date is rejected. Other articles remain review links. Model-family announcements may lack configuration specifications; those fields remain empty until a reliable source or admin supplies them. Corporate news and industrial products outside the selected item types are not catalog products.

The Mobile Specs GitHub project was removed because its documentation provides no hosted API.

## EU EPREL appliance registry

The [European Product Registry for Energy Labelling (EPREL)](https://eprel.ec.europa.eu/screen/product/ovens) publishes verified manufacturer/model records with manufacturer-declared first EU/EEA market dates. We import current records only when that first-market date is within the three-year cutoff. The date describes EU/EEA availability, not necessarily the model's first worldwide launch. EPREL covers ovens, refrigerators, freezers, dishwashers, washing machines and tumble dryers; it does not cover microwave ovens. EPREL does not return retail product photos, so imported models use the site's neutral unavailable-image placeholder.

## Structured catalog sources

**[TechAPI](https://gettechapi.github.io/TechAPI/)** provides public static JSON lists and per-product details. Imports normalize supported specification fields, retain source attribution and reject explicitly unverified records. The dataset is licensed CC-BY-SA 4.0; preserve that attribution when redistributing its data.

**Open Icecat XML** downloads succeeded with the supplied account. Credentials are stored only in the private `.env`:

```dotenv
ICECAT_USERNAME=your_icecat_username
ICECAT_PASSWORD=your_icecat_password
```

The XML adapter uses HTTP Basic authentication; it does not require a Dynamic API token. `ICECAT_API_TOKEN` applies to the separate legacy bundle builder.

For household appliances, the successful bounded index is the public [English household vertical XML index](https://data.icecat.biz/export/freexml/EN/1314.vertical.files.index.xml.gz):

```text
https://data.icecat.biz/export/freexml/EN/1314.vertical.files.index.xml.gz
```

The default discovery URL for general recurring updates is the authenticated daily index:

```text
https://data.icecat.biz/export/freexml/EN/daily.index.csv.gz
```

For a broader initial scan, configure the full index:

```text
https://data.icecat.biz/export/freexml/EN/files.index.csv.gz
```

An index discovers candidates. The fetcher then downloads individual English product XML records, normalizes features, and requires actual release evidence. Index `Date_Added` and last-modified dates never substitute for a release date. Full indexes can exceed the bounded download/time limit; use the daily index for recurring updates.

If an account later receives HTTP 401/403, sign into Icecat, confirm Open Icecat download access and update `.env`, then restart the backend. Closed/full catalog products may need a different subscription. The [Open Catalog Interface guide](https://iceclog.com/wp-content/uploads/2018/12/Open-Catalog-Interface.pdf) describes the index and XML interface.

Downloaded responses are cached privately under `products/tmp/source-imports/`. Normalized products are stored in MariaDB. Neither the account password nor authorization headers appear in API responses.

## Additional admin-selected sources

Both apps can add a public HTTPS JSON feed. It must return an array, or an object with `products`, `results` or `items`, containing records like:

```json
{
  "id": "manufacturer-model-2026",
  "name": "Example model",
  "brand": "Example manufacturer",
  "product_type": "Refrigerators",
  "release_date": "2026-02-15",
  "specifications": {"Total net capacity": "350 L"}
}
```

An arbitrary HTML URL needs a matching adapter; the JSON feed option does not promise to extract products from every website.

## Age rules and existing data

New imports accept released products no older than three calendar years: the cutoff on 13 October 2026 is **13 October 2023**. Future, missing, ambiguous boundary-year and discontinued records are skipped. A date identifying an announcement is labelled separately from an explicit release date.

Existing legacy data is retained unless an actual pre-2017 release is established. Fourteen confirmed old Samsung tablet variants were retired after private backup; historical bids remain. Some surviving 2017/2020 models have corrected manufacturer release years. Many legacy records still have catalog-added years, so their exact age is unknown.

Read [PRODUCT_CATALOG_REPORT.md](PRODUCT_CATALOG_REPORT.md) for category/year/brand totals. Private CSV reports in `products/reports/` list retired products, older products, approximate reported ages and confidence. Refresh them with:

```powershell
python backend\scripts\audit_product_catalog.py
```

Buyer and admin filters search the full database using four groups: Categories, Product type, Brand/manufacturer and Release year. Technical specifications remain available in product details. Dealer selection and bid routing continue to use those category/item IDs. Counts include configurations and regional product variants; distinct brand/model-code counts are also reported and are not guaranteed to represent distinct marketing model families.

For current appliance counts, source coverage and the full household-index result, see [HOUSEHOLD_PRODUCTS_REPORT.md](HOUSEHOLD_PRODUCTS_REPORT.md) and [ICECAT_DATA_REPORT.md](ICECAT_DATA_REPORT.md). Index imports stream files to disk with a 512 MiB limit, distribute discovery attempts across item types, and count new/updated records toward the import limit. Unchanged records do not consume that limit. Remote index metadata is checked on each import so scheduled runs do not blindly reuse a day-old index.
