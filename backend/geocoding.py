"""Cached, paced requests to the configured Nominatim-compatible geocoder."""

from collections import OrderedDict
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException

_lock = threading.Lock()
_cache = OrderedDict()
_last_request = 0.0


def lookup(kind: str, params: dict):
    global _last_request
    key = (kind, urllib.parse.urlencode(params))
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < 86400:
            _cache.move_to_end(key)
            return cached[1]
        delay = 1.05 - (time.monotonic() - _last_request)
        if delay > 0:
            time.sleep(delay)
        _last_request = time.monotonic()
        base = os.getenv("TURACOZ_GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")
        request = urllib.request.Request(
            f"{base}/{kind}?{key[1]}",
            headers={"User-Agent": "TuracozBidTool/1.0 (marketplace location picker)", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                result = json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="Location lookup is unavailable. Try again, or confirm your pin and enter the address manually.") from exc
        _cache[key] = (time.monotonic(), result)
        _cache.move_to_end(key)
        while len(_cache) > 256:
            _cache.popitem(last=False)
        return result


def search(query: str):
    result = lookup("search", {"q": query, "format": "json", "limit": 5, "addressdetails": 1})
    return result if isinstance(result, list) else []


def reverse(latitude: float, longitude: float):
    result = lookup("reverse", {"lat": latitude, "lon": longitude, "format": "json", "zoom": 18, "addressdetails": 1})
    if not isinstance(result, dict) or result.get("error"):
        raise HTTPException(status_code=404, detail="No street address was found for this pin. Enter the address manually.")
    return result
