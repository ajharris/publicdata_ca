"""
Tests for HTTP utilities module.
"""

import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, HTTPError as RequestsHTTPError
import requests

import pytest

from publicdata_ca.http import (
    get_default_headers,
    retry_request,
    download_file
)


def test_get_default_headers():
    """Test that default headers include required fields."""
    headers = get_default_headers()
    
    assert 'User-Agent' in headers
    assert 'publicdata_ca' in headers['User-Agent']
    assert 'Accept' in headers
    assert 'Accept-Encoding' in headers


def test_retry_request_success_on_first_try():
    """Test successful request on first attempt."""
    mock_response = Mock()
    mock_response.content = b'test data'
    mock_response.status_code = 200
    
    with patch('publicdata_ca.http.requests.get', return_value=mock_response) as mock_get:
        response = retry_request('https://example.com/data.csv')
        
        assert response == mock_response
        assert mock_get.call_count == 1


def test_retry_request_with_custom_headers():
    """Test that custom headers are used in requests."""
    mock_response = Mock()
    mock_response.status_code = 200
    custom_headers = {'Authorization': 'Bearer token123'}
    
    with patch('publicdata_ca.http.requests.get', return_value=mock_response) as mock_get:
        retry_request('https://example.com/data.csv', headers=custom_headers)
        
        # Verify get was called with custom headers
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['headers'] == custom_headers


def test_retry_request_succeeds_after_retries():
    """Test that request succeeds after transient failures."""
    mock_response = Mock()
    mock_response.content = b'test data'
    mock_response.status_code = 200
    
    # Fail twice, then succeed
    with patch('publicdata_ca.http.requests.get') as mock_get, \
         patch('publicdata_ca.http.time.sleep'):  # Mock sleep to speed up test
        
        mock_get.side_effect = [
            RequestException('Connection failed'),
            RequestException('Connection failed'),
            mock_response
        ]
        
        response = retry_request('https://example.com/data.csv', max_retries=3, retry_delay=0.1)
        
        assert response == mock_response
        assert mock_get.call_count == 3


def test_retry_request_fails_after_max_retries():
    """Test that request fails after exceeding max retries."""
    with patch('publicdata_ca.http.requests.get') as mock_get, \
         patch('publicdata_ca.http.time.sleep'):
        
        mock_get.side_effect = RequestException('Connection failed')
        
        with pytest.raises(RequestException):
            retry_request('https://example.com/data.csv', max_retries=3, retry_delay=0.1)
        
        assert mock_get.call_count == 3


def test_retry_request_does_not_retry_4xx_errors():
    """Test that 4xx client errors are not retried (except 429 and 408)."""
    with patch('publicdata_ca.http.requests.get') as mock_get:
        
        # 404 should not be retried
        mock_response = Mock()
        mock_response.status_code = 404
        error = requests.HTTPError("404 Client Error")
        error.response = mock_response
        mock_get.side_effect = error
        
        with pytest.raises(requests.HTTPError):
            retry_request('https://example.com/data.csv', max_retries=3)
        
        # Should only try once, no retries
        assert mock_get.call_count == 1


def test_retry_request_retries_5xx_errors():
    """Test that 5xx server errors are retried."""
    mock_success = Mock()
    mock_success.status_code = 200
    
    with patch('publicdata_ca.http.requests.get') as mock_get, \
         patch('publicdata_ca.http.time.sleep'):
        
        # Fail with 500, then succeed
        mock_error = Mock()
        mock_error.status_code = 500
        error = requests.HTTPError("500 Server Error")
        error.response = mock_error
        mock_get.side_effect = [error, mock_success]
        
        response = retry_request('https://example.com/data.csv', max_retries=3, retry_delay=0.1)
        
        assert response == mock_success
        assert mock_get.call_count == 2


def test_retry_request_retries_429_rate_limit():
    """Test that 429 rate limit errors are retried."""
    mock_success = Mock()
    mock_success.status_code = 200
    
    with patch('publicdata_ca.http.requests.get') as mock_get, \
         patch('publicdata_ca.http.time.sleep'):
        
        # Fail with 429, then succeed
        mock_error = Mock()
        mock_error.status_code = 429
        error = requests.HTTPError("429 Too Many Requests")
        error.response = mock_error
        mock_get.side_effect = [error, mock_success]
        
        response = retry_request('https://example.com/data.csv', max_retries=3, retry_delay=0.1)
        
        assert response == mock_success
        assert mock_get.call_count == 2


def test_download_file_creates_file():
    """Test that download_file creates a file with correct content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test_file.csv')
        test_data = b'column1,column2\nvalue1,value2\n'
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/csv'}
        # Simulate streaming by returning chunks
        mock_response.iter_content = Mock(return_value=[test_data[:10], test_data[10:]])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            result_path = download_file('https://example.com/data.csv', output_path, write_metadata=False)
            
            assert result_path == output_path
            assert os.path.exists(output_path)
            
            with open(output_path, 'rb') as f:
                content = f.read()
                assert content == test_data



def test_download_file_streaming_with_chunks():
    """Test that download_file uses streaming with configurable chunk size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'large_file.dat')
        
        # Create test data larger than default chunk size
        test_data = b'x' * 20000
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'application/octet-stream'}
        # Simulate reading in chunks
        chunk_size = 8192
        chunks = [test_data[i:i+chunk_size] for i in range(0, len(test_data), chunk_size)]
        mock_response.iter_content = Mock(return_value=chunks)
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/large.dat', output_path, chunk_size=chunk_size, write_metadata=False)
            
            # Verify file was written correctly
            with open(output_path, 'rb') as f:
                content = f.read()
                assert content == test_data
            
            # Verify iter_content was called with chunk_size
            mock_response.iter_content.assert_called_once_with(chunk_size=chunk_size)


def test_download_file_with_custom_chunk_size():
    """Test download_file with custom chunk size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.dat')
        test_data = b'abcd' * 100  # 400 bytes
        custom_chunk_size = 50
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'application/octet-stream'}
        chunks = [test_data[i:i+custom_chunk_size] 
                  for i in range(0, len(test_data), custom_chunk_size)]
        mock_response.iter_content = Mock(return_value=chunks)
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.dat', output_path, chunk_size=custom_chunk_size, write_metadata=False)
            
            with open(output_path, 'rb') as f:
                assert f.read() == test_data
            
            # Verify iter_content was called with custom chunk size
            mock_response.iter_content.assert_called_with(chunk_size=custom_chunk_size)


def test_download_file_respects_max_retries():
    """Test that download_file passes max_retries to retry_request."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.csv')
        
        with patch('publicdata_ca.http.retry_request') as mock_retry:
            mock_response = Mock()
            mock_response.headers = {}
            mock_response.iter_content = Mock(return_value=[])
            mock_retry.return_value = mock_response
            
            download_file('https://example.com/data.csv', output_path, max_retries=5, write_metadata=False)
            
            # Verify max_retries was passed through
            mock_retry.assert_called_once()
            assert mock_retry.call_args[1]['max_retries'] == 5


def test_download_file_respects_custom_headers():
    """Test that download_file passes custom headers to retry_request."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.csv')
        custom_headers = {'X-Custom': 'value'}
        
        with patch('publicdata_ca.http.retry_request') as mock_retry:
            mock_response = Mock()
            mock_response.headers = {}
            mock_response.iter_content = Mock(return_value=[])
            mock_retry.return_value = mock_response
            
            download_file('https://example.com/data.csv', output_path, headers=custom_headers, write_metadata=False)
            
            # Verify headers were passed through
            assert mock_retry.call_args[1]['headers'] == custom_headers


def test_retry_request_timeout_parameter():
    """Test that timeout parameter is used in requests."""
    mock_response = Mock()
    mock_response.status_code = 200
    
    with patch('publicdata_ca.http.requests.get', return_value=mock_response) as mock_get:
        retry_request('https://example.com/data.csv', timeout=60)
        
        # Verify get was called with timeout
        call_args = mock_get.call_args
        assert call_args[1]['timeout'] == 60


def test_exponential_backoff_timing():
    """Test that retry delays follow exponential backoff."""
    with patch('publicdata_ca.http.requests.get') as mock_get, \
         patch('publicdata_ca.http.time.sleep') as mock_sleep:
        
        mock_get.side_effect = [
            RequestException('Failed'),
            RequestException('Failed'),
            RequestException('Failed')
        ]
        
        with pytest.raises(RequestException):
            retry_request('https://example.com/data.csv', max_retries=3, retry_delay=1.0)
        
        # Should sleep twice (after first and second attempts)
        assert mock_sleep.call_count == 2
        
        # Verify exponential backoff: 1.0, 2.0
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0  # First retry delay
        assert sleep_calls[1] == 2.0  # Second retry delay (doubled)


def test_download_file_with_content_validation_accepts_csv():
    """Test that download_file with validation accepts CSV content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'col1,col2\nval1,val2\n'
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/csv'}
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            result_path = download_file(
                'https://example.com/data.csv',
                output_path,
                validate_content_type=True
            )
            
            assert result_path == output_path
            assert os.path.exists(output_path)
            
            with open(output_path, 'rb') as f:
                assert f.read() == test_data


def test_download_file_with_content_validation_rejects_html():
    """Test that download_file with validation rejects HTML content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/html; charset=utf-8'}
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            with pytest.raises(ValueError) as exc_info:
                download_file(
                    'https://example.com/data.csv',
                    output_path,
                    validate_content_type=True
                )
            
            # Verify error message is actionable
            error_msg = str(exc_info.value)
            assert 'HTML content' in error_msg
            assert 'Content-Type' in error_msg
            assert 'text/html' in error_msg
            
            # File should not be created
            assert not os.path.exists(output_path)


def test_download_file_with_content_validation_rejects_xhtml():
    """Test that download_file with validation rejects XHTML content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.xlsx')
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'application/xhtml+xml'}
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            with pytest.raises(ValueError) as exc_info:
                download_file(
                    'https://example.com/data.xlsx',
                    output_path,
                    validate_content_type=True
                )
            
            assert 'HTML content' in str(exc_info.value)
            assert not os.path.exists(output_path)


def test_download_file_without_validation_accepts_html():
    """Test that download_file without validation accepts HTML (backward compatibility)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'page.html')
        test_data = b'<html><body>Content</body></html>'
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            # Should not raise when validation is disabled (default)
            result_path = download_file(
                'https://example.com/page.html',
                output_path,
                validate_content_type=False,
                write_metadata=False
            )
            
            assert result_path == output_path
            assert os.path.exists(output_path)


def test_download_file_writes_metadata():
    """Test that download_file writes provenance metadata by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'column1,column2\nvalue1,value2\n'
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/csv; charset=utf-8'}
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.csv', output_path, write_metadata=True)
            
            # Verify data file exists
            assert os.path.exists(output_path)
            
            # Verify metadata file was created
            meta_file = output_path + '.meta.json'
            assert os.path.exists(meta_file)
            
            # Verify metadata content
            import json
            with open(meta_file, 'r') as f:
                metadata = json.load(f)
            
            assert metadata['source_url'] == 'https://example.com/data.csv'
            assert metadata['content_type'] == 'text/csv; charset=utf-8'
            assert metadata['file'] == 'data.csv'
            assert 'hash' in metadata
            assert 'downloaded_at' in metadata


def test_download_file_metadata_disabled():
    """Test that metadata writing can be disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'test data'
        
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/csv'}
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.csv', output_path, write_metadata=False)
            
            # Verify data file exists
            assert os.path.exists(output_path)
            
            # Verify metadata file was NOT created
            meta_file = output_path + '.meta.json'
            assert not os.path.exists(meta_file)


def test_download_file_with_http_cache_saves_metadata():
    """Test that download_file saves HTTP cache metadata when caching is enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'test,data\n1,2\n'
        
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'text/csv',
            'ETag': '"abc123"',
            'Last-Modified': 'Wed, 21 Oct 2015 07:28:00 GMT'
        }
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.csv', output_path, write_metadata=False, use_cache=True)
            
            # Verify file was downloaded
            assert os.path.exists(output_path)
            
            # Verify HTTP cache metadata was created
            cache_file = output_path + '.http_cache.json'
            assert os.path.exists(cache_file)
            
            # Verify cache contents
            import json
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            assert cache_data['etag'] == '"abc123"'
            assert cache_data['last_modified'] == 'Wed, 21 Oct 2015 07:28:00 GMT'
            assert cache_data['url'] == 'https://example.com/data.csv'


def test_download_file_with_cache_disabled_no_metadata():
    """Test that HTTP cache metadata is not saved when caching is disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'test data'
        
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'text/csv',
            'ETag': '"abc123"'
        }
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.csv', output_path, write_metadata=False, use_cache=False)
            
            # Verify file was downloaded
            assert os.path.exists(output_path)
            
            # Verify HTTP cache metadata was NOT created
            cache_file = output_path + '.http_cache.json'
            assert not os.path.exists(cache_file)


def test_download_file_revalidation_304_not_modified():
    """Test that download_file handles 304 Not Modified responses correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        original_data = b'original,data\n1,2\n'
        
        # Create existing file with cache metadata
        with open(output_path, 'wb') as f:
            f.write(original_data)
        
        from publicdata_ca.http_cache import save_cache_metadata
        save_cache_metadata(
            output_path,
            etag='"abc123"',
            last_modified='Wed, 21 Oct 2015 07:28:00 GMT',
            url='https://example.com/data.csv'
        )
        
        # Mock 304 Not Modified response
        def mock_retry_with_304(url, max_retries=3, headers=None):
            # Check that conditional headers were sent
            assert headers is not None
            assert 'If-None-Match' in headers
            assert headers['If-None-Match'] == '"abc123"'
            assert 'If-Modified-Since' in headers
            
            # Raise HTTPError with 304 status
            mock_response = Mock()
            mock_response.status_code = 304
            error = requests.HTTPError("304 Not Modified")
            error.response = mock_response
            raise error
        
        with patch('publicdata_ca.http.retry_request', side_effect=mock_retry_with_304):
            result = download_file('https://example.com/data.csv', output_path, write_metadata=False, use_cache=True)
            
            # Verify file path is returned
            assert result == output_path
            
            # Verify original file is unchanged
            with open(output_path, 'rb') as f:
                assert f.read() == original_data


def test_download_file_revalidation_200_file_changed():
    """Test that download_file downloads when server returns 200 (file changed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        original_data = b'original,data\n1,2\n'
        new_data = b'new,data\n3,4\n'
        
        # Create existing file with cache metadata
        with open(output_path, 'wb') as f:
            f.write(original_data)
        
        from publicdata_ca.http_cache import save_cache_metadata
        save_cache_metadata(
            output_path,
            etag='"abc123"',
            url='https://example.com/data.csv'
        )
        
        # Mock response with new data and new ETag
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'text/csv',
            'ETag': '"xyz789"'  # Different ETag
        }
        mock_response.iter_content = Mock(return_value=[new_data])
        
        def mock_retry_with_conditional(url, max_retries=3, headers=None):
            # Verify conditional headers were sent
            assert 'If-None-Match' in headers
            return mock_response
        
        with patch('publicdata_ca.http.retry_request', side_effect=mock_retry_with_conditional):
            result = download_file('https://example.com/data.csv', output_path, write_metadata=False, use_cache=True)
            
            # Verify file was updated
            with open(output_path, 'rb') as f:
                assert f.read() == new_data
            
            # Verify cache metadata was updated
            import json
            cache_file = output_path + '.http_cache.json'
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            assert cache_data['etag'] == '"xyz789"'


def test_download_file_first_download_with_cache():
    """Test first download creates cache metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'new_file.csv')
        test_data = b'test,data\n1,2\n'
        
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'text/csv',
            'ETag': '"first123"'
        }
        mock_response.iter_content = Mock(return_value=[test_data])
        
        def mock_retry_first_download(url, max_retries=3, headers=None):
            # Should not have conditional headers on first download
            assert 'If-None-Match' not in headers
            assert 'If-Modified-Since' not in headers
            return mock_response
        
        with patch('publicdata_ca.http.retry_request', side_effect=mock_retry_first_download):
            download_file('https://example.com/new.csv', output_path, write_metadata=False, use_cache=True)
            
            # Verify cache metadata was created
            import json
            cache_file = output_path + '.http_cache.json'
            assert os.path.exists(cache_file)
            
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            assert cache_data['etag'] == '"first123"'


def test_download_file_cache_with_only_etag():
    """Test caching works with only ETag (no Last-Modified)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'test data'
        
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'text/csv',
            'ETag': '"etag-only"'
            # No Last-Modified header
        }
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.csv', output_path, write_metadata=False, use_cache=True)
            
            import json
            cache_file = output_path + '.http_cache.json'
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            assert cache_data['etag'] == '"etag-only"'
            assert cache_data['last_modified'] is None


def test_download_file_cache_with_only_last_modified():
    """Test caching works with only Last-Modified (no ETag)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'test data'
        
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'text/csv',
            'Last-Modified': 'Thu, 22 Oct 2015 08:30:00 GMT'
            # No ETag header
        }
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.csv', output_path, write_metadata=False, use_cache=True)
            
            import json
            cache_file = output_path + '.http_cache.json'
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            assert cache_data['etag'] is None
            assert cache_data['last_modified'] == 'Thu, 22 Oct 2015 08:30:00 GMT'


def test_download_file_no_cache_headers_no_metadata():
    """Test that no cache metadata is saved when server doesn't send cache headers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'data.csv')
        test_data = b'test data'
        
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'text/csv'
            # No ETag or Last-Modified
        }
        mock_response.iter_content = Mock(return_value=[test_data])
        
        with patch('publicdata_ca.http.retry_request', return_value=mock_response):
            download_file('https://example.com/data.csv', output_path, write_metadata=False, use_cache=True)
            
            # Verify file was downloaded
            assert os.path.exists(output_path)
            
            # Verify no cache metadata was created (no headers to cache)
            cache_file = output_path + '.http_cache.json'
            assert not os.path.exists(cache_file)
