"""Tests for the fetch_dataset convenience function."""

import json
import pytest
from unittest.mock import Mock, patch
from publicdata_ca import DatasetRef, fetch_dataset, get_registry


# Sample CKAN API response for testing
SAMPLE_PACKAGE_RESPONSE = {
    "success": True,
    "result": {
        "id": "dataset-1",
        "name": "test-dataset",
        "title": "Test Dataset",
        "notes": "Test description",
        "resources": [
            {
                "id": "resource-1",
                "name": "Test CSV",
                "url": "https://example.com/test.csv",
                "format": "CSV",
            }
        ]
    }
}


class TestFetchDataset:
    """Test the fetch_dataset convenience function."""
    
    @patch('publicdata_ca.providers.ckan.download_file')
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_fetch_dataset_open_canada(self, mock_retry, mock_download, tmp_path):
        """Test fetch_dataset with Open Canada provider."""
        # Mock API response
        mock_response = Mock()
        mock_response.content = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Mock file download - return value doesn't matter, just needs to not raise
        mock_download.return_value = str(tmp_path / 'test.csv')
        
        # Create a dataset reference
        ref = DatasetRef(
            provider='open_canada',
            id='test-dataset',
            params={'format': 'CSV'}
        )
        
        # Use the convenience function
        result = fetch_dataset(ref, str(tmp_path))
        
        # Verify the result
        assert result['dataset_id'] == 'open_canada_test-dataset'
        assert result['provider'] == 'open_canada'
        assert len(result['files']) == 1
        # The filename is based on resource name, not the mocked return value
        assert result['files'][0].endswith('.csv')
    
    def test_fetch_dataset_invalid_provider(self, tmp_path):
        """Test fetch_dataset with an invalid provider raises KeyError."""
        ref = DatasetRef(
            provider='nonexistent_provider',
            id='test-dataset'
        )
        
        with pytest.raises(KeyError, match="Provider 'nonexistent_provider' is not registered"):
            fetch_dataset(ref, str(tmp_path))
    
    def test_fetch_dataset_uses_global_registry(self):
        """Test that fetch_dataset uses the global registry."""
        # Get the global registry
        registry = get_registry()
        
        # Verify common providers are registered
        assert registry.has_provider('open_canada')
        assert registry.has_provider('statcan')
        assert registry.has_provider('cmhc')
        assert registry.has_provider('ckan')
        assert registry.has_provider('socrata')
        assert registry.has_provider('sdmx')
        assert registry.has_provider('valet')
        assert registry.has_provider('boc_valet')  # Alias
    
    @patch('publicdata_ca.providers.ckan.download_file')
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_fetch_dataset_with_kwargs(self, mock_retry, mock_download, tmp_path):
        """Test fetch_dataset passes kwargs to provider."""
        # Mock API response
        mock_response = Mock()
        mock_response.content = json.dumps(SAMPLE_PACKAGE_RESPONSE).encode('utf-8')
        mock_retry.return_value = mock_response
        
        # Mock file download
        mock_download.return_value = str(tmp_path / 'test.csv')
        
        # Create a dataset reference
        ref = DatasetRef(
            provider='open_canada',
            id='test-dataset',
            params={'format': 'CSV'}
        )
        
        # Use the convenience function with kwargs
        result = fetch_dataset(ref, str(tmp_path), max_retries=5)
        
        # Verify the result
        assert result['dataset_id'] == 'open_canada_test-dataset'
        assert len(result['files']) == 1
        assert result['files'][0].endswith('.csv')


class TestGlobalRegistry:
    """Test the global registry auto-registration."""
    
    def test_global_registry_has_providers(self):
        """Test that the global registry has providers auto-registered."""
        registry = get_registry()
        providers = registry.list_providers()
        
        # Check that common providers are registered
        assert 'statcan' in providers
        assert 'cmhc' in providers
        assert 'open_canada' in providers
        assert 'ckan' in providers
        assert 'socrata' in providers
        assert 'sdmx' in providers
        assert 'valet' in providers
        assert 'boc_valet' in providers
    
    def test_global_registry_get_provider(self):
        """Test getting providers from the global registry."""
        registry = get_registry()
        
        # Get Open Canada provider
        provider = registry.get_provider('open_canada')
        assert provider.name == 'open_canada'
        assert provider.base_url == 'https://open.canada.ca/data'
    
    def test_global_registry_valet_alias(self):
        """Test that valet and boc_valet are aliases."""
        registry = get_registry()
        
        # Both should return the same provider class
        valet_provider = registry.get_provider('valet')
        boc_provider = registry.get_provider('boc_valet')
        
        assert valet_provider.name == 'valet'
        assert boc_provider.name == 'boc_valet'
        assert type(valet_provider) == type(boc_provider)


class TestTopLevelExports:
    """Test that all providers are exported from top-level package."""
    
    def test_all_providers_exported(self):
        """Test that all provider classes are exported."""
        from publicdata_ca import (
            StatCanProvider,
            CMHCProvider,
            OpenCanadaProvider,
            CKANProvider,
            SocrataProvider,
            SDMXProvider,
            ValetProvider,
        )
        
        # Just verify they can be imported
        assert StatCanProvider is not None
        assert CMHCProvider is not None
        assert OpenCanadaProvider is not None
        assert CKANProvider is not None
        assert SocrataProvider is not None
        assert SDMXProvider is not None
        assert ValetProvider is not None
    
    def test_fetch_dataset_exported(self):
        """Test that fetch_dataset is exported."""
        from publicdata_ca import fetch_dataset
        
        assert fetch_dataset is not None
        assert callable(fetch_dataset)
