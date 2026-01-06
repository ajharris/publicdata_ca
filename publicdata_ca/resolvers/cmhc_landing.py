"""
CMHC landing page resolver.

This module provides robust scraping and URL resolution for CMHC landing pages.
CMHC data files are often accessed through landing pages where direct download URLs
may change, requiring dynamic resolution.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from publicdata_ca.http import retry_request
from publicdata_ca.url_cache import load_cached_urls, save_cached_urls


# Constants for ranking
INVALID_ASSET_PENALTY = -1000  # Penalty for assets that fail validation


def _check_content_type(url: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Check if a URL returns a data file (not HTML).
    
    Makes a GET request to check the Content-Type header.
    Only reads the headers, not the full content.
    
    Args:
        url: URL to check.
        timeout: Request timeout in seconds (default: 10).
    
    Returns:
        Tuple of (is_valid, content_type):
            - is_valid: True if the URL returns a data file (not HTML)
            - content_type: The Content-Type header value, or None if unavailable
    
    Examples:
        >>> is_valid, ct = _check_content_type('https://example.com/data.csv')
        >>> is_valid
        True
        >>> 'text/csv' in ct
        True
    """
    try:
        # Make request to check Content-Type header
        response = retry_request(url, max_retries=1, timeout=timeout)
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Reject HTML responses
        if 'text/html' in content_type or 'application/xhtml' in content_type:
            return False, content_type
        
        # Accept known data file types
        data_content_types = [
            'text/csv',
            'application/csv',
            'application/vnd.ms-excel',  # XLS
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # XLSX
            'application/zip',
            'application/x-zip-compressed',
            'application/json',
            'application/xml',
            'text/xml',
            'text/plain',
            'application/octet-stream',  # Generic binary
        ]
        
        # If we have a recognized data content type, it's valid
        for valid_type in data_content_types:
            if valid_type in content_type:
                return True, content_type
        
        # If content-type is empty or unknown but not HTML, consider it potentially valid
        # (Some servers don't set proper Content-Type headers)
        if not content_type or content_type.strip() == '':
            return True, content_type
        
        # Unknown content type that's not HTML - be permissive
        return True, content_type
        
    except Exception:
        # If validation fails, assume the URL might be valid
        # (Don't reject URLs just because validation failed)
        return True, None


def _rank_candidate(candidate: Dict[str, str]) -> int:
    """
    Calculate a ranking score for a URL candidate.
    
    Higher scores indicate better candidates. Ranking considers:
    - File extension preference (XLSX > CSV > XLS > ZIP)
    - URL structure (direct file URLs ranked higher)
    - Title informativeness
    
    Args:
        candidate: Dictionary with 'url', 'title', and 'format' keys.
    
    Returns:
        Integer ranking score (higher is better).
    
    Examples:
        >>> _rank_candidate({'url': 'data.xlsx', 'title': 'Data', 'format': 'xlsx'})
        300
        >>> _rank_candidate({'url': 'data.csv', 'title': 'Data', 'format': 'csv'})
        200
    """
    score = 0
    url = candidate.get('url', '')
    title = candidate.get('title', '')
    file_format = candidate.get('format', '').lower()
    
    # Extension preference (higher is better)
    extension_scores = {
        'xlsx': 300,  # Modern Excel format, preferred
        'csv': 200,   # CSV is clean and portable
        'xls': 100,   # Older Excel format
        'zip': 150,   # Compressed archives
        'json': 180,  # Structured data
        'xml': 160,   # Structured data
        'dat': 50,    # Generic data files
        'txt': 50,    # Plain text
    }
    score += extension_scores.get(file_format, 0)
    
    # Prefer URLs that look like direct file downloads
    # (not through query parameters or redirects)
    if '?' not in url:
        score += 50
    
    # Prefer URLs with descriptive paths
    if '/data/' in url.lower() or '/download/' in url.lower():
        score += 30
    
    # Penalize URLs with session IDs or temporary tokens
    if any(token in url.lower() for token in ['session', 'token', 'temp', 'tmp']):
        score -= 50
    
    # Prefer informative titles (not just the filename)
    if title and len(title) > 10 and title != url.split('/')[-1]:
        score += 20
    
    return score


def resolve_cmhc_landing_page(
    landing_url: str,
    validate: bool = True,
    max_validation_attempts: int = 5,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Scrape and resolve direct download URLs from a CMHC landing page.
    
    This function parses a CMHC landing page to extract direct download links
    for data files. It handles various HTML structures and link patterns commonly
    used on CMHC websites. Candidates are ranked by quality and validated to
    reject HTML responses.
    
    Args:
        landing_url: URL of the CMHC landing/catalog page.
        validate: If True, validates URLs to reject HTML responses (default: True).
        max_validation_attempts: Maximum number of top candidates to validate (default: 5).
        use_cache: If True, uses cached URLs if available and valid (default: True).
    
    Returns:
        List of dictionaries, each containing:
            - url: Direct download URL (absolute)
            - title: Link text or filename
            - format: File extension (e.g., 'csv', 'xlsx', 'zip')
            - rank: Ranking score (higher is better)
            - validated: Boolean indicating if URL was validated (if validate=True)
    
    Example:
        >>> assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page')
        >>> for asset in assets:
        ...     print(f"{asset['title']}: {asset['url']} ({asset['format']}, rank={asset['rank']})")
    
    Notes:
        - Returns absolute URLs by resolving relative links
        - Filters for common data file formats (csv, xlsx, xls, zip, json, xml)
        - Ranks candidates by extension preference and URL structure
        - Validates top candidates to reject HTML responses
        - Extracts titles from link text or filenames
        - Robust to HTML structure variations
        - Caches resolved URLs to reduce churn across runs
    """
    # Try to load from cache first
    if use_cache:
        cached_assets = load_cached_urls(landing_url)
        if cached_assets is not None:
            # Validate cached URLs if validation is requested
            if validate and cached_assets:
                # Check if the top cached URL is still valid
                top_asset = cached_assets[0] if cached_assets else None
                if top_asset:
                    is_valid, _ = _check_content_type(top_asset['url'])
                    if is_valid:
                        # Cache is valid, return cached assets
                        return cached_assets
                    # If validation fails, fall through to re-resolve
            else:
                # No validation requested, use cache as-is
                return cached_assets
    # Fetch the landing page
    response = retry_request(landing_url)
    html_content = response.read().decode('utf-8', errors='ignore')
    
    # Parse base URL for resolving relative links
    parsed_url = urlparse(landing_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # Common data file extensions to look for
    data_extensions = {
        'csv', 'xlsx', 'xls', 'zip', 'json', 'xml', 'dat', 'txt'
    }
    
    assets = []
    
    # Pattern 1: Match <a> tags with href attributes
    # Looks for: <a href="..." ...>text</a>
    link_pattern = re.compile(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )
    
    for match in link_pattern.finditer(html_content):
        href = match.group(1)
        link_text = match.group(2)
        
        # Clean link text (remove HTML tags)
        link_text = re.sub(r'<[^>]+>', '', link_text).strip()
        
        # Check if this is a data file link
        file_ext = None
        for ext in data_extensions:
            if href.lower().endswith(f'.{ext}'):
                file_ext = ext
                break
        
        if file_ext:
            # Resolve to absolute URL
            if href.startswith('http://') or href.startswith('https://'):
                absolute_url = href
            elif href.startswith('//'):
                absolute_url = f"{parsed_url.scheme}:{href}"
            elif href.startswith('/'):
                absolute_url = f"{base_url}{href}"
            else:
                # Relative to current page
                absolute_url = urljoin(landing_url, href)
            
            # Extract filename from URL if link text is empty or generic
            filename = href.split('/')[-1].split('?')[0]
            title = link_text if link_text and len(link_text) > 0 else filename
            
            # Avoid duplicates
            if not any(a['url'] == absolute_url for a in assets):
                assets.append({
                    'url': absolute_url,
                    'title': title,
                    'format': file_ext
                })
    
    # Pattern 2: Direct file URLs in various attributes (data-url, data-href, etc.)
    data_url_pattern = re.compile(
        r'(?:data-url|data-href|data-download)=["\']([^"\']+\.(?:' +
        '|'.join(data_extensions) + r'))["\']',
        re.IGNORECASE
    )
    
    for match in data_url_pattern.finditer(html_content):
        href = match.group(1)
        
        # Determine file extension
        file_ext = href.split('.')[-1].lower()
        if file_ext in data_extensions:
            # Resolve to absolute URL
            if href.startswith('http://') or href.startswith('https://'):
                absolute_url = href
            elif href.startswith('//'):
                absolute_url = f"{parsed_url.scheme}:{href}"
            elif href.startswith('/'):
                absolute_url = f"{base_url}{href}"
            else:
                absolute_url = urljoin(landing_url, href)
            
            filename = href.split('/')[-1].split('?')[0]
            
            # Avoid duplicates
            if not any(a['url'] == absolute_url for a in assets):
                assets.append({
                    'url': absolute_url,
                    'title': filename,
                    'format': file_ext
                })
    
    # Rank all candidates
    for asset in assets:
        asset['rank'] = _rank_candidate(asset)
        asset['validated'] = False
    
    # Sort by rank (descending)
    assets.sort(key=lambda x: x['rank'], reverse=True)
    
    # Validate top candidates if requested
    if validate and assets:
        # Validate up to max_validation_attempts top candidates
        for i, asset in enumerate(assets[:max_validation_attempts]):
            is_valid, content_type = _check_content_type(asset['url'])
            asset['validated'] = True
            
            # If validation fails (HTML response), mark with negative rank
            if not is_valid:
                asset['rank'] = INVALID_ASSET_PENALTY  # Move invalid assets to the bottom
                if content_type:
                    asset['validation_error'] = f'HTML response detected: {content_type}'
                else:
                    asset['validation_error'] = 'Invalid content type'
        
        # Re-sort after validation to move invalid assets to bottom
        assets.sort(key=lambda x: x['rank'], reverse=True)
    
    # Save to cache if enabled and we have valid assets
    if use_cache and assets:
        save_cached_urls(landing_url, assets)
    
    return assets


def extract_metadata_from_page(landing_url: str) -> Dict[str, str]:
    """
    Extract metadata (title, description) from a CMHC landing page.
    
    Args:
        landing_url: URL of the CMHC landing page.
    
    Returns:
        Dictionary containing page metadata:
            - title: Page title from <title> tag or <h1>
            - description: Meta description or first paragraph
    """
    response = retry_request(landing_url)
    html_content = response.read().decode('utf-8', errors='ignore')
    
    metadata = {}
    
    # Extract title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        metadata['title'] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
    else:
        # Fallback to h1
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
        if h1_match:
            metadata['title'] = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
    
    # Extract description from meta tag
    desc_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
        html_content,
        re.IGNORECASE
    )
    if desc_match:
        metadata['description'] = desc_match.group(1).strip()
    
    return metadata
