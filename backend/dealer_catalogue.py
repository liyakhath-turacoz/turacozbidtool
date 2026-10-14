"""Dealer product catalogue: reading uploaded files and adding products without ever duplicating one.

A dealer can (a) tick a product that is already in the common database, (b) type a product in by hand, or
(c) upload a CSV or Excel file. Every path ends in ``add_product``, which first looks the product up in the
common database by barcode, part number, model and name. A match links the dealer to the existing product;
only a genuinely new product is created. Products that are merely *similar* are returned for the dealer to
decide, never merged automatically.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

try:
    from . import product_identity as identity
except ImportError:  # run as a plain script
    import product_identity as identity

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 3000
MAX_UNZIPPED_BYTES = 40 * 1024 * 1024
LOCK_NAME = "turacoz_product_catalogue"

FIELD_LIMITS = {"name": 255, "brand": 190, "model": 190, "mpn": 190, "category": 120, "item": 120, "description": 4000, "sku": 120}

# Column headings people actually use, reduced to lower-case letters and digits.
ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "productname", "product", "title", "itemname", "productdescription", "description1"),
    "brand": ("brand", "make", "manufacturer", "company", "brandname"),
    "model": ("model", "modelnumber", "modelno", "modelname", "modelnumberno"),
    "mpn": ("mpn", "partnumber", "partno", "manufacturerpartnumber", "productcode", "itemcode"),
    "gtin": ("gtin", "ean", "upc", "barcode", "ean13", "gtin13", "eancode"),
    "category": ("category", "department", "maincategory", "productcategory"),
    "item": ("item", "subcategory", "producttype", "type", "itemtype", "subcategoryitem"),
    "description": ("description", "details", "about", "notes", "specifications"),
    "sku": ("sku", "yoursku", "shopsku", "internalcode", "stockcode"),
    "price": ("price", "mrp", "yourprice", "sellingprice", "rate", "pricers", "rs"),
}

TEMPLATE_HEADERS = ["Name", "Brand", "Model", "Part number (MPN)", "Barcode (EAN)", "Category", "Item type", "Description", "Your SKU", "Your price (Rs.)"]
TEMPLATE_ROWS = [
    ["Samsung 55 inch 4K Smart TV", "Samsung", "UA55AU7700", "UA55AU7700KLXL", "", "TVs, Video & Home Entertainment", "Televisions", "Crystal 4K UHD, 3 HDMI ports", "TV-SAM-55", "42990"],
    ["Philips Air Fryer 4.1 L", "Philips", "HD9252/90", "", "8710103834012", "Kitchen Appliances", "Air Fryers", "", "", ""],
]


class CatalogueError(Exception):
    """A problem with the whole file (wrong type, too big, unreadable)."""


def template_csv() -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerows(TEMPLATE_ROWS)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Reading files
# ---------------------------------------------------------------------------

def _letters(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _canonical_field(heading: Any) -> str | None:
    """Match a column heading to one of our fields. "Part number (MPN)" matches on the words outside the
    brackets, inside them, or both together."""
    text = str(heading or "")
    candidates = {_letters(text), _letters(re.sub(r"\(.*?\)", "", text))}
    candidates.update(_letters(inner) for inner in re.findall(r"\((.*?)\)", text))
    candidates.discard("")
    for field, names in ALIASES.items():
        if candidates.intersection(names):
            return field
    return None


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference or "")
    index = 0
    for letter in letters.group(0) if letters else "A":
        index = index * 26 + (ord(letter) - 64)
    return index - 1


def _elements(root, name: str):
    """All descendants with this tag, whatever XML namespace the file uses (iter() has no namespace wildcard)."""
    return [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == name]


def read_xlsx(content: bytes) -> list[list[str]]:
    """First worksheet of an .xlsx file as rows of text, using only the standard library."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise CatalogueError("This is not a valid Excel (.xlsx) file.") from error
    with archive:
        if sum(info.file_size for info in archive.infolist()) > MAX_UNZIPPED_BYTES:
            raise CatalogueError("This Excel file is too large to read. Save it as CSV or split it into smaller files.")
        names = set(archive.namelist())
        sheets = sorted(name for name in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
        if not sheets:
            raise CatalogueError("This Excel file has no worksheet to read.")
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in _elements(root, "si"):
                shared.append("".join(node.text or "" for node in _elements(item, "t")))
        rows: list[list[str]] = []
        sheet = ET.fromstring(archive.read(sheets[0]))
        for row in _elements(sheet, "row"):
            cells: dict[int, str] = {}
            for cell in _elements(row, "c"):
                kind = cell.get("t")
                value_node = cell.find("{*}v")
                if kind == "s" and value_node is not None and value_node.text is not None:
                    index = int(value_node.text)
                    text = shared[index] if index < len(shared) else ""
                elif kind == "inlineStr":
                    text = "".join(node.text or "" for node in _elements(cell, "t"))
                else:
                    text = value_node.text if value_node is not None and value_node.text is not None else ""
                    if re.fullmatch(r"-?\d+\.0+", text):
                        text = text.split(".")[0]
                cells[_column_index(cell.get("r", "A1"))] = text
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, "") for i in range(width)])
            if len(rows) > MAX_ROWS + 5:
                break
    return rows


def read_csv(content: bytes) -> list[list[str]]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise CatalogueError("We could not read this file's text. Save it as CSV (UTF-8) and try again.")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return [row for row in csv.reader(io.StringIO(text), dialect)]


def parse_catalogue_file(filename: str, content: bytes) -> list[dict[str, str]]:
    """Rows as dictionaries keyed by our field names. Raises CatalogueError for problems with the file itself."""
    if not content:
        raise CatalogueError("The file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise CatalogueError("The file is larger than 5 MB. Split it into smaller files.")
    lowered = (filename or "").lower()
    if lowered.endswith(".xlsx"):
        table = read_xlsx(content)
    elif lowered.endswith((".csv", ".txt", ".tsv")):
        table = read_csv(content)
    elif lowered.endswith(".xls"):
        raise CatalogueError("Old .xls files are not supported. In Excel choose Save As and pick .xlsx or CSV.")
    else:
        raise CatalogueError("Upload a CSV or Excel (.xlsx) file.")
    table = [row for row in table if any(str(cell).strip() for cell in row)]
    if len(table) < 2:
        raise CatalogueError("The file needs a heading row and at least one product.")
    mapping = {index: _canonical_field(heading) for index, heading in enumerate(table[0])}
    if "name" not in mapping.values():
        raise CatalogueError("We could not find a product name column. Use the headings in the template: Name, Brand, Model, Category.")
    if len(table) - 1 > MAX_ROWS:
        raise CatalogueError(f"The file has more than {MAX_ROWS:,} products. Split it into smaller files.")
    parsed = []
    for number, raw in enumerate(table[1:], start=2):
        row = {"_row": str(number)}
        for index, value in enumerate(raw):
            field = mapping.get(index)
            if field and field not in row:
                row[field] = str(value).strip()
        parsed.append(row)
    return parsed


# ---------------------------------------------------------------------------
# Cleaning one product
# ---------------------------------------------------------------------------

def clean_row(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """(row, errors, warnings). Errors stop this product from being added; warnings are shown but do not."""
    row: dict[str, Any] = {key: " ".join(str(raw.get(key) or "").split()) for key in FIELD_LIMITS}
    row["description"] = str(raw.get("description") or "").strip()
    errors: list[str] = []
    warnings: list[str] = []
    if not row["name"]:
        errors.append("The product name is empty.")
    if not row["brand"]:
        errors.append("The brand is empty. Use the maker's name, for example Samsung.")
    for key, limit in FIELD_LIMITS.items():
        if len(row[key]) > limit:
            errors.append(f"{key.replace('item', 'item type').capitalize()} is longer than {limit} characters.")
    barcodes = identity.gtins(raw.get("gtin"))
    row["gtin"] = ", ".join(barcodes)
    if str(raw.get("gtin") or "").strip() and not barcodes:
        warnings.append("The barcode is not valid, so it was ignored.")
    price_text = str(raw.get("price") or "").strip()
    row["price"] = None
    if price_text:
        try:
            amount = Decimal(re.sub(r"[^0-9.]", "", price_text) or "x")
            if amount < 0 or amount > Decimal("99999999"):
                raise InvalidOperation
            row["price"] = amount.quantize(Decimal("0.01"))
        except InvalidOperation:
            warnings.append("The price is not a number, so it was ignored.")
    return row, errors, warnings


def row_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key, "") for key in ("name", "brand", "model", "mpn", "gtin", "category", "item", "description", "sku")} | {"price": str(row["price"]) if row.get("price") is not None else ""}


# ---------------------------------------------------------------------------
# The common database
# ---------------------------------------------------------------------------

def acquire_lock(cursor) -> None:
    """One catalogue write at a time, so two shops adding the same new product cannot both create it."""
    cursor.execute("SELECT GET_LOCK(%s, 20) AS got", [LOCK_NAME])
    if not cursor.fetchone()["got"]:
        raise CatalogueError("The catalogue is busy. Please try again in a moment.")


def release_lock(cursor) -> None:
    cursor.execute("SELECT RELEASE_LOCK(%s)", [LOCK_NAME])
    cursor.fetchone()


@contextmanager
def catalogue_lock(cursor):
    """Hold the catalogue write lock for a block, and always give it back, even when an error is raised."""
    acquire_lock(cursor)
    try:
        yield
    finally:
        try:
            release_lock(cursor)
        except Exception:  # the connection may already be broken; the lock dies with it
            pass


def register_identities(cursor, product_id: str, product: dict[str, Any]) -> list[str]:
    """Claim this product's identity keys. Returns the keys that already belonged to a different product."""
    taken = []
    for kind, key in identity.identity_keys(product.get("name"), product.get("brand"), product.get("model"), product.get("mpn"), product.get("gtin")):
        cursor.execute(
            "INSERT IGNORE INTO product_identities (identity_key, product_id, kind, created_at) VALUES (%s, %s, %s, NOW())",
            [key, product_id, kind],
        )
        if cursor.rowcount == 0:
            cursor.execute("SELECT product_id FROM product_identities WHERE identity_key=%s", [key])
            owner = cursor.fetchone()
            if owner and owner["product_id"] != product_id:
                taken.append(key)
    return taken


def sync_identities(cursor) -> int:
    """Register keys for any product that has none yet (imports and older products), so they are matched too.
    Keys written under an older version of the matching rules are removed first, so they are rebuilt."""
    prefixes = identity.current_prefixes()
    cursor.execute(
        f"DELETE FROM product_identities WHERE SUBSTRING_INDEX(identity_key, ':', 1) NOT IN ({','.join(['%s'] * len(prefixes))})",
        list(prefixes),
    )
    cursor.execute(
        """
        SELECT p.id, p.name, p.brand, p.model, p.mpn, p.gtin FROM products p
        WHERE p.deleted_at IS NULL AND NOT EXISTS (SELECT 1 FROM product_identities pi WHERE pi.product_id = p.id)
        """
    )
    count = 0
    for product in cursor.fetchall():
        register_identities(cursor, product["id"], product)
        count += 1
    return count


def find_exact(cursor, row: dict[str, Any]) -> dict[str, Any] | None:
    keys = identity.identity_keys(row.get("name"), row.get("brand"), row.get("model"), row.get("mpn"), row.get("gtin"))
    if not keys:
        return None
    placeholders = ",".join(["%s"] * len(keys))
    cursor.execute(
        f"""
        SELECT pi.identity_key, pi.kind, p.id, p.name, p.brand, p.model, p.status, p.deleted_at
        FROM product_identities pi JOIN products p ON p.id = pi.product_id
        WHERE pi.identity_key IN ({placeholders})
        """,
        [key for _, key in keys],
    )
    found = {row_["identity_key"]: row_ for row_ in cursor.fetchall()}
    for kind, key in keys:  # strongest key first
        if key in found:
            hit = found[key]
            return {"id": hit["id"], "name": hit["name"], "brand": hit["brand"], "model": hit["model"], "matched_by": kind, "active": hit["status"] == "active" and hit["deleted_at"] is None}
    return None


def find_similar(cursor, row: dict[str, Any]) -> list[dict[str, Any]]:
    brand = row.get("brand") or ""
    first_word = (identity.norm_text(brand).split() or [""])[0]
    if len(first_word) < 2:
        return []
    cursor.execute(
        "SELECT id, name, brand, model FROM products WHERE deleted_at IS NULL AND status='active' AND brand LIKE %s LIMIT 800",
        [first_word + "%"],
    )
    same_brand = [p for p in cursor.fetchall() if identity.norm_brand(p["brand"]) == identity.norm_brand(brand)]
    return identity.similar_products(row, same_brand, threshold=0.7)


def resolve_taxonomy(cursor, category: str, item: str) -> tuple[str | None, str | None, str | None]:
    if not category:
        return None, None, "Choose a category for this new product."
    cursor.execute("SELECT id, name, parent_id FROM categories WHERE status='active' AND deleted_at IS NULL")
    rows = cursor.fetchall()
    wanted = identity.norm_text(category)
    parents = [r for r in rows if r["parent_id"] is None and identity.norm_text(r["name"]) == wanted]
    if not parents:
        return None, None, f"We could not find the category “{category}”. Use a category name from the list."
    parent = parents[0]
    if not item:
        return parent["id"], None, None
    children = [r for r in rows if r["parent_id"] == parent["id"] and identity.norm_text(r["name"]) == identity.norm_text(item)]
    if not children:
        return None, None, f"“{item}” is not an item type under {parent['name']}. Use an item type from the list."
    return parent["id"], children[0]["id"], None


def link_dealer(cursor, dealer_id: str, product_id: str, source: str, sku: str, price: Any) -> str:
    cursor.execute("SELECT 1 FROM dealer_products WHERE dealer_id=%s AND product_id=%s", [dealer_id, product_id])
    exists = cursor.fetchone() is not None
    if exists:
        cursor.execute(
            "UPDATE dealer_products SET dealer_sku=COALESCE(NULLIF(%s,''), dealer_sku), dealer_price=COALESCE(%s, dealer_price), updated_at=NOW() WHERE dealer_id=%s AND product_id=%s",
            [sku, price, dealer_id, product_id],
        )
        return "already_listed"
    cursor.execute(
        "INSERT INTO dealer_products (dealer_id, product_id, source, dealer_sku, dealer_price, created_at, updated_at) VALUES (%s, %s, %s, NULLIF(%s,''), %s, NOW(), NOW())",
        [dealer_id, product_id, source, sku, price],
    )
    return "linked"


def create_product(cursor, dealer_id: str, row: dict[str, Any], category_id: str, item_id: str | None, new_id: Callable[[], str]) -> str:
    product_id = new_id()
    first_barcode = (row.get("gtin") or "").split(",")[0].strip() or None
    cursor.execute(
        """
        INSERT INTO products
          (id, category_id, subcategory_id, name, brand, manufacturer, model, source, source_product_id, mpn, gtin, description,
           verification_status, status, catalog_visible, catalog_added_at, created_by, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NULLIF(%s,''), 'dealer', %s, NULLIF(%s,''), %s, NULLIF(%s,''),
                'dealer_added', 'active', TRUE, CURDATE(), %s, NOW(), NOW())
        """,
        [product_id, category_id, item_id, row["name"], row["brand"], row["brand"], row.get("model", ""), product_id,
         row.get("mpn", ""), first_barcode, row.get("description", ""), dealer_id],
    )
    taken = register_identities(cursor, product_id, row)
    if taken:
        # Another product owns one of the keys (a race or an older duplicate). Never keep two products for one key.
        raise CatalogueError("This product was just added by someone else. Try again and it will be matched.")
    return product_id


def add_product(cursor, dealer_id: str, raw: dict[str, Any], source: str, new_id: Callable[[], str], resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    """Add one product to the dealer's list. Returns {status, ...}; status is one of
    created, linked, already_listed, review, error."""
    row, errors, warnings = clean_row(raw)
    base: dict[str, Any] = {"row": raw.get("_row"), "input": row_summary(row), "warnings": warnings}
    resolution = resolution or {}

    if resolution.get("action") == "link" and resolution.get("product_id"):
        cursor.execute("SELECT id, name, brand, model FROM products WHERE id=%s AND status='active' AND deleted_at IS NULL", [resolution["product_id"]])
        product = cursor.fetchone()
        if not product:
            return {**base, "status": "error", "message": "That product is no longer in the catalogue."}
        status = link_dealer(cursor, dealer_id, product["id"], source, row["sku"], row["price"])
        return {**base, "status": status, "product": product}

    if errors:
        return {**base, "status": "error", "message": " ".join(errors)}

    match = find_exact(cursor, row)
    if match:
        if not match["active"]:
            return {**base, "status": "error", "message": f"“{match['name']}” has been withdrawn from the catalogue."}
        status = link_dealer(cursor, dealer_id, match["id"], source, row["sku"], row["price"])
        return {**base, "status": status, "matched_by": match["matched_by"], "product": {k: match[k] for k in ("id", "name", "brand", "model")}}

    if resolution.get("action") != "create":
        similar = find_similar(cursor, row)
        if similar:
            return {**base, "status": "review", "candidates": [{k: c[k] for k in ("id", "name", "brand", "model", "score")} for c in similar]}

    category_id, item_id, problem = resolve_taxonomy(cursor, row["category"], row["item"])
    if problem:
        return {**base, "status": "error", "message": problem}
    product_id = create_product(cursor, dealer_id, row, category_id, item_id, new_id)
    link_dealer(cursor, dealer_id, product_id, source, row["sku"], row["price"])
    return {**base, "status": "created", "product": {"id": product_id, "name": row["name"], "brand": row["brand"], "model": row["model"]}}
