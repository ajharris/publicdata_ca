"""
Tests for CMHC provider module.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from publicdata_ca.providers.cmhc import (
    download_cmhc_asset,
    resolve_cmhc_assets
)


@pytest.fixture(autouse=True)
def disable_cache():
    """Disable URL caching for all provider tests to avoid interference."""
    with patch('publicdata_ca.resolvers.cmhc_landing.load_cached_urls', return_value=None), \
         patch('publicdata_ca.resolvers.cmhc_landing.save_cached_urls'):
        yield


def test_download_cmhc_asset_validates_content_type():
    """Test that download_cmhc_asset rejects HTML downloads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock landing page with one CSV asset
        html_content = '<html><body><a href="data.csv">Data File</a></body></html>'
        mock_landing_response = Mock()
        mock_landing_response.read.return_value = html_content.encode('utf-8')
        mock_landing_response.headers = {}
        
        # Mock the download response as HTML (invalid)
        mock_download_response = Mock()
        mock_download_response.headers = {'Content-Type': 'text/html; charset=utf-8'}
        
        def mock_retry_request(url, *args, **kwargs):
            if 'data.csv' in url:
                # The asset URL returns HTML (should be rejected)
                return mock_download_response
            else:
                # Landing page
                return mock_landing_response
        
        with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', side_effect=mock_retry_request), \
             patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', return_value=(True, 'text/csv')), \
             patch('publicdata_ca.http.retry_request', side_effect=mock_retry_request):
            
            result = download_cmhc_asset(
                'https://example.com/landing',
                tmpdir
            )
            
            # Should have errors reported
            assert 'errors' in result
            assert len(result['errors']) > 0
            
            # Error should mention HTML content
            error_msg = result['errors'][0]
            assert 'HTML content' in error_msg
            
            # Should have asset with error field
            assert len(result['assets']) == 1
            assert 'error' in result['assets'][0]
            
            # No files should be downloaded
            assert len(result['files']) == 0


def test_download_cmhc_asset_successful_download():
    """Test successful download of CMHC assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock landing page with one CSV asset
        html_content = '<html><body><a href="data.csv">Data File</a></body></html>'
        mock_landing_response = Mock()
        mock_landing_response.read.return_value = html_content.encode('utf-8')
        mock_landing_response.headers = {}
        
        # Mock the download response as valid CSV
        test_csv_data = b'col1,col2\nval1,val2\n'
        mock_download_response = Mock()
        mock_download_response.headers = {'Content-Type': 'text/csv'}
        mock_download_response.read.side_effect = [test_csv_data, b'']
        
        def mock_retry_request(url, *args, **kwargs):
            if 'data.csv' in url:
                # The asset URL returns CSV
                return mock_download_response
            else:
                # Landing page
                return mock_landing_response
        
        with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', side_effect=mock_retry_request), \
             patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', return_value=(True, 'text/csv')), \
             patch('publicdata_ca.http.retry_request', side_effect=mock_retry_request):
            
            result = download_cmhc_asset(
                'https://example.com/landing',
                tmpdir
            )
            
            # Should have no errors
            assert 'errors' in result
            assert len(result['errors']) == 0
            
            # Should have downloaded one file
            assert len(result['files']) == 1
            
            # File should exist
            assert len(result['assets']) == 1
            assert 'local_path' in result['assets'][0]
            assert os.path.exists(result['assets'][0]['local_path'])
            
            # File content should be correct
            with open(result['assets'][0]['local_path'], 'rb') as f:
                assert f.read() == test_csv_data


def test_download_cmhc_asset_mixed_success_and_failure():
    """Test download with some assets succeeding and some failing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock landing page with two assets
        html_content = '''
        <html><body>
            <a href="good.csv">Good CSV</a>
            <a href="bad.csv">Bad CSV (HTML)</a>
        </body></html>
        '''
        mock_landing_response = Mock()
        mock_landing_response.read.return_value = html_content.encode('utf-8')
        mock_landing_response.headers = {}
        
        # Mock responses for each asset
        test_csv_data = b'col1,col2\nval1,val2\n'
        
        def mock_retry_request(url, *args, **kwargs):
            if 'good.csv' in url:
                # Valid CSV
                mock_response = Mock()
                mock_response.headers = {'Content-Type': 'text/csv'}
                mock_response.read.side_effect = [test_csv_data, b'']
                return mock_response
            elif 'bad.csv' in url:
                # HTML response (invalid)
                mock_response = Mock()
                mock_response.headers = {'Content-Type': 'text/html; charset=utf-8'}
                return mock_response
            else:
                # Landing page
                return mock_landing_response
        
        def mock_check_content_type(url):
            if 'bad.csv' in url:
                return (False, 'text/html')
            return (True, 'text/csv')
        
        with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', side_effect=mock_retry_request), \
             patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', side_effect=mock_check_content_type), \
             patch('publicdata_ca.http.retry_request', side_effect=mock_retry_request):
            
            result = download_cmhc_asset(
                'https://example.com/landing',
                tmpdir
            )
            
            # Should have one success and one error
            assert len(result['files']) == 1
            assert len(result['errors']) == 1
            
            # Good file should be downloaded
            assert any('Good_CSV' in f for f in result['files'])
            
            # Error should mention the bad file
            assert any('Bad CSV (HTML)' in e or 'bad.csv' in e for e in result['errors'])


def test_download_cmhc_asset_with_filter():
    """Test filtering assets by format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock landing page with multiple formats
        html_content = '''
        <html><body>
            <a href="data.csv">CSV File</a>
            <a href="data.xlsx">Excel File</a>
        </body></html>
        '''
        mock_landing_response = Mock()
        mock_landing_response.read.return_value = html_content.encode('utf-8')
        mock_landing_response.headers = {}
        
        test_csv_data = b'col1,col2\nval1,val2\n'
        
        def mock_retry_request(url, *args, **kwargs):
            if 'data.csv' in url:
                mock_response = Mock()
                mock_response.headers = {'Content-Type': 'text/csv'}
                mock_response.read.side_effect = [test_csv_data, b'']
                return mock_response
            else:
                return mock_landing_response
        
        with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', side_effect=mock_retry_request), \
             patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', return_value=(True, 'text/csv')), \
             patch('publicdata_ca.http.retry_request', side_effect=mock_retry_request):
            
            # Filter for CSV only
            result = download_cmhc_asset(
                'https://example.com/landing',
                tmpdir,
                asset_filter='csv'
            )
            
            # Should only download CSV file
            assert len(result['files']) == 1
            assert 'CSV_File' in result['files'][0]


def test_resolve_cmhc_assets_returns_list():
    """Test that resolve_cmhc_assets returns a list of assets."""
    html_content = '''
    <html><body>
        <a href="data.csv">CSV File</a>
    </body></html>
    '''
    mock_response = Mock()
    mock_response.read.return_value = html_content.encode('utf-8')
    mock_response.headers = {}
    
    with patch('publicdata_ca.resolvers.cmhc_landing.retry_request', return_value=mock_response), \
         patch('publicdata_ca.resolvers.cmhc_landing._check_content_type', return_value=(True, 'text/csv')):
        
        assets = resolve_cmhc_assets('https://example.com/landing')
        
        assert isinstance(assets, list)
        assert len(assets) == 1
        assert 'url' in assets[0]
        assert 'title' in assets[0]
        assert 'format' in assets[0]
