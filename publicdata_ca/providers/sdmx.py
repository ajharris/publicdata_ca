"""
SDMX (Statistical Data and Metadata eXchange) generic data provider.

This module provides functionality to fetch data series and metadata from
SDMX REST API endpoints. SDMX is a widely-used ISO standard for exchanging
statistical data and metadata, used by many statistical organizations worldwide
including Statistics Canada, OECD, ECB, Eurostat, and many others.

The provider supports:
- Fetching data series from SDMX REST endpoints
- Retrieving metadata about data structures and dataflows
- Resolving data references with filters and parameters
- Working with multiple SDMX data providers via base URL configuration

Supported formats:
- SDMX-ML (XML): Standard SDMX format
- SDMX-JSON: JSON format for data messages

Note: This implementation focuses on direct series fetch and metadata retrieval.
Search functionality can be added later as SDMX search endpoints vary across providers.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote
from publicdata_ca.http import retry_request, download_file
from publicdata_ca.provider import Provider, DatasetRef


# SDMX XML namespaces (commonly used)
SDMX_NAMESPACES = {
    'message': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
    'generic': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic',
    'common': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
    'structure': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
}


def get_sdmx_dataflow(
    base_url: str,
    agency_id: str,
    dataflow_id: str,
    version: str = 'latest'
) -> Dict[str, Any]:
    """
    Get metadata about a specific SDMX dataflow.
    
    Uses the SDMX REST API dataflow endpoint to retrieve metadata about
    a dataflow including its name, description, and structure reference.
    
    Args:
        base_url: Base URL of the SDMX endpoint (e.g., 'https://sdmx.oecd.org')
        agency_id: Agency identifier (e.g., 'OECD', 'ESTAT')
        dataflow_id: Dataflow identifier
        version: Version of the dataflow (default: 'latest')
    
    Returns:
        Dictionary containing dataflow metadata including:
            - id: Dataflow ID
            - agency_id: Agency ID
            - version: Version
            - name: Dataflow name (multilingual)
            - description: Dataflow description (if available)
            - structure_ref: Reference to the data structure definition
    
    Example:
        >>> metadata = get_sdmx_dataflow(
        ...     'https://sdmx.oecd.org/public/rest',
        ...     'OECD',
        ...     'QNA'
        ... )
        >>> print(metadata['name'])
    
    Raises:
        RuntimeError: If the dataflow metadata cannot be retrieved
    """
    # Build SDMX REST API URL for dataflow
    # Format: /dataflow/{agencyID}/{resourceID}/{version}
    api_path = f'dataflow/{agency_id}/{dataflow_id}/{version}'
    api_url = urljoin(base_url.rstrip('/') + '/', api_path)
    
    try:
        response = retry_request(api_url)
        content = response.content.decode('utf-8')
        
        # Parse XML response
        root = ET.fromstring(content)
        
        # Find dataflow element (handle namespaced elements)
        dataflow_elem = None
        for elem in root.iter():
            if 'Dataflow' in elem.tag:
                dataflow_elem = elem
                break
        
        if dataflow_elem is None:
            raise RuntimeError("No dataflow found in response")
        
        # Extract metadata
        metadata = {
            'id': dataflow_id,
            'agency_id': agency_id,
            'version': version,
            'name': {},
            'description': {},
        }
        
        # Extract names (multilingual)
        for name_elem in dataflow_elem.iter():
            if 'Name' in name_elem.tag and name_elem.text:
                lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                metadata['name'][lang] = name_elem.text
        
        # Extract descriptions (multilingual)
        for desc_elem in dataflow_elem.iter():
            if 'Description' in desc_elem.tag and desc_elem.text:
                lang = desc_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                metadata['description'][lang] = desc_elem.text
        
        # Extract structure reference
        for ref_elem in dataflow_elem.iter():
            if 'Structure' in ref_elem.tag:
                for ref_child in ref_elem.iter():
                    if 'Ref' in ref_child.tag:
                        metadata['structure_ref'] = {
                            'agency_id': ref_child.get('agencyID'),
                            'id': ref_child.get('id'),
                            'version': ref_child.get('version'),
                        }
                        break
        
        return metadata
        
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse SDMX XML response: {str(e)}")
    except Exception as e:
        raise RuntimeError(
            f"Failed to get SDMX dataflow {dataflow_id} from {base_url}: {str(e)}"
        )


def get_sdmx_data_structure(
    base_url: str,
    agency_id: str,
    dsd_id: str,
    version: str = 'latest'
) -> Dict[str, Any]:
    """
    Get metadata about a specific SDMX Data Structure Definition (DSD).
    
    Uses the SDMX REST API datastructure endpoint to retrieve metadata about
    dimensions, attributes, and measures defined in the DSD.
    
    Args:
        base_url: Base URL of the SDMX endpoint
        agency_id: Agency identifier
        dsd_id: Data Structure Definition identifier
        version: Version of the DSD (default: 'latest')
    
    Returns:
        Dictionary containing DSD metadata including:
            - id: DSD ID
            - agency_id: Agency ID
            - version: Version
            - name: DSD name (multilingual)
            - dimensions: List of dimension metadata
            - attributes: List of attribute metadata
            - measures: List of measure metadata
    
    Example:
        >>> dsd = get_sdmx_data_structure(
        ...     'https://sdmx.oecd.org/public/rest',
        ...     'OECD',
        ...     'QNA'
        ... )
        >>> print(len(dsd['dimensions']))
    
    Raises:
        RuntimeError: If the DSD metadata cannot be retrieved
    """
    # Build SDMX REST API URL for datastructure
    # Format: /datastructure/{agencyID}/{resourceID}/{version}
    api_path = f'datastructure/{agency_id}/{dsd_id}/{version}'
    api_url = urljoin(base_url.rstrip('/') + '/', api_path)
    
    try:
        response = retry_request(api_url)
        content = response.content.decode('utf-8')
        
        # Parse XML response
        root = ET.fromstring(content)
        
        # Find DataStructure element
        dsd_elem = None
        for elem in root.iter():
            if 'DataStructure' in elem.tag:
                dsd_elem = elem
                break
        
        if dsd_elem is None:
            raise RuntimeError("No DataStructure found in response")
        
        # Extract metadata
        metadata = {
            'id': dsd_id,
            'agency_id': agency_id,
            'version': version,
            'name': {},
            'dimensions': [],
            'attributes': [],
            'measures': [],
        }
        
        # Extract names
        for name_elem in dsd_elem.iter():
            if 'Name' in name_elem.tag and name_elem.text:
                lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                metadata['name'][lang] = name_elem.text
        
        # Extract dimensions
        for dim_elem in dsd_elem.iter():
            if 'Dimension' in dim_elem.tag:
                dim_id = dim_elem.get('id')
                if dim_id:
                    dim_info = {'id': dim_id}
                    # Get dimension names
                    for name_elem in dim_elem.iter():
                        if 'Name' in name_elem.tag and name_elem.text:
                            lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                            if 'name' not in dim_info:
                                dim_info['name'] = {}
                            dim_info['name'][lang] = name_elem.text
                    metadata['dimensions'].append(dim_info)
        
        # Extract attributes
        for attr_elem in dsd_elem.iter():
            if 'Attribute' in attr_elem.tag and 'AttributeList' not in attr_elem.tag:
                attr_id = attr_elem.get('id')
                if attr_id:
                    attr_info = {'id': attr_id}
                    # Get attribute names
                    for name_elem in attr_elem.iter():
                        if 'Name' in name_elem.tag and name_elem.text:
                            lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                            if 'name' not in attr_info:
                                attr_info['name'] = {}
                            attr_info['name'][lang] = name_elem.text
                    metadata['attributes'].append(attr_info)
        
        # Extract measures
        for measure_elem in dsd_elem.iter():
            if 'PrimaryMeasure' in measure_elem.tag:
                measure_id = measure_elem.get('id')
                if measure_id:
                    measure_info = {'id': measure_id}
                    # Get measure names
                    for name_elem in measure_elem.iter():
                        if 'Name' in name_elem.tag and name_elem.text:
                            lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                            if 'name' not in measure_info:
                                measure_info['name'] = {}
                            measure_info['name'][lang] = name_elem.text
                    metadata['measures'].append(measure_info)
        
        return metadata
        
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse SDMX XML response: {str(e)}")
    except Exception as e:
        raise RuntimeError(
            f"Failed to get SDMX data structure {dsd_id} from {base_url}: {str(e)}"
        )


def fetch_sdmx_data(
    base_url: str,
    dataflow: str,
    key: Optional[str] = None,
    provider_ref: Optional[str] = None,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    format: str = 'sdmx-ml',
    **kwargs
) -> Dict[str, Any]:
    """
    Fetch data from an SDMX REST API endpoint.
    
    Uses the SDMX REST API data endpoint to retrieve time series data.
    
    Args:
        base_url: Base URL of the SDMX endpoint
        dataflow: Dataflow identifier in format 'AGENCY,DATAFLOW,VERSION' or just 'DATAFLOW'
        key: Data key/filter (e.g., 'A...' for all dimensions). If None, fetches all data.
        provider_ref: Provider reference/agency (if required by the endpoint)
        start_period: Start period for time filter (ISO format, e.g., '2020-01')
        end_period: End period for time filter (ISO format, e.g., '2023-12')
        format: Response format ('sdmx-ml' for XML, 'sdmx-json' for JSON)
        **kwargs: Additional parameters (e.g., dimensionAtObservation, detail)
    
    Returns:
        Dictionary containing:
            - raw_data: Raw response content (XML string or JSON dict)
            - format: Response format
            - url: Request URL
            - dataflow: Dataflow identifier
    
    Example:
        >>> data = fetch_sdmx_data(
        ...     'https://sdmx.oecd.org/public/rest',
        ...     'OECD,QNA,1.0',
        ...     key='AUS...',
        ...     start_period='2020-Q1',
        ...     end_period='2023-Q4'
        ... )
        >>> print(data['format'])
    
    Raises:
        RuntimeError: If the data cannot be fetched
    """
    # Parse dataflow identifier
    if ',' in dataflow:
        # Format: AGENCY,DATAFLOW,VERSION
        parts = dataflow.split(',')
        if len(parts) >= 2:
            dataflow_path = '/'.join(parts)
        else:
            dataflow_path = dataflow
    else:
        # Just dataflow ID, may need agency prefix
        if provider_ref:
            dataflow_path = f"{provider_ref}/{dataflow}"
        else:
            dataflow_path = dataflow
    
    # Build data query path
    # Format: /data/{dataflow}/{key}
    if key:
        api_path = f'data/{dataflow_path}/{key}'
    else:
        api_path = f'data/{dataflow_path}'
    
    # Add query parameters
    params = []
    
    if start_period:
        params.append(f'startPeriod={quote(start_period)}')
    
    if end_period:
        params.append(f'endPeriod={quote(end_period)}')
    
    # Add format parameter if not XML (XML is often default)
    if format == 'sdmx-json':
        params.append('format=sdmx-json')
    
    # Add any additional parameters
    for key_param, value in kwargs.items():
        params.append(f'{key_param}={quote(str(value))}')
    
    # Build full URL
    api_url = urljoin(base_url.rstrip('/') + '/', api_path)
    if params:
        api_url = f"{api_url}?{'&'.join(params)}"
    
    try:
        response = retry_request(api_url)
        content = response.content.decode('utf-8')
        
        # Parse based on format
        if format == 'sdmx-json':
            try:
                data_parsed = json.loads(content)
                raw_data = data_parsed
            except json.JSONDecodeError:
                raw_data = content
        else:
            # SDMX-ML (XML)
            raw_data = content
        
        return {
            'raw_data': raw_data,
            'format': format,
            'url': api_url,
            'dataflow': dataflow,
        }
        
    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch SDMX data from {base_url} for dataflow {dataflow}: {str(e)}"
        )


def download_sdmx_data(
    base_url: str,
    dataflow: str,
    output_path: str,
    key: Optional[str] = None,
    provider_ref: Optional[str] = None,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    format: str = 'sdmx-ml',
    max_retries: int = 3,
    **kwargs
) -> Dict[str, Any]:
    """
    Download SDMX data to a file.
    
    Fetches data from an SDMX REST API endpoint and saves it to a local file.
    
    Args:
        base_url: Base URL of the SDMX endpoint
        dataflow: Dataflow identifier
        output_path: Full path where the file will be saved
        key: Data key/filter (optional)
        provider_ref: Provider reference/agency (optional)
        start_period: Start period for time filter (optional)
        end_period: End period for time filter (optional)
        format: Response format ('sdmx-ml' or 'sdmx-json', default: 'sdmx-ml')
        max_retries: Maximum number of download retry attempts (default: 3)
        **kwargs: Additional SDMX API parameters
    
    Returns:
        Dictionary containing:
            - file: Path to the downloaded file
            - url: Source URL
            - format: File format
            - dataflow: Dataflow identifier
    
    Example:
        >>> result = download_sdmx_data(
        ...     'https://sdmx.oecd.org/public/rest',
        ...     'OECD,QNA,1.0',
        ...     './data/oecd_qna.xml',
        ...     key='AUS...',
        ...     start_period='2020-Q1'
        ... )
        >>> print(result['file'])
    
    Notes:
        - Creates output directory if it doesn't exist
        - Writes provenance metadata automatically
    """
    # Create output directory if needed
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse dataflow identifier for URL construction
    if ',' in dataflow:
        parts = dataflow.split(',')
        if len(parts) >= 2:
            dataflow_path = '/'.join(parts)
        else:
            dataflow_path = dataflow
    else:
        if provider_ref:
            dataflow_path = f"{provider_ref}/{dataflow}"
        else:
            dataflow_path = dataflow
    
    # Build data query path
    if key:
        api_path = f'data/{dataflow_path}/{key}'
    else:
        api_path = f'data/{dataflow_path}'
    
    # Add query parameters
    params = []
    
    if start_period:
        params.append(f'startPeriod={quote(start_period)}')
    
    if end_period:
        params.append(f'endPeriod={quote(end_period)}')
    
    if format == 'sdmx-json':
        params.append('format=sdmx-json')
    
    for key_param, value in kwargs.items():
        params.append(f'{key_param}={quote(str(value))}')
    
    # Build full URL
    api_url = urljoin(base_url.rstrip('/') + '/', api_path)
    if params:
        api_url = f"{api_url}?{'&'.join(params)}"
    
    # Download the file
    try:
        download_file(
            api_url,
            output_path,
            max_retries=max_retries,
            validate_content_type=False  # SDMX may use various content types
        )
        
        return {
            'file': output_path,
            'url': api_url,
            'format': format,
            'dataflow': dataflow,
        }
    except Exception as e:
        raise RuntimeError(
            f"Failed to download SDMX data from {base_url} for dataflow {dataflow}: {str(e)}"
        )


class SDMXProvider(Provider):
    """
    Generic SDMX (Statistical Data and Metadata eXchange) data provider.
    
    This provider implements the standard Provider interface for SDMX endpoints.
    It can work with any SDMX REST API compliant endpoint by configuring the
    base URL. SDMX is an ISO standard for exchanging statistical data.
    
    The provider supports:
    - Fetching data series with dimension filters and time ranges
    - Retrieving dataflow metadata
    - Retrieving data structure definitions (DSD)
    - Working with both SDMX-ML (XML) and SDMX-JSON formats
    
    Attributes:
        name: Provider identifier (default: 'sdmx')
        base_url: Base URL of the SDMX REST API endpoint
    
    Example:
        >>> # Using OECD SDMX endpoint
        >>> provider = SDMXProvider(
        ...     name='oecd',
        ...     base_url='https://sdmx.oecd.org/public/rest'
        ... )
        >>> 
        >>> # Fetch data with filters
        >>> ref = DatasetRef(
        ...     provider='oecd',
        ...     id='OECD,QNA,1.0',
        ...     params={
        ...         'key': 'AUS...',
        ...         'start_period': '2020-Q1',
        ...         'end_period': '2023-Q4',
        ...         'format': 'sdmx-json'
        ...     }
        ... )
        >>> result = provider.fetch(ref, './data')
        >>> print(result['files'])
    
    Notes:
        - Search is not implemented as SDMX search endpoints vary across providers
        - Resolve returns metadata about the dataflow and data structure
        - Fetch downloads the actual data series to a file
    """
    
    def __init__(self, name: str = 'sdmx', base_url: Optional[str] = None):
        """
        Initialize the SDMX provider.
        
        Args:
            name: Unique provider identifier (default: 'sdmx')
            base_url: Base URL of the SDMX REST API endpoint. Can also be set via
                     DatasetRef params with key 'base_url'
        """
        super().__init__(name)
        self.base_url = base_url
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for datasets in the SDMX endpoint.
        
        Note: This method is not fully implemented as SDMX search endpoints
        vary significantly across providers. Most SDMX endpoints require
        knowing the dataflow ID rather than searching by keyword.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
        
        Returns:
            Empty list (search not implemented)
        
        Raises:
            NotImplementedError: SDMX search is not standardized across providers
        """
        raise NotImplementedError(
            "Search is not implemented for SDMX provider. "
            "SDMX endpoints typically require direct dataflow references. "
            "Use the dataflow catalog or documentation to find dataflow IDs."
        )
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve an SDMX dataset reference into metadata.
        
        Retrieves metadata about the dataflow and optionally the data structure.
        
        Args:
            ref: Dataset reference with SDMX dataflow ID
                Required params:
                    - base_url: SDMX endpoint base URL (or set in provider)
                Optional params:
                    - agency_id: Agency identifier (extracted from dataflow if not provided)
                    - version: Version (default: 'latest')
                    - include_dsd: Include data structure metadata (default: False)
        
        Returns:
            Dictionary containing:
                - dataflow_id: Dataflow identifier
                - dataflow_metadata: Dataflow metadata (name, description, etc.)
                - dsd_metadata: Data structure metadata (if include_dsd=True)
                - provider: Provider name
                - base_url: SDMX endpoint URL
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='sdmx',
            ...     id='OECD,QNA,1.0',
            ...     params={
            ...         'base_url': 'https://sdmx.oecd.org/public/rest',
            ...         'include_dsd': True
            ...     }
            ... )
            >>> metadata = provider.resolve(ref)
            >>> print(metadata['dataflow_metadata']['name'])
        
        Raises:
            ValueError: If base_url is not configured
        """
        # Get base URL from params or instance
        base_url = ref.params.get('base_url', self.base_url)
        if not base_url:
            raise ValueError(
                "base_url must be provided in DatasetRef params or provider initialization"
            )
        
        # Parse dataflow ID (format: AGENCY,DATAFLOW,VERSION or just DATAFLOW)
        dataflow_parts = ref.id.split(',')
        if len(dataflow_parts) >= 2:
            agency_id = dataflow_parts[0]
            dataflow_id = dataflow_parts[1]
            version = dataflow_parts[2] if len(dataflow_parts) >= 3 else 'latest'
        else:
            # Dataflow ID only, get agency from params
            agency_id = ref.params.get('agency_id', 'all')
            dataflow_id = ref.id
            version = ref.params.get('version', 'latest')
        
        # Get dataflow metadata
        try:
            dataflow_metadata = get_sdmx_dataflow(
                base_url,
                agency_id,
                dataflow_id,
                version
            )
        except Exception as e:
            # If dataflow metadata fails, return basic info
            dataflow_metadata = {
                'id': dataflow_id,
                'agency_id': agency_id,
                'version': version,
                'error': str(e)
            }
        
        result = {
            'dataflow_id': ref.id,
            'dataflow_metadata': dataflow_metadata,
            'provider': self.name,
            'base_url': base_url,
        }
        
        # Optionally get data structure metadata
        if ref.params.get('include_dsd', False):
            # Get DSD ID from dataflow metadata or params
            dsd_id = None
            if 'structure_ref' in dataflow_metadata:
                dsd_id = dataflow_metadata['structure_ref'].get('id')
                dsd_agency = dataflow_metadata['structure_ref'].get('agency_id', agency_id)
                dsd_version = dataflow_metadata['structure_ref'].get('version', 'latest')
            else:
                dsd_id = ref.params.get('dsd_id', dataflow_id)
                dsd_agency = ref.params.get('dsd_agency', agency_id)
                dsd_version = ref.params.get('dsd_version', 'latest')
            
            if dsd_id:
                try:
                    dsd_metadata = get_sdmx_data_structure(
                        base_url,
                        dsd_agency,
                        dsd_id,
                        dsd_version
                    )
                    result['dsd_metadata'] = dsd_metadata
                except Exception as e:
                    result['dsd_error'] = str(e)
        
        return result
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download SDMX data to the specified output directory.
        
        Args:
            ref: Dataset reference with SDMX dataflow ID
                Required params:
                    - base_url: SDMX endpoint base URL (or set in provider)
                Optional params:
                    - key: Data key/filter (e.g., 'AUS...')
                    - provider_ref: Provider reference/agency
                    - start_period: Start period (ISO format)
                    - end_period: End period (ISO format)
                    - format: Response format ('sdmx-ml' or 'sdmx-json', default: 'sdmx-ml')
                    - Additional SDMX API parameters
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters:
                - max_retries: Maximum retry attempts (default: 3)
                - filename: Custom filename (default: dataflow_id.{xml|json})
        
        Returns:
            Dictionary containing:
                - dataset_id: Dataset identifier
                - provider: Provider name
                - files: List containing the downloaded file path
                - base_url: SDMX endpoint URL
                - format: File format
                - dataflow: Dataflow identifier
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='sdmx',
            ...     id='OECD,QNA,1.0',
            ...     params={
            ...         'base_url': 'https://sdmx.oecd.org/public/rest',
            ...         'key': 'AUS...',
            ...         'start_period': '2020-Q1',
            ...         'end_period': '2023-Q4',
            ...         'format': 'sdmx-json'
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
        key = ref.params.get('key')
        provider_ref = ref.params.get('provider_ref')
        start_period = ref.params.get('start_period')
        end_period = ref.params.get('end_period')
        format = ref.params.get('format', 'sdmx-ml')
        
        # Get additional SDMX parameters
        sdmx_params = {}
        for param_key in ['dimensionAtObservation', 'detail', 'includeHistory']:
            if param_key in ref.params:
                sdmx_params[param_key] = ref.params[param_key]
        
        # Determine output filename
        file_ext = 'xml' if format == 'sdmx-ml' else 'json'
        # Sanitize dataflow ID for filename
        safe_dataflow_id = ref.id.replace(',', '_').replace('/', '_')
        filename = kwargs.get('filename', f"{safe_dataflow_id}.{file_ext}")
        output_path = str(Path(output_dir) / filename)
        
        # Download the data
        result = download_sdmx_data(
            base_url=base_url,
            dataflow=ref.id,
            output_path=output_path,
            key=key,
            provider_ref=provider_ref,
            start_period=start_period,
            end_period=end_period,
            format=format,
            max_retries=max_retries,
            **sdmx_params
        )
        
        return {
            'dataset_id': f"{self.name}_{safe_dataflow_id}",
            'provider': self.name,
            'files': [result['file']],
            'base_url': base_url,
            'format': format,
            'dataflow': ref.id,
            'download_url': result['url'],
        }
