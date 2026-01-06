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
from publicdata_ca.datasets import (
    DEFAULT_DATASETS,
    Dataset,
    build_dataset_catalog,
    refresh_datasets,
)
from publicdata_ca.http import get_default_headers, retry_request
from publicdata_ca.manifest import build_manifest_file, build_run_manifest
from publicdata_ca.provider import (
    Provider,
    DatasetRef,
    ProviderRegistry,
    get_registry,
)
from publicdata_ca.providers import (
    StatCanProvider,
    CMHCProvider,
)

__all__ = [
    "Catalog",
    "Dataset",
    "DEFAULT_DATASETS",
    "build_dataset_catalog",
    "build_manifest_file",
    "build_run_manifest",
    "retry_request",
    "get_default_headers",
    "refresh_datasets",
    "Provider",
    "DatasetRef",
    "ProviderRegistry",
    "get_registry",
    "StatCanProvider",
    "CMHCProvider",
]
