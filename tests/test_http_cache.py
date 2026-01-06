"""
Tests for HTTP cache metadata management.
"""

import os
import json
import tempfile
from pathlib import Path

import pytest

from publicdata_ca.http_cache import (
    save_cache_metadata,
    load_cache_metadata,
    clear_cache_metadata,
    get_conditional_headers,
    _get_cache_metadata_path
)


def test_get_cache_metadata_path():
    """Test that cache metadata path is correctly generated."""
    file_path = '/path/to/data.csv'
    cache_path = _get_cache_metadata_path(file_path)
    
    assert str(cache_path) == '/path/to/data.csv.http_cache.json'


def test_save_and_load_cache_metadata():
    """Test saving and loading cache metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        # Create the actual file first (cache requires file to exist)
        with open(file_path, 'w') as f:
            f.write('test data')
        
        # Save cache metadata
        save_cache_metadata(
            file_path,
            etag='"abc123"',
            last_modified='Wed, 21 Oct 2015 07:28:00 GMT',
            url='https://example.com/data.csv'
        )
        
        # Load and verify
        metadata = load_cache_metadata(file_path)
        
        assert metadata is not None
        assert metadata['etag'] == '"abc123"'
        assert metadata['last_modified'] == 'Wed, 21 Oct 2015 07:28:00 GMT'
        assert metadata['url'] == 'https://example.com/data.csv'
        assert 'cached_at' in metadata


def test_save_cache_metadata_with_only_etag():
    """Test saving cache metadata with only ETag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(
            file_path,
            etag='"xyz789"',
            url='https://example.com/data.csv'
        )
        
        metadata = load_cache_metadata(file_path)
        
        assert metadata['etag'] == '"xyz789"'
        assert metadata['last_modified'] is None


def test_save_cache_metadata_with_only_last_modified():
    """Test saving cache metadata with only Last-Modified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(
            file_path,
            last_modified='Thu, 22 Oct 2015 08:30:00 GMT',
            url='https://example.com/data.csv'
        )
        
        metadata = load_cache_metadata(file_path)
        
        assert metadata['etag'] is None
        assert metadata['last_modified'] == 'Thu, 22 Oct 2015 08:30:00 GMT'


def test_save_cache_metadata_skips_when_no_headers():
    """Test that cache metadata is not saved when no cache headers are provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(file_path, url='https://example.com/data.csv')
        
        cache_file = _get_cache_metadata_path(file_path)
        assert not cache_file.exists()


def test_load_cache_metadata_nonexistent_file():
    """Test loading cache metadata when the actual file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'nonexistent.csv')
        
        metadata = load_cache_metadata(file_path)
        
        assert metadata is None


def test_load_cache_metadata_no_cache():
    """Test loading cache metadata when cache file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        # Create file without cache
        with open(file_path, 'w') as f:
            f.write('test data')
        
        metadata = load_cache_metadata(file_path)
        
        assert metadata is None


def test_load_cache_metadata_corrupted():
    """Test loading corrupted cache metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        # Create the actual file
        with open(file_path, 'w') as f:
            f.write('test data')
        
        # Create corrupted cache file
        cache_file = _get_cache_metadata_path(file_path)
        with open(cache_file, 'w') as f:
            f.write('invalid json{')
        
        metadata = load_cache_metadata(file_path)
        
        assert metadata is None


def test_clear_cache_metadata():
    """Test clearing cache metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        # Create file and cache
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(
            file_path,
            etag='"abc123"',
            url='https://example.com/data.csv'
        )
        
        cache_file = _get_cache_metadata_path(file_path)
        assert cache_file.exists()
        
        # Clear cache
        clear_cache_metadata(file_path)
        
        assert not cache_file.exists()


def test_clear_cache_metadata_nonexistent():
    """Test clearing cache metadata that doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        # Should not raise an error
        clear_cache_metadata(file_path)


def test_get_conditional_headers_with_etag():
    """Test getting conditional headers with ETag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(
            file_path,
            etag='"abc123"',
            url='https://example.com/data.csv'
        )
        
        headers = get_conditional_headers(file_path)
        
        assert headers['If-None-Match'] == '"abc123"'
        assert 'If-Modified-Since' not in headers


def test_get_conditional_headers_with_last_modified():
    """Test getting conditional headers with Last-Modified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(
            file_path,
            last_modified='Wed, 21 Oct 2015 07:28:00 GMT',
            url='https://example.com/data.csv'
        )
        
        headers = get_conditional_headers(file_path)
        
        assert headers['If-Modified-Since'] == 'Wed, 21 Oct 2015 07:28:00 GMT'
        assert 'If-None-Match' not in headers


def test_get_conditional_headers_with_both():
    """Test getting conditional headers with both ETag and Last-Modified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(
            file_path,
            etag='"abc123"',
            last_modified='Wed, 21 Oct 2015 07:28:00 GMT',
            url='https://example.com/data.csv'
        )
        
        headers = get_conditional_headers(file_path)
        
        assert headers['If-None-Match'] == '"abc123"'
        assert headers['If-Modified-Since'] == 'Wed, 21 Oct 2015 07:28:00 GMT'


def test_get_conditional_headers_no_cache():
    """Test getting conditional headers when no cache exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        headers = get_conditional_headers(file_path)
        
        assert headers == {}


def test_get_conditional_headers_file_not_exists():
    """Test getting conditional headers when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'nonexistent.csv')
        
        headers = get_conditional_headers(file_path)
        
        assert headers == {}


def test_cache_metadata_preserves_url():
    """Test that cache metadata preserves the source URL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        url = 'https://data.example.com/large_dataset.csv'
        save_cache_metadata(
            file_path,
            etag='"abc123"',
            url=url
        )
        
        metadata = load_cache_metadata(file_path)
        
        assert metadata['url'] == url


def test_cache_metadata_structure():
    """Test the complete structure of cache metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test_file.csv')
        
        with open(file_path, 'w') as f:
            f.write('test data')
        
        save_cache_metadata(
            file_path,
            etag='"version123"',
            last_modified='Wed, 21 Oct 2015 07:28:00 GMT',
            url='https://example.com/data.csv'
        )
        
        # Load from file directly to verify structure
        cache_file = _get_cache_metadata_path(file_path)
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        assert 'url' in data
        assert 'etag' in data
        assert 'last_modified' in data
        assert 'cached_at' in data
        # Check that timestamp is in ISO format with timezone
        assert 'T' in data['cached_at']
        assert '+00:00' in data['cached_at'] or data['cached_at'].endswith('Z')
