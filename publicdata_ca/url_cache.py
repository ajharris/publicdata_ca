"""
URL cache for CMHC landing page resolutions.

This module provides caching functionality for CMHC direct download URLs
to reduce churn and make refresh runs stable. URLs are cached in a JSON file
and validated before use.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def _get_cache_dir() -> Path:
    """Get the cache directory for storing URL cache files."""
    # Store in publicdata_ca package directory
    cache_dir = Path(__file__).parent / ".cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def _get_cache_file_path(landing_url: str) -> Path:
    """
    Get the cache file path for a given landing URL.
    
    Args:
        landing_url: The landing page URL to cache URLs for.
    
    Returns:
        Path to the cache file.
    """
    # Create a safe filename from the landing URL
    parsed = urlparse(landing_url)
    # Use the path component (without leading slash) and replace slashes with underscores
    path_part = parsed.path.lstrip('/').replace('/', '_')
    if not path_part:
        path_part = parsed.netloc.replace('.', '_')
    
    cache_filename = f"cmhc_{path_part}.json"
    return _get_cache_dir() / cache_filename


def load_cached_urls(landing_url: str) -> Optional[List[Dict[str, Any]]]:
    """
    Load cached URLs for a given landing page.
    
    Args:
        landing_url: The landing page URL to load cached URLs for.
    
    Returns:
        List of cached asset dictionaries, or None if no cache exists.
    """
    cache_file = _get_cache_file_path(landing_url)
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Validate cache structure
        if not isinstance(cache_data, dict):
            return None
        
        if 'landing_url' not in cache_data or 'assets' not in cache_data:
            return None
        
        # Verify this cache is for the correct landing URL
        if cache_data['landing_url'] != landing_url:
            return None
        
        assets = cache_data['assets']
        if not isinstance(assets, list):
            return None
        
        return assets
    
    except (json.JSONDecodeError, IOError):
        # If cache is corrupted or unreadable, return None
        return None


def save_cached_urls(landing_url: str, assets: List[Dict[str, Any]]) -> None:
    """
    Save resolved URLs to cache for a given landing page.
    
    Args:
        landing_url: The landing page URL.
        assets: List of asset dictionaries to cache.
    """
    cache_file = _get_cache_file_path(landing_url)
    
    cache_data = {
        'landing_url': landing_url,
        'assets': assets
    }
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except IOError:
        # If we can't write the cache, just continue without caching
        pass


def clear_cache(landing_url: Optional[str] = None) -> None:
    """
    Clear cached URLs.
    
    Args:
        landing_url: If provided, clear cache for this specific URL.
                    If None, clear all caches.
    """
    if landing_url:
        cache_file = _get_cache_file_path(landing_url)
        if cache_file.exists():
            cache_file.unlink()
    else:
        # Clear all cache files
        cache_dir = _get_cache_dir()
        for cache_file in cache_dir.glob('cmhc_*.json'):
            cache_file.unlink()
