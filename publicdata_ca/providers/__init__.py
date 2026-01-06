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
from publicdata_ca.providers.socrata import (
    search_socrata_datasets,
    get_socrata_metadata,
    download_socrata_dataset,
    SocrataProvider,
)
from publicdata_ca.providers.sdmx import (
    get_sdmx_dataflow,
    get_sdmx_data_structure,
    fetch_sdmx_data,
    download_sdmx_data,
    SDMXProvider,
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
    "search_socrata_datasets",
    "get_socrata_metadata",
    "download_socrata_dataset",
    "SocrataProvider",
    "get_sdmx_dataflow",
    "get_sdmx_data_structure",
    "fetch_sdmx_data",
    "download_sdmx_data",
    "SDMXProvider",
]
