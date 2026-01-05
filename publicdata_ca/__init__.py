"""
publicdata_ca - A lightweight Python package for discovering, resolving, and downloading Canadian public datasets.

This package provides tools for:
- Retrieving StatsCan tables
- Handling CMHC landing-page changes
- Enforcing reproducible file layouts
- Generating manifests for downstream analyses
"""

__version__ = "0.1.0"

from publicdata_ca.catalog import Catalog
from publicdata_ca.manifest import build_run_manifest
from publicdata_ca.http import retry_request, get_default_headers

__all__ = [
    "Catalog",
    "build_run_manifest",
    "retry_request",
    "get_default_headers",
]
