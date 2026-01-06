"""Tests for the Socrata provider."""

import json
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from publicdata_ca.provider import Provider, DatasetRef
from publicdata_ca.providers.socrata import (
    search_socrata_datasets,
    get_socrata_metadata,
    download_socrata_dataset,
    SocrataProvider,
)


# Sample Socrata API responses for testing
SAMPLE_CATALOG_RESPONSE = {
    "results": [
        {
            "resource": {
                "id": "abcd-1234",
                "name": "Seattle Police 911 Calls",
                "description": "All police 911 calls in Seattle",
                "type": "dataset",
                "updatedAt": "2023-12-01T00:00:00.000Z",
                "createdAt": "2020-01-01T00:00:00.000Z",
            },
            "classification": {
                "categories": ["Public Safety"],
                "domain_tags": ["police", "911", "emergency"],
            }
        },
        {
            "resource": {
                "id": "wxyz-5678",
                "name": "Building Permits",
                "description": "All building permits issued",
                "type": "dataset",
                "updatedAt": "2023-11-15T00:00:00.000Z",
                "createdAt": "2019-06-01T00:00:00.000Z",
            },
            "classification": {
                "categories": ["Community Development"],
                "domain_tags": ["permits", "building", "construction"],
            }
        }
    ]
}

SAMPLE_METADATA_RESPONSE = {
    "id": "abcd-1234",
    "name": "Seattle Police 911 Calls",
    "description": "All police 911 calls in Seattle",
    "viewType": "tabular",
    "createdAt": 1577836800,
    "rowsUpdatedAt": 1701388800,
    "columns": [
        {
            "id": 12345,
            "name": "call_date",
            "dataTypeName": "calendar_date",
            "fieldName": "call_date",
            "description": "Date of the call"
        },
        {
            "id": 12346,
            "name": "offense_type",
            "dataTypeName": "text",
            "fieldName": "offense_type",
            "description": "Type of offense"
        },
        {
            "id": 12347,
            "name": "count",
            "dataTypeName": "number",
            "fieldName": "count",
            "description": "Number of incidents"
        }
    ]
}


class TestSearchSocrataDatasets:
    """Test the search_socrata_datasets function."""
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_search_datasets_basic(self, mock_retry):
        """Test basic dataset search."""
        # Mock the response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_CATALOG_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Search datasets
        results = search_socrata_datasets(
            'https://data.seattle.gov',
            'police'
        )
        
        # Verify results
        assert results['count'] == 2
        assert len(results['results']) == 2
        assert results['results'][0]['resource']['id'] == 'abcd-1234'
        assert results['results'][1]['resource']['id'] == 'wxyz-5678'
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_search_datasets_with_pagination(self, mock_retry):
        """Test dataset search with pagination."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_CATALOG_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        results = search_socrata_datasets(
            'https://data.seattle.gov',
            'permits',
            limit=5,
            offset=10
        )
        
        assert results['count'] == 2
        # Verify the function was called (URL building works)
        mock_retry.assert_called_once()
        call_url = mock_retry.call_args[0][0]
        assert 'limit=5' in call_url
        assert 'offset=10' in call_url
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_search_datasets_empty_query(self, mock_retry):
        """Test search with empty query returns all datasets."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_CATALOG_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        results = search_socrata_datasets(
            'https://data.seattle.gov',
            ''
        )
        
        assert results['count'] == 2
        # Verify query parameter is not in URL when empty
        call_url = mock_retry.call_args[0][0]
        # Empty query should not include 'q=' parameter
        assert 'q=' not in call_url or 'q=&' in call_url
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_search_datasets_network_error(self, mock_retry):
        """Test network error handling."""
        mock_retry.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to search Socrata portal"):
            search_socrata_datasets(
                'https://data.seattle.gov',
                'test'
            )


class TestGetSocrataMetadata:
    """Test the get_socrata_metadata function."""
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_get_metadata_success(self, mock_retry):
        """Test getting metadata successfully."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_METADATA_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        metadata = get_socrata_metadata(
            'https://data.seattle.gov',
            'abcd-1234'
        )
        
        assert metadata['id'] == 'abcd-1234'
        assert metadata['name'] == 'Seattle Police 911 Calls'
        assert len(metadata['columns']) == 3
        assert metadata['viewType'] == 'tabular'
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_get_metadata_invalid_json(self, mock_retry):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.read.return_value = b"Not valid JSON"
        mock_retry.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Failed to parse Socrata metadata response"):
            get_socrata_metadata(
                'https://data.seattle.gov',
                'abcd-1234'
            )
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_get_metadata_network_error(self, mock_retry):
        """Test network error handling."""
        mock_retry.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to get Socrata dataset"):
            get_socrata_metadata(
                'https://data.seattle.gov',
                'abcd-1234'
            )


class TestDownloadSocrataDataset:
    """Test the download_socrata_dataset function."""
    
    @patch('publicdata_ca.providers.socrata.download_file')
    def test_download_dataset_basic(self, mock_download, tmp_path):
        """Test basic dataset download."""
        output_path = str(tmp_path / 'data.csv')
        mock_download.return_value = output_path
        
        result = download_socrata_dataset(
            'https://data.seattle.gov',
            'abcd-1234',
            output_path,
            format='csv'
        )
        
        assert result['file'] == output_path
        assert result['format'] == 'csv'
        assert result['dataset_id'] == 'abcd-1234'
        assert 'resource/abcd-1234.csv' in result['url']
        mock_download.assert_called_once()
    
    @patch('publicdata_ca.providers.socrata.download_file')
    def test_download_dataset_with_select(self, mock_download, tmp_path):
        """Test download with column selection."""
        output_path = str(tmp_path / 'data.csv')
        mock_download.return_value = output_path
        
        result = download_socrata_dataset(
            'https://data.seattle.gov',
            'abcd-1234',
            output_path,
            format='csv',
            select='call_date, offense_type, count'
        )
        
        # Verify URL contains select parameter
        call_url = mock_download.call_args[0][0]
        assert '$select=call_date' in call_url or '%24select=' in call_url
    
    @patch('publicdata_ca.providers.socrata.download_file')
    def test_download_dataset_with_where(self, mock_download, tmp_path):
        """Test download with where filter."""
        output_path = str(tmp_path / 'data.csv')
        mock_download.return_value = output_path
        
        result = download_socrata_dataset(
            'https://data.seattle.gov',
            'abcd-1234',
            output_path,
            format='csv',
            where='count > 10'
        )
        
        # Verify URL contains where parameter
        call_url = mock_download.call_args[0][0]
        assert '$where=' in call_url or '%24where=' in call_url
    
    @patch('publicdata_ca.providers.socrata.download_file')
    def test_download_dataset_with_paging(self, mock_download, tmp_path):
        """Test download with limit and offset."""
        output_path = str(tmp_path / 'data.csv')
        mock_download.return_value = output_path
        
        result = download_socrata_dataset(
            'https://data.seattle.gov',
            'abcd-1234',
            output_path,
            format='csv',
            limit=1000,
            offset=500
        )
        
        # Verify URL contains paging parameters
        call_url = mock_download.call_args[0][0]
        assert '$limit=1000' in call_url or '%24limit=1000' in call_url
        assert '$offset=500' in call_url or '%24offset=500' in call_url
    
    @patch('publicdata_ca.providers.socrata.download_file')
    def test_download_dataset_json_format(self, mock_download, tmp_path):
        """Test download in JSON format."""
        output_path = str(tmp_path / 'data.json')
        mock_download.return_value = output_path
        
        result = download_socrata_dataset(
            'https://data.seattle.gov',
            'abcd-1234',
            output_path,
            format='json'
        )
        
        assert result['format'] == 'json'
        assert 'resource/abcd-1234.json' in result['url']
    
    @patch('publicdata_ca.providers.socrata.download_file')
    def test_download_dataset_all_parameters(self, mock_download, tmp_path):
        """Test download with all parameters."""
        output_path = str(tmp_path / 'data.csv')
        mock_download.return_value = output_path
        
        result = download_socrata_dataset(
            'https://data.seattle.gov',
            'abcd-1234',
            output_path,
            format='csv',
            select='call_date, count',
            where='count > 5',
            limit=100,
            offset=50
        )
        
        # Verify URL contains all parameters
        call_url = mock_download.call_args[0][0]
        assert '$select=' in call_url or '%24select=' in call_url
        assert '$where=' in call_url or '%24where=' in call_url
        assert '$limit=100' in call_url or '%24limit=100' in call_url
        assert '$offset=50' in call_url or '%24offset=50' in call_url
    
    @patch('publicdata_ca.providers.socrata.download_file')
    def test_download_dataset_failure(self, mock_download, tmp_path):
        """Test download failure handling."""
        output_path = str(tmp_path / 'data.csv')
        mock_download.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to download Socrata dataset"):
            download_socrata_dataset(
                'https://data.seattle.gov',
                'abcd-1234',
                output_path
            )


class TestSocrataProvider:
    """Test the SocrataProvider class."""
    
    def test_socrata_provider_creation(self):
        """Test creating a Socrata provider."""
        provider = SocrataProvider(name='seattle', base_url='https://data.seattle.gov')
        
        assert provider.name == 'seattle'
        assert provider.base_url == 'https://data.seattle.gov'
        assert isinstance(provider, Provider)
    
    def test_socrata_provider_default_name(self):
        """Test Socrata provider with default name."""
        provider = SocrataProvider(base_url='https://data.example.com')
        assert provider.name == 'socrata'
    
    @patch('publicdata_ca.providers.socrata.search_socrata_datasets')
    def test_socrata_provider_search(self, mock_search):
        """Test Socrata provider search."""
        mock_search.return_value = SAMPLE_CATALOG_RESPONSE
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        results = provider.search('police', limit=5)
        
        assert len(results) == 2
        assert isinstance(results[0], DatasetRef)
        assert results[0].provider == 'socrata'
        assert results[0].id == 'abcd-1234'
        assert results[0].metadata['name'] == 'Seattle Police 911 Calls'
        assert 'police' in results[0].tags
        assert results[0].params['base_url'] == 'https://data.seattle.gov'
    
    @patch('publicdata_ca.providers.socrata.search_socrata_datasets')
    def test_socrata_provider_search_without_base_url(self, mock_search):
        """Test search without base_url raises error."""
        provider = SocrataProvider()
        
        with pytest.raises(ValueError, match="base_url must be provided"):
            provider.search('test')
    
    @patch('publicdata_ca.providers.socrata.search_socrata_datasets')
    def test_socrata_provider_search_with_kwargs_base_url(self, mock_search):
        """Test search with base_url in kwargs."""
        mock_search.return_value = SAMPLE_CATALOG_RESPONSE
        
        provider = SocrataProvider()
        results = provider.search('police', base_url='https://data.seattle.gov')
        
        assert len(results) == 2
        mock_search.assert_called_once()
    
    @patch('publicdata_ca.providers.socrata.get_socrata_metadata')
    def test_socrata_provider_resolve(self, mock_get_metadata):
        """Test Socrata provider resolve."""
        mock_get_metadata.return_value = SAMPLE_METADATA_RESPONSE
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        ref = DatasetRef(
            provider='socrata',
            id='abcd-1234'
        )
        
        metadata = provider.resolve(ref)
        
        assert metadata['dataset_id'] == 'abcd-1234'
        assert metadata['name'] == 'Seattle Police 911 Calls'
        assert metadata['provider'] == 'socrata'
        assert len(metadata['columns']) == 3
        assert metadata['download_params']['format'] == 'csv'
    
    @patch('publicdata_ca.providers.socrata.get_socrata_metadata')
    def test_socrata_provider_resolve_with_params(self, mock_get_metadata):
        """Test resolve with custom parameters."""
        mock_get_metadata.return_value = SAMPLE_METADATA_RESPONSE
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        ref = DatasetRef(
            provider='socrata',
            id='abcd-1234',
            params={
                'format': 'json',
                'select': 'call_date, count',
                'where': 'count > 10',
                'limit': 1000
            }
        )
        
        metadata = provider.resolve(ref)
        
        assert metadata['download_params']['format'] == 'json'
        assert metadata['download_params']['select'] == 'call_date, count'
        assert metadata['download_params']['where'] == 'count > 10'
        assert metadata['download_params']['limit'] == 1000
    
    @patch('publicdata_ca.providers.socrata.get_socrata_metadata')
    def test_socrata_provider_resolve_without_base_url(self, mock_get_metadata):
        """Test resolve without base_url raises error."""
        provider = SocrataProvider()
        ref = DatasetRef(provider='socrata', id='abcd-1234')
        
        with pytest.raises(ValueError, match="base_url must be provided"):
            provider.resolve(ref)
    
    @patch('publicdata_ca.providers.socrata.download_socrata_dataset')
    def test_socrata_provider_fetch(self, mock_download, tmp_path):
        """Test Socrata provider fetch."""
        mock_download.return_value = {
            'file': str(tmp_path / 'abcd-1234.csv'),
            'url': 'https://data.seattle.gov/resource/abcd-1234.csv',
            'format': 'csv',
            'dataset_id': 'abcd-1234'
        }
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        ref = DatasetRef(
            provider='socrata',
            id='abcd-1234',
            params={'format': 'csv'}
        )
        
        result = provider.fetch(ref, str(tmp_path))
        
        assert result['dataset_id'] == 'socrata_abcd-1234'
        assert result['provider'] == 'socrata'
        assert len(result['files']) == 1
        assert 'abcd-1234.csv' in result['files'][0]
        assert result['format'] == 'csv'
    
    @patch('publicdata_ca.providers.socrata.download_socrata_dataset')
    def test_socrata_provider_fetch_with_filters(self, mock_download, tmp_path):
        """Test fetch with filters and column selection."""
        mock_download.return_value = {
            'file': str(tmp_path / 'abcd-1234.csv'),
            'url': 'https://data.seattle.gov/resource/abcd-1234.csv?$select=...',
            'format': 'csv',
            'dataset_id': 'abcd-1234'
        }
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        ref = DatasetRef(
            provider='socrata',
            id='abcd-1234',
            params={
                'format': 'csv',
                'select': 'call_date, count',
                'where': 'count > 10',
                'limit': 500
            }
        )
        
        result = provider.fetch(ref, str(tmp_path))
        
        # Verify download was called with correct parameters
        mock_download.assert_called_once()
        call_args = mock_download.call_args[1]
        assert call_args['select'] == 'call_date, count'
        assert call_args['where'] == 'count > 10'
        assert call_args['limit'] == 500
    
    @patch('publicdata_ca.providers.socrata.download_socrata_dataset')
    def test_socrata_provider_fetch_json_format(self, mock_download, tmp_path):
        """Test fetch with JSON format."""
        mock_download.return_value = {
            'file': str(tmp_path / 'abcd-1234.json'),
            'url': 'https://data.seattle.gov/resource/abcd-1234.json',
            'format': 'json',
            'dataset_id': 'abcd-1234'
        }
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        ref = DatasetRef(
            provider='socrata',
            id='abcd-1234',
            params={'format': 'json'}
        )
        
        result = provider.fetch(ref, str(tmp_path))
        
        assert result['format'] == 'json'
        assert 'abcd-1234.json' in result['files'][0]
    
    @patch('publicdata_ca.providers.socrata.download_socrata_dataset')
    def test_socrata_provider_fetch_custom_filename(self, mock_download, tmp_path):
        """Test fetch with custom filename."""
        mock_download.return_value = {
            'file': str(tmp_path / 'custom_data.csv'),
            'url': 'https://data.seattle.gov/resource/abcd-1234.csv',
            'format': 'csv',
            'dataset_id': 'abcd-1234'
        }
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        ref = DatasetRef(
            provider='socrata',
            id='abcd-1234',
            params={'format': 'csv'}
        )
        
        result = provider.fetch(ref, str(tmp_path), filename='custom_data.csv')
        
        # Verify custom filename was used
        call_args = mock_download.call_args[1]
        assert 'custom_data.csv' in call_args['output_path']
    
    @patch('publicdata_ca.providers.socrata.download_socrata_dataset')
    def test_socrata_provider_fetch_without_base_url(self, mock_download, tmp_path):
        """Test fetch without base_url raises error."""
        provider = SocrataProvider()
        ref = DatasetRef(provider='socrata', id='abcd-1234')
        
        with pytest.raises(ValueError, match="base_url must be provided"):
            provider.fetch(ref, str(tmp_path))


class TestSocrataProviderIntegration:
    """Integration tests for Socrata provider."""
    
    def test_socrata_provider_with_base_url_in_params(self):
        """Test using base_url in DatasetRef params instead of provider init."""
        provider = SocrataProvider()
        
        ref = DatasetRef(
            provider='socrata',
            id='abcd-1234',
            params={'base_url': 'https://data.seattle.gov'}
        )
        
        # Should be able to use params base_url
        assert ref.params['base_url'] == 'https://data.seattle.gov'
    
    def test_socrata_provider_registry_compatible(self):
        """Test Socrata provider works with provider registry."""
        from publicdata_ca.provider import ProviderRegistry
        
        registry = ProviderRegistry()
        registry.register('seattle', SocrataProvider)
        
        # Should be able to get provider
        provider = registry.get_provider('seattle')
        assert isinstance(provider, SocrataProvider)
        assert isinstance(provider, Provider)
    
    @patch('publicdata_ca.providers.socrata.search_socrata_datasets')
    def test_socrata_provider_metadata_extraction(self, mock_search):
        """Test that metadata is properly extracted."""
        mock_search.return_value = SAMPLE_CATALOG_RESPONSE
        
        provider = SocrataProvider(base_url='https://data.seattle.gov')
        results = provider.search('police')
        
        # Check metadata extraction
        assert results[0].metadata['name'] == 'Seattle Police 911 Calls'
        assert results[0].metadata['type'] == 'dataset'
        assert 'Public Safety' in results[0].metadata['categories']
        assert 'police' in results[0].tags
