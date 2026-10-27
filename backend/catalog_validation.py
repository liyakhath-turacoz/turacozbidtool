"""Fail closed before replacing the visible, India-only store catalogue."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

try:
    from .product_identity import norm_brand, norm_text
except ImportError:  # direct-script import compatibility
    from product_identity import norm_brand, norm_text


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
        status = row.get('verification_status')
        is_icecat_listing = False
        if status == 'icecat_content_india_listing_price_image_verified':
            content_host = (urlparse(row.get('product_source_url', '')).hostname or '').lower()
            listing_url = row.get('product_url', '')
            listing_host = (urlparse(listing_url).hostname or '').lower()
            is_icecat_listing = (
                content_host == 'data.icecat.biz' and
                listing_host and listing_host != 'data.icecat.biz' and
                row.get('price_source_url') == listing_url
            )
        if (row.get('price_currency') != 'INR' or row.get('price_market') != 'India' or
                not (status == 'india_store_listing_image_verified' or is_icecat_listing)):
            raise ValueError(f'Unverified India product listing: {name}')
        try:
            if not Decimal(row['official_price']).is_finite() or Decimal(row['official_price']) <= 0:
                raise ValueError('non-positive or non-finite price')
            checked = date.fromisoformat(row['collected_on'])
            if not 0 <= (today - checked).days <= 30:
                raise ValueError('India product-page evidence is stale or future-dated')
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
        # Preserve meaningful model punctuation: ``Pro`` and ``Pro+`` are
        # different phone models, while ordinary spacing/punctuation changes
        # still collapse through the shared identity normalizer.
        key = (norm_brand(row['brand']), norm_text(name))
        if key in identities:
            raise ValueError(f'Duplicate product: {name}')
        identities.add(key)
