from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRODUCTS_ROOT = ROOT / "products"
DEFAULT_CATEGORY_FILE = Path(__file__).with_name("catalog_categories.json")
INDEX_URL = "https://data.icecat.biz/export/freexml/EN/files.index.csv.gz"
API_URL = "https://live.icecat.biz/api"
MIB = 1024 * 1024


def text(value: Any) -> str:
    return str(value or "").strip()


def localized_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return text(value.get("Value") or value.get("value") or value.get("_"))
    if isinstance(value, list):
        return ", ".join(filter(None, (localized_value(item) for item in value)))
    return text(value)


def parse_icecat_date(value: Any) -> date | None:
    raw = text(value)
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    for size, pattern in ((8, "%Y%m%d"), (6, "%Y%m")):
        if len(digits) >= size:
            try:
                return datetime.strptime(digits[:size], pattern).date()
            except ValueError:
                pass
    for pattern in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(raw[: len(pattern)], pattern).date()
        except ValueError:
            pass
    return None


def three_year_cutoff(today: date | None = None) -> date:
    today = today or date.today()
    try:
        return today.replace(year=today.year - 3)
    except ValueError:
        return today.replace(year=today.year - 3, day=28)


def safe_filename(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(filter(None, cleaned.split("-"))) or "uncategorized"


@dataclass(frozen=True)
class Candidate:
    category: str
    category_id: int
    product_id: int
    added: str
    updated: str
    quality: str
    product_view: int


class RateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        self.interval = 1.0 / max(requests_per_second, 1.0)
        self.lock = threading.Lock()
        self.next_time = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(self.next_time - now, 0.0)
            self.next_time = max(now, self.next_time) + self.interval
        if delay:
            time.sleep(delay)


class IcecatCatalogBuilder:
    def __init__(
        self,
        username: str,
        api_token: str,
        products_root: Path = DEFAULT_PRODUCTS_ROOT,
        target_mb: int = 350,
        hard_limit_mb: int = 400,
        workers: int = 24,
        requests_per_second: int = 35,
        max_products: int | None = None,
    ) -> None:
        if not username or not api_token:
            raise ValueError("ICECAT_USERNAME and ICECAT_API_TOKEN are required")
        if target_mb <= 0 or hard_limit_mb < target_mb:
            raise ValueError("The hard limit must be greater than or equal to the target")
        self.username = username
        self.api_token = api_token
        self.products_root = products_root.resolve()
        self.target_bytes = target_mb * MIB
        self.hard_limit_bytes = hard_limit_mb * MIB
        self.workers = max(1, min(workers, 64))
        self.max_products = max_products
        self.rate_limiter = RateLimiter(requests_per_second)
        self.cutoff = three_year_cutoff()
        self.categories: dict[str, list[int]] = json.loads(DEFAULT_CATEGORY_FILE.read_text(encoding="utf-8"))
        self.category_by_id = {
            int(category_id): category
            for category, category_ids in self.categories.items()
            for category_id in category_ids
        }
        self.tmp_root = self.products_root / "tmp"
        self.data_root = self.products_root / "data"
        self.reports_root = self.products_root / "reports"
        self.candidate_db = self.tmp_root / "candidates.sqlite3"
        self.state_path = self.products_root / "catalog-state.json"
        self.failures_path = self.reports_root / "failures.jsonl"

    def prepare(self, resume: bool) -> None:
        self.products_root.mkdir(parents=True, exist_ok=True)
        if not resume:
            for path in (self.data_root, self.reports_root, self.tmp_root):
                if path.exists():
                    shutil.rmtree(path)
            for path in (self.state_path, self.products_root / "manifest.json"):
                if path.exists():
                    path.unlink()
        self.tmp_root.mkdir(parents=True, exist_ok=True)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.reports_root.mkdir(parents=True, exist_ok=True)

    def request(self, url: str, timeout: int = 90) -> urllib.response.addinfourl:
        self.rate_limiter.wait()
        request = urllib.request.Request(
            url,
            headers={
                "api-token": self.api_token,
                "User-Agent": "TuracozCatalogBuilder/1.0",
                "Accept-Encoding": "identity",
            },
        )
        return urllib.request.urlopen(request, timeout=timeout)

    def discover_candidates(self) -> dict[str, int]:
        if self.candidate_db.exists():
            conn = sqlite3.connect(self.candidate_db)
            try:
                return dict(conn.execute("SELECT category, COUNT(*) FROM candidates GROUP BY category"))
            finally:
                conn.close()

        print(f"Downloading and filtering Icecat index; freshness cutoff is {self.cutoff.isoformat()}...")
        conn = sqlite3.connect(self.candidate_db)
        try:
            conn.execute("PRAGMA journal_mode=OFF")
            conn.execute("PRAGMA synchronous=OFF")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute(
                """
                CREATE TABLE candidates (
                  category TEXT NOT NULL,
                  category_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  added TEXT NOT NULL,
                  updated TEXT NOT NULL,
                  quality TEXT NOT NULL,
                  product_view INTEGER NOT NULL,
                  PRIMARY KEY (category, product_id)
                ) WITHOUT ROWID
                """
            )
            batch: list[tuple[Any, ...]] = []
            with self.request(INDEX_URL, timeout=180) as raw:
                with gzip.GzipFile(fileobj=raw) as gz:
                    with io.TextIOWrapper(gz, encoding="utf-8-sig", errors="replace", newline="") as stream:
                        for row in csv.DictReader(stream, delimiter="\t"):
                            category_id_raw = text(row.get("catid"))
                            if not category_id_raw.isdigit():
                                continue
                            category_id = int(category_id_raw)
                            category = self.category_by_id.get(category_id)
                            if not category or text(row.get("on_market")) != "1":
                                continue
                            quality = text(row.get("quality")).upper()
                            if quality == "REMOVED":
                                continue
                            added_date = parse_icecat_date(row.get("Date_Added"))
                            if not added_date or added_date < self.cutoff:
                                continue
                            product_id = text(row.get("product_id"))
                            if not product_id.isdigit():
                                continue
                            try:
                                product_view = int(text(row.get("product_view")) or 0)
                            except ValueError:
                                product_view = 0
                            batch.append(
                                (
                                    category,
                                    category_id,
                                    int(product_id),
                                    added_date.isoformat(),
                                    text(row.get("updated")),
                                    quality,
                                    product_view,
                                )
                            )
                            if len(batch) >= 25_000:
                                conn.executemany(
                                    """
                                    INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(category, product_id) DO UPDATE SET
                                      category_id=excluded.category_id,
                                      added=MAX(added, excluded.added),
                                      updated=MAX(updated, excluded.updated),
                                      quality=CASE WHEN quality='ICECAT' THEN quality ELSE excluded.quality END,
                                      product_view=MAX(product_view, excluded.product_view)
                                    """,
                                    batch,
                                )
                                conn.commit()
                                batch.clear()
                        if batch:
                            conn.executemany(
                                "INSERT OR IGNORE INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)",
                                batch,
                            )
                            conn.commit()
            conn.execute(
                "CREATE INDEX idx_candidate_rank ON candidates(category, quality, updated DESC, product_view DESC)"
            )
            conn.commit()
            counts = dict(conn.execute("SELECT category, COUNT(*) FROM candidates GROUP BY category"))
            print(f"Found {sum(counts.values()):,} unique fresh, on-market candidates.")
            return counts
        finally:
            conn.close()

    def load_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {
            "version": 1,
            "cutoff": self.cutoff.isoformat(),
            "offsets": {category: 0 for category in self.categories},
            "counts": {category: 0 for category in self.categories},
            "failures": 0,
            "rejected_old": 0,
            "rejected_discontinued": 0,
            "bytes": self.current_bundle_bytes(),
        }

    def save_state(self, state: dict[str, Any]) -> None:
        content = json.dumps(state, indent=2, sort_keys=True)
        last_error: OSError | None = None
        for attempt in range(6):
            temporary = self.products_root / (
                f".catalog-state-{os.getpid()}-{threading.get_ident()}-{time.time_ns()}.tmp"
            )
            try:
                temporary.write_text(content, encoding="utf-8")
                os.replace(temporary, self.state_path)
                return
            except OSError as exc:
                last_error = exc
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                time.sleep(0.1 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def candidates_batch(
        self, conn: sqlite3.Connection, state: dict[str, Any], batch_per_category: int = 8
    ) -> list[Candidate]:
        batch: list[Candidate] = []
        for category in self.categories:
            offset = int(state["offsets"].get(category, 0))
            rows = conn.execute(
                """
                SELECT category, category_id, product_id, added, updated, quality, product_view
                FROM candidates
                WHERE category=?
                ORDER BY CASE quality WHEN 'ICECAT' THEN 0 ELSE 1 END,
                         updated DESC, product_view DESC, product_id DESC
                LIMIT ? OFFSET ?
                """,
                (category, batch_per_category, offset),
            ).fetchall()
            batch.extend(Candidate(*row) for row in rows)
            state["offsets"][category] = offset + len(rows)
        return batch

    def fetch_product(self, candidate: Candidate) -> tuple[Candidate, dict[str, Any] | None, str | None]:
        query = urllib.parse.urlencode(
            {
                "lang": "en",
                "shopname": self.username,
                "icecat_id": candidate.product_id,
                "content": "",
                "relationslimit": "1",
            }
        )
        last_error = ""
        for attempt in range(4):
            try:
                with self.request(f"{API_URL}?{query}") as response:
                    payload = json.load(response)
                if payload.get("msg") != "OK" or not payload.get("data"):
                    return candidate, None, text(payload.get("msg") or "empty response")
                return candidate, self.normalize(candidate, payload["data"]), None
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code}"
                if exc.code in {400, 401, 403, 404}:
                    break
            except Exception as exc:  # transient network/JSON failures are retried
                last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(min(2**attempt, 8))
        return candidate, None, last_error

    def normalize(self, candidate: Candidate, data: dict[str, Any]) -> dict[str, Any]:
        general = data.get("GeneralInfo") or {}
        release_date = parse_icecat_date(general.get("ReleaseDate"))
        effective_date = release_date or parse_icecat_date(candidate.added)
        end_of_life = parse_icecat_date(general.get("EndOfLifeDate"))

        technical_groups: list[dict[str, Any]] = []
        software_groups: list[dict[str, Any]] = []
        highlights: dict[str, str] = {}
        for group in data.get("FeaturesGroups") or []:
            feature_group = group.get("FeatureGroup") or {}
            group_name = localized_value(feature_group.get("Name")) or "Other"
            normalized_features = []
            for feature in group.get("Features") or []:
                definition = feature.get("Feature") or {}
                measure = definition.get("Measure") or {}
                value = text(
                    feature.get("PresentationValue")
                    or feature.get("LocalValue")
                    or feature.get("Value")
                    or feature.get("RawValue")
                )
                name = localized_value(definition.get("Name"))
                if not name or not value:
                    continue
                normalized = {
                    "id": text(definition.get("ID") or feature.get("CategoryFeatureId")),
                    "name": name,
                    "value": value,
                    "raw_value": text(feature.get("RawValue")),
                    "unit": localized_value((measure.get("Signs") or {})) or text(measure.get("Sign")),
                    "type": text(feature.get("Type")),
                    "description": text(feature.get("Description")),
                    "searchable": text(feature.get("Searchable")) == "1",
                    "sort_order": int(text(feature.get("SortNo")) or 0),
                }
                normalized_features.append(normalized)
                if normalized["searchable"] and len(highlights) < 8:
                    highlights.setdefault(name, value)
            if not normalized_features:
                continue
            normalized_group = {
                "id": text(feature_group.get("ID") or group.get("ID")),
                "name": group_name,
                "sort_order": int(text(group.get("SortNo")) or 0),
                "features": sorted(normalized_features, key=lambda item: item["sort_order"], reverse=True),
            }
            software_terms = ("software", "operating system", "license", "system requirement", "firmware")
            target = software_groups if any(term in group_name.lower() for term in software_terms) else technical_groups
            target.append(normalized_group)

        image = data.get("Image") or {}
        gallery = []
        for asset in data.get("Gallery") or []:
            url = text(asset.get("Pic") or asset.get("Pic500x500") or asset.get("ThumbPic"))
            if url:
                gallery.append(
                    {
                        "url": url,
                        "thumbnail_url": text(asset.get("ThumbPic")),
                        "width": int(text(asset.get("PicWidth")) or 0),
                        "height": int(text(asset.get("PicHeight")) or 0),
                        "is_main": text(asset.get("IsMain")).upper() == "Y",
                        "sort_order": int(text(asset.get("No")) or 0),
                    }
                )

        multimedia = []
        for asset in data.get("Multimedia") or []:
            url = text(asset.get("URL"))
            if url:
                multimedia.append(
                    {
                        "url": url,
                        "type": text(asset.get("Type")),
                        "content_type": text(asset.get("ContentType")),
                        "description": text(asset.get("Description")),
                        "language": text(asset.get("Language")),
                    }
                )

        category_info = general.get("Category") or {}
        description = general.get("Description") or {}
        if isinstance(description, dict):
            description = (
                localized_value(description.get("LongDesc"))
                or localized_value(description.get("ShortDesc"))
                or localized_value(description)
            )

        return {
            "source": "icecat",
            "source_product_id": str(candidate.product_id),
            "source_category_id": str(candidate.category_id),
            "category": "Electronics",
            "subcategory": candidate.category,
            "icecat_category": localized_value(category_info.get("Name")),
            "name": text(general.get("Title") or general.get("ProductName")),
            "brand": text(general.get("Brand")),
            "model": text(general.get("BrandPartCode") or general.get("ProductName")),
            "mpn": text(general.get("BrandPartCode")),
            "gtins": [text(item) for item in (general.get("GTINs") or general.get("GTIN") or []) if text(item)],
            "product_family": localized_value(general.get("ProductFamily")),
            "product_series": localized_value(general.get("ProductSeries")),
            "description": text(description),
            "summary_description": localized_value(general.get("SummaryDescription")),
            "release_date": release_date.isoformat() if release_date else candidate.added,
            "release_year": effective_date.year if effective_date else None,
            "end_of_life_date": end_of_life.isoformat() if end_of_life else "",
            "source_updated_at": candidate.updated,
            "quality": candidate.quality,
            "on_market": True,
            "image_url": text(image.get("HighPic") or image.get("Pic500x500") or image.get("LowPic")),
            "gallery": gallery,
            "multimedia": multimedia,
            "reasons_to_buy": [
                {
                    "title": localized_value(item.get("Title")),
                    "description": localized_value(item.get("Value") or item.get("Description")),
                }
                for item in (data.get("ReasonsToBuy") or [])
            ],
            "highlights": highlights,
            "technical_specifications": sorted(technical_groups, key=lambda item: item["sort_order"]),
            "software_specifications": sorted(software_groups, key=lambda item: item["sort_order"]),
        }

    def current_bundle_bytes(self) -> int:
        if not self.products_root.exists():
            return 0
        total = 0
        for path in self.products_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                path.relative_to(self.tmp_root)
                continue
            except ValueError:
                total += path.stat().st_size
        return total

    def append_record(self, category: str, record: dict[str, Any]) -> int:
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        compressed = gzip.compress(line, compresslevel=6, mtime=0)
        destination = self.data_root / f"{safe_filename(category)}.jsonl.gz"
        with destination.open("ab") as stream:
            stream.write(compressed)
        return len(compressed)

    def log_failure(self, candidate: Candidate, reason: str) -> None:
        with self.failures_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "category": candidate.category,
                        "source_product_id": candidate.product_id,
                        "reason": reason,
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )

    def build(self, resume: bool = False) -> dict[str, Any]:
        self.prepare(resume)
        candidate_counts = self.discover_candidates()
        state = self.load_state()
        conn = sqlite3.connect(self.candidate_db)
        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                while state["bytes"] < self.target_bytes:
                    if self.max_products and sum(state["counts"].values()) >= self.max_products:
                        break
                    candidates = self.candidates_batch(conn, state)
                    if not candidates:
                        break
                    futures = [pool.submit(self.fetch_product, candidate) for candidate in candidates]
                    results = [future.result() for future in as_completed(futures)]
                    results.sort(key=lambda item: (item[0].category, item[0].product_id))
                    for candidate, record, error in results:
                        if error or not record:
                            state["failures"] += 1
                            self.log_failure(candidate, error or "empty normalized record")
                            continue
                        effective_date = parse_icecat_date(record.get("release_date"))
                        if effective_date and effective_date < self.cutoff:
                            state["rejected_old"] += 1
                            continue
                        if record.get("end_of_life_date"):
                            state["rejected_discontinued"] += 1
                            continue
                        compressed = gzip.compress(
                            json.dumps(record, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n",
                            compresslevel=6,
                            mtime=0,
                        )
                        projected = self.current_bundle_bytes() + len(compressed) + 256 * 1024
                        if projected > self.hard_limit_bytes:
                            state["bytes"] = self.current_bundle_bytes()
                            self.save_state(state)
                            return self.finalize(state, candidate_counts, stopped_by="hard_limit")
                        state["bytes"] += self.append_record(candidate.category, record)
                        state["counts"][candidate.category] += 1
                        if self.max_products and sum(state["counts"].values()) >= self.max_products:
                            break
                    state["bytes"] = self.current_bundle_bytes()
                    self.save_state(state)
                    print(
                        f"Saved {sum(state['counts'].values()):,} products; "
                        f"bundle is {state['bytes'] / MIB:.1f} MiB"
                    )
            reason = "target_reached" if state["bytes"] >= self.target_bytes else "candidates_exhausted"
            if self.max_products and sum(state["counts"].values()) >= self.max_products:
                reason = "max_products"
            return self.finalize(state, candidate_counts, stopped_by=reason)
        finally:
            conn.close()

    def finalize(
        self, state: dict[str, Any], candidate_counts: dict[str, int], stopped_by: str
    ) -> dict[str, Any]:
        exact_counts = {category: 0 for category in self.categories}
        seen_product_ids: set[str] = set()
        for path in sorted(self.data_root.glob("*.jsonl.gz")):
            temporary = path.with_suffix(".dedupe.tmp")
            try:
                with gzip.open(path, "rt", encoding="utf-8") as source, temporary.open("wb") as output:
                    try:
                        for line in source:
                            if not line.strip():
                                continue
                            record = json.loads(line)
                            product_id = str(record.get("source_product_id") or "")
                            if not product_id or product_id in seen_product_ids:
                                continue
                            seen_product_ids.add(product_id)
                            category = str(record.get("subcategory") or "")
                            if category in exact_counts:
                                exact_counts[category] += 1
                            output.write(gzip.compress(line.encode("utf-8"), compresslevel=6, mtime=0))
                    except (EOFError, OSError, json.JSONDecodeError):
                        # A killed writer can leave only its final gzip member incomplete.
                        pass
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        state["counts"] = exact_counts
        state["bytes"] = self.current_bundle_bytes()
        self.save_state(state)
        data_files = sorted(self.data_root.glob("*.jsonl.gz"))
        checksums = {}
        for path in data_files:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(MIB), b""):
                    digest.update(chunk)
            checksums[str(path.relative_to(self.products_root)).replace("\\", "/")] = digest.hexdigest()
        manifest = {
            "schema_version": 1,
            "catalog_version": datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            "source": "Open Icecat",
            "language": "en",
            "freshness_cutoff": self.cutoff.isoformat(),
            "filters": {
                "on_market": True,
                "removed": False,
                "maximum_age_years": 3,
                "category_price_policy": "categories generally expected to contain products above INR 15000; individual prices unavailable",
            },
            "target_bytes": self.target_bytes,
            "hard_limit_bytes": self.hard_limit_bytes,
            "stopped_by": stopped_by,
            "product_count": sum(state["counts"].values()),
            "category_counts": state["counts"],
            "candidate_counts": candidate_counts,
            "failure_count": state["failures"],
            "rejected_old": state["rejected_old"],
            "rejected_discontinued": state["rejected_discontinued"],
            "files": checksums,
            "attribution": "Specs Icecat",
            "attribution_url": "https://icecat.biz/",
            "disclaimer": "Product data is supplied by Icecat AS IS.",
        }
        manifest_path = self.products_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        manifest["final_bytes"] = self.current_bundle_bytes()
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        if manifest["final_bytes"] > self.hard_limit_bytes:
            raise RuntimeError("Final products bundle exceeded its hard size limit")
        summary_path = self.reports_root / "summary.json"
        summary_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        print(
            f"Final bundle: {manifest['product_count']:,} products, "
            f"{manifest['final_bytes'] / MIB:.1f} MiB ({stopped_by})."
        )
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the size-capped Turacoz Open Icecat product bundle")
    parser.add_argument("--products-root", type=Path, default=DEFAULT_PRODUCTS_ROOT)
    parser.add_argument("--target-mb", type=int, default=int(os.getenv("ICECAT_PRODUCTS_TARGET_MB", "350")))
    parser.add_argument("--hard-limit-mb", type=int, default=int(os.getenv("ICECAT_PRODUCTS_HARD_LIMIT_MB", "400")))
    parser.add_argument("--workers", type=int, default=int(os.getenv("ICECAT_DOWNLOAD_WORKERS", "24")))
    parser.add_argument("--requests-per-second", type=int, default=int(os.getenv("ICECAT_REQUESTS_PER_SECOND", "35")))
    parser.add_argument("--max-products", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    builder = IcecatCatalogBuilder(
        username=os.getenv("ICECAT_USERNAME", ""),
        api_token=os.getenv("ICECAT_API_TOKEN", ""),
        products_root=args.products_root,
        target_mb=args.target_mb,
        hard_limit_mb=args.hard_limit_mb,
        workers=args.workers,
        requests_per_second=args.requests_per_second,
        max_products=args.max_products,
    )
    builder.build(resume=args.resume)
    if builder.tmp_root.exists():
        shutil.rmtree(builder.tmp_root)


if __name__ == "__main__":
    main()
