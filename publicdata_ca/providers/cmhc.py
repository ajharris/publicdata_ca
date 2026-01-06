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
from publicdata_ca.provider import Provider, DatasetRef


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
            
            # Add CMHC-specific metadata to the provenance file
            _add_cmhc_metadata(str(output_file), asset, landing_url)
        except (ValueError, Exception) as e:
            # Handle all download errors uniformly (ValueError for validation, Exception for others)
            # Both are tracked the same way, but logged differently based on type
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


def _add_cmhc_metadata(file_path: str, asset: Dict[str, Any], landing_url: str) -> None:
    """
    Add CMHC-specific metadata to an existing provenance file.
    
    Enhances the automatically-generated .meta.json file with CMHC-specific
    information like asset title, format, rank, and landing page URL.
    
    Args:
        file_path: Path to the downloaded file.
        asset: Asset metadata dictionary.
        landing_url: Original CMHC landing page URL.
    """
    import json
    from pathlib import Path
    
    meta_file_path = Path(file_path).parent / f"{Path(file_path).name}.meta.json"
    
    if not meta_file_path.exists():
        return
    
    try:
        # Read existing metadata
        with open(meta_file_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Add CMHC-specific fields
        metadata['provider'] = 'cmhc'
        metadata['landing_page_url'] = landing_url
        metadata['asset_title'] = asset.get('title', '')
        metadata['asset_format'] = asset.get('format', '')
        
        # Add rank if available
        if 'rank' in asset:
            metadata['asset_rank'] = asset['rank']
        
        # Write updated metadata
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except Exception:
        # Don't fail if metadata enhancement fails
        pass


class CMHCProvider(Provider):
    """
    Canada Mortgage and Housing Corporation data provider implementation.
    
    This provider implements the standard Provider interface for CMHC datasets.
    It supports resolving landing page URLs to direct download links and fetching
    CMHC datasets with automatic URL resolution.
    
    Example:
        >>> provider = CMHCProvider()
        >>> ref = DatasetRef(
        ...     provider='cmhc',
        ...     id='rental-market-report',
        ...     params={'page_url': 'https://www.cmhc-schl.gc.ca/...'}
        ... )
        >>> result = provider.fetch(ref, './data/raw')
        >>> print(result['files'])
    """
    
    def __init__(self, name: str = 'cmhc'):
        """Initialize the CMHC provider."""
        super().__init__(name)
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for CMHC datasets by keyword.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
        
        Returns:
            List of DatasetRef objects matching the query
        
        Note:
            This is a placeholder implementation. Full search functionality
            would require integration with CMHC's catalog or search API.
        """
        # Placeholder - would require CMHC catalog integration
        return []
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve a CMHC dataset reference into download metadata.
        
        Args:
            ref: Dataset reference with CMHC landing page URL or direct URL
        
        Returns:
            Dictionary containing resolved URLs and metadata
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='cmhc',
            ...     id='housing-starts',
            ...     params={'page_url': 'https://www.cmhc-schl.gc.ca/...'}
            ... )
            >>> metadata = provider.resolve(ref)
            >>> print(metadata['assets'])
        """
        # Check for direct URL first
        if 'direct_url' in ref.params:
            return {
                'url': ref.params['direct_url'],
                'format': self._detect_format(ref.params['direct_url']),
                'title': ref.metadata.get('title', ref.id),
                'provider': self.name,
            }
        
        # Check for landing page URL
        if 'page_url' in ref.params:
            # Resolve assets from landing page
            assets = resolve_cmhc_assets(ref.params['page_url'])
            return {
                'assets': assets,
                'landing_url': ref.params['page_url'],
                'title': ref.metadata.get('title', ref.id),
                'provider': self.name,
            }
        
        # No URL provided
        raise ValueError(
            f"CMHC dataset reference must include 'page_url' or 'direct_url' in params"
        )
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download a CMHC dataset to the specified output directory.
        
        Args:
            ref: Dataset reference with CMHC landing page or direct URL
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters (max_retries, asset_filter, etc.)
        
        Returns:
            Dictionary containing downloaded files and metadata
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='cmhc',
            ...     id='rental-market-report',
            ...     params={'page_url': 'https://www.cmhc-schl.gc.ca/...'}
            ... )
            >>> result = provider.fetch(ref, './data/raw')
            >>> print(result['files'])
        """
        max_retries = kwargs.get('max_retries', 3)
        asset_filter = kwargs.get('asset_filter', None)
        
        # Check for direct URL first
        if 'direct_url' in ref.params:
            # Download directly
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create filename from ID
            file_format = self._detect_format(ref.params['direct_url'])
            output_file = output_path / f"{ref.id}.{file_format}"
            
            try:
                download_file(
                    ref.params['direct_url'],
                    str(output_file),
                    max_retries=max_retries,
                    validate_content_type=True
                )
                
                return {
                    'dataset_id': f"cmhc_{ref.id}",
                    'provider': self.name,
                    'files': [str(output_file)],
                    'url': ref.params['direct_url'],
                }
            except Exception as e:
                raise RuntimeError(
                    f"Failed to download CMHC dataset {ref.id}: {str(e)}"
                )
        
        # Check for landing page URL
        if 'page_url' in ref.params:
            # Use the existing download_cmhc_asset function
            result = download_cmhc_asset(
                landing_url=ref.params['page_url'],
                output_dir=output_dir,
                asset_filter=asset_filter,
                max_retries=max_retries
            )
            return result
        
        # No URL provided
        raise ValueError(
            f"CMHC dataset reference must include 'page_url' or 'direct_url' in params"
        )
    
    def _detect_format(self, url: str) -> str:
        """
        Detect file format from URL.
        
        Args:
            url: Download URL
        
        Returns:
            File format extension (csv, xlsx, etc.)
        """
        url_lower = url.lower()
        if '.xlsx' in url_lower:
            return 'xlsx'
        elif '.csv' in url_lower:
            return 'csv'
        elif '.xls' in url_lower:
            return 'xls'
        elif '.zip' in url_lower:
            return 'zip'
        else:
            return 'dat'
