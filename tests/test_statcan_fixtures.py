"""
Offline tests for StatsCan provider using saved ZIP fixtures.

These tests use real ZIP file fixtures instead of creating ZIPs on the fly
to ensure the extraction logic works with realistic StatsCan data packages.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from publicdata_ca.providers.statcan import (
    download_statcan_table,
    _extract_zip,
    _parse_manifest
)


# Get the path to test fixtures
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'statcan'
SAMPLE_ZIP_FILE = FIXTURES_DIR / '18100004.zip'


def test_extract_zip_with_fixture():
    """Test ZIP extraction using a real StatsCan ZIP fixture."""
    assert SAMPLE_ZIP_FILE.exists(), \
        f"Fixture not found: {SAMPLE_ZIP_FILE}"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Extract the fixture ZIP
        extracted_files = _extract_zip(SAMPLE_ZIP_FILE, output_dir, '18100004')
        
        # Verify files were extracted
        assert len(extracted_files) == 2, \
            "Should extract 2 files (data CSV and metadata CSV)"
        
        # Verify main data file
        data_file = output_dir / '18100004.csv'
        assert data_file.exists(), "Main data CSV should be extracted"
        
        # Verify metadata file
        metadata_file = output_dir / '18100004_MetaData.csv'
        assert metadata_file.exists(), "Metadata CSV should be extracted"
        
        # Verify data file content
        with open(data_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'REF_DATE' in content, "Should have REF_DATE column"
            assert 'GEO' in content, "Should have GEO column"
            assert 'Consumer Price Index' in content, "Should have data values"
            assert 'Canada' in content, "Should have geographic data"
            assert '2020' in content, "Should have year data"
        
        # Verify metadata file content
        with open(metadata_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Cube Title' in content, "Should have metadata headers"
            assert 'Product Id' in content, "Should have Product Id field"
            assert '18100004' in content, "Should reference the table ID"


def test_parse_manifest_with_fixture():
    """Test manifest parsing using extracted fixture data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Extract the fixture ZIP
        _extract_zip(SAMPLE_ZIP_FILE, output_dir, '18100004')
        
        # Parse the manifest
        manifest = _parse_manifest(output_dir, '18100004')
        
        # Should find the metadata CSV
        assert manifest is not None, "Should find manifest data"
        assert 'metadata_file' in manifest, "Should have metadata_file key"
        assert '18100004_MetaData.csv' in manifest['metadata_file'], \
            "Should reference the metadata CSV file"


def test_download_statcan_table_with_fixture():
    """Test full download workflow using a ZIP fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Mock the download_file function to use our fixture
        def mock_download(url, path, max_retries, write_metadata=True):
            # Copy the fixture to the download path
            shutil.copy(SAMPLE_ZIP_FILE, path)
            return path
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table(
                '18100004',
                str(output_dir),
                skip_existing=False
            )
        
        # Verify result structure
        assert result['provider'] == 'statcan'
        assert result['pid'] == '18100004'
        assert result['dataset_id'] == 'statcan_18100004'
        assert result['skipped'] is False
        
        # Verify files were extracted
        assert len(result['files']) == 2, "Should have 2 extracted files"
        
        # Verify main data file exists
        data_file = output_dir / '18100004.csv'
        assert data_file.exists(), "Main data file should exist"
        
        # Verify metadata file exists
        metadata_file = output_dir / '18100004_MetaData.csv'
        assert metadata_file.exists(), "Metadata file should exist"
        
        # Verify ZIP was cleaned up
        zip_file = output_dir / '18100004_temp.zip'
        assert not zip_file.exists(), "Temporary ZIP should be cleaned up"
        
        # Verify manifest was parsed
        assert 'manifest' in result, "Should include manifest data"
        assert result['manifest'] is not None


def test_download_statcan_table_data_integrity():
    """Test that downloaded data maintains integrity through the process."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        def mock_download(url, path, max_retries, write_metadata=True):
            shutil.copy(SAMPLE_ZIP_FILE, path)
            return path
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table(
                '18100004',
                str(output_dir),
                skip_existing=False
            )
        
        # Read and verify the extracted data
        data_file = output_dir / '18100004.csv'
        with open(data_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Verify header row
        header = lines[0].strip()
        assert 'REF_DATE' in header
        assert 'GEO' in header
        assert 'Indicators' in header
        assert 'VALUE' in header
        
        # Verify we have data rows (header + at least one data row)
        assert len(lines) > 1, "Should have data rows in addition to header"
        
        # Verify some data values
        data_content = ''.join(lines)
        assert '2020' in data_content, "Should have 2020 data"
        assert '2021' in data_content, "Should have 2021 data"
        assert 'Canada' in data_content, "Should have Canada data"
        assert 'Ontario' in data_content, "Should have Ontario data"


def test_download_statcan_table_metadata_content():
    """Test that metadata file is correctly extracted and contains expected information."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        def mock_download(url, path, max_retries, write_metadata=True):
            shutil.copy(SAMPLE_ZIP_FILE, path)
            return path
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            download_statcan_table(
                '18100004',
                str(output_dir),
                skip_existing=False
            )
        
        # Read and verify the metadata
        metadata_file = output_dir / '18100004_MetaData.csv'
        with open(metadata_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify key metadata fields
        assert 'Cube Title' in content
        assert 'Product Id' in content
        assert 'Consumer price index' in content, \
            "Should have the table title"
        assert '18100004' in content, \
            "Should reference the table PID"


def test_download_statcan_table_with_hyphenated_id():
    """Test that hyphenated table IDs work with the fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        def mock_download(url, path, max_retries, write_metadata=True):
            shutil.copy(SAMPLE_ZIP_FILE, path)
            # Verify the URL uses normalized PID
            assert '18100004' in url, "URL should use normalized PID"
            return path
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result = download_statcan_table(
                '18-10-0004',  # Hyphenated format
                str(output_dir),
                skip_existing=False
            )
        
        # Should normalize to 18100004
        assert result['pid'] == '18100004'
        
        # Files should use normalized name
        data_file = output_dir / '18100004.csv'
        assert data_file.exists()


def test_download_statcan_table_skip_existing_with_fixture():
    """Test skip-if-exists functionality with fixture data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # First download
        def mock_download(url, path, max_retries, write_metadata=True):
            shutil.copy(SAMPLE_ZIP_FILE, path)
            return path
        
        with patch('publicdata_ca.providers.statcan.download_file', side_effect=mock_download):
            result1 = download_statcan_table(
                '18100004',
                str(output_dir),
                skip_existing=False
            )
        
        assert result1['skipped'] is False
        
        # Modify the data file to detect if it gets overwritten
        data_file = output_dir / '18100004.csv'
        original_size = data_file.stat().st_size
        
        # Second download with skip_existing=True
        result2 = download_statcan_table(
            '18100004',
            str(output_dir),
            skip_existing=True
        )
        
        # Should skip download
        assert result2['skipped'] is True
        assert result2['pid'] == '18100004'
        
        # File should be unchanged
        assert data_file.stat().st_size == original_size


def test_extract_zip_handles_fixture_structure():
    """Test that extraction correctly handles the fixture ZIP structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Extract and verify structure
        extracted_files = _extract_zip(SAMPLE_ZIP_FILE, output_dir, '18100004')
        
        # Should return paths to extracted files
        assert all(os.path.exists(f) for f in extracted_files), \
            "All extracted files should exist"
        
        # Should have exactly the expected files
        file_names = [Path(f).name for f in extracted_files]
        assert '18100004.csv' in file_names
        assert '18100004_MetaData.csv' in file_names
