"""
Tests for CMHC landing page resolver module.
"""

from unittest.mock import Mock, patch
from urllib.error import URLError

import pytest

from publicdata_ca.resolvers.cmhc_landing import (
    resolve_cmhc_landing_page,
    _check_content_type,
    _rank_candidate,
    extract_metadata_from_page
)


def test_rank_candidate_prefers_xlsx():
    """Test that XLSX files get higher ranking than other formats."""
    xlsx_candidate = {'url': 'data.xlsx', 'title': 'Data', 'format': 'xlsx'}
    csv_candidate = {'url': 'data.csv', 'title': 'Data', 'format': 'csv'}
    xls_candidate = {'url': 'data.xls', 'title': 'Data', 'format': 'xls'}
    
    xlsx_rank = _rank_candidate(xlsx_candidate)
    csv_rank = _rank_candidate(csv_candidate)
    xls_rank = _rank_candidate(xls_candidate)
    
    assert xlsx_rank > csv_rank
    assert csv_rank > xls_rank


def test_rank_candidate_prefers_direct_urls():
    """Test that direct URLs (no query params) rank higher."""
    direct_url = {'url': 'https://example.com/data.csv', 'title': 'Data', 'format': 'csv'}
    query_url = {'url': 'https://example.com/data.csv?id=123', 'title': 'Data', 'format': 'csv'}
    
    direct_rank = _rank_candidate(direct_url)
    query_rank = _rank_candidate(query_url)
    
    assert direct_rank > query_rank


def test_rank_candidate_prefers_data_paths():
    """Test that URLs with /data/ or /download/ paths rank higher."""
    data_url = {'url': 'https://example.com/data/file.csv', 'title': 'File', 'format': 'csv'}
    download_url = {'url': 'https://example.com/download/file.csv', 'title': 'File', 'format': 'csv'}
    other_url = {'url': 'https://example.com/other/file.csv', 'title': 'File', 'format': 'csv'}
    
    data_rank = _rank_candidate(data_url)
    download_rank = _rank_candidate(download_url)
    other_rank = _rank_candidate(other_url)
    
    assert data_rank > other_rank
    assert download_rank > other_rank


def test_rank_candidate_penalizes_session_urls():
    """Test that URLs with session/temp tokens are penalized."""
    clean_url = {'url': 'https://example.com/data.csv', 'title': 'Data', 'format': 'csv'}
    session_url = {'url': 'https://example.com/data.csv?session=abc', 'title': 'Data', 'format': 'csv'}
    temp_url = {'url': 'https://example.com/temp/data.csv', 'title': 'Data', 'format': 'csv'}
    
    clean_rank = _rank_candidate(clean_url)
    session_rank = _rank_candidate(session_url)
    temp_rank = _rank_candidate(temp_url)
    
    assert clean_rank > session_rank
    assert clean_rank > temp_rank


def test_rank_candidate_prefers_informative_titles():
    """Test that informative titles increase ranking."""
    descriptive = {'url': 'https://example.com/abc123.csv', 'title': 'Housing Market Statistics 2023', 'format': 'csv'}
    filename_only = {'url': 'https://example.com/abc123.csv', 'title': 'abc123.csv', 'format': 'csv'}
    
    descriptive_rank = _rank_candidate(descriptive)
    filename_rank = _rank_candidate(filename_only)
    
    assert descriptive_rank > filename_rank


def test_check_content_type_rejects_html():
    """Test that HTML content types are rejected."""
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'text/html; charset=utf-8'}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/page.html')
        
        assert not is_valid
        assert 'text/html' in content_type


def test_check_content_type_accepts_csv():
    """Test that CSV content types are accepted."""
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'text/csv'}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/data.csv')
        
        assert is_valid
        assert content_type == 'text/csv'


def test_check_content_type_accepts_xlsx():
    """Test that XLSX content types are accepted."""
    mock_response = Mock()
    mock_response.headers = {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/data.xlsx')
        
        assert is_valid


def test_check_content_type_accepts_zip():
    """Test that ZIP content types are accepted."""
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'application/zip'}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/data.zip')
        
        assert is_valid


def test_check_content_type_accepts_json():
    """Test that JSON content types are accepted."""
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'application/json'}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/data.json')
        
        assert is_valid


def test_check_content_type_accepts_octet_stream():
    """Test that generic binary content types are accepted."""
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'application/octet-stream'}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/data.bin')
        
        assert is_valid


def test_check_content_type_handles_empty_header():
    """Test that empty Content-Type headers are treated as valid."""
    mock_response = Mock()
    mock_response.headers = {}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/data.csv')
        
        assert is_valid


def test_check_content_type_handles_request_failure():
    """Test that request failures don't reject URLs."""
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', side_effect=URLError('Failed')):
        is_valid, content_type = _check_content_type('https://example.com/data.csv')
        
        # Should assume valid if we can't check
        assert is_valid
        assert content_type is None


def test_resolve_cmhc_landing_page_extracts_csv_links():
    """Test extraction of CSV links from HTML."""
    html_content = '''
    <html>
        <body>
            <a href="data1.csv">Housing Data</a>
            <a href="/downloads/data2.csv">Market Stats</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response), \
         patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', return_value=(True, 'text/csv')):
        
        assets = resolve_cmhc_landing_page('https://example.com/landing', validate=True)
        
        assert len(assets) == 2
        assert all(a['format'] == 'csv' for a in assets)
        assert assets[0]['title'] == 'Housing Data'
        assert assets[1]['title'] == 'Market Stats'


def test_resolve_cmhc_landing_page_extracts_xlsx_links():
    """Test extraction of XLSX links from HTML."""
    html_content = '''
    <html>
        <body>
            <a href="report.xlsx">Annual Report</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response), \
         patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', return_value=(True, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')):
        
        assets = resolve_cmhc_landing_page('https://example.com/landing', validate=True)
        
        assert len(assets) == 1
        assert assets[0]['format'] == 'xlsx'
        assert assets[0]['title'] == 'Annual Report'


def test_resolve_cmhc_landing_page_ranks_candidates():
    """Test that candidates are ranked correctly."""
    html_content = '''
    <html>
        <body>
            <a href="data.csv">CSV Data</a>
            <a href="data.xlsx">Excel Data</a>
            <a href="data.xls">Old Excel</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page('https://example.com/landing', validate=False)
        
        # Should have all three files
        assert len(assets) == 3
        
        # All should have rank scores
        assert all('rank' in a for a in assets)
        
        # XLSX should be ranked highest
        assert assets[0]['format'] == 'xlsx'
        assert assets[0]['rank'] > assets[1]['rank']


def test_resolve_cmhc_landing_page_validates_and_rejects_html():
    """Test that HTML responses are validated and ranked lower."""
    html_content = '''
    <html>
        <body>
            <a href="data.csv">Real CSV</a>
            <a href="fake.csv">Fake CSV (actually HTML)</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    def mock_check(url):
        if 'fake' in url:
            return (False, 'text/html')
        return (True, 'text/csv')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response), \
         patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', side_effect=mock_check):
        
        assets = resolve_cmhc_landing_page('https://example.com/landing', validate=True)
        
        assert len(assets) == 2
        
        # Real CSV should be first (positive rank)
        assert assets[0]['title'] == 'Real CSV'
        assert assets[0]['rank'] > 0
        assert assets[0]['validated']
        
        # Fake CSV should be last (negative rank)
        assert assets[1]['title'] == 'Fake CSV (actually HTML)'
        assert assets[1]['rank'] < 0
        assert assets[1]['validated']
        assert 'validation_error' in assets[1]


def test_resolve_cmhc_landing_page_without_validation():
    """Test that validation can be disabled."""
    html_content = '''
    <html>
        <body>
            <a href="data.csv">CSV Data</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page('https://example.com/landing', validate=False)
        
        assert len(assets) == 1
        assert not assets[0]['validated']
        assert 'validation_error' not in assets[0]


def test_resolve_cmhc_landing_page_resolves_absolute_urls():
    """Test that relative URLs are converted to absolute."""
    html_content = '''
    <html>
        <body>
            <a href="/data/file.csv">Absolute Path</a>
            <a href="relative.csv">Relative</a>
            <a href="https://other.com/file.csv">Full URL</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page('https://example.com/page', validate=False)
        
        assert len(assets) == 3
        
        # All URLs should be absolute
        assert all(a['url'].startswith('http') for a in assets)
        
        # Check specific resolutions
        urls = {a['title']: a['url'] for a in assets}
        assert urls['Absolute Path'] == 'https://example.com/data/file.csv'
        assert urls['Relative'].startswith('https://example.com/')
        assert urls['Full URL'] == 'https://other.com/file.csv'


def test_resolve_cmhc_landing_page_avoids_duplicates():
    """Test that duplicate URLs are filtered out."""
    html_content = '''
    <html>
        <body>
            <a href="data.csv">Data File</a>
            <a href="data.csv">Same File Different Text</a>
            <a href="other.csv">Different File</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page('https://example.com/page', validate=False)
        
        # Should deduplicate - first two are same URL, third is different
        assert len(assets) == 2
        
        # URLs should be unique
        urls = [a['url'] for a in assets]
        assert len(urls) == len(set(urls))


def test_resolve_cmhc_landing_page_extracts_data_attributes():
    """Test extraction of URLs from data-* attributes."""
    html_content = '''
    <html>
        <body>
            <div data-url="dataset1.csv">Dataset 1</div>
            <div data-href="dataset2.xlsx">Dataset 2</div>
            <div data-download="dataset3.zip">Dataset 3</div>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        assets = resolve_cmhc_landing_page('https://example.com/page', validate=False)
        
        assert len(assets) == 3
        formats = {a['format'] for a in assets}
        assert formats == {'csv', 'xlsx', 'zip'}


def test_resolve_cmhc_landing_page_limits_validation_attempts():
    """Test that validation is limited to top candidates."""
    html_content = '''
    <html>
        <body>
            <a href="file1.csv">File 1</a>
            <a href="file2.csv">File 2</a>
            <a href="file3.csv">File 3</a>
            <a href="file4.csv">File 4</a>
            <a href="file5.csv">File 5</a>
            <a href="file6.csv">File 6</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    validation_calls = []
    
    def mock_check(url):
        validation_calls.append(url)
        return (True, 'text/csv')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response), \
         patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', side_effect=mock_check):
        
        assets = resolve_cmhc_landing_page(
            'https://example.com/page',
            validate=True,
            max_validation_attempts=3
        )
        
        # Should validate only top 3 candidates
        assert len(validation_calls) == 3
        
        # First 3 should be validated
        validated_count = sum(1 for a in assets if a['validated'])
        assert validated_count == 3


def test_extract_metadata_from_page():
    """Test extraction of page metadata."""
    html_content = '''
    <html>
        <head>
            <title>CMHC Housing Data Portal</title>
            <meta name="description" content="Access housing market statistics and data">
        </head>
        <body>
            <h1>Housing Data</h1>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        metadata = extract_metadata_from_page('https://example.com/page')
        
        assert metadata['title'] == 'CMHC Housing Data Portal'
        assert metadata['description'] == 'Access housing market statistics and data'


def test_extract_metadata_fallback_to_h1():
    """Test that metadata extraction falls back to h1 if no title tag."""
    html_content = '''
    <html>
        <body>
            <h1>Main Heading</h1>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        metadata = extract_metadata_from_page('https://example.com/page')
        
        assert metadata['title'] == 'Main Heading'


def test_check_content_type_case_insensitive():
    """Test that content type checking is case insensitive."""
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'TEXT/HTML; charset=utf-8'}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response):
        is_valid, content_type = _check_content_type('https://example.com/page.html')
        
        assert not is_valid
        assert 'text/html' in content_type.lower()
