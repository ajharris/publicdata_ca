"""
Tests for Statistics Canada (StatsCan) provider module.
"""

import json
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from publicdata_ca.providers.statcan import (
    download_statcan_table,
    _normalize_pid,
    _build_wds_url,
    _extract_zip,
    _parse_manifest
)


def test_normalize_pid_already_normalized():
    """Test normalizing a PID that's already in correct format."""
    assert _normalize_pid('18100004') == '18100004'


def test_normalize_pid_with_hyphens():
    """Test normalizing a hyphenated table ID."""
    assert _normalize_pid('18-10-0004') == '18100004'
    assert _normalize_pid('14-10-0287-01') == '14100287'


def test_normalize_pid_with_trailing_digits():
    """Test normalizing a 10-digit table ID."""
    assert _normalize_pid('1810000401') == '18100004'


def test_normalize_pid_with_spaces():
    """Test normalizing a PID with spaces."""
    assert _normalize_pid(' 18100004 ') == '18100004'
    assert _normalize_pid('18 10 00 04') == '18100004'


def test_normalize_pid_invalid_format():
    """Test that invalid PIDs raise ValueError."""
    with pytest.raises(ValueError):
        _normalize_pid('invalid')
    
    with pytest.raises(ValueError):
        _normalize_pid('123')  # Too short
    
    with pytest.raises(ValueError):
        _normalize_pid('abc12345')  # Contains letters


def test_build_wds_url_english():
    """Test building WDS URL for English."""
    url = _build_wds_url('18100004', 'en')
    assert url == 'https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/en/18100004'


def test_build_wds_url_french():
    """Test building WDS URL for French."""
    url = _build_wds_url('18100004', 'fr')
    assert url == 'https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/fr/18100004'


def test_extract_zip():
    """Test extracting a ZIP file with CSV and metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a test ZIP file
        zip_path = tmpdir / 'test.zip'
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('18100004.csv', 'col1,col2\nval1,val2\n')
            zf.writestr('18100004_MetaData.csv', 'metadata_col\nmetadata_val\n')
        
        # Extract the ZIP
        output_dir = tmpdir / 'output'
        output_dir.mkdir()
        
        extracted_files = _extract_zip(zip_path, output_dir, '18100004')
        
        # Verify files were extracted
        assert len(extracted_files) == 2
        assert (output_dir / '18100004.csv').exists()
        assert (output_dir / '18100004_MetaData.csv').exists()
        
        # Verify content
        with open(output_dir / '18100004.csv', 'r') as f:
            content = f.read()
            assert 'col1,col2' in content


def test_extract_zip_skips_directories():
    """Test that directory entries in ZIP are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a test ZIP file with directory entries
        zip_path = tmpdir / 'test.zip'
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('data/', '')  # Directory entry
            zf.writestr('data/file.csv', 'content')
        
        output_dir = tmpdir / 'output'
        output_dir.mkdir()
        
        extracted_files = _extract_zip(zip_path, output_dir, '18100004')
        
        # Should only have the file, not the directory entry
        assert len(extracted_files) == 1
        assert (output_dir / 'data' / 'file.csv').exists()


def test_parse_manifest_with_json():
    """Test parsing a JSON manifest file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a manifest JSON file
        manifest_data = {
            'title': 'Consumer Price Index',
            'pid': '18100004',
            'version': '1.0'
        }
        manifest_path = tmpdir / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f)
        
        result = _parse_manifest(tmpdir, '18100004')
        
        assert result is not None
        assert result['title'] == 'Consumer Price Index'
        assert result['pid'] == '18100004'


def test_parse_manifest_with_metadata_csv():
    """Test parsing with metadata CSV file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a metadata CSV file
        metadata_path = tmpdir / '18100004_MetaData.csv'
        metadata_path.write_text('column\nvalue\n')
        
        result = _parse_manifest(tmpdir, '18100004')
        
        assert result is not None
        assert 'metadata_file' in result
        assert '18100004_MetaData.csv' in result['metadata_file']


def test_parse_manifest_no_manifest():
    """Test parsing when no manifest exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        result = _parse_manifest(tmpdir, '18100004')
        
        assert result is None


def test_parse_manifest_invalid_json():
    """Test parsing with invalid JSON manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create an invalid JSON file
        manifest_path = tmpdir / 'manifest.json'
        manifest_path.write_text('{ invalid json')
        
        result = _parse_manifest(tmpdir, '18100004')
        
        # Should return None on invalid JSON
        assert result is None


def test_download_statcan_table_success():
    """Test successful download and extraction of a StatsCan table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a mock ZIP file
        test_zip_data = b'PK\x03\x04'  # ZIP file signature
        with zipfile.ZipFile(tmpdir / 'mock.zip', 'w') as zf:
            zf.writestr('18100004.csv', 'data,values\n1,2\n')
            zf.writestr('18100004_MetaData.csv', 'meta,data\na,b\n')
        
        with open(tmpdir / 'mock.zip', 'rb') as f:
            zip_content = f.read()
        
        # Mock the download_file function
        def mock_download(url, path, max_retries):
            # Write the test ZIP to the specified path
            with open(path, 'wb') as f:
                f.write(zip_content)
            return path
        
        output_dir = tmpdir / 'output'
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table('18100004', str(output_dir), skip_existing=False)
        
        # Verify result
        assert result['provider'] == 'statcan'
        assert result['pid'] == '18100004'
        assert result['dataset_id'] == 'statcan_18100004'
        assert result['skipped'] is False
        assert len(result['files']) == 2
        
        # Verify files were extracted
        assert (output_dir / '18100004.csv').exists()
        assert (output_dir / '18100004_MetaData.csv').exists()
        
        # Verify ZIP was cleaned up
        assert not (output_dir / '18100004_temp.zip').exists()


def test_download_statcan_table_skip_existing():
    """Test skip-if-exists logic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_dir = tmpdir / 'output'
        output_dir.mkdir()
        
        # Create an existing CSV file
        existing_file = output_dir / '18100004.csv'
        existing_file.write_text('existing,data\n1,2\n')
        
        # Should skip download
        result = download_statcan_table('18100004', str(output_dir), skip_existing=True)
        
        assert result['skipped'] is True
        assert result['pid'] == '18100004'
        assert len(result['files']) == 1
        
        # File should still exist with original content
        assert existing_file.exists()
        content = existing_file.read_text()
        assert content == 'existing,data\n1,2\n'


def test_download_statcan_table_force_redownload():
    """Test that skip_existing=False forces redownload."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_dir = tmpdir / 'output'
        output_dir.mkdir()
        
        # Create an existing CSV file
        existing_file = output_dir / '18100004.csv'
        existing_file.write_text('old,data\n')
        
        # Create mock ZIP with new data
        with zipfile.ZipFile(tmpdir / 'mock.zip', 'w') as zf:
            zf.writestr('18100004.csv', 'new,data\n3,4\n')
        
        with open(tmpdir / 'mock.zip', 'rb') as f:
            zip_content = f.read()
        
        def mock_download(url, path, max_retries):
            with open(path, 'wb') as f:
                f.write(zip_content)
            return path
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table('18100004', str(output_dir), skip_existing=False)
        
        # Should have downloaded
        assert result['skipped'] is False
        
        # File should have new content
        content = existing_file.read_text()
        assert content == 'new,data\n3,4\n'


def test_download_statcan_table_with_hyphenated_id():
    """Test download with hyphenated table ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create mock ZIP
        with zipfile.ZipFile(tmpdir / 'mock.zip', 'w') as zf:
            zf.writestr('18100004.csv', 'data\n')
        
        with open(tmpdir / 'mock.zip', 'rb') as f:
            zip_content = f.read()
        
        def mock_download(url, path, max_retries):
            with open(path, 'wb') as f:
                f.write(zip_content)
            # Verify URL uses normalized PID
            assert '18100004' in url
            return path
        
        output_dir = tmpdir / 'output'
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table('18-10-0004', str(output_dir), skip_existing=False)
        
        # Should normalize to 18100004
        assert result['pid'] == '18100004'


def test_download_statcan_table_french_language():
    """Test download with French language parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create mock ZIP
        with zipfile.ZipFile(tmpdir / 'mock.zip', 'w') as zf:
            zf.writestr('18100004.csv', 'données\n')
        
        with open(tmpdir / 'mock.zip', 'rb') as f:
            zip_content = f.read()
        
        def mock_download(url, path, max_retries):
            # Verify URL uses French language
            assert '/fr/' in url
            with open(path, 'wb') as f:
                f.write(zip_content)
            return path
        
        output_dir = tmpdir / 'output'
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table('18100004', str(output_dir), language='fr', skip_existing=False)
        
        assert '/fr/' in result['url']


def test_download_statcan_table_with_manifest():
    """Test download with manifest parsing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create mock ZIP with manifest
        with zipfile.ZipFile(tmpdir / 'mock.zip', 'w') as zf:
            zf.writestr('18100004.csv', 'data\n')
            zf.writestr('18100004_MetaData.csv', 'metadata\n')
        
        with open(tmpdir / 'mock.zip', 'rb') as f:
            zip_content = f.read()
        
        def mock_download(url, path, max_retries):
            with open(path, 'wb') as f:
                f.write(zip_content)
            return path
        
        output_dir = tmpdir / 'output'
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table('18100004', str(output_dir), skip_existing=False)
        
        # Should have manifest data
        assert 'manifest' in result
        assert result['manifest'] is not None


def test_download_statcan_table_cleanup_on_error():
    """Test that ZIP file is cleaned up on error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_dir = tmpdir / 'output'
        output_dir.mkdir()
        
        # Create an invalid ZIP file
        def mock_download(url, path, max_retries):
            with open(path, 'wb') as f:
                f.write(b'not a zip file')
            return path
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            with pytest.raises(RuntimeError):
                download_statcan_table('18100004', str(output_dir), skip_existing=False)
        
        # Verify ZIP was cleaned up
        assert not (output_dir / '18100004_temp.zip').exists()


def test_download_statcan_table_respects_max_retries():
    """Test that max_retries parameter is passed to download_file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create mock ZIP
        with zipfile.ZipFile(tmpdir / 'mock.zip', 'w') as zf:
            zf.writestr('18100004.csv', 'data\n')
        
        with open(tmpdir / 'mock.zip', 'rb') as f:
            zip_content = f.read()
        
        def mock_download(url, path, max_retries):
            assert max_retries == 5
            with open(path, 'wb') as f:
                f.write(zip_content)
            return path
        
        output_dir = tmpdir / 'output'
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            download_statcan_table('18100004', str(output_dir), max_retries=5, skip_existing=False)
