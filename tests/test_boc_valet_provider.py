"""Tests for the Bank of Canada Valet API provider."""

import json
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from publicdata_ca.provider import Provider, DatasetRef
from publicdata_ca.providers.boc_valet import (
    get_valet_series_metadata,
    fetch_valet_series,
    download_valet_series,
    ValetProvider,
)


# Sample Valet API responses for testing
SAMPLE_SERIES_METADATA_RESPONSE = {
    "seriesDetail": {
        "FXUSDCAD": {
            "label": "US dollar, closing daily average rate in Canadian dollars",
            "description": "Closing daily average exchange rate for US dollar in Canadian dollars",
            "dimension": {
                "key": "d",
                "name": "Date"
            },
            "type": "Daily"
        }
    }
}

SAMPLE_OBSERVATIONS_RESPONSE = {
    "seriesDetail": {
        "FXUSDCAD": {
            "label": "US dollar, closing daily average rate in Canadian dollars",
            "description": "Closing daily average exchange rate",
            "type": "Daily"
        }
    },
    "observations": [
        {"d": "2023-01-03", "FXUSDCAD": {"v": "1.3500"}},
        {"d": "2023-01-04", "FXUSDCAD": {"v": "1.3525"}},
        {"d": "2023-01-05", "FXUSDCAD": {"v": "1.3510"}},
    ]
}

# Simplified format for testing
SAMPLE_SIMPLE_OBSERVATIONS = [
    {"d": "2023-01-03", "v": "1.3500"},
    {"d": "2023-01-04", "v": "1.3525"},
    {"d": "2023-01-05", "v": "1.3510"},
]


class TestGetValetSeriesMetadata:
    """Test the get_valet_series_metadata function."""
    
    @patch('publicdata_ca.providers.boc_valet.retry_request')
    def test_get_metadata_success(self, mock_retry):
        """Test successful metadata retrieval."""
        # Mock the response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_SERIES_METADATA_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Get metadata
        metadata = get_valet_series_metadata('FXUSDCAD')
        
        # Verify results
        assert metadata['label'] == "US dollar, closing daily average rate in Canadian dollars"
        assert metadata['type'] == "Daily"
        assert 'dimension' in metadata
        
        # Verify URL was correct
        call_url = mock_retry.call_args[0][0]
        assert 'valet/series/FXUSDCAD/json' in call_url
    
    @patch('publicdata_ca.providers.boc_valet.retry_request')
    def test_get_metadata_no_detail(self, mock_retry):
        """Test metadata retrieval when seriesDetail is not available."""
        # Mock response without seriesDetail
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"observations": []}).encode('utf-8')
        mock_retry.return_value = mock_response
        
        metadata = get_valet_series_metadata('UNKNOWN')
        
        # Should return minimal metadata
        assert metadata['series_name'] == 'UNKNOWN'
        assert 'label' in metadata
    
    @patch('publicdata_ca.providers.boc_valet.retry_request')
    def test_get_metadata_network_error(self, mock_retry):
        """Test network error handling."""
        mock_retry.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to get metadata"):
            get_valet_series_metadata('FXUSDCAD')


class TestFetchValetSeries:
    """Test the fetch_valet_series function."""
    
    @patch('publicdata_ca.providers.boc_valet.retry_request')
    def test_fetch_series_basic(self, mock_retry):
        """Test basic series fetch."""
        # Mock the response
        mock_response = Mock()
        response_data = {
            "seriesDetail": SAMPLE_SERIES_METADATA_RESPONSE["seriesDetail"],
            "observations": SAMPLE_SIMPLE_OBSERVATIONS
        }
        mock_response.read.return_value = json.dumps(response_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Fetch series
        data = fetch_valet_series('FXUSDCAD')
        
        # Verify results
        assert data['series_name'] == 'FXUSDCAD'
        assert len(data['observations']) == 3
        assert data['observations'][0]['d'] == '2023-01-03'
        assert data['observations'][0]['v'] == '1.3500'
        assert 'metadata' in data
        assert 'url' in data
    
    @patch('publicdata_ca.providers.boc_valet.retry_request')
    def test_fetch_series_with_date_range(self, mock_retry):
        """Test series fetch with date range."""
        mock_response = Mock()
        response_data = {
            "seriesDetail": SAMPLE_SERIES_METADATA_RESPONSE["seriesDetail"],
            "observations": SAMPLE_SIMPLE_OBSERVATIONS
        }
        mock_response.read.return_value = json.dumps(response_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Fetch with date range
        data = fetch_valet_series(
            'FXUSDCAD',
            start_date='2023-01-01',
            end_date='2023-01-31'
        )
        
        # Verify URL includes date parameters
        assert data['start_date'] == '2023-01-01'
        assert data['end_date'] == '2023-01-31'
        assert 'start_date=2023-01-01' in data['url']
        assert 'end_date=2023-01-31' in data['url']
    
    @patch('publicdata_ca.providers.boc_valet.retry_request')
    def test_fetch_series_network_error(self, mock_retry):
        """Test network error handling."""
        mock_retry.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to fetch series"):
            fetch_valet_series('FXUSDCAD')


class TestDownloadValetSeries:
    """Test the download_valet_series function."""
    
    @patch('publicdata_ca.providers.boc_valet.fetch_valet_series')
    @patch('publicdata_ca.providers.boc_valet._write_valet_metadata')
    def test_download_series_basic(self, mock_write_meta, mock_fetch, tmp_path):
        """Test basic series download."""
        # Mock fetch_valet_series response
        mock_fetch.return_value = {
            'series_name': 'FXUSDCAD',
            'observations': SAMPLE_SIMPLE_OBSERVATIONS,
            'metadata': SAMPLE_SERIES_METADATA_RESPONSE['seriesDetail']['FXUSDCAD'],
            'url': 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json',
            'start_date': None,
            'end_date': None,
        }
        
        # Download series
        result = download_valet_series('FXUSDCAD', str(tmp_path))
        
        # Verify result
        assert result['dataset_id'] == 'boc_valet_FXUSDCAD'
        assert result['provider'] == 'boc_valet'
        assert result['series_name'] == 'FXUSDCAD'
        assert result['observations'] == 3
        assert result['skipped'] is False
        assert len(result['files']) == 1
        
        # Verify file was created
        output_file = tmp_path / 'FXUSDCAD.csv'
        assert output_file.exists()
        
        # Verify CSV content
        df = pd.read_csv(output_file)
        assert len(df) == 3
        assert 'date' in df.columns
        assert 'value' in df.columns
        assert 'series_name' in df.columns
        assert df['series_name'].iloc[0] == 'FXUSDCAD'
        
        # Verify metadata writing was called
        mock_write_meta.assert_called_once()
    
    @patch('publicdata_ca.providers.boc_valet.fetch_valet_series')
    def test_download_series_skip_existing(self, mock_fetch, tmp_path):
        """Test skip_existing functionality."""
        # Create an existing file
        output_file = tmp_path / 'FXUSDCAD.csv'
        output_file.write_text('date,value\n2023-01-01,1.35\n')
        
        # Try to download with skip_existing=True (default)
        result = download_valet_series('FXUSDCAD', str(tmp_path), skip_existing=True)
        
        # Should skip download
        assert result['skipped'] is True
        assert result['series_name'] == 'FXUSDCAD'
        
        # fetch_valet_series should not have been called
        mock_fetch.assert_not_called()
    
    @patch('publicdata_ca.providers.boc_valet.fetch_valet_series')
    @patch('publicdata_ca.providers.boc_valet._write_valet_metadata')
    def test_download_series_with_date_range(self, mock_write_meta, mock_fetch, tmp_path):
        """Test download with date range."""
        mock_fetch.return_value = {
            'series_name': 'FXUSDCAD',
            'observations': SAMPLE_SIMPLE_OBSERVATIONS,
            'metadata': SAMPLE_SERIES_METADATA_RESPONSE['seriesDetail']['FXUSDCAD'],
            'url': 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?start_date=2023-01-01',
            'start_date': '2023-01-01',
            'end_date': '2023-01-31',
        }
        
        result = download_valet_series(
            'FXUSDCAD',
            str(tmp_path),
            start_date='2023-01-01',
            end_date='2023-01-31'
        )
        
        # Verify fetch was called with date range
        mock_fetch.assert_called_once_with('FXUSDCAD', '2023-01-01', '2023-01-31')
        
        # Verify metadata includes date range
        meta_call_args = mock_write_meta.call_args[0]
        assert meta_call_args[4] == '2023-01-01'  # start_date
        assert meta_call_args[5] == '2023-01-31'  # end_date
    
    @patch('publicdata_ca.providers.boc_valet.fetch_valet_series')
    def test_download_series_no_observations(self, mock_fetch, tmp_path):
        """Test error handling when no observations are returned."""
        mock_fetch.return_value = {
            'series_name': 'FXUSDCAD',
            'observations': [],
            'metadata': {},
            'url': 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json',
            'start_date': None,
            'end_date': None,
        }
        
        with pytest.raises(RuntimeError, match="No observations returned"):
            download_valet_series('FXUSDCAD', str(tmp_path))


class TestValetProvider:
    """Test the ValetProvider class."""
    
    def test_provider_initialization(self):
        """Test provider initialization."""
        provider = ValetProvider()
        assert provider.name == 'boc_valet'
        
        # Test custom name
        provider2 = ValetProvider(name='custom_valet')
        assert provider2.name == 'custom_valet'
    
    def test_search_placeholder(self):
        """Test search method (placeholder implementation)."""
        provider = ValetProvider()
        results = provider.search('exchange rate')
        
        # Should return empty list (placeholder)
        assert results == []
    
    def test_resolve_basic(self):
        """Test basic resolve functionality."""
        provider = ValetProvider()
        ref = DatasetRef(provider='boc_valet', id='FXUSDCAD')
        
        metadata = provider.resolve(ref)
        
        assert metadata['series_name'] == 'FXUSDCAD'
        assert metadata['format'] == 'json'
        assert metadata['provider'] == 'boc_valet'
        assert 'url' in metadata
        assert 'valet/observations/FXUSDCAD' in metadata['url']
    
    def test_resolve_with_date_range(self):
        """Test resolve with date range parameters."""
        provider = ValetProvider()
        ref = DatasetRef(
            provider='boc_valet',
            id='FXUSDCAD',
            params={
                'start_date': '2023-01-01',
                'end_date': '2023-12-31'
            }
        )
        
        metadata = provider.resolve(ref)
        
        assert metadata['start_date'] == '2023-01-01'
        assert metadata['end_date'] == '2023-12-31'
        assert 'start_date=2023-01-01' in metadata['url']
        assert 'end_date=2023-12-31' in metadata['url']
    
    @patch('publicdata_ca.providers.boc_valet.download_valet_series')
    def test_fetch_basic(self, mock_download, tmp_path):
        """Test basic fetch functionality."""
        # Mock download_valet_series
        mock_download.return_value = {
            'dataset_id': 'boc_valet_FXUSDCAD',
            'provider': 'boc_valet',
            'files': [str(tmp_path / 'FXUSDCAD.csv')],
            'url': 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json',
            'series_name': 'FXUSDCAD',
            'metadata': {},
            'observations': 100,
            'skipped': False
        }
        
        provider = ValetProvider()
        ref = DatasetRef(provider='boc_valet', id='FXUSDCAD')
        
        result = provider.fetch(ref, str(tmp_path))
        
        # Verify result
        assert result['provider'] == 'boc_valet'
        assert result['series_name'] == 'FXUSDCAD'
        assert result['observations'] == 100
        
        # Verify download_valet_series was called correctly
        mock_download.assert_called_once_with(
            series_name='FXUSDCAD',
            output_dir=str(tmp_path),
            start_date=None,
            end_date=None,
            skip_existing=True,
            max_retries=3
        )
    
    @patch('publicdata_ca.providers.boc_valet.download_valet_series')
    def test_fetch_with_params(self, mock_download, tmp_path):
        """Test fetch with parameters."""
        mock_download.return_value = {
            'dataset_id': 'boc_valet_FXUSDCAD',
            'provider': 'boc_valet',
            'files': [str(tmp_path / 'FXUSDCAD.csv')],
            'url': 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json',
            'series_name': 'FXUSDCAD',
            'metadata': {},
            'observations': 50,
            'skipped': False
        }
        
        provider = ValetProvider()
        ref = DatasetRef(
            provider='boc_valet',
            id='FXUSDCAD',
            params={
                'start_date': '2023-01-01',
                'end_date': '2023-06-30'
            }
        )
        
        result = provider.fetch(
            ref,
            str(tmp_path),
            skip_existing=False,
            max_retries=5
        )
        
        # Verify download_valet_series was called with correct params
        mock_download.assert_called_once_with(
            series_name='FXUSDCAD',
            output_dir=str(tmp_path),
            start_date='2023-01-01',
            end_date='2023-06-30',
            skip_existing=False,
            max_retries=5
        )
    
    def test_provider_inherits_from_provider_base(self):
        """Test that ValetProvider inherits from Provider base class."""
        provider = ValetProvider()
        assert isinstance(provider, Provider)
