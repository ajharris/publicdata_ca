"""
Statistics Canada (StatsCan) data provider.

This module provides functionality to download tables and datasets from Statistics Canada.
"""

import json
import time
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from publicdata_ca.http import download_file, get_default_headers, retry_request
from publicdata_ca.provider import Provider, DatasetRef


_STATCAN_MANIFEST_READY_STATUSES = {'SUCCESS', 'DONE', 'READY'}
_STATCAN_MANIFEST_WAIT_STATUSES = {'PENDING', 'PROGRESS', 'RUNNING'}
_STATCAN_MANIFEST_POLL_INTERVAL_SECONDS = 2


def download_statcan_table(
    table_id: str,
    output_dir: str,
    file_format: str = "csv",
    max_retries: int = 3,
    skip_existing: bool = True,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Download a Statistics Canada table from the WDS API.
    
    This function downloads full table data from StatsCan's Web Data Service (WDS) API.
    The API returns a ZIP file containing CSV data and metadata files. The function
    extracts the ZIP, parses the manifest, and returns information about downloaded files.
    
    Args:
        table_id: StatsCan table identifier (e.g., '14-10-0287-01' or '14100287').
                 Accepts both hyphenated and non-hyphenated PID formats.
        output_dir: Directory where the table files will be saved.
        file_format: Output format ('csv' only for WDS API). Default is 'csv'.
        max_retries: Maximum number of download retry attempts (default: 3).
        skip_existing: If True, skip download if the main CSV file already exists (default: True).
        language: Language for download ('en' or 'fr'). Default is 'en'.
    
    Returns:
        Dictionary containing:
            - dataset_id: The table identifier
            - provider: 'statcan'
            - files: List of extracted file paths
            - url: Source URL
            - title: Table title (from manifest if available)
            - pid: Product ID
            - manifest: Parsed manifest data (if available)
    
    Example:
        >>> result = download_statcan_table('18100004', './data')
        >>> print(result['files'])
        ['./data/18100004.csv', './data/18100004_MetaData.csv']
    
    Notes:
        - Uses StatsCan Web Data Service (WDS) REST API
        - Downloads come as ZIP files containing CSV and metadata
        - Supports skip-if-exists to avoid redundant downloads
        - Manifest files are parsed when present in the ZIP
    """
    # Normalize table ID to PID format (8 digits, no hyphens)
    pid = _normalize_pid(table_id)
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Define the main output CSV file
    main_csv_file = output_path / f"{pid}.csv"
    
    # Skip download if file exists and skip_existing is True
    if skip_existing and main_csv_file.exists():
        return {
            'dataset_id': f'statcan_{pid}',
            'provider': 'statcan',
            'files': [str(main_csv_file)],
            'url': _build_wds_url(pid, language),
            'title': f'StatsCan Table {pid}',
            'pid': pid,
            'skipped': True
        }
    
    try:
        # Retrieve manifest metadata and download link from StatsCan WDS
        wds_manifest = _get_wds_download_manifest(pid, language, max_retries)
        download_url = wds_manifest['download_link']

        # Some legacy endpoints (and unit tests) return the manifest object as a plain URL
        # string instead of the full metadata dict. Normalize it so downstream helpers expect
        # a mapping.
        manifest_object = wds_manifest.get('object')
        if isinstance(manifest_object, str):
            manifest_object = {'downloadLink': manifest_object}
        elif isinstance(manifest_object, list):
            manifest_object = manifest_object[0] if manifest_object else {}
        elif not isinstance(manifest_object, dict) or manifest_object is None:
            manifest_object = {}

        manifest_title = _extract_manifest_title(manifest_object, language, pid)
        
        # Download ZIP file to temporary location
        zip_path = output_path / f"{pid}_temp.zip"
        
        # StatsCan WDS API is sensitive to Accept headers; omit it to avoid HTTP 406 errors
        statcan_headers = {
            'User-Agent': get_default_headers()['User-Agent'],
        }
        
        download_file(download_url, str(zip_path), max_retries=max_retries, write_metadata=False, headers=statcan_headers)
        
        # Extract ZIP file
        extracted_files = _extract_zip(zip_path, output_path, pid)
        
        # Parse manifest if available and merge with WDS metadata
        manifest_data = _parse_manifest(output_path, pid) or {}
        if not manifest_data.get('title'):
            manifest_data['title'] = manifest_title
        manifest_data['wds_manifest'] = manifest_object
        manifest_data['manifest_url'] = wds_manifest['manifest_url']
        manifest_data['download_link'] = download_url
        manifest_data['manifest_status'] = wds_manifest['status']
        
        # Write provenance metadata for extracted files
        _write_statcan_metadata(
            extracted_files,
            download_url,
            pid,
            manifest_data
        )
        
        # Clean up ZIP file
        if zip_path.exists():
            zip_path.unlink()
        
        result = {
            'dataset_id': f'statcan_{pid}',
            'provider': 'statcan',
            'files': extracted_files,
            'url': download_url,
            'title': manifest_data.get('title', f'StatsCan Table {pid}'),
            'pid': pid,
            'skipped': False
        }
        
        if manifest_data:
            result['manifest'] = manifest_data
        
        return result
        
    except Exception as e:
        # Clean up temporary ZIP file on error
        zip_path = output_path / f"{pid}_temp.zip"
        if zip_path.exists():
            zip_path.unlink()
        raise RuntimeError(f"Failed to download StatsCan table {pid}: {str(e)}")


def search_statcan_tables(query: str) -> list:
    """
    Search for Statistics Canada tables by keyword.
    
    This function searches the StatsCan catalog for tables matching the query.
    
    Args:
        query: Search query string.
    
    Returns:
        List of matching table metadata dictionaries.
    
    Note:
        This is a placeholder for future implementation.
        The actual implementation would query StatsCan's search API.
    """
    # Placeholder for future implementation
    # Would integrate with StatsCan's search/discovery API
    return []


def _normalize_pid(table_id: str) -> str:
    """
    Normalize a table ID to PID format (8 digits, no hyphens).
    
    Accepts formats like:
        - '18100004' (already normalized)
        - '18-10-0004' (hyphenated)
        - '1810000401' (10 digits with suffix)
    
    Args:
        table_id: Table identifier in various formats.
    
    Returns:
        Normalized 8-digit PID string.
    
    Raises:
        ValueError: If the table ID format is invalid.
    """
    # Remove spaces and hyphens
    pid = table_id.strip().replace(' ', '').replace('-', '')
    
    # Extract first 8 digits
    if len(pid) >= 8 and pid[:8].isdigit():
        return pid[:8]
    
    raise ValueError(f"Invalid StatsCan table ID format: {table_id}")


def _build_wds_url(pid: str, language: str = "en") -> str:
    """
    Build StatsCan WDS API URL for full table CSV manifest metadata.
    
    Args:
        pid: 8-digit Product ID.
        language: Language code ('en' or 'fr').
    
    Returns:
        Full WDS API manifest URL.
    """
    return f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{pid}/{language}"


def _get_wds_download_manifest(pid: str, language: str, max_retries: int) -> Dict[str, Any]:
    """Retrieve the StatsCan WDS manifest describing the table download."""
    manifest_url = _build_wds_url(pid, language)
    headers = get_default_headers().copy()
    headers['Accept'] = 'application/json'
    poll_attempts = max(1, max_retries)
    
    for attempt in range(poll_attempts):
        response = retry_request(manifest_url, max_retries=max_retries, headers=headers)
        payload = _parse_wds_json(response, manifest_url)
        status = str(payload.get('status', '')).upper()
        
        if status in _STATCAN_MANIFEST_READY_STATUSES:
            manifest_object = _extract_manifest_object(payload)
            download_link = (
                manifest_object.get('downloadLink') or
                manifest_object.get('downloadlink') or
                manifest_object.get('downloadURL') or
                manifest_object.get('downloadUrl')
            )
            if not download_link:
                raise RuntimeError("StatsCan WDS response did not include a downloadLink entry")
            return {
                'manifest_url': manifest_url,
                'download_link': download_link,
                'object': manifest_object,
                'status': status,
                'raw': payload
            }
        
        if status in _STATCAN_MANIFEST_WAIT_STATUSES and attempt < poll_attempts - 1:
            time.sleep(_STATCAN_MANIFEST_POLL_INTERVAL_SECONDS)
            continue
        
        message = payload.get('message') or payload.get('error') or f"Unexpected status '{status}'"
        raise RuntimeError(f"StatsCan WDS error for table {pid}: {message}")
    
    raise RuntimeError(
        f"StatsCan WDS download for table {pid} did not become available after {poll_attempts} attempts"
    )


def _parse_wds_json(response, manifest_url: str) -> Dict[str, Any]:
    """Safely parse JSON from a WDS manifest response."""
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON returned from StatsCan manifest endpoint {manifest_url}: {exc}") from exc
    if isinstance(payload, list):
        if not payload:
            raise RuntimeError(f"StatsCan manifest endpoint {manifest_url} returned an empty response list")
        payload = payload[0]
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected manifest payload type {type(payload)} from {manifest_url}")
    return payload


def _extract_manifest_object(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the manifest object from the WDS payload."""
    manifest_object = payload.get('object')
    if manifest_object is None:
        manifest_object = payload.get('objects') or payload.get('objectList')
    if manifest_object is None and any(
        key in payload for key in ('downloadLink', 'downloadlink', 'downloadURL', 'downloadUrl')
    ):
        manifest_object = payload
    if isinstance(manifest_object, list):
        if not manifest_object:
            raise RuntimeError('StatsCan WDS response returned an empty object list')
        manifest_object = manifest_object[0]
    if isinstance(manifest_object, str):
        return {'downloadLink': manifest_object}
    if isinstance(manifest_object, dict):
        return manifest_object
    raise RuntimeError(
        f"StatsCan WDS response missing object metadata: {json.dumps(payload)[:200]}"
    )


def _extract_manifest_title(manifest_object: Dict[str, Any], language: str, pid: str) -> str:
    """Determine the best title to use for the dataset based on manifest metadata."""
    language = language.lower()
    title_key = 'titleEn' if language == 'en' else 'titleFr'
    title = manifest_object.get(title_key)
    if not title:
        # Fallbacks if title isn't language-specific
        title = manifest_object.get('title') or manifest_object.get('tableTitle')
    return title or f'StatsCan Table {pid}'


def _extract_zip(zip_path: Path, output_dir: Path, pid: str) -> List[str]:
    """
    Extract ZIP file contents to output directory.
    
    StatsCan ZIP files typically contain:
        - {PID}.csv - Main data file
        - {PID}_MetaData.csv - Metadata file
        - Other supporting files
    
    Args:
        zip_path: Path to the ZIP file.
        output_dir: Directory to extract files to.
        pid: Product ID for file naming.
    
    Returns:
        List of extracted file paths (relative to output_dir).
    
    Raises:
        zipfile.BadZipFile: If the ZIP file is invalid.
    """
    extracted_files = []
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get list of files in ZIP
        zip_contents = zip_ref.namelist()
        
        # Extract all files
        for file_name in zip_contents:
            # Skip directories
            if file_name.endswith('/'):
                continue
            
            # Extract the file
            zip_ref.extract(file_name, output_dir)
            extracted_path = output_dir / file_name
            
            # Store relative path
            extracted_files.append(str(extracted_path))
    
    return extracted_files


def _parse_manifest(output_dir: Path, pid: str) -> Optional[Dict[str, Any]]:
    """
    Parse manifest or metadata file if present.
    
    StatsCan ZIP files may contain metadata in various formats:
        - {PID}_MetaData.csv
        - manifest.json (less common)
    
    Args:
        output_dir: Directory containing extracted files.
        pid: Product ID.
    
    Returns:
        Dictionary with parsed manifest data, or None if no manifest found.
    """
    # Check for JSON manifest
    manifest_json = output_dir / "manifest.json"
    if manifest_json.exists():
        try:
            with open(manifest_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Check for metadata CSV
    metadata_csv = output_dir / f"{pid}_MetaData.csv"
    if metadata_csv.exists():
        # Metadata CSV exists but parsing it into structured data
        # would require more complex logic. For now, just note its presence.
        return {
            'metadata_file': str(metadata_csv),
            'title': f'StatsCan Table {pid}'
        }
    
    return None


def _write_statcan_metadata(
    extracted_files: List[str],
    source_url: str,
    pid: str,
    manifest_data: Optional[Dict[str, Any]]
) -> None:
    """
    Write provenance metadata for StatsCan extracted files using unified schema.
    
    Creates .meta.json sidecar files for each extracted file with:
    - Source URL (ZIP download URL)
    - StatsCan-specific metadata (PID, table title)
    - Standard provenance info (timestamp, hash, size)
    
    Args:
        extracted_files: List of extracted file paths.
        source_url: Original ZIP download URL.
        pid: StatsCan Product ID.
        manifest_data: Parsed manifest data (if available).
    """
    from publicdata_ca.provenance import write_provenance_metadata
    
    # Build provider-specific metadata
    provider_specific = {
        'pid': pid,
        'table_number': _format_table_number(pid)
    }
    
    # Add title if available from manifest
    if manifest_data and 'title' in manifest_data:
        provider_specific['title'] = manifest_data['title']
    
    # Write metadata for each extracted file using unified schema
    for file_path in extracted_files:
        try:
            write_provenance_metadata(
                file_path,
                source_url,
                content_type='application/zip',  # Original download was ZIP
                provider_name='statcan',
                provider_specific=provider_specific
            )
        except Exception:
            # Don't fail the download if metadata writing fails
            pass


def _format_table_number(pid: str) -> str:
    """
    Format PID as table number with hyphens.
    
    Args:
        pid: 8-digit Product ID (e.g., '18100004').
    
    Returns:
        Formatted table number (e.g., '18-10-0004').
    """
    if len(pid) == 8:
        return f"{pid[:2]}-{pid[2:4]}-{pid[4:]}"
    return pid


class StatCanProvider(Provider):
    """
    Statistics Canada data provider implementation.
    
    This provider implements the standard Provider interface for StatsCan datasets.
    It supports searching (placeholder), resolving table references to download URLs,
    and fetching StatsCan tables via the WDS API.
    
    Example:
        >>> provider = StatCanProvider()
        >>> ref = DatasetRef(provider='statcan', id='18100004')
        >>> result = provider.fetch(ref, './data/raw')
        >>> print(result['files'])
    """
    
    def __init__(self, name: str = 'statcan'):
        """Initialize the StatsCan provider."""
        super().__init__(name)
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for StatsCan tables by keyword.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
        
        Returns:
            List of DatasetRef objects matching the query
        
        Note:
            This is a placeholder implementation. Full search functionality
            would integrate with StatsCan's search/discovery API.
        """
        # Placeholder - would integrate with StatsCan's search API
        # For now, return empty list
        return []
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve a StatsCan dataset reference into download metadata.
        
        Args:
            ref: Dataset reference with StatsCan table ID
        
        Returns:
            Dictionary containing download URL, format, and metadata
        
        Example:
            >>> ref = DatasetRef(provider='statcan', id='18100004')
            >>> metadata = provider.resolve(ref)
            >>> print(metadata['url'])
        """
        # Normalize the table ID
        pid = _normalize_pid(ref.id)
        
        # Get language from params or default to 'en'
        language = ref.params.get('language', 'en')
        
        # Build WDS URL
        url = _build_wds_url(pid, language)
        
        return {
            'url': url,
            'format': 'csv',
            'pid': pid,
            'table_number': _format_table_number(pid),
            'title': ref.metadata.get('title', f'StatsCan Table {pid}'),
            'provider': self.name,
        }
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download a StatsCan table to the specified output directory.
        
        Args:
            ref: Dataset reference with StatsCan table ID
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters (skip_existing, max_retries, etc.)
        
        Returns:
            Dictionary containing downloaded files and metadata
        
        Example:
            >>> ref = DatasetRef(provider='statcan', id='18100004')
            >>> result = provider.fetch(ref, './data/raw')
            >>> print(result['files'])
        """
        # Extract parameters
        skip_existing = kwargs.get('skip_existing', True)
        max_retries = kwargs.get('max_retries', 3)
        language = ref.params.get('language', 'en')
        
        # Use the existing download_statcan_table function
        result = download_statcan_table(
            table_id=ref.id,
            output_dir=output_dir,
            max_retries=max_retries,
            skip_existing=skip_existing,
            language=language
        )
        
        return result
