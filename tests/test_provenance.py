"""
Tests for provenance metadata module.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from publicdata_ca.provenance import (
    calculate_file_hash,
    write_provenance_metadata,
    read_provenance_metadata,
    verify_file_integrity
)


def test_calculate_file_hash():
    """Test hash calculation for a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.txt')
        test_content = b'Hello, World!'
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Calculate hash
        hash_value = calculate_file_hash(test_file, algorithm='sha256')
        
        # Verify it's a valid hex string
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 produces 64 hex chars
        assert all(c in '0123456789abcdef' for c in hash_value)


def test_calculate_file_hash_md5():
    """Test hash calculation with MD5 algorithm."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.txt')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        hash_value = calculate_file_hash(test_file, algorithm='md5')
        
        # MD5 produces 32 hex chars
        assert len(hash_value) == 32


def test_write_provenance_metadata_basic():
    """Test writing basic provenance metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = os.path.join(tmpdir, 'data.csv')
        test_content = b'column1,column2\nvalue1,value2\n'
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Write metadata
        source_url = 'https://example.com/data.csv'
        meta_file = write_provenance_metadata(
            test_file,
            source_url,
            content_type='text/csv'
        )
        
        # Verify metadata file was created
        assert os.path.exists(meta_file)
        assert meta_file == test_file + '.meta.json'
        
        # Read and verify metadata content
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['file'] == 'data.csv'
        assert metadata['source_url'] == source_url
        assert metadata['content_type'] == 'text/csv'
        assert 'downloaded_at' in metadata
        assert 'file_size_bytes' in metadata
        assert metadata['file_size_bytes'] == len(test_content)
        assert 'hash' in metadata
        assert metadata['hash']['algorithm'] == 'sha256'
        assert 'value' in metadata['hash']


def test_write_provenance_metadata_with_additional_metadata():
    """Test writing metadata with additional fields using backward compatibility."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'table.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Write metadata with additional fields (backward compatibility test)
        additional = {
            'provider': 'statcan',
            'pid': '18100004',
            'table_number': '18-10-0004'
        }
        
        meta_file = write_provenance_metadata(
            test_file,
            'https://statcan.gc.ca/table.zip',
            additional_metadata=additional
        )
        
        # Read and verify - fields should be migrated to unified schema
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
        
        # Verify unified schema structure
        assert metadata['schema_version'] == '1.0'
        assert metadata['provider']['name'] == 'statcan'
        assert metadata['provider']['specific']['pid'] == '18100004'
        assert metadata['provider']['specific']['table_number'] == '18-10-0004'


def test_write_provenance_metadata_file_not_found():
    """Test that writing metadata for non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        write_provenance_metadata(
            '/nonexistent/file.csv',
            'https://example.com/data.csv'
        )


def test_read_provenance_metadata():
    """Test reading provenance metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Write metadata
        source_url = 'https://example.com/data.csv'
        write_provenance_metadata(test_file, source_url)
        
        # Read metadata
        metadata = read_provenance_metadata(test_file)
        
        assert metadata['source_url'] == source_url
        assert metadata['file'] == 'data.csv'


def test_read_provenance_metadata_direct():
    """Test reading metadata by specifying .meta.json file directly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        write_provenance_metadata(test_file, 'https://example.com/data.csv')
        
        # Read by specifying .meta.json file
        meta_file = test_file + '.meta.json'
        metadata = read_provenance_metadata(meta_file)
        
        assert metadata['file'] == 'data.csv'


def test_read_provenance_metadata_not_found():
    """Test that reading missing metadata raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Try to read metadata that doesn't exist
        with pytest.raises(FileNotFoundError):
            read_provenance_metadata(test_file)


def test_verify_file_integrity_success():
    """Test successful file integrity verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Write metadata
        write_provenance_metadata(test_file, 'https://example.com/data.csv')
        
        # Verify integrity
        assert verify_file_integrity(test_file) is True


def test_verify_file_integrity_failure():
    """Test file integrity verification fails when file is modified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'original data')
        
        # Write metadata
        write_provenance_metadata(test_file, 'https://example.com/data.csv')
        
        # Modify the file
        with open(test_file, 'wb') as f:
            f.write(b'modified data')
        
        # Verify integrity should fail
        assert verify_file_integrity(test_file) is False


def test_verify_file_integrity_no_hash():
    """Test integrity verification raises error when hash is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        meta_file = test_file + '.meta.json'
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Write metadata without hash
        metadata = {
            'file': 'data.csv',
            'source_url': 'https://example.com/data.csv'
        }
        
        with open(meta_file, 'w') as f:
            json.dump(metadata, f)
        
        # Verify should raise error
        with pytest.raises(ValueError):
            verify_file_integrity(test_file)


def test_hash_consistency():
    """Test that same content produces same hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, 'file1.txt')
        file2 = os.path.join(tmpdir, 'file2.txt')
        
        test_content = b'identical content'
        
        with open(file1, 'wb') as f:
            f.write(test_content)
        
        with open(file2, 'wb') as f:
            f.write(test_content)
        
        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)
        
        assert hash1 == hash2


def test_large_file_hash():
    """Test hash calculation for larger files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'large.dat')
        
        # Create a file larger than chunk size (8192 bytes)
        test_content = b'x' * 100000
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Calculate hash
        hash_value = calculate_file_hash(test_file)
        
        # Verify it's a valid hash
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64


def test_metadata_timestamp_format():
    """Test that timestamp is in ISO format with Z suffix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test')
        
        write_provenance_metadata(test_file, 'https://example.com/data.csv')
        
        metadata = read_provenance_metadata(test_file)
        timestamp = metadata['downloaded_at']
        
        # Should be ISO format ending with Z
        assert timestamp.endswith('Z')
        assert 'T' in timestamp  # ISO format has T separator
