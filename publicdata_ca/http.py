"""
HTTP utilities for making robust requests to data providers.

This module provides utilities for making HTTP requests with retry logic and
appropriate headers for accessing Canadian public data sources.
"""

import os
import time
from typing import Dict, Optional, Any
import requests
from requests.exceptions import RequestException, HTTPError, Timeout


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
) -> requests.Response:
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
        Response object from requests library.
    
    Raises:
        RequestException: If all retry attempts fail.
        HTTPError: If the server returns an HTTP error code after all retries.
    
    Example:
        >>> response = retry_request('https://www150.statcan.gc.ca/data.csv')
        >>> data = response.content
    """
    if headers is None:
        headers = get_default_headers()
    
    last_error = None
    delay = retry_delay
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()
            return response
        
        except HTTPError as e:
            # Don't retry on client errors (4xx), only on server errors (5xx) and specific codes
            if 400 <= e.response.status_code < 500 and e.response.status_code not in [429, 408]:
                raise
            last_error = e
            
        except (RequestException, Timeout) as e:
            last_error = e
        
        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    
    # All retries failed
    if last_error:
        raise last_error
    else:
        raise RequestException(f"Failed to fetch {url} after {max_retries} attempts")


def download_file(
    url: str,
    output_path: str,
    max_retries: int = 3,
    headers: Optional[Dict[str, str]] = None,
    chunk_size: int = 8192,
    validate_content_type: bool = False,
    write_metadata: bool = True,
    use_cache: bool = True
) -> str:
    """
    Download a file from a URL to a local path with retry logic and streaming support.
    
    This function downloads files in chunks to avoid loading large files entirely
    into memory, making it suitable for downloading large datasets.
    
    Supports HTTP caching with ETag and Last-Modified headers. When use_cache=True
    (default), the function will:
    1. Check if the file already exists and has cache metadata
    2. Send conditional request headers (If-None-Match, If-Modified-Since)
    3. Skip download if server returns 304 Not Modified
    4. Save cache metadata (ETag, Last-Modified) after successful download
    
    Args:
        url: The URL to download from.
        output_path: Local file path where the downloaded file will be saved.
        max_retries: Maximum number of retry attempts (default: 3).
        headers: Optional dictionary of HTTP headers.
        chunk_size: Size of chunks to read at a time in bytes (default: 8192).
            Larger chunks can be faster but use more memory.
        validate_content_type: If True, validates that response is not HTML (default: False).
            Raises ValueError if HTML content is detected.
        write_metadata: If True, writes provenance metadata to a .meta.json sidecar file (default: True).
        use_cache: If True, uses HTTP caching with ETag/Last-Modified (default: True).
            Set to False to force re-download regardless of cache status.
    
    Returns:
        Path to the downloaded file.
    
    Raises:
        RequestException: If download fails after all retries.
        HTTPError: If the server returns an HTTP error code (except 304 with caching enabled).
        ValueError: If validate_content_type=True and HTML content is detected.
    
    Example:
        >>> # Download a large file with streaming and caching
        >>> download_file('https://example.com/large_dataset.csv', './data.csv')
        './data.csv'
        
        >>> # Download with content type validation
        >>> download_file('https://example.com/data.csv', './data.csv', validate_content_type=True)
        './data.csv'
        
        >>> # Force re-download without using cache
        >>> download_file('https://example.com/data.csv', './data.csv', use_cache=False)
        './data.csv'
    """
    from publicdata_ca.http_cache import get_conditional_headers, save_cache_metadata
    
    # Prepare headers
    request_headers = headers if headers is not None else get_default_headers()
    
    # Add conditional headers if caching is enabled and file exists
    if use_cache and os.path.exists(output_path):
        conditional_headers = get_conditional_headers(output_path)
        request_headers = {**request_headers, **conditional_headers}
    
    try:
        response = retry_request(url, max_retries=max_retries, headers=request_headers)
    except HTTPError as e:
        # Handle 304 Not Modified - file hasn't changed
        if e.response.status_code == 304 and use_cache and os.path.exists(output_path):
            # File is still valid, no need to download
            return output_path
        # Re-raise other HTTP errors
        raise
    
    # Get content type from response headers
    content_type = response.headers.get('Content-Type', '')
    
    # Validate content type if requested
    if validate_content_type:
        content_type_lower = content_type.lower()
        # Check for HTML or XHTML content (using 'in' to match variants like 'application/xhtml+xml')
        if 'text/html' in content_type_lower or 'application/xhtml' in content_type_lower:
            raise ValueError(
                f"Expected data file but received HTML content (Content-Type: {content_type}). "
                f"URL may be invalid or may have changed. Please verify the URL points to a data file."
            )
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    
    # Save HTTP cache metadata if caching is enabled
    if use_cache:
        etag = response.headers.get('ETag')
        last_modified = response.headers.get('Last-Modified')
        save_cache_metadata(
            output_path,
            etag=etag,
            last_modified=last_modified,
            url=url
        )
    
    # Write provenance metadata if requested
    if write_metadata:
        from publicdata_ca.provenance import write_provenance_metadata
        try:
            write_provenance_metadata(
                output_path,
                url,
                content_type=content_type if content_type else None
            )
        except Exception:
            # Don't fail the download if metadata writing fails
            # This is a best-effort operation
            pass
    
    return output_path
