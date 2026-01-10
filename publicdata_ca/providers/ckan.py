"""
CKAN (Comprehensive Knowledge Archive Network) generic data provider.

This module provides functionality to search datasets and download resources from
any CKAN portal by configuring the base URL. CKAN is a widely-used open-source
data portal platform used by many government organizations worldwide.

The provider supports:
- Searching datasets using the CKAN package_search API
- Resolving resources by format (CSV, JSON, GeoJSON, etc.)
- Fetching resources with automatic format filtering
- Working with multiple CKAN portals via base URL configuration
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote
from requests.exceptions import HTTPError
from publicdata_ca.http import retry_request, download_file
from publicdata_ca.provider import Provider, DatasetRef


_NON_DOWNLOADABLE_RESOURCE_TYPES = {
    'documentation',
    'guide',
    'metadata',
    'webpage',
    'website',
}

_NON_DOWNLOADABLE_FORMATS = {
    'html',
    'htm',
    'web page',
    'website',
}


def _resource_is_downloadable(resource: Dict[str, Any]) -> bool:
    """Return True when a CKAN resource points to a real file or API."""
    url = resource.get('url')
    if not url:
        return False
    resource_type = (resource.get('resource_type') or '').strip().lower()
    format_hint = (resource.get('format') or '').strip().lower()

    if resource_type in _NON_DOWNLOADABLE_RESOURCE_TYPES:
        return False
    if format_hint in _NON_DOWNLOADABLE_FORMATS and resource_type not in {'api'}:
        return False
    return True


def search_ckan_datasets(
    base_url: str,
    query: str,
    rows: int = 10,
    start: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """
    Search for datasets in a CKAN portal.
    
    Uses the CKAN package_search API endpoint to find datasets matching the query.
    
    Args:
        base_url: Base URL of the CKAN portal (e.g., 'https://open.canada.ca/data')
        query: Search query string (supports SOLR query syntax)
        rows: Number of results to return (default: 10)
        start: Offset for pagination (default: 0)
        **kwargs: Additional CKAN API parameters (e.g., fq for filtering)
    
    Returns:
        Dictionary containing:
            - count: Total number of matching datasets
            - results: List of dataset/package dictionaries
            - success: Boolean indicating if the request was successful
    
    Example:
        >>> results = search_ckan_datasets(
        ...     'https://open.canada.ca/data',
        ...     'housing',
        ...     rows=5
        ... )
        >>> print(f"Found {results['count']} datasets")
        >>> for dataset in results['results']:
        ...     print(dataset['title'])
    
    Notes:
        - Uses CKAN API v3 (action API)
        - Returns raw CKAN response structure
        - Query supports SOLR syntax for advanced filtering
    """
    # Build API endpoint URL
    api_url = urljoin(base_url.rstrip('/') + '/', 'api/3/action/package_search')
    
    # Build query parameters
    params = {
        'q': query,
        'rows': rows,
        'start': start,
    }
    
    # Add any additional parameters
    for key, value in kwargs.items():
        params[key] = value
    
    # Build full URL with query parameters
    query_string = '&'.join(f"{k}={quote(str(v))}" for k, v in params.items())
    full_url = f"{api_url}?{query_string}"
    
    try:
        response = retry_request(full_url)
        data = json.loads(response.content.decode('utf-8'))
        
        if data.get('success'):
            return {
                'count': data['result']['count'],
                'results': data['result']['results'],
                'success': True
            }
        else:
            return {
                'count': 0,
                'results': [],
                'success': False,
                'error': data.get('error', {})
            }
    except HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(
                f"CKAN portal not found at {base_url}.\n"
                f"Please verify the portal URL is correct."
            ) from e
        else:
            raise RuntimeError(f"HTTP error {e.response.status_code} when searching CKAN portal at {base_url}: {e.response.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse CKAN search response: {str(e)}") from e
    except Exception as e:
        if isinstance(e, (RuntimeError, ValueError)):
            raise
        raise RuntimeError(f"Failed to search CKAN portal at {base_url}: {str(e)}") from e


def get_ckan_package(base_url: str, package_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific CKAN package/dataset.
    
    Uses the CKAN package_show API endpoint to retrieve complete metadata
    for a dataset including all resources.
    
    Args:
        base_url: Base URL of the CKAN portal
        package_id: Package identifier (name or ID)
    
    Returns:
        Dictionary containing complete package metadata including:
            - title: Dataset title
            - name: Dataset name/slug
            - notes: Dataset description
            - resources: List of resource dictionaries
            - metadata_created: Creation timestamp
            - metadata_modified: Last modification timestamp
            - organization: Organization information
            - tags: List of tags
    
    Example:
        >>> package = get_ckan_package(
        ...     'https://open.canada.ca/data',
        ...     'census-2021-population'
        ... )
        >>> print(package['title'])
        >>> print(f"Resources: {len(package['resources'])}")
    
    Raises:
        RuntimeError: If the package cannot be retrieved
    """
    # Build API endpoint URL
    api_url = urljoin(base_url.rstrip('/') + '/', 'api/3/action/package_show')
    full_url = f"{api_url}?id={quote(package_id)}"
    
    try:
        response = retry_request(full_url)
        data = json.loads(response.content.decode('utf-8'))
        
        if data.get('success'):
            return data['result']
        else:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            raise RuntimeError(f"CKAN API error: {error_msg}")
    except HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(
                f"Dataset '{package_id}' not found in the CKAN portal at {base_url}.\n"
                f"Please verify:\n"
                f"  1. The dataset ID is correct\n"
                f"  2. The dataset exists in the portal\n"
                f"  3. You can browse datasets at: {base_url.replace('/data', '/en/open-data') if 'open.canada.ca' in base_url else base_url}"
            ) from e
        else:
            raise RuntimeError(f"HTTP error {e.response.status_code} when accessing CKAN package {package_id}: {e.response.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse CKAN response: {str(e)}") from e
    except Exception as e:
        if isinstance(e, (RuntimeError, ValueError)):
            raise
        raise RuntimeError(f"Failed to get CKAN package {package_id} from {base_url}: {str(e)}") from e


def list_ckan_resources(
    base_url: str,
    package_id: str,
    format_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List resources for a CKAN package/dataset with optional format filtering.
    
    Args:
        base_url: Base URL of the CKAN portal
        package_id: Package identifier (name or ID)
        format_filter: Optional format filter (e.g., 'CSV', 'JSON', 'GeoJSON')
            If None, returns all resources
    
    Returns:
        List of resource dictionaries, each containing:
            - id: Resource ID
            - name: Resource name
            - url: Download URL
            - format: File format
            - description: Resource description
            - created: Creation timestamp
            - last_modified: Last modification timestamp
            - size: File size (if available)
    
    Example:
        >>> # Get all CSV resources
        >>> csv_resources = list_ckan_resources(
        ...     'https://open.canada.ca/data',
        ...     'census-data',
        ...     format_filter='CSV'
        ... )
        >>> for resource in csv_resources:
        ...     print(f"{resource['name']}: {resource['url']}")
    
    Notes:
        - Format comparison is case-insensitive
        - Returns resources in the order they appear in the package
    """
    package = get_ckan_package(base_url, package_id)
    resources = package.get('resources', [])
    
    # Apply format filter if specified
    if format_filter:
        format_lower = format_filter.lower()
        resources = [
            r for r in resources
            if r.get('format', '').lower() == format_lower
        ]
    
    return resources


def download_ckan_resource(
    resource_url: str,
    output_dir: str,
    resource_name: Optional[str] = None,
    resource_format: Optional[str] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Download a CKAN resource to the specified output directory.
    
    Args:
        resource_url: Direct URL to the resource file
        output_dir: Directory where the file will be saved
        resource_name: Optional resource name for the filename (defaults to 'resource')
        resource_format: Optional file format/extension (defaults to 'dat')
        max_retries: Maximum number of download retry attempts (default: 3)
    
    Returns:
        Dictionary containing:
            - file: Path to the downloaded file
            - url: Source URL
            - format: File format
    
    Example:
        >>> result = download_ckan_resource(
        ...     'https://open.canada.ca/data/dataset/123/resource.csv',
        ...     './data',
        ...     resource_name='census_2021',
        ...     resource_format='csv'
        ... )
        >>> print(result['file'])
    
    Notes:
        - Creates output directory if it doesn't exist
        - Sanitizes filenames to prevent path traversal
        - Writes provenance metadata automatically
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Sanitize resource name
    safe_name = 'resource'
    if resource_name:
        # Remove any path separators and only allow safe characters
        safe_name = "".join(c for c in resource_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        # Remove any remaining path separators
        safe_name = safe_name.replace('/', '_').replace('\\', '_').replace('..', '_')
    
    # Ensure name is not empty
    if not safe_name:
        safe_name = 'resource'
    
    # Sanitize format
    safe_format = 'dat'
    if resource_format:
        safe_format = "".join(c for c in resource_format if c.isalnum()).lower()
    
    if not safe_format:
        safe_format = 'dat'
    
    # Build output file path
    file_name = f"{safe_name}.{safe_format}"
    output_file = output_path / file_name
    
    # Download the file
    try:
        download_file(
            resource_url,
            str(output_file),
            max_retries=max_retries,
            validate_content_type=True
        )
        
        return {
            'file': str(output_file),
            'url': resource_url,
            'format': safe_format
        }
    except Exception as e:
        raise RuntimeError(f"Failed to download CKAN resource from {resource_url}: {str(e)}")


class CKANProvider(Provider):
    """
    Generic CKAN (Comprehensive Knowledge Archive Network) data provider.
    
    This provider implements the standard Provider interface for CKAN portals.
    It can work with any CKAN instance by configuring the base URL. CKAN is
    a widely-used open-source data portal platform.
    
    The provider supports:
    - Searching datasets using CKAN's package_search API
    - Resolving resources by format (CSV, JSON, GeoJSON, etc.)
    - Fetching resources with automatic format filtering
    
    Attributes:
        name: Provider identifier (default: 'ckan')
        base_url: Base URL of the CKAN portal
    
    Example:
        >>> # Using Open Canada portal
        >>> provider = CKANProvider(
        ...     name='open_canada',
        ...     base_url='https://open.canada.ca/data'
        ... )
        >>> results = provider.search('census')
        >>> for ref in results:
        ...     print(ref.canonical_id)
        
        >>> # Download a specific dataset
        >>> ref = DatasetRef(
        ...     provider='open_canada',
        ...     id='census-2021',
        ...     params={'format': 'CSV'}
        ... )
        >>> result = provider.fetch(ref, './data')
        >>> print(result['files'])
    """
    
    def __init__(self, name: str = 'ckan', base_url: Optional[str] = None):
        """
        Initialize the CKAN provider.
        
        Args:
            name: Unique provider identifier (default: 'ckan')
            base_url: Base URL of the CKAN portal. Can also be set via
                     DatasetRef params with key 'base_url'
        
        Raises:
            ValueError: If base_url is not provided and not in DatasetRef params
        """
        super().__init__(name)
        self.base_url = base_url
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for datasets in the CKAN portal.
        
        Args:
            query: Search query string (supports SOLR query syntax)
            **kwargs: Additional search parameters:
                - base_url: Override the provider's base URL
                - rows: Number of results to return (default: 10)
                - start: Offset for pagination (default: 0)
                - Other CKAN API parameters (e.g., fq for filtering)
        
        Returns:
            List of DatasetRef objects matching the query
        
        Example:
            >>> provider = CKANProvider(base_url='https://open.canada.ca/data')
            >>> results = provider.search('housing', rows=5)
            >>> for ref in results:
            ...     print(f"{ref.id}: {ref.metadata.get('title')}")
        
        Raises:
            ValueError: If base_url is not configured
        """
        # Get base URL from kwargs or instance
        base_url = kwargs.pop('base_url', self.base_url)
        if not base_url:
            raise ValueError(
                "base_url must be provided either in provider initialization or search kwargs"
            )
        
        # Search CKAN portal (kwargs already contains rows if specified)
        search_results = search_ckan_datasets(base_url, query, **kwargs)
        
        # Convert results to DatasetRef objects
        refs = []
        for package in search_results.get('results', []):
            resources = package.get('resources', [])
            downloadable_resources = [r for r in resources if _resource_is_downloadable(r)]
            if not downloadable_resources:
                # Skip packages that only link to landing pages or documentation
                continue
            # Get resource formats
            formats = [r.get('format', '').upper() for r in downloadable_resources]
            formats = [f for f in formats if f]  # Remove empty strings
            
            ref = DatasetRef(
                provider=self.name,
                id=package.get('name', package.get('id')),
                params={'base_url': base_url},
                metadata={
                    'title': package.get('title', ''),
                    'description': package.get('notes', ''),
                    'organization': package.get('organization', {}).get('title', ''),
                    'num_resources': len(downloadable_resources),
                    'formats': formats,
                },
                tags=[tag.get('name', '') for tag in package.get('tags', [])]
            )
            refs.append(ref)
        
        return refs
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve a CKAN dataset reference into resource metadata.
        
        Args:
            ref: Dataset reference with CKAN package ID
                Required params:
                    - base_url: CKAN portal base URL (or set in provider)
                Optional params:
                    - format: Filter resources by format (e.g., 'CSV', 'JSON')
                    - resource_id: Specific resource ID to resolve
        
        Returns:
            Dictionary containing:
                - resources: List of resource dictionaries
                - package_id: Package identifier
                - title: Dataset title
                - provider: Provider name
                - base_url: CKAN portal URL
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='ckan',
            ...     id='census-data',
            ...     params={'base_url': 'https://open.canada.ca/data', 'format': 'CSV'}
            ... )
            >>> metadata = provider.resolve(ref)
            >>> for resource in metadata['resources']:
            ...     print(f"{resource['name']}: {resource['url']}")
        
        Raises:
            ValueError: If base_url is not configured
        """
        # Get base URL from params or instance
        base_url = ref.params.get('base_url', self.base_url)
        if not base_url:
            raise ValueError(
                "base_url must be provided in DatasetRef params or provider initialization"
            )
        
        # Get format filter if specified
        format_filter = ref.params.get('format')
        
        # Get specific resource ID if specified
        resource_id = ref.params.get('resource_id')
        
        # Get package details
        package = get_ckan_package(base_url, ref.id)
        
        # Get resources with optional format filter
        resources = package.get('resources', [])
        
        # Filter by specific resource ID if provided
        if resource_id:
            resources = [r for r in resources if r.get('id') == resource_id]
        else:
            resources = [r for r in resources if _resource_is_downloadable(r)]
            # Otherwise filter by format if provided
            if format_filter:
                format_lower = format_filter.lower()
                resources = [
                    r for r in resources
                    if r.get('format', '').lower() == format_lower
                ]
        
        return {
            'resources': resources,
            'package_id': ref.id,
            'title': package.get('title', ref.id),
            'description': package.get('notes', ''),
            'provider': self.name,
            'base_url': base_url,
        }
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download CKAN resources to the specified output directory.
        
        Args:
            ref: Dataset reference with CKAN package ID
                Required params:
                    - base_url: CKAN portal base URL (or set in provider)
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
                - base_url: CKAN portal URL
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='ckan',
            ...     id='census-data',
            ...     params={'base_url': 'https://open.canada.ca/data', 'format': 'CSV'}
            ... )
            >>> result = provider.fetch(ref, './data')
            >>> print(f"Downloaded {len(result['files'])} files")
            >>> for file_path in result['files']:
            ...     print(file_path)
        
        Raises:
            ValueError: If base_url is not configured or no resources found
        """
        max_retries = kwargs.get('max_retries', 3)
        
        # Resolve resources
        resolved = self.resolve(ref)
        resources = resolved['resources']
        
        if not resources:
            raise ValueError(
                f"No resources found for package '{ref.id}' with specified filters. "
                f"Try without format filter or check package exists."
            )
        
        # Download each resource
        downloaded_files = []
        resource_metadata = []
        
        for resource in resources:
            resource_url = resource.get('url')
            if not resource_url:
                continue
            
            resource_name = resource.get('name', resource.get('id', 'resource'))
            resource_format = resource.get('format', 'dat')
            
            try:
                result = download_ckan_resource(
                    resource_url,
                    output_dir,
                    resource_name=resource_name,
                    resource_format=resource_format,
                    max_retries=max_retries
                )
                downloaded_files.append(result['file'])
                resource_metadata.append({
                    'id': resource.get('id'),
                    'name': resource_name,
                    'format': resource_format,
                    'url': resource_url,
                    'local_path': result['file']
                })
            except Exception as e:
                # Log error but continue with other resources
                print(f"Warning: Failed to download resource '{resource_name}': {str(e)}")
                resource_metadata.append({
                    'id': resource.get('id'),
                    'name': resource_name,
                    'format': resource_format,
                    'url': resource_url,
                    'error': str(e)
                })
        
        return {
            'dataset_id': f"{self.name}_{ref.id}",
            'provider': self.name,
            'files': downloaded_files,
            'resources': resource_metadata,
            'base_url': resolved['base_url'],
            'package_id': ref.id,
        }
