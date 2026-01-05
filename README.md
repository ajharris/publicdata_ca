# publicdata_ca
publicdata_ca is a lightweight Python package for discovering, resolving, and downloading Canadian public datasets. It automates StatsCan table retrieval, handles CMHC landing-page churn, enforces reproducible file layouts, and generates manifests so downstream analyses fail fast when data is missing.

## Key Features

### CMHC Landing Page Resolver
The CMHC landing page resolver now includes advanced URL resolution with:
- **Ranking**: Automatically prioritizes candidates based on file format (XLSX > CSV > XLS > ZIP), URL structure, and other quality indicators
- **Validation**: Checks URLs to reject HTML responses and verify actual file types before download
- **Robust extraction**: Handles various HTML structures and link patterns on CMHC websites

Example usage:
```python
from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page

# Resolve with validation (default)
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page')
for asset in assets:
    print(f"{asset['title']}: {asset['url']} (rank: {asset['rank']})")
    
# Disable validation for faster resolution
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page', validate=False)
```

## Package layout

- `publicdata_ca/catalog.py` — in-memory catalog for registering and searching dataset metadata.
- `publicdata_ca/datasets.py` — curated dataset definitions and pandas helpers ported from the ingestion notebook.
- `publicdata_ca/providers/` — provider integrations such as StatsCan table metadata and CMHC landing-page handling.
- `publicdata_ca/resolvers/` — HTML scrapers that translate landing pages into direct asset URLs.
- `publicdata_ca/manifest.py` — utilities for building and validating download manifests.
- `tests/` — pytest suite covering the high-level catalog and manifest flows.

## Editable install

1. Create a virtual environment (Python 3.9+): `python -m venv .venv`
2. Activate it: `source .venv/bin/activate`
3. Install the package in editable mode with dev extras: `python -m pip install -e ".[dev]"`

This installs the `publicdata` console script, making CLI commands such as `publicdata fetch statcan 14-10-0287-01` available in your shell.

## Running tests

Run the pytest suite from the project root:

```bash
pytest
```

You can also use `pytest -k catalog` to focus on a subset of tests while iterating on specific features.
