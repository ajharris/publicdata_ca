"""
CMHC landing page resolver.

This module provides robust scraping and URL resolution for CMHC landing pages.
CMHC data files are often accessed through landing pages where direct download URLs
may change, requiring dynamic resolution.
"""

import re
from typing import List, Dict
from urllib.parse import urljoin, urlparse
from publicdata_ca.http import retry_request


def resolve_cmhc_landing_page(landing_url: str) -> List[Dict[str, str]]:
    """
    Scrape and resolve direct download URLs from a CMHC landing page.
    
    This function parses a CMHC landing page to extract direct download links
    for data files. It handles various HTML structures and link patterns commonly
    used on CMHC websites.
    
    Args:
        landing_url: URL of the CMHC landing/catalog page.
    
    Returns:
        List of dictionaries, each containing:
            - url: Direct download URL (absolute)
            - title: Link text or filename
            - format: File extension (e.g., 'csv', 'xlsx', 'zip')
    
    Example:
        >>> assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page')
        >>> for asset in assets:
        ...     print(f"{asset['title']}: {asset['url']} ({asset['format']})")
    
    Notes:
        - Returns absolute URLs by resolving relative links
        - Filters for common data file formats (csv, xlsx, xls, zip, json, xml)
        - Extracts titles from link text or filenames
        - Robust to HTML structure variations
    """
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
