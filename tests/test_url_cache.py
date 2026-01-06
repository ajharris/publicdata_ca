"""
Tests for URL cache module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from publicdata_ca.url_cache import (
    load_cached_urls,
    save_cached_urls,
    clear_cache,
    _get_cache_file_path,
)


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    
    # Patch the _get_cache_dir function to use temp directory
    with patch('publicdata_ca.url_cache._get_cache_dir', return_value=cache_dir):
        yield cache_dir


def test_get_cache_file_path():
    """Test that cache file paths are generated correctly."""
    landing_url = "https://www.cmhc-schl.gc.ca/professionals/housing-data/table"
    cache_path = _get_cache_file_path(landing_url)
    
    assert cache_path.name.startswith('cmhc_')
    assert cache_path.name.endswith('.json')
    assert cache_path.parent.name == '.cache'


def test_save_and_load_cached_urls(temp_cache_dir):
    """Test saving and loading cached URLs."""
    landing_url = "https://example.com/data-page"
    assets = [
        {'url': 'https://example.com/file1.csv', 'title': 'File 1', 'format': 'csv', 'rank': 200},
        {'url': 'https://example.com/file2.xlsx', 'title': 'File 2', 'format': 'xlsx', 'rank': 300},
    ]
    
    # Save to cache
    save_cached_urls(landing_url, assets)
    
    # Load from cache
    loaded_assets = load_cached_urls(landing_url)
    
    assert loaded_assets is not None
    assert len(loaded_assets) == 2
    assert loaded_assets[0]['url'] == 'https://example.com/file1.csv'
    assert loaded_assets[1]['url'] == 'https://example.com/file2.xlsx'


def test_load_cached_urls_returns_none_when_no_cache(temp_cache_dir):
    """Test that load_cached_urls returns None when no cache exists."""
    landing_url = "https://example.com/nonexistent-page"
    
    loaded_assets = load_cached_urls(landing_url)
    
    assert loaded_assets is None


def test_load_cached_urls_returns_none_for_corrupted_cache(temp_cache_dir):
    """Test that load_cached_urls returns None for corrupted cache files."""
    landing_url = "https://example.com/data-page"
    cache_file = _get_cache_file_path(landing_url)
    
    # Create a corrupted cache file
    with open(cache_file, 'w') as f:
        f.write("not valid json{")
    
    loaded_assets = load_cached_urls(landing_url)
    
    assert loaded_assets is None


def test_load_cached_urls_returns_none_for_wrong_structure(temp_cache_dir):
    """Test that load_cached_urls returns None for wrong cache structure."""
    landing_url = "https://example.com/data-page"
    cache_file = _get_cache_file_path(landing_url)
    
    # Create a cache file with wrong structure
    with open(cache_file, 'w') as f:
        json.dump({'wrong_key': 'value'}, f)
    
    loaded_assets = load_cached_urls(landing_url)
    
    assert loaded_assets is None


def test_load_cached_urls_validates_landing_url(temp_cache_dir):
    """Test that load_cached_urls validates the landing URL matches."""
    landing_url = "https://example.com/data-page"
    cache_file = _get_cache_file_path(landing_url)
    
    # Create a cache for a different URL
    cache_data = {
        'landing_url': 'https://different.com/page',
        'assets': [{'url': 'https://example.com/file.csv', 'title': 'File', 'format': 'csv'}]
    }
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f)
    
    loaded_assets = load_cached_urls(landing_url)
    
    assert loaded_assets is None


def test_clear_cache_specific_url(temp_cache_dir):
    """Test clearing cache for a specific URL."""
    landing_url = "https://example.com/data-page"
    assets = [{'url': 'https://example.com/file.csv', 'title': 'File', 'format': 'csv'}]
    
    # Save to cache
    save_cached_urls(landing_url, assets)
    assert load_cached_urls(landing_url) is not None
    
    # Clear cache for this URL
    clear_cache(landing_url)
    
    # Cache should be gone
    assert load_cached_urls(landing_url) is None


def test_clear_cache_all(temp_cache_dir):
    """Test clearing all caches."""
    landing_url1 = "https://example.com/page1"
    landing_url2 = "https://example.com/page2"
    assets = [{'url': 'https://example.com/file.csv', 'title': 'File', 'format': 'csv'}]
    
    # Save to multiple caches
    save_cached_urls(landing_url1, assets)
    save_cached_urls(landing_url2, assets)
    
    assert load_cached_urls(landing_url1) is not None
    assert load_cached_urls(landing_url2) is not None
    
    # Clear all caches
    clear_cache()
    
    # All caches should be gone
    assert load_cached_urls(landing_url1) is None
    assert load_cached_urls(landing_url2) is None


def test_save_cached_urls_creates_directory_if_missing():
    """Test that save_cached_urls handles missing cache directory gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "new_cache_dir"
        # Create the directory since _get_cache_dir would normally do this
        cache_dir.mkdir()
        
        with patch('publicdata_ca.url_cache._get_cache_dir', return_value=cache_dir):
            landing_url = "https://example.com/data-page"
            assets = [{'url': 'https://example.com/file.csv', 'title': 'File', 'format': 'csv'}]
            
            # Save should work even with a fresh directory
            save_cached_urls(landing_url, assets)
            
            # And we should be able to load the cache
            loaded = load_cached_urls(landing_url)
            assert loaded is not None


def test_cache_preserves_all_asset_fields(temp_cache_dir):
    """Test that caching preserves all asset fields."""
    landing_url = "https://example.com/data-page"
    assets = [
        {
            'url': 'https://example.com/file.csv',
            'title': 'File 1',
            'format': 'csv',
            'rank': 200,
            'validated': True,
        }
    ]
    
    save_cached_urls(landing_url, assets)
    loaded = load_cached_urls(landing_url)
    
    assert loaded is not None
    assert loaded[0]['url'] == assets[0]['url']
    assert loaded[0]['title'] == assets[0]['title']
    assert loaded[0]['format'] == assets[0]['format']
    assert loaded[0]['rank'] == assets[0]['rank']
    assert loaded[0]['validated'] == assets[0]['validated']
