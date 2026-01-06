"""
Statistics Canada (StatsCan) data provider.

This module provides functionality to download tables and datasets from Statistics Canada.
"""

import json
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from publicdata_ca.http import download_file
from publicdata_ca.provider import Provider, DatasetRef


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
    
    # Build StatsCan WDS API URL
    download_url = _build_wds_url(pid, language)
    
    try:
        # Download ZIP file to temporary location
        zip_path = output_path / f"{pid}_temp.zip"
        download_file(download_url, str(zip_path), max_retries=max_retries, write_metadata=False)
        
        # Extract ZIP file
        extracted_files = _extract_zip(zip_path, output_path, pid)
        
        # Parse manifest if available
        manifest_data = _parse_manifest(output_path, pid)
        
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
            'title': manifest_data.get('title', f'StatsCan Table {pid}') if manifest_data else f'StatsCan Table {pid}',
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
    Build StatsCan WDS API URL for full table CSV download.
    
    Args:
        pid: 8-digit Product ID.
        language: Language code ('en' or 'fr').
    
    Returns:
        Full WDS API URL.
    """
    return f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{language}/{pid}"


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
    Write provenance metadata for StatsCan extracted files.
    
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
    
    # Build additional metadata common to all files
    additional_metadata = {
        'provider': 'statcan',
        'pid': pid,
        'table_number': _format_table_number(pid)
    }
    
    # Add title if available from manifest
    if manifest_data and 'title' in manifest_data:
        additional_metadata['title'] = manifest_data['title']
    
    # Write metadata for each extracted file
    for file_path in extracted_files:
        try:
            write_provenance_metadata(
                file_path,
                source_url,
                content_type='application/zip',  # Original download was ZIP
                additional_metadata=additional_metadata
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
