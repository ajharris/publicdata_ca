# publicdata_ca
publicdata_ca is a lightweight Python package for discovering, resolving, and downloading Canadian public datasets. It automates StatsCan table retrieval, handles CMHC landing-page churn, enforces reproducible file layouts, and generates manifests so downstream analyses fail fast when data is missing.

## Key Features

### CMHC Landing Page Resolver
The CMHC landing page resolver now includes advanced URL resolution with:
- **Ranking**: Automatically prioritizes candidates based on file format (XLSX > CSV > XLS > ZIP), URL structure, and other quality indicators
- **Validation**: Checks URLs to reject HTML responses and verify actual file types before download
- **Robust extraction**: Handles various HTML structures and link patterns on CMHC websites
- **Caching**: Caches resolved URLs to reduce churn and make refresh runs stable

Example usage:
```python
from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page

# Resolve with validation and caching (default)
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page')
for asset in assets:
    print(f"{asset['title']}: {asset['url']} (rank: {asset['rank']})")
    
# Disable validation for faster resolution
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page', validate=False)

# Disable caching to always fetch fresh URLs
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page', use_cache=False)
```

#### URL Caching
Resolved CMHC URLs are automatically cached in `publicdata_ca/.cache/` to reduce unnecessary HTTP requests and ensure stability across runs. The cache:
- Stores resolved URLs per landing page in JSON format
- Validates cached URLs before use (checks if they still return data files)
- Automatically refreshes when cached URLs become invalid
- Can be disabled with `use_cache=False` parameter
- Can be cleared using the `clear_cache()` function from `publicdata_ca.url_cache`

## Package layout

- `publicdata_ca/catalog.py` — in-memory catalog for registering and searching dataset metadata.
- `publicdata_ca/datasets.py` — curated dataset definitions, pandas helpers, and the `refresh_datasets()` function for automated downloads.
- `publicdata_ca/providers/` — provider integrations such as StatsCan table metadata and CMHC landing-page handling.
- `publicdata_ca/resolvers/` — HTML scrapers that translate landing pages into direct asset URLs.
- `publicdata_ca/url_cache.py` — URL caching utilities for CMHC resolved URLs.
- `publicdata_ca/manifest.py` — utilities for building and validating download manifests.
- `tests/` — pytest suite covering the high-level catalog and manifest flows.

## Automated dataset refresh

The `refresh_datasets()` function provides automated downloading of datasets from the catalog. It iterates through datasets, downloads missing files, and returns a detailed report as a pandas DataFrame.

```python
from publicdata_ca import refresh_datasets, DEFAULT_DATASETS

# Refresh all default datasets
report = refresh_datasets()
print(report[['dataset', 'provider', 'result', 'notes']])

# Refresh only StatsCan datasets
statcan_only = [d for d in DEFAULT_DATASETS if d.provider == 'statcan']
report = refresh_datasets(datasets=statcan_only)

# Force re-download even if files exist
report = refresh_datasets(force_download=True)
```

The function returns a DataFrame with columns:
- `dataset`: Dataset identifier
- `provider`: Provider name (statcan, cmhc)
- `target_file`: Target file path
- `result`: Status (exists, downloaded, error, manual_required, etc.)
- `notes`: Additional information about the result
- `run_started_utc`: Timestamp when the refresh started

## Editable install

1. Create a virtual environment (Python 3.9+): `python -m venv .venv`
2. Activate it: `source .venv/bin/activate`
3. Install the package in editable mode with dev extras: `python -m pip install -e ".[dev]"`

This installs the `publicdata` console script, making CLI commands available in your shell.

## Command-Line Interface

The `publicdata` CLI provides several commands for working with Canadian public datasets:

### Refresh all datasets

Download or update all datasets in the catalog:

```bash
# Refresh all datasets
publicdata refresh

# Refresh only StatsCan datasets
publicdata refresh --provider statcan

# Force re-download even if files exist
publicdata refresh --force

# Show detailed results for all datasets
publicdata refresh --verbose

# Create a manifest file after refresh
publicdata refresh --manifest
```

### Fetch a specific dataset

Download a specific dataset by provider and ID:

```bash
# Download a StatsCan table
publicdata fetch statcan 14-10-0287-01

# Download a CMHC dataset with manifest
publicdata fetch cmhc https://www.cmhc-schl.gc.ca/data-page --manifest
```

### Search for datasets

Search the catalog by keyword:

```bash
# Search all providers
publicdata search "housing"

# Search only StatsCan
publicdata search "employment" --provider statcan
```

### Manage manifests

Create or validate data manifests:

```bash
# Create a manifest
publicdata manifest create --output ./data

# Validate a manifest
publicdata manifest validate --manifest-file ./data/manifest.json
```

## Running tests

Run the pytest suite from the project root:

```bash
pytest
```

You can also use `pytest -k catalog` to focus on a subset of tests while iterating on specific features.
