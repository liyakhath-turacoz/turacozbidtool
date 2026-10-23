"""Fail closed before replacing the visible, India-only store catalogue."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo


def validate_snapshot(rows, image_directory: Path, today=None):
    today = today or datetime.now(ZoneInfo('Asia/Kolkata')).date()
    if not rows:
        raise ValueError('Refusing to replace the catalogue with an empty snapshot')
    identities = set()
    for row in rows:
        name = row.get('product_name', '')
        required = ('product_name', 'brand', 'model', 'department', 'subcategory', 'description', 'product_url', 'product_source_url', 'price_source_url')
        if any(not str(row.get(k) or '').strip() for k in required):
            raise ValueError(f'Incomplete product: {name}')
        if row.get('price_currency') != 'INR' or row.get('price_market') != 'India' or row.get('verification_status') != 'india_store_in_stock_image_verified':
            raise ValueError(f'Unverified India inventory: {name}')
        try:
            if not Decimal(row['official_price']).is_finite() or Decimal(row['official_price']) <= 0:
                raise ValueError('non-positive or non-finite price')
            checked = date.fromisoformat(row['collected_on'])
            if not 0 <= (today - checked).days <= 7:
                raise ValueError('inventory evidence is older than seven days or future-dated')
            specs = json.loads(row['specifications_json'])
            if not isinstance(specs, dict) or len(specs) < 2:
                raise ValueError('missing technical details')
        except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'Invalid product {name}: {exc}') from exc
        image = row.get('image_url', '')
        if not re.fullmatch(r'/catalog-images/[0-9a-f]{24}\.webp', image):
            raise ValueError(f'Unverified or unsafe image path: {name}')
        path = image_directory / image.rsplit('/', 1)[1]
        if not path.is_file() or path.stat().st_size < 500:
            raise ValueError(f'Missing downloaded product photo: {name}')
        key = (row['brand'].casefold(), re.sub(r'\W+', '', name).casefold())
        if key in identities:
            raise ValueError(f'Duplicate product: {name}')
        identities.add(key)
