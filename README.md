# publicdata_ca
publicdata_ca is a lightweight Python package for discovering, resolving, and downloading Canadian public datasets. It automates StatsCan table retrieval, handles CMHC landing-page churn, enforces reproducible file layouts, and generates manifests so downstream analyses fail fast when data is missing.

## Quickstart

Get started quickly with publicdata_ca:

```bash
# Create and activate a virtual environment (Python 3.9+)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in editable mode from source
# (This also installs the 'publicdata' CLI command)
python -m pip install -e ".[dev]"

# Note: Once published to PyPI, you'll be able to install with:
# pip install publicdata-ca
```

**Download a StatsCan table:**
```python
from publicdata_ca.providers.statcan import download_statcan_table

# Download Consumer Price Index data
download_statcan_table("18100004", "./data/raw")
```

**Refresh all datasets using the CLI:**
```bash
publicdata refresh
```

**Or use the Python API:**
```python
from publicdata_ca import refresh_datasets

report = refresh_datasets()
print(report[['dataset', 'provider', 'result', 'notes']])
```

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

### CMHC Failure Modes and Troubleshooting

CMHC landing pages can change frequently, causing download failures. Here's how to diagnose and handle common issues:

#### **Problem: "No files downloaded from landing page"**

**Cause:** The landing page structure changed, or no data file links were found.

**Solutions:**
1. **Inspect the landing page manually** - Visit the URL in a browser to see what changed
2. **Disable caching temporarily** to force fresh resolution:
   ```python
   from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page
   assets = resolve_cmhc_landing_page(url, use_cache=False)
   ```
3. **Clear the cache** if stale URLs are causing issues:
   ```python
   from publicdata_ca.url_cache import clear_cache
   clear_cache(landing_url)  # Clear specific URL cache
   clear_cache()             # Clear all CMHC caches
   ```
4. **Check if the page uses JavaScript** - Some CMHC pages load content dynamically, requiring manual URL extraction

#### **Problem: Landing page returns HTML instead of data file**

**Cause:** The resolver extracted a link that points to another HTML page, not a direct file.

**Solutions:**
1. **Validation is enabled by default** - The resolver will detect and skip HTML responses
2. **Check the resolved assets** to see what was found:
   ```python
   assets = resolve_cmhc_landing_page(url, validate=True)
   for asset in assets:
       print(f"{asset['title']}: {asset['url']} (rank: {asset['rank']}, validated: {asset['validated']})")
   ```
3. **Look for validation errors** in the asset metadata:
   ```python
   if 'validation_error' in asset:
       print(f"Validation failed: {asset['validation_error']}")
   ```

#### **Problem: Download succeeds but gets wrong file format**

**Cause:** Multiple file formats available; ranking selected a lower-quality format.

**Solutions:**
1. **Check asset rankings** - XLSX is ranked highest, followed by CSV, then XLS
2. **Filter by format** in the CMHC provider:
   ```python
   from publicdata_ca.providers.cmhc import download_cmhc_asset
   result = download_cmhc_asset(url, output_dir, asset_filter='xlsx')
   ```
3. **Manually select from resolved assets**:
   ```python
   assets = resolve_cmhc_landing_page(url)
   xlsx_assets = [a for a in assets if a['format'] == 'xlsx']
   ```

#### **Problem: Cache contains outdated URLs**

**Cause:** CMHC updated their file URLs but cache still has old URLs.

**Solutions:**
1. **The cache auto-validates** - If the cached URL returns HTML, it's automatically refreshed
2. **Force refresh by clearing cache**:
   ```bash
   python -c "from publicdata_ca.url_cache import clear_cache; clear_cache()"
   ```
3. **Disable caching during development**:
   ```python
   report = refresh_datasets()  # Uses cache by default
   # To force fresh resolution, modify datasets.py or use direct API
   ```

#### **Problem: "Manual download required" in refresh report**

**Cause:** Dataset has neither `direct_url` nor `page_url` configured.

**Solutions:**
1. **Find the correct URL** - Visit CMHC's website to locate the dataset
2. **Update the dataset definition** in `publicdata_ca/datasets.py`:
   ```python
   Dataset(
       dataset="my_cmhc_dataset",
       provider="cmhc",
       page_url="https://www.cmhc-schl.gc.ca/...",  # Add this
       # ... other fields
   )
   ```
3. **Or provide a direct URL** if known:
   ```python
   Dataset(
       dataset="my_cmhc_dataset",
       provider="cmhc",
       direct_url="https://assets.cmhc-schl.gc.ca/...",  # Direct link to file
       # ... other fields
   )
   ```

#### **Best Practices for CMHC Downloads**

1. **Use caching in production** - Reduces load on CMHC servers and improves reliability
2. **Validate during development** - Set `validate=True` to catch broken links early
3. **Monitor refresh reports** - Check `result` and `notes` columns for issues:
   ```python
   report = refresh_datasets()
   errors = report[report['result'] == 'error']
   if not errors.empty:
       print("Failed downloads:")
       print(errors[['dataset', 'notes']])
   ```
4. **Pin working direct URLs** - If you find a stable Azure blob URL, add it as `direct_url` to skip landing page resolution
5. **Test after CMHC releases** - Major CMHC data releases (e.g., annual reports) often come with website redesigns

## Package layout

- `publicdata_ca/catalog.py` — in-memory catalog for registering and searching dataset metadata.
- `publicdata_ca/datasets.py` — curated dataset definitions, pandas helpers, and the `refresh_datasets()` function for automated downloads.
- `publicdata_ca/providers/` — provider integrations such as StatsCan table metadata and CMHC landing-page handling.
- `publicdata_ca/resolvers/` — HTML scrapers that translate landing pages into direct asset URLs.
- `publicdata_ca/url_cache.py` — URL caching utilities for CMHC resolved URLs.
- `publicdata_ca/manifest.py` — utilities for building and validating download manifests.
- `tests/` — pytest suite covering the high-level catalog and manifest flows.

## Catalog Design

The catalog is built around a strongly-typed `Dataset` dataclass that captures all metadata needed to fetch Canadian public data:

```python
@dataclass
class Dataset:
    dataset: str              # Unique identifier (e.g., "cpi_all_items")
    provider: str             # "statcan" or "cmhc"
    metric: str               # Human-readable description
    pid: str | None           # StatsCan table number (8 digits)
    frequency: str            # "Monthly", "Annual", etc.
    geo_scope: str            # Geographic coverage
    delivery: str             # Download method: "download_statcan_table" or "download_cmhc_asset"
    target_file: Path | None  # Destination path in data/raw
    automation_status: str    # "automatic" or "semi-automatic"
    status_note: str          # Notes about the dataset
    page_url: str | None      # CMHC landing page URL
    direct_url: str | None    # Direct download URL (if available)
```

**Default catalog:** The package ships with a curated catalog (`DEFAULT_DATASETS`) containing essential Canadian datasets like CPI, population estimates, unemployment rates, and CMHC housing data.

**Catalog workflow:**
1. Define datasets in `datasets.py` with all required metadata
2. Use `refresh_datasets()` to download missing files automatically
3. The function routes each dataset to the appropriate provider (StatsCan or CMHC)
4. Returns a pandas DataFrame report with status for each dataset

**Example - inspecting the catalog:**
```python
from publicdata_ca import DEFAULT_DATASETS, build_dataset_catalog

# View the catalog as a DataFrame
catalog_df = build_dataset_catalog()
print(catalog_df[['dataset', 'provider', 'automation_status', 'target_file']])

# Filter StatsCan datasets
statcan_datasets = [d for d in DEFAULT_DATASETS if d.provider == 'statcan']
```

## Automated dataset refresh

The `refresh_datasets()` function provides automated downloading of datasets from the catalog. It iterates through datasets, downloads missing files, and returns a detailed report as a pandas DataFrame.

### Basic Usage

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

### Refresh Workflow

The refresh function follows this workflow for each dataset:

1. **Check if target file exists** - If `skip_existing=True` (default), skip datasets with existing files
2. **Route to appropriate provider**:
   - **StatsCan**: Downloads using table ID via the StatsCan API
   - **CMHC**: Resolves landing page URLs or downloads from direct URLs
3. **Download the file(s)** to the configured `target_file` location
4. **Record the result** - Returns status code and notes for each dataset

**Result codes:**
- `exists` - File already present, skipped
- `downloaded` - Successfully downloaded
- `error` - Download failed (see `notes` for details)
- `manual_required` - No URL configured, manual download needed
- `missing_target` - No `target_file` specified in dataset definition

### Return Value

The function returns a DataFrame with columns:
- `dataset`: Dataset identifier
- `provider`: Provider name (statcan, cmhc)
- `target_file`: Target file path
- `result`: Status (exists, downloaded, error, manual_required, etc.)
- `notes`: Additional information about the result
- `run_started_utc`: Timestamp when the refresh started

### Example - Handling Errors

```python
# Run refresh and check for errors
report = refresh_datasets()

# Filter for failed downloads
errors = report[report['result'] == 'error']
if not errors.empty:
    print(f"\n{len(errors)} datasets failed to download:")
    for idx, row in errors.iterrows():
        print(f"  - {row['dataset']}: {row['notes']}")
    
# Check which datasets need manual intervention
manual = report[report['result'] == 'manual_required']
if not manual.empty:
    print(f"\n{len(manual)} datasets require manual download:")
    for idx, row in manual.iterrows():
        print(f"  - {row['dataset']}: {row['notes']}")
```

### Integration with Manifests

Combine refresh with manifest generation for reproducible workflows:

```python
from publicdata_ca import refresh_datasets, build_manifest_file

# Refresh all datasets
report = refresh_datasets()

# Build manifest from successfully downloaded files
successful = report[report['result'].isin(['downloaded', 'exists'])]
manifest_datasets = [
    {
        'dataset_id': row['dataset'],
        'provider': row['provider'],
        'files': [row['target_file']],
    }
    for _, row in successful.iterrows()
]

manifest_path = build_manifest_file(
    output_dir='./data',
    datasets=manifest_datasets
)
print(f"Manifest created: {manifest_path}")
```

## Installation

### From Source (Editable Install)

1. Clone the repository: `git clone https://github.com/ajharris/publicdata_ca.git`
2. Create a virtual environment (Python 3.9+): `python -m venv .venv`
3. Activate it: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
4. Install the package in editable mode with dev extras: `python -m pip install -e ".[dev]"`

This installs the `publicdata` console script, making CLI commands available in your shell.

### From PyPI (Future)

Once published to PyPI, you'll be able to install with:
```bash
pip install publicdata-ca
```

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
