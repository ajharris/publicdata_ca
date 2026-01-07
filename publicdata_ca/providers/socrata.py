"""
Socrata (SODA API) generic data provider.

This module provides functionality to search datasets and download resources from
any Socrata open data portal by configuring the base URL. Socrata powers many
government open data portals through its SODA (Socrata Open Data API).

The provider supports:
- Searching datasets using the catalog API
- Column selection via SoQL $select parameter
- Basic where filters via SoQL $where parameter
- Paging via $limit and $offset parameters
- Export to CSV and JSON formats
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote, urlencode
from publicdata_ca.http import retry_request, download_file
from publicdata_ca.provider import Provider, DatasetRef


def search_socrata_datasets(
    base_url: str,
    query: str = "",
    limit: int = 10,
    offset: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """
    Search for datasets in a Socrata portal using the catalog API.
    
    Uses the Socrata catalog API endpoint to find datasets matching the query.
    
    Args:
        base_url: Base URL of the Socrata portal (e.g., 'https://data.seattle.gov')
        query: Search query string (default: "" returns all datasets)
        limit: Number of results to return (default: 10)
        offset: Offset for pagination (default: 0)
        **kwargs: Additional API parameters (e.g., categories, tags, only)
    
    Returns:
        Dictionary containing:
            - results: List of dataset/resource dictionaries
            - count: Number of results returned
    
    Example:
        >>> results = search_socrata_datasets(
        ...     'https://data.seattle.gov',
        ...     'police',
        ...     limit=5
        ... )
        >>> print(f"Found {results['count']} datasets")
        >>> for dataset in results['results']:
        ...     print(dataset['resource']['name'])
    
    Notes:
        - Uses Socrata Discovery API v2.1
        - Returns raw Socrata response structure
        - Query supports free-text search across dataset metadata
    """
    # Build catalog API endpoint URL
    api_url = urljoin(base_url.rstrip('/') + '/', 'api/catalog/v1')
    
    # Build query parameters
    params = {
        'limit': limit,
        'offset': offset,
    }
    
    # Add search query if provided
    if query:
        params['q'] = query
    
    # Add any additional parameters
    for key, value in kwargs.items():
        if value is not None:
            params[key] = value
    
    # Build full URL with query parameters
    query_string = urlencode(params)
    full_url = f"{api_url}?{query_string}"
    
    try:
        response = retry_request(full_url)
        data = json.loads(response.content.decode('utf-8'))
        
        # Socrata catalog API returns results directly
        results = data.get('results', [])
        
        return {
            'results': results,
            'count': len(results)
        }
    except Exception as e:
        raise RuntimeError(f"Failed to search Socrata portal at {base_url}: {str(e)}")


def get_socrata_metadata(base_url: str, dataset_id: str) -> Dict[str, Any]:
    """
    Get detailed metadata about a specific Socrata dataset.
    
    Uses the Socrata metadata API to retrieve complete information about a dataset
    including column schema and view type.
    
    Args:
        base_url: Base URL of the Socrata portal
        dataset_id: Dataset identifier (4x4 format, e.g., 'abcd-1234')
    
    Returns:
        Dictionary containing complete dataset metadata including:
            - name: Dataset name
            - description: Dataset description
            - columns: List of column definitions
            - viewType: Type of view (dataset, calendar, etc.)
            - createdAt: Creation timestamp
            - rowsUpdatedAt: Last update timestamp
    
    Example:
        >>> metadata = get_socrata_metadata(
        ...     'https://data.seattle.gov',
        ...     'abcd-1234'
        ... )
        >>> print(metadata['name'])
        >>> print(f"Columns: {len(metadata['columns'])}")
    
    Raises:
        RuntimeError: If the metadata cannot be retrieved
    """
    # Build metadata API endpoint URL
    api_url = urljoin(
        base_url.rstrip('/') + '/',
        f'api/views/{dataset_id}.json'
    )
    
    try:
        response = retry_request(api_url)
        data = json.loads(response.content.decode('utf-8'))
        return data
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Socrata metadata response: {str(e)}")
    except Exception as e:
        raise RuntimeError(
            f"Failed to get Socrata dataset {dataset_id} from {base_url}: {str(e)}"
        )


def download_socrata_dataset(
    base_url: str,
    dataset_id: str,
    output_path: str,
    format: str = 'csv',
    select: Optional[str] = None,
    where: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Download a Socrata dataset with optional filters and column selection.
    
    Uses the SODA API to download data with SoQL query parameters for filtering,
    column selection, and pagination.
    
    Args:
        base_url: Base URL of the Socrata portal
        dataset_id: Dataset identifier (4x4 format, e.g., 'abcd-1234')
        output_path: Full path where the file will be saved
        format: Export format ('csv' or 'json', default: 'csv')
        select: SoQL select clause for column selection (e.g., 'name, date, count')
        where: SoQL where clause for filtering (e.g., 'count > 100')
        limit: Maximum number of rows to return (default: None for all rows)
        offset: Number of rows to skip (default: None)
        max_retries: Maximum number of download retry attempts (default: 3)
    
    Returns:
        Dictionary containing:
            - file: Path to the downloaded file
            - url: Source URL
            - format: File format
            - rows_downloaded: Estimated number of rows (if available)
    
    Example:
        >>> result = download_socrata_dataset(
        ...     'https://data.seattle.gov',
        ...     'abcd-1234',
        ...     './data/seattle_police.csv',
        ...     select='date, offense_type, count',
        ...     where='count > 10',
        ...     limit=1000
        ... )
        >>> print(result['file'])
    
    Notes:
        - SoQL syntax: https://dev.socrata.com/docs/queries/
        - CSV format is recommended for large datasets
        - JSON format may be limited by API constraints
    """
    # Create output directory if needed
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build resource API endpoint URL with format
    resource_url = urljoin(
        base_url.rstrip('/') + '/',
        f'resource/{dataset_id}.{format}'
    )
    
    # Build query parameters using SoQL
    params = {}
    
    if select:
        params['$select'] = select
    
    if where:
        params['$where'] = where
    
    if limit is not None:
        params['$limit'] = str(limit)
    
    if offset is not None:
        params['$offset'] = str(offset)
    
    # Build full URL with query parameters
    if params:
        query_string = urlencode(params)
        full_url = f"{resource_url}?{query_string}"
    else:
        full_url = resource_url
    
    # Download the file
    try:
        download_file(
            full_url,
            output_path,
            max_retries=max_retries,
            validate_content_type=True
        )
        
        return {
            'file': output_path,
            'url': full_url,
            'format': format,
            'dataset_id': dataset_id
        }
    except Exception as e:
        raise RuntimeError(
            f"Failed to download Socrata dataset {dataset_id} from {base_url}: {str(e)}"
        )


class SocrataProvider(Provider):
    """
    Generic Socrata (SODA API) data provider.
    
    This provider implements the standard Provider interface for Socrata portals.
    It can work with any Socrata instance by configuring the base URL. Socrata
    powers many government open data portals worldwide.
    
    The provider supports:
    - Searching datasets using Socrata's catalog API
    - Column selection via SoQL $select parameter
    - Basic filtering via SoQL $where parameter
    - Paging via $limit and $offset parameters
    - Export to CSV and JSON formats
    
    Attributes:
        name: Provider identifier (default: 'socrata')
        base_url: Base URL of the Socrata portal
    
    Example:
        >>> # Using Seattle open data portal
        >>> provider = SocrataProvider(
        ...     name='seattle',
        ...     base_url='https://data.seattle.gov'
        ... )
        >>> results = provider.search('police')
        >>> for ref in results:
        ...     print(ref.canonical_id)
        
        >>> # Download with filters and column selection
        >>> ref = DatasetRef(
        ...     provider='seattle',
        ...     id='abcd-1234',
        ...     params={
        ...         'format': 'csv',
        ...         'select': 'date, offense, count',
        ...         'where': 'count > 10',
        ...         'limit': 1000
        ...     }
        ... )
        >>> result = provider.fetch(ref, './data')
        >>> print(result['files'])
    """
    
    def __init__(self, name: str = 'socrata', base_url: Optional[str] = None):
        """
        Initialize the Socrata provider.
        
        Args:
            name: Unique provider identifier (default: 'socrata')
            base_url: Base URL of the Socrata portal. Can also be set via
                     DatasetRef params with key 'base_url'
        
        Raises:
            ValueError: If base_url is not provided and not in DatasetRef params
        """
        super().__init__(name)
        self.base_url = base_url
    
    def search(self, query: str = "", **kwargs) -> List[DatasetRef]:
        """
        Search for datasets in the Socrata portal.
        
        Args:
            query: Search query string (default: "" returns all datasets)
            **kwargs: Additional search parameters:
                - base_url: Override the provider's base URL
                - limit: Number of results to return (default: 10)
                - offset: Offset for pagination (default: 0)
                - categories: Filter by category
                - tags: Filter by tags
                - only: Filter by type (e.g., 'datasets', 'charts', 'maps')
        
        Returns:
            List of DatasetRef objects matching the query
        
        Example:
            >>> provider = SocrataProvider(base_url='https://data.seattle.gov')
            >>> results = provider.search('police', limit=5)
            >>> for ref in results:
            ...     print(f"{ref.id}: {ref.metadata.get('name')}")
        
        Raises:
            ValueError: If base_url is not configured
        """
        # Get base URL from kwargs or instance
        base_url = kwargs.pop('base_url', self.base_url)
        if not base_url:
            raise ValueError(
                "base_url must be provided either in provider initialization or search kwargs"
            )
        
        # Search Socrata portal
        search_results = search_socrata_datasets(base_url, query, **kwargs)
        
        # Convert results to DatasetRef objects
        refs = []
        for item in search_results.get('results', []):
            resource = item.get('resource', {})
            classification = item.get('classification', {})
            
            # Extract dataset ID (4x4 identifier)
            dataset_id = resource.get('id', '')
            if not dataset_id:
                continue
            
            # Extract metadata
            ref = DatasetRef(
                provider=self.name,
                id=dataset_id,
                params={'base_url': base_url},
                metadata={
                    'name': resource.get('name', ''),
                    'description': resource.get('description', ''),
                    'type': resource.get('type', ''),
                    'updatedAt': resource.get('updatedAt', ''),
                    'createdAt': resource.get('createdAt', ''),
                    'categories': classification.get('categories', []),
                    'domain_tags': classification.get('domain_tags', []),
                },
                tags=classification.get('domain_tags', [])
            )
            refs.append(ref)
        
        return refs
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve a Socrata dataset reference into metadata.
        
        Args:
            ref: Dataset reference with Socrata dataset ID
                Required params:
                    - base_url: Socrata portal base URL (or set in provider)
                Optional params:
                    - format: Export format ('csv' or 'json', default: 'csv')
                    - select: Column selection (SoQL $select clause)
                    - where: Filter clause (SoQL $where clause)
                    - limit: Maximum rows to return
                    - offset: Number of rows to skip
        
        Returns:
            Dictionary containing:
                - dataset_id: Dataset identifier
                - name: Dataset name
                - description: Dataset description
                - columns: List of column definitions
                - provider: Provider name
                - base_url: Socrata portal URL
                - download_params: Parameters for download
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='socrata',
            ...     id='abcd-1234',
            ...     params={
            ...         'base_url': 'https://data.seattle.gov',
            ...         'format': 'csv',
            ...         'select': 'date, offense, count'
            ...     }
            ... )
            >>> metadata = provider.resolve(ref)
            >>> print(f"Columns: {len(metadata['columns'])}")
        
        Raises:
            ValueError: If base_url is not configured
        """
        # Get base URL from params or instance
        base_url = ref.params.get('base_url', self.base_url)
        if not base_url:
            raise ValueError(
                "base_url must be provided in DatasetRef params or provider initialization"
            )
        
        # Get metadata from Socrata
        metadata = get_socrata_metadata(base_url, ref.id)
        
        # Extract download parameters from ref
        download_params = {
            'format': ref.params.get('format', 'csv'),
            'select': ref.params.get('select'),
            'where': ref.params.get('where'),
            'limit': ref.params.get('limit'),
            'offset': ref.params.get('offset'),
        }
        
        return {
            'dataset_id': ref.id,
            'name': metadata.get('name', ref.id),
            'description': metadata.get('description', ''),
            'columns': metadata.get('columns', []),
            'viewType': metadata.get('viewType', ''),
            'provider': self.name,
            'base_url': base_url,
            'download_params': download_params,
        }
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download Socrata dataset to the specified output directory.
        
        Args:
            ref: Dataset reference with Socrata dataset ID
                Required params:
                    - base_url: Socrata portal base URL (or set in provider)
                Optional params:
                    - format: Export format ('csv' or 'json', default: 'csv')
                    - select: Column selection (SoQL $select clause)
                    - where: Filter clause (SoQL $where clause)
                    - limit: Maximum rows to return
                    - offset: Number of rows to skip
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters:
                - max_retries: Maximum retry attempts (default: 3)
                - filename: Custom filename (default: dataset_id.format)
        
        Returns:
            Dictionary containing:
                - dataset_id: Dataset identifier
                - provider: Provider name
                - files: List containing the downloaded file path
                - base_url: Socrata portal URL
                - format: File format
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='socrata',
            ...     id='abcd-1234',
            ...     params={
            ...         'base_url': 'https://data.seattle.gov',
            ...         'format': 'csv',
            ...         'select': 'date, count',
            ...         'where': 'count > 10',
            ...         'limit': 1000
            ...     }
            ... )
            >>> result = provider.fetch(ref, './data')
            >>> print(f"Downloaded to {result['files'][0]}")
        
        Raises:
            ValueError: If base_url is not configured
        """
        max_retries = kwargs.get('max_retries', 3)
        
        # Get base URL from params or instance
        base_url = ref.params.get('base_url', self.base_url)
        if not base_url:
            raise ValueError(
                "base_url must be provided in DatasetRef params or provider initialization"
            )
        
        # Get download parameters
        format = ref.params.get('format', 'csv')
        select = ref.params.get('select')
        where = ref.params.get('where')
        limit = ref.params.get('limit')
        offset = ref.params.get('offset')
        
        # Determine output filename
        filename = kwargs.get('filename', f"{ref.id}.{format}")
        output_path = str(Path(output_dir) / filename)
        
        # Download the dataset
        result = download_socrata_dataset(
            base_url=base_url,
            dataset_id=ref.id,
            output_path=output_path,
            format=format,
            select=select,
            where=where,
            limit=limit,
            offset=offset,
            max_retries=max_retries
        )
        
        return {
            'dataset_id': f"{self.name}_{ref.id}",
            'provider': self.name,
            'files': [result['file']],
            'base_url': base_url,
            'format': format,
            'download_url': result['url'],
        }
