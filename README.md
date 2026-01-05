# publicdata_ca
publicdata_ca is a lightweight Python package for discovering, resolving, and downloading Canadian public datasets. It automates StatsCan table retrieval, handles CMHC landing-page churn, enforces reproducible file layouts, and generates manifests so downstream analyses fail fast when data is missing.

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
