"""
HTTP cache metadata management for ETag and Last-Modified headers.

This module provides utilities for storing and retrieving HTTP cache metadata
(ETag and Last-Modified headers) to enable efficient revalidation of cached
files. This allows skipping downloads when remote files haven't changed.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone


def _get_cache_metadata_path(file_path: str) -> Path:
    """
    Get the cache metadata file path for a given downloaded file.
    
    Args:
        file_path: Path to the downloaded file.
    
    Returns:
        Path to the cache metadata JSON file.
    """
    # Store cache metadata alongside the file with .http_cache.json extension
    return Path(str(file_path) + '.http_cache.json')


def save_cache_metadata(
    file_path: str,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
    url: Optional[str] = None
) -> None:
    """
    Save HTTP cache metadata for a downloaded file.
    
    Args:
        file_path: Path to the downloaded file.
        etag: ETag header value from the response.
        last_modified: Last-Modified header value from the response.
        url: Source URL of the file.
    """
    # Only save if we have at least one cache header
    if not etag and not last_modified:
        return
    
    cache_file = _get_cache_metadata_path(file_path)
    
    metadata = {
        'url': url,
        'etag': etag,
        'last_modified': last_modified,
        'cached_at': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except IOError:
        # If we can't write cache metadata, continue without caching
        pass


def load_cache_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load HTTP cache metadata for a file.
    
    Args:
        file_path: Path to the downloaded file.
    
    Returns:
        Dictionary with cache metadata (etag, last_modified, url, cached_at)
        or None if no cache metadata exists or file doesn't exist.
    """
    # If the actual file doesn't exist, cache is invalid
    if not Path(file_path).exists():
        return None
    
    cache_file = _get_cache_metadata_path(file_path)
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Validate structure
        if not isinstance(metadata, dict):
            return None
        
        return metadata
    
    except (json.JSONDecodeError, IOError):
        # If cache is corrupted or unreadable, return None
        return None


def clear_cache_metadata(file_path: str) -> None:
    """
    Clear HTTP cache metadata for a file.
    
    Args:
        file_path: Path to the downloaded file.
    """
    cache_file = _get_cache_metadata_path(file_path)
    
    if cache_file.exists():
        try:
            cache_file.unlink()
        except IOError:
            pass


def get_conditional_headers(file_path: str) -> Dict[str, str]:
    """
    Get conditional request headers (If-None-Match, If-Modified-Since) for a file.
    
    This function loads cache metadata and returns appropriate headers for
    HTTP conditional requests to check if the file has been modified.
    
    Args:
        file_path: Path to the downloaded file.
    
    Returns:
        Dictionary of conditional headers to include in the request.
        Empty dict if no cache metadata exists.
    
    Example:
        >>> headers = get_conditional_headers('/path/to/data.csv')
        >>> headers
        {'If-None-Match': '"abc123"', 'If-Modified-Since': 'Wed, 21 Oct 2015 07:28:00 GMT'}
    """
    metadata = load_cache_metadata(file_path)
    
    if not metadata:
        return {}
    
    headers = {}
    
    if metadata.get('etag'):
        headers['If-None-Match'] = metadata['etag']
    
    if metadata.get('last_modified'):
        headers['If-Modified-Since'] = metadata['last_modified']
    
    return headers
