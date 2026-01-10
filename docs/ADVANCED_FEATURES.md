# Advanced Features

This document covers advanced features of publicdata_ca for power users and automation workflows.

## Table of Contents

- [HTTP Caching](#http-caching)
- [Provenance Tracking](#provenance-tracking)
- [Run Reports](#run-reports)
- [Profiles System](#profiles-system)
- [Normalization Utilities](#normalization-utilities)
- [Manifest Management](#manifest-management)

## HTTP Caching

The HTTP download utilities support intelligent caching using ETag and Last-Modified headers to avoid re-downloading unchanged files.

### How It Works

1. **First download**: File is downloaded and server's ETag/Last-Modified headers are saved
2. **Subsequent downloads**: Conditional request headers (If-None-Match/If-Modified-Since) are sent
3. **304 Not Modified**: If file hasn't changed, download is skipped entirely
4. **200 OK**: If file changed, new version is downloaded and cache is updated

### Usage

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

### Cache Storage

- Cache metadata is stored alongside downloaded files with `.http_cache.json` extension
- Contains ETag, Last-Modified, source URL, and cache timestamp
- Automatically cleaned up when files are deleted
- Excluded from version control via `.gitignore`

### Benefits

- **Bandwidth savings**: Skip downloads when files haven't changed
- **Faster refreshes**: Reduce time for data refresh operations
- **Server-friendly**: Reduces load on data provider servers
- **Automatic**: Works transparently when servers support caching headers

For examples, see `examples/http_caching_demo.py`.

## Provenance Tracking

All downloaded files are accompanied by `.meta.json` sidecar files that track provenance information using a unified schema across all data providers.

### Metadata Schema

Version 1.0 schema:

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

### Key Features

- **Schema versioning**: Forward and backward compatibility support
- **Provider standardization**: Consistent structure across all providers
- **Integrity verification**: SHA-256 hashes for validating file integrity
- **Provider-specific metadata**: Extensible structure for provider-unique fields

### Usage

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

## Run Reports

The `refresh_datasets()` function generates detailed run reports summarizing what changed, what succeeded, what failed, and why.

### Export Formats

Reports can be exported in CSV or JSON format:

```bash
# Export as CSV (default)
publicdata refresh --report

# Export as JSON
publicdata refresh --report --report-format json

# Specify output path
publicdata refresh --report --report-output ./reports/latest_run.csv
```

### Python API

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

### Report Fields

- `dataset`: Dataset identifier
- `provider`: Data provider (statcan, cmhc, etc.)
- `target_file`: Path to the downloaded file
- `result`: Status (downloaded, exists, error, manual_required)
- `notes`: Detailed information about the result
- `run_started_utc`: Timestamp when the run started

## Profiles System

The profiles system allows you to organize datasets into logical collections defined in YAML files.

### Use Cases

- **Multi-project workflows**: Define separate profiles for different projects or analyses
- **Reproducible data pipelines**: Version-control your data refresh configurations
- **Team collaboration**: Share standard dataset collections across your organization
- **Selective refresh**: Run refreshes on specific subsets of datasets

### Profile Structure

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

For more information, see `profiles/README.md`.

## Normalization Utilities

The normalization module provides utilities to standardize common metadata fields across Canadian public datasets.

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

For examples, see `examples/normalization_demo.py`.

## Manifest Management

Manifests help ensure reproducibility by tracking which files should exist in your data directory.

### Creating Manifests

```python
from publicdata_ca import build_manifest_file

# Build manifest from successfully downloaded files
manifest_path = build_manifest_file(
    output_dir='./data',
    datasets=[
        {
            'dataset_id': 'cpi_all_items',
            'provider': 'statcan',
            'files': ['data/raw/cpi_all_items.csv'],
        }
    ]
)
```

### CLI Usage

```bash
# Create a manifest
publicdata manifest create --output ./data

# Validate a manifest
publicdata manifest validate --manifest-file ./data/manifest.json
```

### Benefits

- **Fail fast**: Downstream analyses can check the manifest before running
- **Version control**: Track expected data files in your repository
- **Reproducibility**: Ensure all required data is present before analysis
