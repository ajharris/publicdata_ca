"""
HTTP utilities for making robust requests to data providers.

This module provides utilities for making HTTP requests with retry logic and
appropriate headers for accessing Canadian public data sources.
"""

import time
from typing import Dict, Optional, Any
from urllib import request
from urllib.error import URLError, HTTPError


def get_default_headers() -> Dict[str, str]:
    """
    Get default HTTP headers for requests to Canadian public data sources.
    
    Returns:
        Dictionary of HTTP headers including User-Agent.
    """
    return {
        'User-Agent': 'publicdata_ca/0.1.0 (Python; Canadian Public Data Client)',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
    }


def retry_request(
    url: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30
) -> Any:
    """
    Make an HTTP GET request with retry logic.
    
    This function attempts to fetch a URL with exponential backoff retry logic
    to handle transient network failures and rate limiting.
    
    Args:
        url: The URL to request.
        max_retries: Maximum number of retry attempts (default: 3).
        retry_delay: Initial delay between retries in seconds (default: 1.0).
            Delay doubles with each retry (exponential backoff).
        headers: Optional dictionary of HTTP headers. If None, uses default headers.
        timeout: Request timeout in seconds (default: 30).
    
    Returns:
        Response object from urllib.request.urlopen.
    
    Raises:
        URLError: If all retry attempts fail.
        HTTPError: If the server returns an HTTP error code after all retries.
    
    Example:
        >>> response = retry_request('https://www150.statcan.gc.ca/data.csv')
        >>> data = response.read()
    """
    if headers is None:
        headers = get_default_headers()
    
    last_error = None
    delay = retry_delay
    
    for attempt in range(max_retries):
        try:
            req = request.Request(url, headers=headers)
            response = request.urlopen(req, timeout=timeout)
            return response
        
        except HTTPError as e:
            # Don't retry on client errors (4xx), only on server errors (5xx) and specific codes
            if 400 <= e.code < 500 and e.code not in [429, 408]:
                raise
            last_error = e
            
        except URLError as e:
            last_error = e
        
        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    
    # All retries failed
    if last_error:
        raise last_error
    else:
        raise URLError(f"Failed to fetch {url} after {max_retries} attempts")


def download_file(
    url: str,
    output_path: str,
    max_retries: int = 3,
    headers: Optional[Dict[str, str]] = None,
    chunk_size: int = 8192,
    validate_content_type: bool = False
) -> str:
    """
    Download a file from a URL to a local path with retry logic and streaming support.
    
    This function downloads files in chunks to avoid loading large files entirely
    into memory, making it suitable for downloading large datasets.
    
    Args:
        url: The URL to download from.
        output_path: Local file path where the downloaded file will be saved.
        max_retries: Maximum number of retry attempts (default: 3).
        headers: Optional dictionary of HTTP headers.
        chunk_size: Size of chunks to read at a time in bytes (default: 8192).
            Larger chunks can be faster but use more memory.
        validate_content_type: If True, validates that response is not HTML (default: False).
            Raises ValueError if HTML content is detected.
    
    Returns:
        Path to the downloaded file.
    
    Raises:
        URLError: If download fails after all retries.
        ValueError: If validate_content_type=True and HTML content is detected.
    
    Example:
        >>> # Download a large file with streaming
        >>> download_file('https://example.com/large_dataset.csv', './data.csv')
        './data.csv'
        
        >>> # Download with content type validation
        >>> download_file('https://example.com/data.csv', './data.csv', validate_content_type=True)
        './data.csv'
    """
    response = retry_request(url, max_retries=max_retries, headers=headers)
    
    # Validate content type if requested
    if validate_content_type:
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type or 'application/xhtml' in content_type:
            raise ValueError(
                f"Expected data file but received HTML content (Content-Type: {content_type}). "
                f"URL may be invalid or may have changed. Please verify the URL points to a data file."
            )
    
    with open(output_path, 'wb') as f:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
    
    return output_path
