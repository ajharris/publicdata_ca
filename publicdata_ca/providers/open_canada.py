"""
Open Government Canada portal integration.

This module provides a convenience wrapper for accessing the Open Government
Canada data portal (open.canada.ca). The portal is CKAN-backed, so this
provider routes all operations through the generic CKANProvider.

The provider supports:
- Searching datasets in the Open Canada portal
- Downloading resources by format (CSV, JSON, GeoJSON, etc.)
- Simplified API without needing to specify base_url repeatedly
"""

from typing import List, Dict, Any
from publicdata_ca.provider import DatasetRef
from publicdata_ca.providers.ckan import CKANProvider


# Open Canada portal base URL
OPEN_CANADA_BASE_URL = 'https://open.canada.ca/data'


class OpenCanadaProvider(CKANProvider):
    """
    Provider for the Open Government Canada data portal.
    
    This is a thin wrapper around CKANProvider that pre-configures the
    base URL for open.canada.ca. It provides a simplified interface for
    working specifically with Open Canada datasets.
    
    The Open Canada portal is CKAN-backed, so all functionality is
    delegated to the generic CKANProvider implementation.
    
    Attributes:
        name: Provider identifier (default: 'open_canada')
        base_url: Open Canada portal URL (pre-configured)
    
    Example:
        >>> # Search for housing datasets
        >>> provider = OpenCanadaProvider()
        >>> results = provider.search('housing', rows=5)
        >>> for ref in results:
        ...     print(f"{ref.id}: {ref.metadata['title']}")
        
        >>> # Download CSV resources from a dataset
        >>> ref = DatasetRef(
        ...     provider='open_canada',
        ...     id='dataset-id',
        ...     params={'format': 'CSV'}
        ... )
        >>> result = provider.fetch(ref, './data')
        >>> print(f"Downloaded {len(result['files'])} files")
    """
    
    def __init__(self, name: str = 'open_canada'):
        """
        Initialize the Open Canada provider.
        
        Args:
            name: Unique provider identifier (default: 'open_canada')
        
        Notes:
            The base_url is pre-configured to open.canada.ca and should
            not need to be overridden in normal usage.
        """
        super().__init__(name=name, base_url=OPEN_CANADA_BASE_URL)
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for datasets in the Open Canada portal.
        
        Args:
            query: Search query string (supports SOLR query syntax)
            **kwargs: Additional search parameters:
                - rows: Number of results to return (default: 10)
                - start: Offset for pagination (default: 0)
                - Other CKAN API parameters (e.g., fq for filtering)
        
        Returns:
            List of DatasetRef objects matching the query
        
        Example:
            >>> provider = OpenCanadaProvider()
            >>> results = provider.search('census', rows=5)
            >>> for ref in results:
            ...     print(f"{ref.id}: {ref.metadata.get('title')}")
            ...     print(f"  Formats: {', '.join(ref.metadata.get('formats', []))}")
        
        Notes:
            - Results include metadata about available formats
            - Use pagination for large result sets
            - Query syntax supports SOLR operators (AND, OR, NOT)
        """
        return super().search(query, **kwargs)
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve an Open Canada dataset reference into resource metadata.
        
        Args:
            ref: Dataset reference with Open Canada package ID
                Optional params:
                    - format: Filter resources by format (e.g., 'CSV', 'JSON')
                    - resource_id: Specific resource ID to resolve
        
        Returns:
            Dictionary containing:
                - resources: List of resource dictionaries
                - package_id: Package identifier
                - title: Dataset title
                - description: Dataset description
                - provider: Provider name
                - base_url: Open Canada portal URL
        
        Example:
            >>> provider = OpenCanadaProvider()
            >>> ref = DatasetRef(
            ...     provider='open_canada',
            ...     id='census-data',
            ...     params={'format': 'CSV'}
            ... )
            >>> metadata = provider.resolve(ref)
            >>> for resource in metadata['resources']:
            ...     print(f"{resource['name']}: {resource['url']}")
        
        Notes:
            - Format filtering is case-insensitive
            - Returns empty list if no resources match filters
        """
        return super().resolve(ref)
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download Open Canada resources to the specified output directory.
        
        Args:
            ref: Dataset reference with Open Canada package ID
                Optional params:
                    - format: Filter resources by format (e.g., 'CSV', 'JSON')
                    - resource_id: Specific resource ID to download
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters:
                - max_retries: Maximum retry attempts (default: 3)
        
        Returns:
            Dictionary containing:
                - dataset_id: Dataset identifier
                - provider: Provider name
                - files: List of downloaded file paths
                - resources: List of resource metadata
                - base_url: Open Canada portal URL
                - package_id: CKAN package ID
        
        Example:
            >>> provider = OpenCanadaProvider()
            >>> ref = DatasetRef(
            ...     provider='open_canada',
            ...     id='housing-data',
            ...     params={'format': 'CSV'}
            ... )
            >>> result = provider.fetch(ref, './data/open_canada')
            >>> print(f"Downloaded {len(result['files'])} CSV files")
            >>> for file_path in result['files']:
            ...     print(f"  - {file_path}")
        
        Raises:
            ValueError: If no resources found with specified filters
        
        Notes:
            - Creates output directory if it doesn't exist
            - Files are named based on resource names from the portal
            - Partial failures are logged but don't stop other downloads
        """
        return super().fetch(ref, output_dir, **kwargs)
