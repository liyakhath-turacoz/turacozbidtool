# Catalog search matcher

The buyer catalogue keeps exact and prefix searches in MariaDB. If an exact
query has no results, the backend sends a compact list of candidate names,
brands, categories, models and indexed specifications to this small Rust
matcher. It recovers common misspellings and product wording such as laptop /
notebook without loading a language model or running a search service.

The matcher uses the Rust `strsim` crate's normalized Damerau-Levenshtein
similarity for transposed or mistyped letters. Search aliases handle common
catalog terminology. The fallback is deliberately disabled for explicit RAM
capacity queries so a request for (for example) `16 GB RAM` never returns a
different capacity as a fuzzy match.

On Windows, build the executable with:

```powershell
cd backend/search_engine
.\build.ps1
```

The generated `bin/catalog_matcher.exe` is used automatically. If the binary
is absent or fails to launch, the backend uses its small Python fallback. The
binary handles one query at a time and exits immediately after ranking; it
does not run as a service.

## License

The `catalog-matcher` binary statically includes the `strsim` 0.11.1 crate by Danny Guo, Titus Wormer, and Akash Kurdekar. `strsim` is licensed under MIT; the full notice is in `licenses/strsim-MIT.txt`.
