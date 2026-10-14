"""Low-memory fuzzy ranking for catalog searches with no exact SQL matches."""
from __future__ import annotations

import difflib
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_MATCHER = ROOT / "search_engine" / "bin" / ("catalog_matcher.exe" if os.name == "nt" else "catalog_matcher")
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
STOP_WORDS = {
    "a", "an", "and", "any", "best", "buy", "find", "for", "from", "in", "latest",
    "me", "of", "or", "please", "product", "products", "the", "to", "with",
}
SEARCH_ALIASES = {
    "laptop": ("laptop", "notebook", "portable computer"),
    "laptops": ("laptops", "notebooks", "portable computers"),
    "notebook": ("notebook", "laptop", "portable computer"),
    "notebooks": ("notebooks", "laptops", "portable computers"),
    "smartphone": ("smartphone", "mobile phone", "cell phone"),
    "smartphones": ("smartphones", "mobile phones", "cell phones"),
    "phone": ("phone", "mobile", "smartphone"),
    "phones": ("phones", "mobiles", "smartphones"),
    "fridge": ("fridge", "refrigerator"),
    "refrigerator": ("refrigerator", "fridge"),
    "aircon": ("aircon", "air conditioner", "air conditioning"),
    "tv": ("tv", "television"),
    "television": ("television", "tv"),
    "washer": ("washer", "washing machine"),
}
SEARCH_PHRASES = {
    "smart phone": ("smartphone", "mobile phone"),
    "smart phones": ("smartphones", "mobile phones"),
    "cell phone": ("phone", "smartphone"),
    "cell phones": ("phones", "smartphones"),
    "mobile phone": ("mobile", "smartphone"),
    "mobile phones": ("mobiles", "smartphones"),
    "air con": ("aircon", "air conditioner"),
    "air conditioning": ("aircon", "air conditioner"),
}


def _tokens(value: object) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(str(value or "")) if token]


def _query_aliases(query: str) -> list[str]:
    normalized_query = " ".join(query.split())
    aliases = [normalized_query]
    aliases.extend(SEARCH_PHRASES.get(normalized_query.casefold(), ()))
    terms = _tokens(normalized_query)
    if len(terms) == 1:
        aliases.extend(SEARCH_ALIASES.get(terms[0], ()))
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _similarity(query: str, word: str) -> float:
    if query == word:
        return 1.0
    if len(query) >= 3 and word.startswith(query):
        return 0.93
    if len(word) >= 3 and query.startswith(word):
        return 0.86
    if min(len(query), len(word)) < 4 or abs(len(query) - len(word)) > 2:
        return 0.0
    score = difflib.SequenceMatcher(None, query, word).ratio()
    return score if score >= 0.67 else 0.0


def _field_score(query: str, text: object) -> float:
    return max((_similarity(query, token) for token in _tokens(text)), default=0.0)


def _score_alias(alias: str, row: dict[str, Any]) -> float:
    terms = [term for term in _tokens(alias) if term not in STOP_WORDS]
    if not terms:
        return 0.0
    fields = (
        (row.get("name"), 1.0),
        (row.get("model"), 1.0),
        (row.get("brand"), 0.96),
        (row.get("manufacturer"), 0.94),
        (row.get("category"), 0.91),
        (row.get("item"), 0.91),
        (row.get("searchable_specs"), 0.76),
    )
    values = [max((_field_score(term, field) * weight for field, weight in fields), default=0.0) for term in terms]
    matched = sum(value >= 0.64 for value in values)
    minimum_matches = (len(terms) * 2 + 2) // 3
    if matched < minimum_matches:
        return 0.0
    return sum(values) / len(values)


def _python_rank(query: str, rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
    aliases = _query_aliases(query)
    ranked = []
    for row in rows:
        score = max((_score_alias(alias, row) for alias in aliases), default=0.0)
        if score >= 0.64:
            ranked.append((row, score))
    return sorted(ranked, key=lambda pair: (-pair[1], str(pair[0].get("id", ""))))


def rank_catalog_rows(query: str, rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
    """Rank a small catalog candidate set, preferring the compiled Rust matcher."""
    if not rows or not query.strip():
        return []
    matcher = Path(os.getenv("TURACOZ_CATALOG_MATCHER", str(DEFAULT_MATCHER)))
    if not matcher.is_file():
        return _python_rank(query, rows)

    aliases = _query_aliases(query)
    payload = [str(len(aliases)), *aliases]
    row_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        record_id = str(row.get("id") or index)
        row_by_id[record_id] = row
        fields = [
            record_id,
            str(row.get("name") or ""),
            str(row.get("brand") or ""),
            str(row.get("manufacturer") or ""),
            str(row.get("model") or ""),
            str(row.get("category") or ""),
            str(row.get("item") or ""),
            str(row.get("searchable_specs") or ""),
        ]
        payload.append("\t".join(value.replace("\t", " ").replace("\r", " ").replace("\n", " ") for value in fields))
    try:
        result = subprocess.run(
            [str(matcher)], input="\n".join(payload) + "\n", text=True, encoding="utf-8", capture_output=True,
            timeout=2.5, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            return _python_rank(query, rows)
        ranked = []
        for line in result.stdout.splitlines():
            record_id, separator, score_text = line.partition("\t")
            if not separator or record_id not in row_by_id:
                continue
            try:
                score = int(score_text) / 10000
            except ValueError:
                continue
            ranked.append((row_by_id[record_id], score))
        return ranked
    except (OSError, subprocess.SubprocessError):
        return _python_rank(query, rows)
