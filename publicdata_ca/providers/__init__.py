"""
Data providers subpackage.

This subpackage contains modules for downloading data from various Canadian public data sources.
"""

from publicdata_ca.providers.statcan import download_statcan_table, StatCanProvider
from publicdata_ca.providers.cmhc import resolve_cmhc_assets, download_cmhc_asset, CMHCProvider

__all__ = [
    "download_statcan_table",
    "StatCanProvider",
    "resolve_cmhc_assets",
    "download_cmhc_asset",
    "CMHCProvider",
]
