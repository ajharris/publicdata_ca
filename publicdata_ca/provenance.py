"""
Provenance metadata utilities for tracking data file origins and integrity.

This module provides functionality to write sidecar metadata files (.meta.json)
alongside downloaded data files, recording source URLs, timestamps, hashes,
and content types for reproducibility and verification.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


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
    hash_algorithm: str = 'sha256'
) -> str:
    """
    Write provenance metadata as a .meta.json sidecar file.
    
    Creates a JSON file alongside the downloaded file containing:
    - Source URL(s)
    - Download timestamp
    - File hash for integrity verification
    - Content type
    - File size
    - Additional metadata (optional)
    
    Args:
        file_path: Path to the data file.
        source_url: URL where the file was downloaded from.
        content_type: HTTP Content-Type header value (optional).
        additional_metadata: Additional metadata to include (optional).
            Can include provider-specific info like table IDs, titles, etc.
        hash_algorithm: Hash algorithm to use (default: 'sha256').
    
    Returns:
        Path to the created metadata file.
    
    Example:
        >>> write_provenance_metadata(
        ...     '/data/table.csv',
        ...     'https://example.com/table.csv',
        ...     content_type='text/csv',
        ...     additional_metadata={'table_id': '12345', 'provider': 'statcan'}
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
    
    # Build metadata
    metadata = {
        "file": str(file_path_obj.name),
        "source_url": source_url,
        "downloaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "file_size_bytes": file_size,
        "hash": {
            "algorithm": hash_algorithm,
            "value": file_hash
        }
    }
    
    # Add content type if provided
    if content_type:
        metadata["content_type"] = content_type
    
    # Add additional metadata if provided
    if additional_metadata:
        metadata.update(additional_metadata)
    
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
