"""
Tests for unified metadata schema and run report export.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
import pandas as pd

from publicdata_ca.provenance import (
    write_provenance_metadata,
    read_provenance_metadata,
    METADATA_SCHEMA_VERSION
)
from publicdata_ca.datasets import export_run_report


def test_unified_metadata_schema_basic():
    """Test that unified schema includes all required fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Write metadata with unified schema
        meta_file = write_provenance_metadata(
            test_file,
            'https://example.com/data.csv',
            content_type='text/csv',
            provider_name='test_provider'
        )
        
        # Read and verify schema
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
        
        # Check schema version
        assert metadata['schema_version'] == METADATA_SCHEMA_VERSION
        
        # Check required fields
        assert 'file' in metadata
        assert 'source_url' in metadata
        assert 'downloaded_at' in metadata
        assert 'file_size_bytes' in metadata
        assert 'hash' in metadata
        assert 'content_type' in metadata
        
        # Check provider section
        assert 'provider' in metadata
        assert metadata['provider']['name'] == 'test_provider'


def test_unified_metadata_schema_with_provider_specific():
    """Test unified schema with provider-specific metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'table.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Write metadata with provider-specific fields
        provider_specific = {
            'pid': '18100004',
            'table_number': '18-10-0004',
            'title': 'Consumer Price Index'
        }
        
        meta_file = write_provenance_metadata(
            test_file,
            'https://statcan.gc.ca/table.zip',
            content_type='application/zip',
            provider_name='statcan',
            provider_specific=provider_specific
        )
        
        # Read and verify
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['schema_version'] == METADATA_SCHEMA_VERSION
        assert metadata['provider']['name'] == 'statcan'
        assert metadata['provider']['specific']['pid'] == '18100004'
        assert metadata['provider']['specific']['table_number'] == '18-10-0004'
        assert metadata['provider']['specific']['title'] == 'Consumer Price Index'


def test_unified_metadata_backward_compatibility():
    """Test backward compatibility with additional_metadata parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'data.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Write metadata using old additional_metadata parameter
        additional = {
            'provider': 'old_provider',
            'custom_field': 'custom_value',
            'another_field': 123
        }
        
        meta_file = write_provenance_metadata(
            test_file,
            'https://example.com/data.csv',
            additional_metadata=additional
        )
        
        # Read and verify - fields should be migrated to provider.specific
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['schema_version'] == METADATA_SCHEMA_VERSION
        assert metadata['provider']['name'] == 'old_provider'
        assert metadata['provider']['specific']['custom_field'] == 'custom_value'
        assert metadata['provider']['specific']['another_field'] == 123


def test_export_run_report_csv():
    """Test exporting run report as CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample report DataFrame
        report_data = [
            {
                'dataset': 'cpi_data',
                'provider': 'statcan',
                'target_file': '/data/cpi.csv',
                'result': 'downloaded',
                'notes': 'Successfully downloaded',
                'run_started_utc': '2024-01-01T00:00:00Z'
            },
            {
                'dataset': 'housing_starts',
                'provider': 'cmhc',
                'target_file': '/data/housing.xlsx',
                'result': 'error',
                'notes': 'Download failed: Connection timeout',
                'run_started_utc': '2024-01-01T00:00:00Z'
            }
        ]
        report = pd.DataFrame(report_data)
        
        # Export as CSV
        output_path = export_run_report(report, tmpdir, format='csv')
        
        # Verify file was created
        assert os.path.exists(output_path)
        assert output_path.endswith('.csv')
        
        # Read and verify content
        exported_df = pd.read_csv(output_path)
        assert len(exported_df) == 2
        assert 'dataset' in exported_df.columns
        assert 'result' in exported_df.columns
        assert exported_df.iloc[0]['dataset'] == 'cpi_data'
        assert exported_df.iloc[1]['result'] == 'error'


def test_export_run_report_json():
    """Test exporting run report as JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample report DataFrame
        report_data = [
            {
                'dataset': 'unemployment_rate',
                'provider': 'statcan',
                'target_file': '/data/unemployment.csv',
                'result': 'exists',
                'notes': 'File already present',
                'run_started_utc': '2024-01-01T00:00:00Z'
            }
        ]
        report = pd.DataFrame(report_data)
        
        # Export as JSON
        output_path = export_run_report(report, tmpdir, format='json')
        
        # Verify file was created
        assert os.path.exists(output_path)
        assert output_path.endswith('.json')
        
        # Read and verify content
        with open(output_path, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 1
        assert exported_data[0]['dataset'] == 'unemployment_rate'
        assert exported_data[0]['result'] == 'exists'


def test_export_run_report_specific_filename():
    """Test exporting run report with specific filename."""
    with tempfile.TemporaryDirectory() as tmpdir:
        report_data = [
            {
                'dataset': 'test_dataset',
                'provider': 'test_provider',
                'target_file': '/data/test.csv',
                'result': 'downloaded',
                'notes': 'Test note',
                'run_started_utc': '2024-01-01T00:00:00Z'
            }
        ]
        report = pd.DataFrame(report_data)
        
        # Export with specific filename
        specific_path = os.path.join(tmpdir, 'my_report.csv')
        output_path = export_run_report(report, specific_path, format='csv')
        
        # Verify correct path was used
        assert output_path == specific_path
        assert os.path.exists(specific_path)


def test_export_run_report_timestamped_filename():
    """Test that directory path generates timestamped filename."""
    with tempfile.TemporaryDirectory() as tmpdir:
        report_data = [
            {
                'dataset': 'test_dataset',
                'provider': 'test_provider',
                'target_file': '/data/test.csv',
                'result': 'downloaded',
                'notes': 'Test note',
                'run_started_utc': '2024-01-01T00:00:00Z'
            }
        ]
        report = pd.DataFrame(report_data)
        
        # Export to directory
        output_path = export_run_report(report, tmpdir, format='csv')
        
        # Verify timestamped filename was generated
        assert os.path.exists(output_path)
        assert 'run_report_' in os.path.basename(output_path)
        assert output_path.endswith('.csv')


def test_metadata_schema_statcan_format():
    """Test that StatsCan provider metadata follows unified schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, '18100004.csv')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Simulate StatsCan metadata
        provider_specific = {
            'pid': '18100004',
            'table_number': '18-10-0004',
            'title': 'Consumer Price Index'
        }
        
        write_provenance_metadata(
            test_file,
            'https://statcan.gc.ca/api/table.zip',
            content_type='application/zip',
            provider_name='statcan',
            provider_specific=provider_specific
        )
        
        # Read and verify
        metadata = read_provenance_metadata(test_file)
        
        assert metadata['schema_version'] == METADATA_SCHEMA_VERSION
        assert metadata['provider']['name'] == 'statcan'
        assert 'specific' in metadata['provider']
        assert metadata['provider']['specific']['pid'] == '18100004'


def test_metadata_schema_cmhc_format():
    """Test that CMHC provider metadata follows unified schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'housing_data.xlsx')
        
        with open(test_file, 'wb') as f:
            f.write(b'test data')
        
        # Simulate CMHC metadata
        provider_specific = {
            'landing_page_url': 'https://cmhc.gc.ca/housing-starts',
            'asset_title': 'Housing Starts Data',
            'asset_format': 'xlsx',
            'asset_rank': 1
        }
        
        write_provenance_metadata(
            test_file,
            'https://cmhc.gc.ca/data/housing.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            provider_name='cmhc',
            provider_specific=provider_specific
        )
        
        # Read and verify
        metadata = read_provenance_metadata(test_file)
        
        assert metadata['schema_version'] == METADATA_SCHEMA_VERSION
        assert metadata['provider']['name'] == 'cmhc'
        assert metadata['provider']['specific']['landing_page_url'] == 'https://cmhc.gc.ca/housing-starts'
        assert metadata['provider']['specific']['asset_title'] == 'Housing Starts Data'
