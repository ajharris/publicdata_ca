"""
Provenance metadata utilities for tracking data file origins and integrity.

This module provides functionality to write sidecar metadata files (.meta.json)
alongside downloaded data files, recording source URLs, timestamps, hashes,
and content types for reproducibility and verification.

Metadata Schema Version: 1.0
Schema fields:
  - schema_version: Version of the metadata schema (for backward compatibility)
  - file: Filename of the data file
  - source_url: URL where the file was downloaded from
  - downloaded_at: ISO 8601 timestamp of download (UTC)
  - file_size_bytes: Size of the file in bytes
  - content_type: HTTP Content-Type header value
  - hash: File integrity hash (algorithm and value)
  - provider: Data provider information
    - name: Provider identifier (e.g., 'statcan', 'cmhc', 'ckan')
    - specific: Provider-specific metadata (optional)
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# Current metadata schema version
METADATA_SCHEMA_VERSION = "1.0"

# Standard metadata fields (excluding provider-specific fields)
STANDARD_METADATA_FIELDS = {
    "schema_version", "file", "source_url", "downloaded_at",
    "file_size_bytes", "hash", "content_type", "provider"
}


def _format_utc_timestamp(dt: datetime) -> str:
    """
    Format a datetime as ISO 8601 with 'Z' suffix for UTC.
    
    Args:
        dt: Datetime object in UTC timezone.
    
    Returns:
        ISO 8601 formatted string with 'Z' suffix (e.g., '2024-01-01T12:00:00Z').
    """
    # Use strftime for explicit formatting to avoid timezone offset variations
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'


def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    Calculate cryptographic hash of a file.
    
    Args:
        file_path: Path to the file to hash.
        algorithm: Hash algorithm to use (default: 'sha256').
            Supported: 'md5', 'sha1', 'sha256', 'sha512'.
    
    Returns:
        Hexadecimal hash digest string.
    
    Example:
        >>> hash_value = calculate_file_hash('/path/to/file.csv')
        >>> print(hash_value)
        'a1b2c3d4...'
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        # Read in chunks to handle large files efficiently
        while chunk := f.read(8192):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def write_provenance_metadata(
    file_path: str,
    source_url: str,
    content_type: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
    hash_algorithm: str = 'sha256',
    provider_name: Optional[str] = None,
    provider_specific: Optional[Dict[str, Any]] = None
) -> str:
    """
    Write provenance metadata as a .meta.json sidecar file using unified schema.
    
    Creates a JSON file alongside the downloaded file containing standardized
    provenance information following the unified metadata schema v1.0.
    
    Unified Schema Fields:
    - schema_version: Version of the metadata schema (for backward compatibility)
    - file: Filename of the data file
    - source_url: URL where the file was downloaded from
    - downloaded_at: ISO 8601 timestamp of download (UTC)
    - file_size_bytes: Size of the file in bytes
    - content_type: HTTP Content-Type header value (optional)
    - hash: File integrity hash (algorithm and value)
    - provider: Data provider information
      - name: Provider identifier (e.g., 'statcan', 'cmhc', 'ckan')
      - specific: Provider-specific metadata (optional)
    
    Args:
        file_path: Path to the data file.
        source_url: URL where the file was downloaded from.
        content_type: HTTP Content-Type header value (optional).
        additional_metadata: DEPRECATED. Additional metadata to include (optional).
            For backward compatibility only. Use provider_specific instead.
        hash_algorithm: Hash algorithm to use (default: 'sha256').
        provider_name: Name of the data provider (e.g., 'statcan', 'cmhc').
        provider_specific: Provider-specific metadata fields (optional).
            Examples: {'pid': '18100004', 'table_number': '18-10-0004'} for StatsCan.
    
    Returns:
        Path to the created metadata file.
    
    Example:
        >>> write_provenance_metadata(
        ...     '/data/table.csv',
        ...     'https://example.com/table.csv',
        ...     content_type='text/csv',
        ...     provider_name='statcan',
        ...     provider_specific={'pid': '18100004', 'table_number': '18-10-0004', 'title': 'CPI Table'}
        ... )
        '/data/table.csv.meta.json'
    """
    file_path_obj = Path(file_path)
    
    # Check if file exists
    if not file_path_obj.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    # Calculate file hash
    file_hash = calculate_file_hash(str(file_path_obj), algorithm=hash_algorithm)
    
    # Get file size
    file_size = file_path_obj.stat().st_size
    
    # Build metadata using unified schema
    metadata = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "file": str(file_path_obj.name),
        "source_url": source_url,
        "downloaded_at": _format_utc_timestamp(datetime.now(timezone.utc)),
        "file_size_bytes": file_size,
        "hash": {
            "algorithm": hash_algorithm,
            "value": file_hash
        }
    }
    
    # Add content type if provided
    if content_type:
        metadata["content_type"] = content_type
    
    # Build provider section
    if provider_name or provider_specific or additional_metadata:
        metadata["provider"] = {}
        
        # Handle provider_name
        if provider_name:
            metadata["provider"]["name"] = provider_name
        elif additional_metadata and "provider" in additional_metadata:
            # Extract from additional_metadata for backward compatibility
            metadata["provider"]["name"] = additional_metadata["provider"]
        
        # Handle provider_specific
        if provider_specific:
            metadata["provider"]["specific"] = provider_specific
    
    # Handle backward compatibility with additional_metadata
    # Merge fields that aren't part of the standard schema into provider.specific
    if additional_metadata:
        # Extract non-standard fields
        for key, value in additional_metadata.items():
            if key not in STANDARD_METADATA_FIELDS and key != "provider":
                # Add to provider.specific section
                if "provider" not in metadata:
                    metadata["provider"] = {}
                if "specific" not in metadata["provider"]:
                    metadata["provider"]["specific"] = {}
                metadata["provider"]["specific"][key] = value
    
    # Write metadata file
    meta_file_path = file_path_obj.parent / f"{file_path_obj.name}.meta.json"
    
    with open(meta_file_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return str(meta_file_path)


def read_provenance_metadata(file_path: str) -> Dict[str, Any]:
    """
    Read provenance metadata from a .meta.json sidecar file.
    
    Args:
        file_path: Path to the data file or the .meta.json file itself.
    
    Returns:
        Dictionary containing the metadata.
    
    Raises:
        FileNotFoundError: If the metadata file doesn't exist.
        json.JSONDecodeError: If the metadata file is not valid JSON.
    
    Example:
        >>> metadata = read_provenance_metadata('/data/table.csv')
        >>> print(metadata['source_url'])
        'https://example.com/table.csv'
    """
    file_path_obj = Path(file_path)
    
    # If the path ends with .meta.json, use it directly
    if file_path_obj.name.endswith('.meta.json'):
        meta_file_path = file_path_obj
    else:
        # Otherwise, construct the metadata file path
        meta_file_path = file_path_obj.parent / f"{file_path_obj.name}.meta.json"
    
    if not meta_file_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_file_path}")
    
    with open(meta_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def verify_file_integrity(file_path: str) -> bool:
    """
    Verify file integrity using the hash from its metadata.
    
    Args:
        file_path: Path to the data file.
    
    Returns:
        True if the file hash matches the metadata, False otherwise.
    
    Raises:
        FileNotFoundError: If the file or metadata doesn't exist.
    
    Example:
        >>> if verify_file_integrity('/data/table.csv'):
        ...     print("File integrity verified")
        ... else:
        ...     print("File has been modified!")
    """
    metadata = read_provenance_metadata(file_path)
    
    # Get hash info from metadata
    hash_info = metadata.get('hash', {})
    algorithm = hash_info.get('algorithm', 'sha256')
    expected_hash = hash_info.get('value')
    
    if not expected_hash:
        raise ValueError("No hash value found in metadata")
    
    # Calculate current file hash
    current_hash = calculate_file_hash(file_path, algorithm=algorithm)
    
    return current_hash == expected_hash
