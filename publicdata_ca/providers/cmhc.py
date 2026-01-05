"""
Canada Mortgage and Housing Corporation (CMHC) data provider.

This module provides functionality to download datasets from CMHC, including
handling landing page resolution for datasets with changing URLs.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from publicdata_ca.http import download_file
from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page


def resolve_cmhc_assets(landing_url: str) -> List[Dict[str, str]]:
    """
    Resolve direct download URLs from a CMHC landing page.
    
    CMHC data files are often hosted on landing pages where the direct download URLs
    change over time. This function extracts the current direct URLs from the landing page.
    
    Args:
        landing_url: URL of the CMHC landing/catalog page.
    
    Returns:
        List of asset dictionaries, each containing:
            - url: Direct download URL
            - title: Asset title/name
            - format: File format (e.g., 'csv', 'xlsx')
    
    Example:
        >>> assets = resolve_cmhc_assets('https://www.cmhc-schl.gc.ca/...')
        >>> for asset in assets:
        ...     print(f"{asset['title']}: {asset['url']}")
    """
    return resolve_cmhc_landing_page(landing_url)


def download_cmhc_asset(
    landing_url: str,
    output_dir: str,
    asset_filter: Optional[str] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Download CMHC data assets from a landing page.
    
    This function resolves the current download URLs from a CMHC landing page
    and downloads the data files. It handles the common case where CMHC
    landing pages have changing direct download URLs.
    
    Args:
        landing_url: URL of the CMHC landing/catalog page.
        output_dir: Directory where files will be saved.
        asset_filter: Optional filter string to select specific assets (e.g., 'csv').
            If None, downloads all assets.
        max_retries: Maximum number of download retry attempts (default: 3).
    
    Returns:
        Dictionary containing:
            - dataset_id: Generated dataset identifier
            - provider: 'cmhc'
            - files: List of downloaded file paths
            - landing_url: Original landing page URL
            - assets: List of asset metadata
    
    Example:
        >>> result = download_cmhc_asset(
        ...     'https://www.cmhc-schl.gc.ca/data/housing-starts',
        ...     './data',
        ...     asset_filter='csv'
        ... )
        >>> print(result['files'])
    
    Notes:
        - The function uses the cmhc_landing resolver to extract current URLs
        - Files are saved with sanitized names based on asset titles
        - Supports filtering by format or title keywords
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Resolve assets from landing page
    assets = resolve_cmhc_assets(landing_url)
    
    # Filter assets if requested
    if asset_filter:
        filter_lower = asset_filter.lower()
        assets = [
            a for a in assets
            if filter_lower in a.get('format', '').lower() or
               filter_lower in a.get('title', '').lower()
        ]
    
    # Download each asset
    downloaded_files = []
    download_errors = []
    
    for asset in assets:
        # Create a safe filename
        file_format = asset.get('format', 'dat')
        title = asset.get('title', 'asset')
        # Sanitize filename to prevent directory traversal
        # Remove any path separators and only allow safe characters
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        # Remove any remaining path separators that might have been introduced
        safe_title = safe_title.replace('/', '_').replace('\\', '_').replace('..', '_')
        # Ensure the title is not empty
        if not safe_title:
            safe_title = 'asset'
        
        # Sanitize file format to only allow alphanumeric characters
        safe_format = "".join(c for c in file_format if c.isalnum())
        if not safe_format:
            safe_format = 'dat'
        
        file_name = f"{safe_title}.{safe_format}"
        output_file = output_path / file_name
        
        try:
            # Download with content-type validation to reject HTML responses
            download_file(
                asset['url'],
                str(output_file),
                max_retries=max_retries,
                validate_content_type=True
            )
            downloaded_files.append(str(output_file.relative_to(output_path.parent)))
            asset['local_path'] = str(output_file)
        except (ValueError, Exception) as e:
            # Handle download errors (both validation and other errors)
            error_msg = f"Failed to download '{asset['title']}' from {asset['url']}: {str(e)}"
            download_errors.append(error_msg)
            
            # Log as error for validation issues, warning for others
            if isinstance(e, ValueError):
                print(f"Error: {error_msg}")
            else:
                print(f"Warning: {error_msg}")
            
            asset['error'] = str(e)
    
    # Generate dataset ID from landing URL
    dataset_id = f"cmhc_{landing_url.split('/')[-1]}"
    
    result = {
        'dataset_id': dataset_id,
        'provider': 'cmhc',
        'files': downloaded_files,
        'landing_url': landing_url,
        'assets': assets,
        'errors': download_errors
    }
    
    return result
