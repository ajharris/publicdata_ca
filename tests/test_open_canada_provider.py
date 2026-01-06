"""Tests for the Open Canada provider."""

import json
from unittest.mock import Mock, patch
from publicdata_ca.provider import Provider, DatasetRef
from publicdata_ca.providers.open_canada import (
    OpenCanadaProvider,
    OPEN_CANADA_BASE_URL,
)


# Sample CKAN API responses for testing
SAMPLE_SEARCH_RESPONSE_RAW = {
    "success": True,
    "result": {
        "count": 2,
        "results": [
            {
                "id": "dataset-1",
                "name": "census-2021",
                "title": "Census 2021 Population Data",
                "notes": "Population statistics from 2021 census",
                "organization": {"title": "Statistics Canada"},
                "tags": [{"name": "census"}, {"name": "population"}],
                "resources": [
                    {"format": "CSV", "url": "https://open.canada.ca/data.csv"},
                    {"format": "JSON", "url": "https://open.canada.ca/data.json"}
                ]
            },
            {
                "id": "dataset-2",
                "name": "housing-starts",
                "title": "Housing Starts Monthly",
                "notes": "Monthly housing construction data",
                "organization": {"title": "CMHC"},
                "tags": [{"name": "housing"}],
                "resources": [
                    {"format": "CSV", "url": "https://open.canada.ca/housing.csv"}
                ]
            }
        ]
    }
}

SAMPLE_PACKAGE_RESPONSE = {
    "success": True,
    "result": {
        "id": "dataset-1",
        "name": "census-2021",
        "title": "Census 2021 Population Data",
        "notes": "Population statistics from 2021 census",
        "organization": {"title": "Statistics Canada"},
        "tags": [{"name": "census"}, {"name": "population"}],
        "resources": [
            {
                "id": "resource-1",
                "name": "Census Data CSV",
                "url": "https://open.canada.ca/census.csv",
                "format": "CSV",
                "description": "Census data in CSV format",
            },
            {
                "id": "resource-2",
                "name": "Census Data JSON",
                "url": "https://open.canada.ca/census.json",
                "format": "JSON",
                "description": "Census data in JSON format",
            }
        ]
    }
}


class TestOpenCanadaProvider:
    """Test the OpenCanadaProvider class."""
    
    def test_open_canada_provider_creation(self):
        """Test creating an Open Canada provider."""
        provider = OpenCanadaProvider()
        
        assert provider.name == 'open_canada'
        assert provider.base_url == OPEN_CANADA_BASE_URL
        assert provider.base_url == 'https://open.canada.ca/data'
        assert isinstance(provider, Provider)
    
    def test_open_canada_provider_custom_name(self):
        """Test Open Canada provider with custom name."""
        provider = OpenCanadaProvider(name='oc_custom')
        assert provider.name == 'oc_custom'
        assert provider.base_url == OPEN_CANADA_BASE_URL
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_provider_search(self, mock_retry):
        """Test Open Canada provider search."""
        # Mock the response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_SEARCH_RESPONSE_RAW).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = OpenCanadaProvider()
        results = provider.search('census', rows=5)
        
        assert len(results) == 2
        assert isinstance(results[0], DatasetRef)
        assert results[0].provider == 'open_canada'
        assert results[0].id == 'census-2021'
        assert results[0].metadata['title'] == 'Census 2021 Population Data'
        assert 'census' in results[0].tags
        assert 'population' in results[0].tags
        
        # Verify base_url was used in the search
        assert results[0].params['base_url'] == OPEN_CANADA_BASE_URL
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_provider_search_with_pagination(self, mock_retry):
        """Test search with pagination parameters."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_SEARCH_RESPONSE_RAW).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = OpenCanadaProvider()
        results = provider.search('housing', rows=10, start=20)
        
        assert len(results) == 2
        # Verify the function was called with correct URL
        mock_retry.assert_called_once()
        call_url = mock_retry.call_args[0][0]
        assert 'rows=10' in call_url
        assert 'start=20' in call_url
        assert 'open.canada.ca' in call_url
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_provider_resolve(self, mock_retry):
        """Test Open Canada provider resolve."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = OpenCanadaProvider()
        ref = DatasetRef(
            provider='open_canada',
            id='census-2021'
        )
        
        metadata = provider.resolve(ref)
        
        assert metadata['package_id'] == 'census-2021'
        assert metadata['title'] == 'Census 2021 Population Data'
        assert metadata['provider'] == 'open_canada'
        assert len(metadata['resources']) == 2
        assert metadata['base_url'] == OPEN_CANADA_BASE_URL
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_provider_resolve_with_format_filter(self, mock_retry):
        """Test resolve with format filter."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = OpenCanadaProvider()
        ref = DatasetRef(
            provider='open_canada',
            id='census-2021',
            params={'format': 'CSV'}
        )
        
        metadata = provider.resolve(ref)
        
        assert len(metadata['resources']) == 1
        assert metadata['resources'][0]['format'] == 'CSV'
    
    @patch('publicdata_ca.providers.ckan.download_file')
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_provider_fetch(self, mock_retry, mock_download, tmp_path):
        """Test Open Canada provider fetch."""
        # Mock package response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Mock download
        mock_download.return_value = str(tmp_path / 'census.csv')
        
        provider = OpenCanadaProvider()
        ref = DatasetRef(
            provider='open_canada',
            id='census-2021',
            params={'format': 'CSV'}
        )
        
        result = provider.fetch(ref, str(tmp_path))
        
        assert result['dataset_id'] == 'open_canada_census-2021'
        assert result['provider'] == 'open_canada'
        assert len(result['files']) == 1
        assert result['files'][0].endswith('.csv')
        assert result['base_url'] == OPEN_CANADA_BASE_URL
    
    @patch('publicdata_ca.providers.ckan.download_file')
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_provider_fetch_multiple_formats(self, mock_retry, mock_download, tmp_path):
        """Test fetching all resources without format filter."""
        # Mock package response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Mock downloads
        mock_download.side_effect = [
            str(tmp_path / 'census.csv'),
            str(tmp_path / 'census.json')
        ]
        
        provider = OpenCanadaProvider()
        ref = DatasetRef(
            provider='open_canada',
            id='census-2021',
            params={}  # No format filter
        )
        
        result = provider.fetch(ref, str(tmp_path))
        
        assert len(result['files']) == 2
        assert len(result['resources']) == 2
    
    def test_open_canada_provider_base_url_preconfigured(self):
        """Test that base_url is pre-configured and doesn't need to be specified."""
        provider = OpenCanadaProvider()
        
        # Create a ref without base_url in params
        ref = DatasetRef(
            provider='open_canada',
            id='test-dataset',
            params={'format': 'CSV'}
        )
        
        # The provider should use its pre-configured base_url
        # No need to specify base_url in params
        assert provider.base_url == OPEN_CANADA_BASE_URL
        assert 'base_url' not in ref.params
    
    def test_open_canada_provider_is_ckan_provider(self):
        """Test that OpenCanadaProvider is a subclass of CKANProvider."""
        from publicdata_ca.providers.ckan import CKANProvider
        
        provider = OpenCanadaProvider()
        assert isinstance(provider, CKANProvider)
        assert isinstance(provider, Provider)
    
    def test_open_canada_provider_registry_compatible(self):
        """Test Open Canada provider works with provider registry."""
        from publicdata_ca.provider import ProviderRegistry
        
        registry = ProviderRegistry()
        registry.register('open_canada', OpenCanadaProvider)
        
        # Should be able to get provider
        provider = registry.get_provider('open_canada')
        assert isinstance(provider, OpenCanadaProvider)
        assert isinstance(provider, Provider)
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_provider_extracts_formats(self, mock_retry):
        """Test that formats are properly extracted to metadata."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_SEARCH_RESPONSE_RAW).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = OpenCanadaProvider()
        results = provider.search('census')
        
        # Check formats in metadata
        assert 'CSV' in results[0].metadata['formats']
        assert 'JSON' in results[0].metadata['formats']
        assert results[0].metadata['num_resources'] == 2
        
        # Second result should only have CSV
        assert 'CSV' in results[1].metadata['formats']
        assert results[1].metadata['num_resources'] == 1


class TestOpenCanadaProviderIntegration:
    """Integration tests for Open Canada provider."""
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_open_canada_end_to_end_workflow(self, mock_retry, tmp_path):
        """Test a complete workflow: search, resolve, and fetch."""
        # This test demonstrates the typical usage pattern
        
        # Step 1: Search for datasets
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_SEARCH_RESPONSE_RAW).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = OpenCanadaProvider()
        results = provider.search('housing', rows=5)
        
        assert len(results) > 0
        first_result = results[0]
        
        # Step 2: Create a reference to download
        ref = DatasetRef(
            provider='open_canada',
            id=first_result.id,
            params={'format': 'CSV'}
        )
        
        # Step 3: Resolve to see what's available
        mock_response.read.return_value = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        metadata = provider.resolve(ref)
        
        assert 'resources' in metadata
        assert len(metadata['resources']) > 0
    
    def test_open_canada_constant_url(self):
        """Test that the OPEN_CANADA_BASE_URL constant is correct."""
        assert OPEN_CANADA_BASE_URL == 'https://open.canada.ca/data'
        
        # Verify it's used by the provider
        provider = OpenCanadaProvider()
        assert provider.base_url == OPEN_CANADA_BASE_URL
