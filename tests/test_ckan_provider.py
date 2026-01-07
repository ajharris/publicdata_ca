"""Tests for the CKAN provider."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from publicdata_ca.provider import Provider, DatasetRef
from publicdata_ca.providers.ckan import (
    search_ckan_datasets,
    get_ckan_package,
    list_ckan_resources,
    download_ckan_resource,
    CKANProvider,
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
                "organization": {"title": "Statistics Agency"},
                "tags": [{"name": "census"}, {"name": "population"}],
                "resources": [
                    {"format": "CSV", "url": "https://example.com/data.csv"},
                    {"format": "JSON", "url": "https://example.com/data.json"}
                ]
            },
            {
                "id": "dataset-2",
                "name": "housing-starts",
                "title": "Housing Starts Monthly",
                "notes": "Monthly housing construction data",
                "organization": {"title": "Housing Agency"},
                "tags": [{"name": "housing"}],
                "resources": [
                    {"format": "CSV", "url": "https://example.com/housing.csv"}
                ]
            }
        ]
    }
}

# What search_ckan_datasets actually returns (unwrapped from CKAN API response)
SAMPLE_SEARCH_RESPONSE = {
    "success": True,
    "count": 2,
    "results": [
        {
            "id": "dataset-1",
            "name": "census-2021",
            "title": "Census 2021 Population Data",
            "notes": "Population statistics from 2021 census",
            "organization": {"title": "Statistics Agency"},
            "tags": [{"name": "census"}, {"name": "population"}],
            "resources": [
                {"format": "CSV", "url": "https://example.com/data.csv"},
                {"format": "JSON", "url": "https://example.com/data.json"}
            ]
        },
        {
            "id": "dataset-2",
            "name": "housing-starts",
            "title": "Housing Starts Monthly",
            "notes": "Monthly housing construction data",
            "organization": {"title": "Housing Agency"},
            "tags": [{"name": "housing"}],
            "resources": [
                {"format": "CSV", "url": "https://example.com/housing.csv"}
            ]
        }
    ]
}

SAMPLE_PACKAGE_RESPONSE = {
    "success": True,
    "result": {
        "id": "dataset-1",
        "name": "census-2021",
        "title": "Census 2021 Population Data",
        "notes": "Population statistics from 2021 census",
        "organization": {"title": "Statistics Agency"},
        "tags": [{"name": "census"}, {"name": "population"}],
        "metadata_created": "2021-01-01T00:00:00",
        "metadata_modified": "2021-06-01T00:00:00",
        "resources": [
            {
                "id": "resource-1",
                "name": "Census Data CSV",
                "url": "https://example.com/census.csv",
                "format": "CSV",
                "description": "Census data in CSV format",
                "created": "2021-01-01T00:00:00",
                "last_modified": "2021-06-01T00:00:00",
                "size": 1024000
            },
            {
                "id": "resource-2",
                "name": "Census Data JSON",
                "url": "https://example.com/census.json",
                "format": "JSON",
                "description": "Census data in JSON format",
                "created": "2021-01-01T00:00:00",
                "last_modified": "2021-06-01T00:00:00",
                "size": 2048000
            },
            {
                "id": "resource-3",
                "name": "Census GeoJSON",
                "url": "https://example.com/census.geojson",
                "format": "GeoJSON",
                "description": "Census data with geography",
                "created": "2021-01-01T00:00:00",
                "last_modified": "2021-06-01T00:00:00",
                "size": 5120000
            }
        ]
    }
}


class TestSearchCkanDatasets:
    """Test the search_ckan_datasets function."""
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_search_datasets_basic(self, mock_retry):
        """Test basic dataset search."""
        # Mock the response
        mock_response = Mock()
        mock_response.content = json.dumps(SAMPLE_SEARCH_RESPONSE_RAW).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Search datasets
        results = search_ckan_datasets(
            'https://open.canada.ca/data',
            'census'
        )
        
        # Verify results
        assert results['success'] is True
        assert results['count'] == 2
        assert len(results['results']) == 2
        assert results['results'][0]['name'] == 'census-2021'
        assert results['results'][1]['name'] == 'housing-starts'
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_search_datasets_with_pagination(self, mock_retry):
        """Test dataset search with pagination."""
        mock_response = Mock()
        mock_response.content = json.dumps(SAMPLE_SEARCH_RESPONSE_RAW).encode('utf-8')
        mock_retry.return_value = mock_response
        
        results = search_ckan_datasets(
            'https://open.canada.ca/data',
            'housing',
            rows=5,
            start=10
        )
        
        assert results['success'] is True
        # Verify the function was called (URL building works)
        mock_retry.assert_called_once()
        call_url = mock_retry.call_args[0][0]
        assert 'rows=5' in call_url
        assert 'start=10' in call_url
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_search_datasets_failure(self, mock_retry):
        """Test search failure handling."""
        mock_response = Mock()
        mock_response.content = json.dumps({
            "success": False,
            "error": {"message": "Not found"}
        }).encode('utf-8')
        mock_retry.return_value = mock_response
        
        results = search_ckan_datasets(
            'https://open.canada.ca/data',
            'nonexistent'
        )
        
        assert results['success'] is False
        assert results['count'] == 0
        assert results['results'] == []
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_search_datasets_network_error(self, mock_retry):
        """Test network error handling."""
        mock_retry.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to search CKAN portal"):
            search_ckan_datasets(
                'https://open.canada.ca/data',
                'test'
            )


class TestGetCkanPackage:
    """Test the get_ckan_package function."""
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_get_package_success(self, mock_retry):
        """Test getting a package successfully."""
        mock_response = Mock()
        mock_response.content = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        package = get_ckan_package(
            'https://open.canada.ca/data',
            'census-2021'
        )
        
        assert package['name'] == 'census-2021'
        assert package['title'] == 'Census 2021 Population Data'
        assert len(package['resources']) == 3
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_get_package_not_found(self, mock_retry):
        """Test getting a non-existent package."""
        mock_response = Mock()
        mock_response.content = json.dumps({
            "success": False,
            "error": {"message": "Package not found"}
        }).encode('utf-8')
        mock_retry.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="CKAN API error"):
            get_ckan_package(
                'https://open.canada.ca/data',
                'nonexistent'
            )
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_get_package_404_error(self, mock_retry):
        """Test getting a package that returns 404."""
        from requests.exceptions import HTTPError
        
        # Create a mock response with 404 status
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason = 'NOT FOUND'
        
        # Create HTTPError with the response
        http_error = HTTPError()
        http_error.response = mock_response
        
        mock_retry.side_effect = http_error
        
        with pytest.raises(ValueError, match="Dataset 'nonexistent' not found"):
            get_ckan_package(
                'https://open.canada.ca/data',
                'nonexistent'
            )
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_get_package_invalid_json(self, mock_retry):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.content = b"Not valid JSON"
        mock_retry.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Failed to parse CKAN response"):
            get_ckan_package(
                'https://open.canada.ca/data',
                'test'
            )


class TestListCkanResources:
    """Test the list_ckan_resources function."""
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_list_all_resources(self, mock_get_package):
        """Test listing all resources without filter."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        resources = list_ckan_resources(
            'https://open.canada.ca/data',
            'census-2021'
        )
        
        assert len(resources) == 3
        assert resources[0]['format'] == 'CSV'
        assert resources[1]['format'] == 'JSON'
        assert resources[2]['format'] == 'GeoJSON'
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_list_resources_with_format_filter(self, mock_get_package):
        """Test listing resources with format filter."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        # Filter for CSV
        csv_resources = list_ckan_resources(
            'https://open.canada.ca/data',
            'census-2021',
            format_filter='CSV'
        )
        
        assert len(csv_resources) == 1
        assert csv_resources[0]['format'] == 'CSV'
        
        # Filter for JSON
        json_resources = list_ckan_resources(
            'https://open.canada.ca/data',
            'census-2021',
            format_filter='JSON'
        )
        
        assert len(json_resources) == 1
        assert json_resources[0]['format'] == 'JSON'
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_list_resources_case_insensitive_filter(self, mock_get_package):
        """Test that format filtering is case-insensitive."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        # Filter with lowercase
        resources = list_ckan_resources(
            'https://open.canada.ca/data',
            'census-2021',
            format_filter='csv'
        )
        
        assert len(resources) == 1
        assert resources[0]['format'] == 'CSV'
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_list_resources_no_match(self, mock_get_package):
        """Test listing resources when no format matches."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        resources = list_ckan_resources(
            'https://open.canada.ca/data',
            'census-2021',
            format_filter='PDF'
        )
        
        assert len(resources) == 0


class TestDownloadCkanResource:
    """Test the download_ckan_resource function."""
    
    @patch('publicdata_ca.providers.ckan.download_file')
    def test_download_resource_success(self, mock_download, tmp_path):
        """Test successful resource download."""
        mock_download.return_value = str(tmp_path / 'census_data.csv')
        
        result = download_ckan_resource(
            'https://example.com/census.csv',
            str(tmp_path),
            resource_name='census_data',
            resource_format='csv'
        )
        
        assert result['url'] == 'https://example.com/census.csv'
        assert result['format'] == 'csv'
        assert 'census_data.csv' in result['file']
        mock_download.assert_called_once()
    
    @patch('publicdata_ca.providers.ckan.download_file')
    def test_download_resource_name_sanitization(self, mock_download, tmp_path):
        """Test that resource names are sanitized."""
        mock_download.return_value = str(tmp_path / 'My_Resource_123.json')
        
        result = download_ckan_resource(
            'https://example.com/data.json',
            str(tmp_path),
            resource_name='My Resource 123!@#$%',
            resource_format='json'
        )
        
        # Verify sanitized name
        assert 'My_Resource_123' in result['file']
    
    @patch('publicdata_ca.providers.ckan.download_file')
    def test_download_resource_default_name(self, mock_download, tmp_path):
        """Test download with default resource name."""
        mock_download.return_value = str(tmp_path / 'resource.dat')
        
        result = download_ckan_resource(
            'https://example.com/data',
            str(tmp_path)
        )
        
        assert 'resource.dat' in result['file']
    
    @patch('publicdata_ca.providers.ckan.download_file')
    def test_download_resource_failure(self, mock_download, tmp_path):
        """Test download failure handling."""
        mock_download.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to download CKAN resource"):
            download_ckan_resource(
                'https://example.com/data.csv',
                str(tmp_path),
                resource_name='test',
                resource_format='csv'
            )


class TestCKANProvider:
    """Test the CKANProvider class."""
    
    def test_ckan_provider_creation(self):
        """Test creating a CKAN provider."""
        provider = CKANProvider(name='open_canada', base_url='https://open.canada.ca/data')
        
        assert provider.name == 'open_canada'
        assert provider.base_url == 'https://open.canada.ca/data'
        assert isinstance(provider, Provider)
    
    def test_ckan_provider_default_name(self):
        """Test CKAN provider with default name."""
        provider = CKANProvider(base_url='https://example.com')
        assert provider.name == 'ckan'
    
    @patch('publicdata_ca.providers.ckan.search_ckan_datasets')
    def test_ckan_provider_search(self, mock_search):
        """Test CKAN provider search."""
        mock_search.return_value = SAMPLE_SEARCH_RESPONSE
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        results = provider.search('census', rows=5)
        
        assert len(results) == 2
        assert isinstance(results[0], DatasetRef)
        assert results[0].provider == 'ckan'
        assert results[0].id == 'census-2021'
        assert results[0].metadata['title'] == 'Census 2021 Population Data'
        assert 'census' in results[0].tags
        assert 'population' in results[0].tags
        assert results[0].params['base_url'] == 'https://open.canada.ca/data'
    
    @patch('publicdata_ca.providers.ckan.search_ckan_datasets')
    def test_ckan_provider_search_without_base_url(self, mock_search):
        """Test search without base_url raises error."""
        provider = CKANProvider()
        
        with pytest.raises(ValueError, match="base_url must be provided"):
            provider.search('test')
    
    @patch('publicdata_ca.providers.ckan.search_ckan_datasets')
    def test_ckan_provider_search_with_kwargs_base_url(self, mock_search):
        """Test search with base_url in kwargs."""
        mock_search.return_value = SAMPLE_SEARCH_RESPONSE
        
        provider = CKANProvider()
        results = provider.search('census', base_url='https://open.canada.ca/data')
        
        assert len(results) == 2
        mock_search.assert_called_once()
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_resolve(self, mock_get_package):
        """Test CKAN provider resolve."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        ref = DatasetRef(
            provider='ckan',
            id='census-2021'
        )
        
        metadata = provider.resolve(ref)
        
        assert metadata['package_id'] == 'census-2021'
        assert metadata['title'] == 'Census 2021 Population Data'
        assert metadata['provider'] == 'ckan'
        assert len(metadata['resources']) == 3
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_resolve_with_format_filter(self, mock_get_package):
        """Test resolve with format filter."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        ref = DatasetRef(
            provider='ckan',
            id='census-2021',
            params={'format': 'CSV'}
        )
        
        metadata = provider.resolve(ref)
        
        assert len(metadata['resources']) == 1
        assert metadata['resources'][0]['format'] == 'CSV'
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_resolve_with_resource_id(self, mock_get_package):
        """Test resolve with specific resource ID."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        ref = DatasetRef(
            provider='ckan',
            id='census-2021',
            params={'resource_id': 'resource-2'}
        )
        
        metadata = provider.resolve(ref)
        
        assert len(metadata['resources']) == 1
        assert metadata['resources'][0]['id'] == 'resource-2'
        assert metadata['resources'][0]['format'] == 'JSON'
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_resolve_without_base_url(self, mock_get_package):
        """Test resolve without base_url raises error."""
        provider = CKANProvider()
        ref = DatasetRef(provider='ckan', id='test')
        
        with pytest.raises(ValueError, match="base_url must be provided"):
            provider.resolve(ref)
    
    @patch('publicdata_ca.providers.ckan.download_ckan_resource')
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_fetch(self, mock_get_package, mock_download, tmp_path):
        """Test CKAN provider fetch."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        mock_download.side_effect = [
            {'file': str(tmp_path / 'census.csv'), 'url': 'https://example.com/census.csv', 'format': 'csv'}
        ]
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        ref = DatasetRef(
            provider='ckan',
            id='census-2021',
            params={'format': 'CSV'}
        )
        
        result = provider.fetch(ref, str(tmp_path))
        
        assert result['dataset_id'] == 'ckan_census-2021'
        assert result['provider'] == 'ckan'
        assert len(result['files']) == 1
        assert 'census.csv' in result['files'][0]
        assert len(result['resources']) == 1
    
    @patch('publicdata_ca.providers.ckan.download_ckan_resource')
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_fetch_multiple_resources(self, mock_get_package, mock_download, tmp_path):
        """Test fetching multiple resources."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        mock_download.side_effect = [
            {'file': str(tmp_path / 'census.csv'), 'url': 'https://example.com/census.csv', 'format': 'csv'},
            {'file': str(tmp_path / 'census.json'), 'url': 'https://example.com/census.json', 'format': 'json'},
            {'file': str(tmp_path / 'census.geojson'), 'url': 'https://example.com/census.geojson', 'format': 'geojson'}
        ]
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        ref = DatasetRef(
            provider='ckan',
            id='census-2021'
        )
        
        result = provider.fetch(ref, str(tmp_path))
        
        assert len(result['files']) == 3
        assert len(result['resources']) == 3
    
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_fetch_no_resources(self, mock_get_package, tmp_path):
        """Test fetch with no matching resources raises error."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        ref = DatasetRef(
            provider='ckan',
            id='census-2021',
            params={'format': 'PDF'}  # No PDF resources
        )
        
        with pytest.raises(ValueError, match="No resources found"):
            provider.fetch(ref, str(tmp_path))
    
    @patch('publicdata_ca.providers.ckan.download_ckan_resource')
    @patch('publicdata_ca.providers.ckan.get_ckan_package')
    def test_ckan_provider_fetch_partial_failure(self, mock_get_package, mock_download, tmp_path, capsys):
        """Test fetch continues on partial failures."""
        mock_get_package.return_value = SAMPLE_PACKAGE_RESPONSE['result']
        # First succeeds, second fails
        mock_download.side_effect = [
            {'file': str(tmp_path / 'census.csv'), 'url': 'https://example.com/census.csv', 'format': 'csv'},
            Exception("Network error"),
            {'file': str(tmp_path / 'census.geojson'), 'url': 'https://example.com/census.geojson', 'format': 'geojson'}
        ]
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        ref = DatasetRef(provider='ckan', id='census-2021')
        
        result = provider.fetch(ref, str(tmp_path))
        
        # Should have 2 successful downloads
        assert len(result['files']) == 2
        # Should have 3 resources (including failed one)
        assert len(result['resources']) == 3
        # Failed resource should have error field
        assert any('error' in r for r in result['resources'])
        
        # Check warning was printed
        captured = capsys.readouterr()
        assert 'Warning: Failed to download' in captured.out


class TestCKANProviderIntegration:
    """Integration tests for CKAN provider."""
    
    def test_ckan_provider_with_base_url_in_params(self):
        """Test using base_url in DatasetRef params instead of provider init."""
        provider = CKANProvider()
        
        ref = DatasetRef(
            provider='ckan',
            id='test-dataset',
            params={'base_url': 'https://open.canada.ca/data'}
        )
        
        # Should be able to use params base_url
        assert ref.params['base_url'] == 'https://open.canada.ca/data'
    
    def test_ckan_provider_registry_compatible(self):
        """Test CKAN provider works with provider registry."""
        from publicdata_ca.provider import ProviderRegistry
        
        registry = ProviderRegistry()
        registry.register('open_canada', CKANProvider)
        
        # Should be able to get provider
        provider = registry.get_provider('open_canada')
        assert isinstance(provider, CKANProvider)
        assert isinstance(provider, Provider)
    
    @patch('publicdata_ca.providers.ckan.search_ckan_datasets')
    def test_ckan_provider_formats_metadata(self, mock_search):
        """Test that formats are properly extracted to metadata."""
        mock_search.return_value = SAMPLE_SEARCH_RESPONSE
        
        provider = CKANProvider(base_url='https://open.canada.ca/data')
        results = provider.search('census')
        
        # Check formats in metadata
        assert 'CSV' in results[0].metadata['formats']
        assert 'JSON' in results[0].metadata['formats']
        assert results[0].metadata['num_resources'] == 2
