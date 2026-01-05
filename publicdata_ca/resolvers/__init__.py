"""
Resolvers subpackage.

This subpackage contains modules for resolving and scraping URLs from data provider
landing pages, particularly useful when direct download links change frequently.
"""

from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page

__all__ = [
    "resolve_cmhc_landing_page",
]
