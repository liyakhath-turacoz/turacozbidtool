# Catalogue search

Search uses the Tantivy Rust engine through the pinned Python package in `backend/requirements.txt`. No separate server, Cargo build or per-query matcher executable is required.

Run `python backend/scripts/ingest_india_catalog.py search-index` from the repository root to rebuild. The API also opens or rebuilds the index during startup and checks for catalogue changes while serving requests.

Generated disk indexes are private runtime data under `indexes/` and are excluded from Git. Generation switching preserves concurrent readers. Each build uses one writer thread with a 16 MB writer heap; that is a writer setting, not a limit on total process memory. Back up the database and catalogue bundle, not the disposable index.

The index supports typo/prefix matching, common English and Hinglish aliases, type/brand/year/specification filters, and model grouping. Bids and carts continue to use the exact variant product ID. SQL rechecks product visibility when search results are loaded.
