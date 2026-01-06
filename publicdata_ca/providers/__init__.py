"""
Data providers subpackage.

This subpackage contains modules for downloading data from various Canadian public data sources.
"""

from publicdata_ca.providers.statcan import download_statcan_table, StatCanProvider
from publicdata_ca.providers.cmhc import resolve_cmhc_assets, download_cmhc_asset, CMHCProvider
from publicdata_ca.providers.ckan import (
    search_ckan_datasets,
    get_ckan_package,
    list_ckan_resources,
    download_ckan_resource,
    CKANProvider,
)

__all__ = [
    "download_statcan_table",
    "StatCanProvider",
    "resolve_cmhc_assets",
    "download_cmhc_asset",
    "CMHCProvider",
    "search_ckan_datasets",
    "get_ckan_package",
    "list_ckan_resources",
    "download_ckan_resource",
    "CKANProvider",
]
