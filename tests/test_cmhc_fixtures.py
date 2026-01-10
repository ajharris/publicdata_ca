"""
Offline tests for CMHC resolver using saved HTML fixtures.

These tests use real HTML fixtures instead of mocks to ensure the resolver
can handle realistic CMHC landing pages.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from urllib.parse import urlparse

from publicdata_ca.resolvers.cmhc_landing import (
    resolve_cmhc_landing_page,
    extract_metadata_from_page
)

# Get the path to test fixtures
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'cmhc'
SAMPLE_LANDING_PAGE = FIXTURES_DIR / 'sample_landing_page.html'


def load_fixture(filename):
    """Load an HTML fixture file."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return f.read()


def make_mock_html_response(html_content: str) -> Mock:
    """Create a requests-like Mock response with encoded HTML content."""
    payload = html_content.encode('utf-8')
    mock_response = Mock()
    mock_response.content = payload
    mock_response.read = Mock(return_value=payload)
    return mock_response


def test_resolve_cmhc_landing_page_with_html_fixture():
    """Test resolving assets from a real HTML fixture."""
    # Load the fixture HTML
    html_content = load_fixture('sample_landing_page.html')
    
    # Mock the HTTP request to return our fixture
    mock_response = make_mock_html_response(html_content)
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page(
            'https://example.com/landing',
            validate=False,
            use_cache=False
        )
    
    # Verify we extracted the expected assets
    # Expected files from fixture: housing-starts-2023.xlsx, market-indicators.csv, 
    # regional-data.csv, prices.xlsx, historical-data.xls, complete-dataset.zip, rental-data.csv
    # (Note: temp-export.csv with query param is not extracted, duplicate market-indicators is filtered)
    assert len(assets) >= 7, f"Expected at least 7 unique data files, got {len(assets)}"
    
    # Check that we have different file formats
    formats = {asset['format'] for asset in assets}
    assert 'xlsx' in formats
    assert 'csv' in formats
    assert 'xls' in formats
    assert 'zip' in formats
    
    # Verify XLSX is ranked highest (preferred format)
    assert assets[0]['format'] == 'xlsx'
    
    # Check specific expected files
    urls = [asset['url'] for asset in assets]
    titles = [asset['title'] for asset in assets]
    
    # Should have the housing starts file
    assert any('housing-starts-2023.xlsx' in url for url in urls)
    assert any('Housing Starts 2023' in title for title in titles)
    
    # Should have market indicators
    assert any('market-indicators.csv' in url for url in urls)
    
    # Should have regional data
    assert any('regional-data.csv' in url for url in urls)
    
    # Should have external URL (absolute)
    assert any(urlparse(url).hostname == 'external.example.com' for url in urls)


def test_resolve_cmhc_landing_page_handles_relative_urls():
    """Test that relative URLs in fixture are resolved to absolute."""
    html_content = load_fixture('sample_landing_page.html')
    
    mock_response = make_mock_html_response(html_content)
    
    base_url = 'https://www.cmhc-schl.gc.ca/en/data'
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page(
            base_url,
            validate=False,
            use_cache=False
        )
    
    # All URLs should be absolute
    for asset in assets:
        url = asset['url']
        assert url.startswith('http://') or url.startswith('https://'), \
            f"URL should be absolute: {url}"
        
        # Relative URLs should be resolved to the base domain
        if '/data/' in url or '/download/' in url:
            assert 'cmhc-schl.gc.ca' in url, \
                f"Relative URL should be resolved to base domain: {url}"


def test_resolve_cmhc_landing_page_deduplicates_urls():
    """Test that duplicate URLs in fixture are filtered out."""
    html_content = load_fixture('sample_landing_page.html')
    
    mock_response = make_mock_html_response(html_content)
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page(
            'https://example.com/landing',
            validate=False,
            use_cache=False
        )
    
    # Extract all URLs
    urls = [asset['url'] for asset in assets]
    
    # Should not have duplicates
    assert len(urls) == len(set(urls)), \
        "URLs should be unique (duplicates should be filtered)"
    
    # The fixture has market-indicators.csv twice with different titles
    # Should only appear once in results
    market_indicator_urls = [url for url in urls if 'market-indicators.csv' in url]
    assert len(market_indicator_urls) == 1, \
        "Duplicate URLs should be filtered even with different link text"


def test_resolve_cmhc_landing_page_ranks_by_format():
    """Test that assets are ranked with XLSX preferred over CSV over XLS."""
    html_content = load_fixture('sample_landing_page.html')
    
    mock_response = make_mock_html_response(html_content)
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page(
            'https://example.com/landing',
            validate=False,
            use_cache=False
        )
    
    # Find assets by format
    xlsx_assets = [a for a in assets if a['format'] == 'xlsx']
    csv_assets = [a for a in assets if a['format'] == 'csv']
    xls_assets = [a for a in assets if a['format'] == 'xls']
    
    # All XLSX files should be ranked higher than all CSV files
    if xlsx_assets and csv_assets:
        min_xlsx_rank = min(a['rank'] for a in xlsx_assets)
        max_csv_rank = max(a['rank'] for a in csv_assets)
        assert min_xlsx_rank > max_csv_rank, \
            "XLSX files should be ranked higher than CSV files"
    
    # All CSV files should be ranked higher than XLS files
    if csv_assets and xls_assets:
        min_csv_rank = min(a['rank'] for a in csv_assets)
        max_xls_rank = max(a['rank'] for a in xls_assets)
        assert min_csv_rank > max_xls_rank, \
            "CSV files should be ranked higher than XLS files"


def test_resolve_cmhc_landing_page_prefers_clean_urls():
    """Test that clean URLs without query parameters are preferred."""
    html_content = load_fixture('sample_landing_page.html')
    
    mock_response = make_mock_html_response(html_content)
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page(
            'https://example.com/landing',
            validate=False,
            use_cache=False
        )
    
    # Verify all extracted URLs are clean (no query params in the current implementation)
    # The resolver only extracts URLs ending with data extensions, so URLs with
    # query params like "file.csv?session=abc" won't be matched
    for asset in assets:
        # This is the current behavior - query params prevent matching
        # If the URL has a query param, it shouldn't be in our results
        if '?' in asset['url']:
            # If we do have query params, they should be after a valid extension
            base_url = asset['url'].split('?')[0]
            assert any(base_url.endswith(f'.{ext}') for ext in ['csv', 'xlsx', 'xls', 'zip'])
    
    # Verify that URLs with /data/ or /download/ paths are ranked higher
    data_path_assets = [a for a in assets if '/data/' in a['url'] or '/download/' in a['url']]
    other_assets = [a for a in assets if '/data/' not in a['url'] and '/download/' not in a['url']]
    
    if data_path_assets and other_assets:
        # Data path URLs should generally be ranked higher
        avg_data_rank = sum(a['rank'] for a in data_path_assets) / len(data_path_assets)
        avg_other_rank = sum(a['rank'] for a in other_assets) / len(other_assets)
        assert avg_data_rank > avg_other_rank, \
            "URLs with /data/ or /download/ paths should be ranked higher on average"


def test_resolve_cmhc_landing_page_extracts_data_attributes():
    """Test that URLs from data-* attributes are extracted."""
    html_content = load_fixture('sample_landing_page.html')
    
    mock_response = make_mock_html_response(html_content)
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page(
            'https://example.com/landing',
            validate=False,
            use_cache=False
        )
    
    # Should extract the rental-data.csv from data-url attribute
    urls = [asset['url'] for asset in assets]
    assert any('rental-data.csv' in url for url in urls), \
        "Should extract URLs from data-url attributes"


def test_extract_metadata_from_page_with_fixture():
    """Test metadata extraction from HTML fixture."""
    html_content = load_fixture('sample_landing_page.html')
    
    mock_response = make_mock_html_response(html_content)
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        metadata = extract_metadata_from_page('https://example.com/landing')
    
    # Verify title extraction
    assert 'title' in metadata
    assert 'CMHC Housing Market Data' in metadata['title']
    
    # Verify description extraction
    assert 'description' in metadata
    assert 'housing market statistics' in metadata['description'].lower()


def test_resolve_cmhc_landing_page_ignores_non_data_links():
    """Test that non-data links (HTML, PDF without extensions) are ignored."""
    html_content = load_fixture('sample_landing_page.html')
    
    mock_response = make_mock_html_response(html_content)
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page(
            'https://example.com/landing',
            validate=False,
            use_cache=False
        )
    
    # Extract all URLs
    urls = [asset['url'] for asset in assets]
    
    # Should not include about.html or contact (no extension)
    assert not any('about.html' in url for url in urls), \
        "Should not extract HTML page links"
    assert not any('contact' in url for url in urls), \
        "Should not extract links without data file extensions"
