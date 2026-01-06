"""
Bank of Canada Valet API data provider.

This module provides functionality to fetch time series data and metadata from the
Bank of Canada's Valet API. The Valet API provides access to economic and financial
data published by the Bank of Canada, including exchange rates, interest rates,
and other key economic indicators.

API Documentation: https://www.bankofcanada.ca/valet/docs
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from publicdata_ca.http import retry_request, download_file
from publicdata_ca.provider import Provider, DatasetRef


def get_valet_series_metadata(series_name: str) -> Dict[str, Any]:
    """
    Get metadata for a Bank of Canada Valet series.
    
    Retrieves detailed metadata for a specific series including description,
    frequency, units, and other attributes.
    
    Args:
        series_name: Series identifier (e.g., 'FXUSDCAD', 'V80691311')
    
    Returns:
        Dictionary containing:
            - label: Series label/description
            - description: Detailed description
            - frequency: Data frequency (daily, monthly, etc.)
            - series_name: Series identifier
            - Additional metadata fields
    
    Example:
        >>> metadata = get_valet_series_metadata('FXUSDCAD')
        >>> print(metadata['label'])
        'US dollar, closing daily average rate in Canadian dollars'
    
    Raises:
        RuntimeError: If the metadata cannot be retrieved
    """
    # Build metadata URL
    url = f"https://www.bankofcanada.ca/valet/series/{series_name}/json"
    
    try:
        response = retry_request(url)
        data = json.loads(response.read().decode('utf-8'))
        
        # Valet API returns series info under 'seriesDetail' key
        if 'seriesDetail' in data and series_name in data['seriesDetail']:
            return data['seriesDetail'][series_name]
        else:
            # Return minimal metadata if detailed metadata not available
            return {
                'series_name': series_name,
                'label': f'Bank of Canada Series {series_name}',
            }
    except Exception as e:
        raise RuntimeError(f"Failed to get metadata for series {series_name}: {str(e)}")


def fetch_valet_series(
    series_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    output_format: str = 'json'
) -> Dict[str, Any]:
    """
    Fetch time series data from Bank of Canada Valet API.
    
    Downloads observations for a specific series within the specified date range.
    Returns the data as a structured dictionary that can be converted to a pandas
    DataFrame for tidy data analysis.
    
    Args:
        series_name: Series identifier (e.g., 'FXUSDCAD', 'V80691311')
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        output_format: Output format - 'json' or 'csv' (default: 'json')
    
    Returns:
        Dictionary containing:
            - series_name: Series identifier
            - observations: List of observation dictionaries with 'd' (date) and 'v' (value) keys
            - metadata: Series metadata
            - url: Source URL
    
    Example:
        >>> data = fetch_valet_series('FXUSDCAD', '2023-01-01', '2023-01-31')
        >>> print(len(data['observations']))
        >>> for obs in data['observations'][:5]:
        ...     print(f"{obs['d']}: {obs['v']}")
    
    Raises:
        RuntimeError: If the data cannot be fetched
    """
    # Build query parameters
    params = []
    if start_date:
        params.append(f"start_date={start_date}")
    if end_date:
        params.append(f"end_date={end_date}")
    
    # Build URL
    query_string = '&'.join(params) if params else ''
    url = f"https://www.bankofcanada.ca/valet/observations/{series_name}/{output_format}"
    if query_string:
        url = f"{url}?{query_string}"
    
    try:
        response = retry_request(url)
        data = json.loads(response.read().decode('utf-8'))
        
        # Extract observations
        observations = data.get('observations', [])
        
        # Get series metadata from the response
        series_detail = {}
        if 'seriesDetail' in data and series_name in data['seriesDetail']:
            series_detail = data['seriesDetail'][series_name]
        
        return {
            'series_name': series_name,
            'observations': observations,
            'metadata': series_detail,
            'url': url,
            'start_date': start_date,
            'end_date': end_date,
        }
    except Exception as e:
        raise RuntimeError(f"Failed to fetch series {series_name}: {str(e)}")


def download_valet_series(
    series_name: str,
    output_dir: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip_existing: bool = True,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Download a Bank of Canada Valet series to CSV file.
    
    Fetches time series data and saves it as a CSV file with provenance metadata.
    The data is saved in tidy format with date and value columns.
    
    Args:
        series_name: Series identifier (e.g., 'FXUSDCAD')
        output_dir: Directory where the file will be saved
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        skip_existing: If True, skip download if file exists (default: True)
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Dictionary containing:
            - dataset_id: Dataset identifier
            - provider: 'boc_valet'
            - files: List of downloaded file paths
            - url: Source URL
            - series_name: Series identifier
            - metadata: Series metadata
            - observations: Number of observations
    
    Example:
        >>> result = download_valet_series('FXUSDCAD', './data', '2023-01-01', '2023-12-31')
        >>> print(result['files'])
        ['./data/FXUSDCAD.csv']
    
    Notes:
        - Creates output directory if it doesn't exist
        - Writes provenance metadata as .meta.json sidecar file
        - Returns tidy data format (date, value columns)
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Define output file
    output_file = output_path / f"{series_name}.csv"
    
    # Skip if file exists and skip_existing is True
    if skip_existing and output_file.exists():
        return {
            'dataset_id': f'boc_valet_{series_name}',
            'provider': 'boc_valet',
            'files': [str(output_file)],
            'url': f"https://www.bankofcanada.ca/valet/observations/{series_name}/json",
            'series_name': series_name,
            'skipped': True
        }
    
    # Fetch the data
    data = fetch_valet_series(series_name, start_date, end_date)
    
    # Convert to tidy format and save as CSV
    import pandas as pd
    
    observations = data['observations']
    if not observations:
        raise RuntimeError(f"No observations returned for series {series_name}")
    
    # Create DataFrame in tidy format
    df = pd.DataFrame(observations)
    
    # Rename columns for clarity (d -> date, v -> value)
    if 'd' in df.columns and 'v' in df.columns:
        df = df.rename(columns={'d': 'date', 'v': 'value'})
    
    # Add series name column for context
    df['series_name'] = series_name
    
    # Reorder columns: date, series_name, value
    df = df[['date', 'series_name', 'value']]
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    
    # Write provenance metadata
    _write_valet_metadata(
        str(output_file),
        data['url'],
        series_name,
        data['metadata'],
        start_date,
        end_date,
        len(observations)
    )
    
    return {
        'dataset_id': f'boc_valet_{series_name}',
        'provider': 'boc_valet',
        'files': [str(output_file)],
        'url': data['url'],
        'series_name': series_name,
        'metadata': data['metadata'],
        'observations': len(observations),
        'skipped': False
    }


def _write_valet_metadata(
    file_path: str,
    source_url: str,
    series_name: str,
    series_metadata: Dict[str, Any],
    start_date: Optional[str],
    end_date: Optional[str],
    num_observations: int
) -> None:
    """
    Write provenance metadata for a Valet series file.
    
    Creates a .meta.json sidecar file with:
    - Source URL
    - Series name and metadata
    - Date range
    - Number of observations
    - Standard provenance info (timestamp, hash, size)
    
    Args:
        file_path: Path to the data file
        source_url: Valet API URL
        series_name: Series identifier
        series_metadata: Series metadata from API
        start_date: Start date of data range
        end_date: End date of data range
        num_observations: Number of observations in the file
    """
    from publicdata_ca.provenance import write_provenance_metadata
    
    # Build additional metadata
    additional_metadata = {
        'provider': 'boc_valet',
        'series_name': series_name,
        'observations': num_observations,
    }
    
    # Add date range if specified
    if start_date:
        additional_metadata['start_date'] = start_date
    if end_date:
        additional_metadata['end_date'] = end_date
    
    # Add series metadata
    if series_metadata:
        additional_metadata['series_metadata'] = series_metadata
    
    try:
        write_provenance_metadata(
            file_path,
            source_url,
            content_type='application/json',
            additional_metadata=additional_metadata
        )
    except Exception:
        # Don't fail the download if metadata writing fails
        pass


class ValetProvider(Provider):
    """
    Bank of Canada Valet API data provider implementation.
    
    This provider implements the standard Provider interface for Bank of Canada
    Valet API datasets. It supports fetching time series data with date ranges
    and returning tidy data with provenance metadata.
    
    Example:
        >>> provider = ValetProvider()
        >>> ref = DatasetRef(
        ...     provider='boc_valet',
        ...     id='FXUSDCAD',
        ...     params={'start_date': '2023-01-01', 'end_date': '2023-12-31'}
        ... )
        >>> result = provider.fetch(ref, './data/raw')
        >>> print(result['files'])
    """
    
    def __init__(self, name: str = 'boc_valet'):
        """Initialize the Bank of Canada Valet provider."""
        super().__init__(name)
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for Bank of Canada series by keyword.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
        
        Returns:
            List of DatasetRef objects matching the query
        
        Note:
            This is a placeholder implementation. The Valet API does not
            provide a search endpoint. Full search functionality would require
            maintaining a local index of series or using the series list endpoint.
        """
        # Placeholder - Valet API doesn't have a built-in search endpoint
        # Would need to fetch the full series list and filter locally
        return []
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve a Valet dataset reference into download metadata.
        
        Args:
            ref: Dataset reference with series identifier
        
        Returns:
            Dictionary containing download URL, format, and metadata
        
        Example:
            >>> ref = DatasetRef(provider='boc_valet', id='FXUSDCAD')
            >>> metadata = provider.resolve(ref)
            >>> print(metadata['url'])
        """
        series_name = ref.id
        
        # Get date range from params
        start_date = ref.params.get('start_date')
        end_date = ref.params.get('end_date')
        
        # Build URL with date range
        params = []
        if start_date:
            params.append(f"start_date={start_date}")
        if end_date:
            params.append(f"end_date={end_date}")
        
        query_string = '&'.join(params) if params else ''
        url = f"https://www.bankofcanada.ca/valet/observations/{series_name}/json"
        if query_string:
            url = f"{url}?{query_string}"
        
        return {
            'url': url,
            'format': 'json',
            'series_name': series_name,
            'title': ref.metadata.get('title', f'Bank of Canada Series {series_name}'),
            'provider': self.name,
            'start_date': start_date,
            'end_date': end_date,
        }
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download a Bank of Canada Valet series to the specified output directory.
        
        Args:
            ref: Dataset reference with series identifier
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters (skip_existing, max_retries, etc.)
        
        Returns:
            Dictionary containing downloaded files and metadata
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='boc_valet',
            ...     id='FXUSDCAD',
            ...     params={'start_date': '2023-01-01', 'end_date': '2023-12-31'}
            ... )
            >>> result = provider.fetch(ref, './data/raw')
            >>> print(result['files'])
        """
        # Extract parameters
        skip_existing = kwargs.get('skip_existing', True)
        max_retries = kwargs.get('max_retries', 3)
        start_date = ref.params.get('start_date')
        end_date = ref.params.get('end_date')
        
        # Use the existing download_valet_series function
        result = download_valet_series(
            series_name=ref.id,
            output_dir=output_dir,
            start_date=start_date,
            end_date=end_date,
            skip_existing=skip_existing,
            max_retries=max_retries
        )
        
        return result
