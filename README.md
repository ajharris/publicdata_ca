# publicdata_ca
publicdata_ca is a lightweight Python package for discovering, resolving, and downloading Canadian public datasets. It automates StatsCan table retrieval, handles CMHC landing-page churn, supports generic CKAN portals for flexible data access, enforces reproducible file layouts, generates manifests so downstream analyses fail fast when data is missing, and provides normalization utilities for standardizing metadata.

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

**Search and download from Open Canada:**
```python
from publicdata_ca.providers import OpenCanadaProvider
from publicdata_ca.provider import DatasetRef

# Search Open Canada portal
provider = OpenCanadaProvider()
results = provider.search('housing', rows=5)

# Download CSV resources from a dataset
ref = DatasetRef(provider='open_canada', id='dataset-id', params={'format': 'CSV'})
provider.fetch(ref, './data/open_canada')
```

**Search and download from any CKAN portal:**
```python
from publicdata_ca.providers import CKANProvider
from publicdata_ca.provider import DatasetRef

# Search a generic CKAN portal
provider = CKANProvider(base_url='https://catalog.data.gov')
results = provider.search('housing', rows=5)

# Download CSV resources from a dataset
ref = DatasetRef(provider='ckan', id='dataset-id', params={'format': 'CSV'})
provider.fetch(ref, './data/ckan')
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

### HTTP Caching with ETag and Last-Modified

The HTTP download utilities support intelligent caching using ETag and Last-Modified headers to avoid re-downloading unchanged files. This feature is particularly beneficial for large datasets.

**How it works:**
1. **First download**: File is downloaded and server's ETag/Last-Modified headers are saved
2. **Subsequent downloads**: Conditional request headers (If-None-Match/If-Modified-Since) are sent
3. **304 Not Modified**: If file hasn't changed, download is skipped entirely
4. **200 OK**: If file changed, new version is downloaded and cache is updated

Example usage:
```python
from publicdata_ca.http import download_file

# Download with caching enabled (default)
download_file(
    'https://example.com/large_dataset.csv',
    './data/dataset.csv',
    use_cache=True  # This is the default
)

# On subsequent runs, if the file hasn't changed on the server,
# the download will be skipped (server returns 304 Not Modified)

# Force re-download without using cache
download_file(
    'https://example.com/large_dataset.csv',
    './data/dataset.csv',
    use_cache=False  # Bypass cache completely
)
```

**Cache metadata storage:**
- Cache metadata is stored alongside downloaded files with `.http_cache.json` extension
- Contains ETag, Last-Modified, source URL, and cache timestamp
- Automatically cleaned up when files are deleted
- Excluded from version control via `.gitignore`

**Benefits:**
- **Bandwidth savings**: Skip downloads when files haven't changed
- **Faster refreshes**: Reduce time for data refresh operations
- **Server-friendly**: Reduces load on data provider servers
- **Automatic**: Works transparently when servers support caching headers

### Unified Metadata Schema and Provenance Tracking

All downloaded files are accompanied by `.meta.json` sidecar files that track provenance information using a unified schema across all data providers. This ensures consistent metadata structure and enables reproducibility.

**Metadata Schema Version 1.0:**
```json
{
  "schema_version": "1.0",
  "file": "data.csv",
  "source_url": "https://example.com/data.csv",
  "downloaded_at": "2024-01-06T18:00:00Z",
  "file_size_bytes": 1024,
  "hash": {
    "algorithm": "sha256",
    "value": "abc123..."
  },
  "content_type": "text/csv",
  "provider": {
    "name": "statcan",
    "specific": {
      "pid": "18100004",
      "table_number": "18-10-0004",
      "title": "Consumer Price Index"
    }
  }
}
```

**Key features:**
- **Schema versioning**: Forward and backward compatibility support
- **Provider standardization**: Consistent structure across StatsCan, CMHC, CKAN, and other providers
- **Integrity verification**: SHA-256 hashes for validating file integrity
- **Provider-specific metadata**: Extensible structure for provider-unique fields

**Example usage:**
```python
from publicdata_ca.provenance import read_provenance_metadata, verify_file_integrity

# Read metadata
metadata = read_provenance_metadata('./data/table.csv')
print(f"Downloaded from: {metadata['source_url']}")
print(f"Provider: {metadata['provider']['name']}")

# Verify file hasn't been modified
if verify_file_integrity('./data/table.csv'):
    print("File integrity verified")
else:
    print("Warning: File has been modified since download")
```

### Run-Level Reports

The `refresh` command generates detailed run reports summarizing what changed, what succeeded, what failed, and why. Reports can be exported in CSV or JSON format for analysis and tracking.

**Export a run report:**
```bash
# Export as CSV (default)
publicdata refresh --report

# Export as JSON
publicdata refresh --report --report-format json

# Specify output path
publicdata refresh --report --report-output ./reports/latest_run.csv
```

**Python API:**
```python
from publicdata_ca.datasets import refresh_datasets, export_run_report

# Run refresh and get report
report = refresh_datasets()

# Export to CSV
export_run_report(report, './reports', format='csv')

# Export to JSON
export_run_report(report, './reports/run.json', format='json')

# Analyze the report
print(report[['dataset', 'provider', 'result', 'notes']])
failures = report[report['result'] == 'error']
print(f"Failed downloads: {len(failures)}")
```

**Report fields:**
- `dataset`: Dataset identifier
- `provider`: Data provider (statcan, cmhc, etc.)
- `target_file`: Path to the downloaded file
- `result`: Status (downloaded, exists, error, manual_required)
- `notes`: Detailed information about the result
- `run_started_utc`: Timestamp when the run started

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
   ```python
   from publicdata_ca.url_cache import clear_cache
   clear_cache()  # Clear all CMHC caches
   ```
3. **Disable caching when calling the resolver directly**:
   ```python
   from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page
   # Force fresh resolution by disabling cache
   assets = resolve_cmhc_landing_page(url, use_cache=False)
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

### Open Canada Provider

The Open Canada provider is a convenience wrapper for accessing the Open Government Canada portal (open.canada.ca). The portal is CKAN-backed, so this provider uses the generic CKAN provider internally with pre-configured URLs.

**Key capabilities:**
- **Simplified API** - No need to specify base URLs repeatedly
- **Search datasets** in the Open Canada portal
- **Resolve resources** by format (CSV, JSON, GeoJSON, XLSX, etc.)
- **Download resources** with automatic format filtering
- **Bilingual support** - Search in English or French

#### Basic Usage

**Search for datasets:**
```python
from publicdata_ca.providers import OpenCanadaProvider

# Initialize provider (base URL is pre-configured)
provider = OpenCanadaProvider()

# Search for datasets
results = provider.search('census', rows=5)
for ref in results:
    print(f"{ref.id}: {ref.metadata['title']}")
    print(f"  Organization: {ref.metadata.get('organization', 'N/A')}")
    print(f"  Formats: {', '.join(ref.metadata['formats'])}")
    print(f"  Tags: {', '.join(ref.tags[:3])}")
```

**Download specific resources by format:**
```python
from publicdata_ca.provider import DatasetRef

# Download only CSV resources from a dataset
ref = DatasetRef(
    provider='open_canada',
    id='census-2021-population',
    params={'format': 'CSV'}  # Filter for CSV only
)

result = provider.fetch(ref, './data/open_canada')
print(f"Downloaded {len(result['files'])} CSV files")
```

**Download all resources:**
```python
# Omit format parameter to download all formats
ref = DatasetRef(
    provider='open_canada',
    id='housing-data',
    params={}  # No format filter
)

result = provider.fetch(ref, './data/open_canada')
for resource in result['resources']:
    print(f"{resource['name']}: {resource['format']}")
```

**Download a specific resource by ID:**
```python
# If you know the specific resource ID
ref = DatasetRef(
    provider='open_canada',
    id='housing-data',
    params={'resource_id': 'abc123-resource-id'}
)

result = provider.fetch(ref, './data/open_canada')
```

#### Search Tips

The Open Canada portal contains thousands of datasets from federal departments and agencies:

```python
provider = OpenCanadaProvider()

# Search by keyword
results = provider.search('census population', rows=10)

# Search by organization using SOLR syntax
results = provider.search('organization:statcan', rows=20)

# Search with tags
results = provider.search('tags:environment', rows=15)

# Boolean operators
results = provider.search('environment AND climate', rows=5)
```

#### Examples

See `examples/open_canada_provider_demo.py` for comprehensive usage examples:

```bash
python examples/open_canada_provider_demo.py
```

You can browse available datasets at: https://open.canada.ca/en/open-data

### CKAN Provider (Generic)

The CKAN provider enables searching and downloading data from any CKAN portal. CKAN (Comprehensive Knowledge Archive Network) is a widely-used open-source data portal platform used by governments and organizations worldwide, including Open Canada, Data.gov, and many provincial/municipal portals.

**Key capabilities:**
- **Search datasets** using the CKAN package_search API
- **Resolve resources** by format (CSV, JSON, GeoJSON, XLSX, etc.)
- **Download resources** with automatic format filtering
- **Multi-portal support** via configurable base URL

#### Basic Usage

**Search for datasets:**
```python
from publicdata_ca.providers import CKANProvider

# Initialize provider with a CKAN portal base URL
provider = CKANProvider(
    name='open_canada',
    base_url='https://open.canada.ca/data'
)

# Search for datasets
results = provider.search('census', rows=5)
for ref in results:
    print(f"{ref.id}: {ref.metadata['title']}")
    print(f"  Formats: {', '.join(ref.metadata['formats'])}")
    print(f"  Tags: {', '.join(ref.tags[:3])}")
```

**Download specific resources by format:**
```python
from publicdata_ca.provider import DatasetRef

# Download only CSV resources from a dataset
ref = DatasetRef(
    provider='open_canada',
    id='census-2021-population',
    params={'format': 'CSV'}  # Filter for CSV only
)

result = provider.fetch(ref, './data/ckan')
print(f"Downloaded {len(result['files'])} CSV files")
```

**Download all resources:**
```python
# Omit format parameter to download all formats
ref = DatasetRef(
    provider='open_canada',
    id='housing-data',
    params={}  # No format filter
)

result = provider.fetch(ref, './data/ckan')
for resource in result['resources']:
    print(f"{resource['name']}: {resource['format']}")
```

**Download a specific resource by ID:**
```python
# If you know the specific resource ID
ref = DatasetRef(
    provider='open_canada',
    id='housing-data',
    params={'resource_id': 'abc123-resource-id'}
)

result = provider.fetch(ref, './data/ckan')
```

#### Using Multiple CKAN Portals

The CKAN provider works with any CKAN instance by configuring the base URL:

```python
# Open Canada
provider_ca = CKANProvider(
    name='open_canada',
    base_url='https://open.canada.ca/data'
)

# Data.gov (US)
provider_us = CKANProvider(
    name='data_gov',
    base_url='https://catalog.data.gov'
)

# BC Data Catalogue
provider_bc = CKANProvider(
    name='bc_data',
    base_url='https://catalogue.data.gov.bc.ca'
)

# Search across different portals
results_ca = provider_ca.search('employment')
results_us = provider_us.search('labor')
results_bc = provider_bc.search('forestry')
```

#### Helper Functions

The CKAN provider also exposes lower-level functions for more control:

```python
from publicdata_ca.providers import (
    search_ckan_datasets,
    get_ckan_package,
    list_ckan_resources,
    download_ckan_resource
)

# Search datasets directly
results = search_ckan_datasets(
    'https://open.canada.ca/data',
    'census',
    rows=10
)

# Get detailed package information
package = get_ckan_package(
    'https://open.canada.ca/data',
    'census-2021'
)

# List resources with format filter
resources = list_ckan_resources(
    'https://open.canada.ca/data',
    'census-2021',
    format_filter='CSV'
)

# Download a specific resource
result = download_ckan_resource(
    'https://example.com/data.csv',
    './data',
    resource_name='census_data',
    resource_format='csv'
)
```

#### Examples

See `examples/ckan_provider_demo.py` for comprehensive usage examples:

```bash
python examples/ckan_provider_demo.py
```

## Package layout

- `publicdata_ca/catalog.py` — in-memory catalog for registering and searching dataset metadata.
- `publicdata_ca/datasets.py` — curated dataset definitions, pandas helpers, and the `refresh_datasets()` function for automated downloads.
- `publicdata_ca/normalize.py` — normalization utilities for standardizing time, geography, frequency, and units across datasets.
- `publicdata_ca/profiles.py` — YAML-based profiles system for multi-project dataset refresh workflows.
- `publicdata_ca/providers/` — provider integrations such as StatsCan, CMHC, Open Canada, CKAN, Socrata, SDMX, and Bank of Canada Valet.
- `publicdata_ca/resolvers/` — HTML scrapers that translate landing pages into direct asset URLs.
- `publicdata_ca/url_cache.py` — URL caching utilities for CMHC resolved URLs.
- `publicdata_ca/http.py` — HTTP utilities with retry logic, streaming downloads, and optional HTTP caching.
- `publicdata_ca/http_cache.py` — HTTP cache metadata management for ETag/Last-Modified headers.
- `publicdata_ca/manifest.py` — utilities for building and validating download manifests.
- `profiles/` — directory containing YAML profile files for organizing dataset collections.
- `tests/` — pytest suite covering the high-level catalog and manifest flows.

## Normalization Utilities

The normalization module provides utilities to standardize common metadata fields across Canadian public datasets while preserving provider-specific information. This enables consistent data processing pipelines across different data sources.

### Key Features

- **Time normalization**: Parse and standardize dates or periods (ISO 8601 format)
- **Frequency normalization**: Standardize frequency labels (monthly, annual, quarterly, etc.)
- **Geographic normalization**: Normalize Canadian geographic labels with standard codes
- **Unit handling**: Standardize measurement units with proper symbols and multipliers

### Basic Usage

```python
from publicdata_ca import (
    normalize_frequency,
    parse_date,
    parse_period,
    normalize_geo,
    normalize_unit,
    normalize_dataset_metadata,
)

# Normalize frequency labels
normalize_frequency('Monthly')  # Returns 'monthly'
normalize_frequency('Q')        # Returns 'quarterly'

# Parse dates to ISO format
parse_date('2023-01')   # Returns '2023-01-01'
parse_date('2023-Q1')   # Returns '2023-01-01'

# Parse periods with frequency
period = parse_period('2023-01', 'monthly')
print(period.start_date)  # '2023-01-01'
print(period.end_date)    # '2023-01-31'

# Normalize geography
geo = normalize_geo('Ontario')
print(geo.code)   # 'CA-ON'
print(geo.level)  # 'province'

# Normalize units
unit = normalize_unit('Thousands of dollars')
print(unit.symbol)      # '$'
print(unit.multiplier)  # 1000.0

# Comprehensive metadata normalization
metadata = {
    'frequency': 'Monthly',
    'geo': 'Ontario',
    'unit': 'Dollars',
    'period': '2023-01',
    'custom_field': 'preserved'
}
normalized = normalize_dataset_metadata(metadata)
# Original fields are preserved, normalized fields added with 'normalized_' prefix
```

### Design Principles

1. **Preserve provider-specific data**: Original fields are kept intact, normalized values are added
2. **Minimal schema**: Support common patterns while allowing flexibility
3. **Fail gracefully**: Unknown values are passed through with minimal transformation
4. **Reference tracking**: Raw values are stored with `raw_` prefix for provenance

### Example Output

See `examples/normalization_demo.py` for a comprehensive demonstration:

```bash
python examples/normalization_demo.py
```

This shows normalization of frequencies, dates, periods, geographies, and units with real examples from Canadian datasets.

## Profiles System

The profiles system allows you to organize datasets into logical collections defined in YAML files. This is ideal for:
- **Multi-project workflows**: Define separate profiles for different projects or analyses
- **Reproducible data pipelines**: Version-control your data refresh configurations
- **Team collaboration**: Share standard dataset collections across your organization
- **Selective refresh**: Run refreshes on specific subsets of datasets

### Profile Structure

A profile is a YAML file that defines:
- **name**: Unique profile identifier
- **description**: Human-readable description of the profile
- **datasets**: List of dataset specifications with provider, ID, and output paths
- **output_dir**: Optional default output directory for all datasets
- **options**: Optional refresh options (e.g., `skip_existing`)

### Example Profile

```yaml
name: economics
description: Core economic indicators for Canada

datasets:
  - provider: statcan
    id: "18100004"
    output: data/raw/cpi_all_items_18100004.csv
    params:
      metric: "Consumer Price Index, all-items (NSA)"
      frequency: "Monthly"
  
  - provider: statcan
    id: "14100459"
    output: data/raw/unemployment_rate_14100459.csv
    params:
      metric: "Labour force characteristics by CMA"
      frequency: "Monthly"

output_dir: data/raw
options:
  skip_existing: true
```

### Working with Profiles

**Python API:**
```python
from publicdata_ca import run_profile, load_profile, list_profiles

# List available profiles
profiles = list_profiles()

# Run a profile
report = run_profile("economics")
print(report[['dataset', 'result', 'notes']])

# Load and inspect a profile
profile = load_profile("profiles/housing.yaml")
```

**CLI:**
```bash
# List profiles
publicdata profile list

# Run a profile
publicdata profile run economics

# Run with options
publicdata profile run housing --force --verbose --manifest
```

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
    
    # Computed properties:
    def destination() -> Path | None      # Resolves target_file to absolute path in data/raw
    @property
    def table_number() -> str | None      # Formats pid as "XX-XX-XXXX" for StatsCan tables
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

### Manage profiles

Profiles allow you to define collections of datasets to refresh together using YAML configuration files. This is ideal for managing multiple related datasets or creating project-specific refresh workflows.

**List available profiles:**

```bash
# List all profiles in the profiles/ directory
publicdata profile list
```

**Run a profile:**

```bash
# Run a profile by name
publicdata profile run economics

# Run with force re-download
publicdata profile run housing --force

# Show detailed results
publicdata profile run population --verbose

# Create a manifest after running the profile
publicdata profile run economics --manifest
```

**Create a profile:**

Profiles are YAML files stored in the `profiles/` directory. Here's an example profile (`profiles/economics.yaml`):

```yaml
name: economics
description: Core economic indicators for Canada including CPI, unemployment, and income

datasets:
  - provider: statcan
    id: "18100004"
    output: data/raw/cpi_all_items_18100004.csv
    params:
      metric: "Consumer Price Index, all-items (NSA)"
      frequency: "Monthly"
      geo_scope: "Canada + provinces"
  
  - provider: statcan
    id: "14100459"
    output: data/raw/unemployment_rate_14100459.csv
    params:
      metric: "Labour force characteristics by CMA (3-month moving avg, SA)"
      frequency: "Monthly"
      geo_scope: "Census metropolitan areas"

output_dir: data/raw
options:
  skip_existing: true
```

**Using profiles programmatically:**

```python
from publicdata_ca import run_profile, load_profile, list_profiles

# List all available profiles
profiles = list_profiles()
print(f"Available profiles: {profiles}")

# Run a profile by name
report = run_profile("economics")
print(report[['dataset', 'result', 'notes']])

# Load and inspect a profile
profile = load_profile("profiles/housing.yaml")
print(f"Profile: {profile.name}")
print(f"Datasets: {len(profile.datasets)}")

# Run with custom options
report = run_profile("economics", force_download=True)
```

## Running tests

Run the pytest suite from the project root:

```bash
pytest
```

You can also use `pytest -k catalog` to focus on a subset of tests while iterating on specific features.

### Testing Strategy

The project uses a comprehensive testing strategy with two types of tests:

- **Contract Tests** (default): Offline tests using real API response fixtures that validate provider implementations. These run automatically and have no network dependencies.
- **Smoke Tests** (optional): Live tests that verify basic connectivity to real provider endpoints. These are skipped by default.

For detailed information about the testing strategy, fixtures, and how to add tests for new providers, see [tests/TESTING.md](tests/TESTING.md).

To run smoke tests explicitly:
```bash
pytest tests/test_provider_smoke.py -v -m smoke
```
