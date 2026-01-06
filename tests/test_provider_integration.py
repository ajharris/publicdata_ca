"""
Integration tests demonstrating the provider interface in action.

These tests show real-world usage patterns of the Provider interface,
DatasetRef schema, and ProviderRegistry.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from publicdata_ca.provider import (
    Provider,
    DatasetRef,
    ProviderRegistry,
    get_registry,
)
from publicdata_ca.providers import StatCanProvider, CMHCProvider


class TestProviderWorkflow:
    """Test end-to-end provider workflows."""
    
    def test_statcan_workflow_with_provider_interface(self):
        """Test using the provider interface for StatsCan downloads."""
        # Create a provider
        provider = StatCanProvider()
        
        # Create a dataset reference
        ref = DatasetRef(
            provider='statcan',
            id='18100004',
            params={'language': 'en'},
            metadata={'title': 'Consumer Price Index'}
        )
        
        # Resolve the reference to get download metadata
        metadata = provider.resolve(ref)
        
        # Verify metadata structure
        assert metadata['provider'] == 'statcan'
        assert metadata['pid'] == '18100004'
        assert metadata['format'] == 'csv'
        assert 'url' in metadata
        assert '18100004' in metadata['url']
    
    def test_cmhc_workflow_with_provider_interface(self):
        """Test using the provider interface for CMHC datasets."""
        # Create a provider
        provider = CMHCProvider()
        
        # Create a dataset reference with direct URL
        ref = DatasetRef(
            provider='cmhc',
            id='rental-market-report',
            params={'direct_url': 'https://example.com/rental_market.xlsx'},
            metadata={'title': 'Rental Market Report'}
        )
        
        # Resolve the reference
        metadata = provider.resolve(ref)
        
        # Verify metadata structure
        assert metadata['provider'] == 'cmhc'
        assert metadata['url'] == 'https://example.com/rental_market.xlsx'
        assert metadata['format'] == 'xlsx'
        assert metadata['title'] == 'Rental Market Report'
    
    def test_registry_based_workflow(self):
        """Test discovering and using providers via the registry."""
        # Create and populate a registry
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        registry.register('cmhc', CMHCProvider)
        
        # List available providers
        providers = registry.list_providers()
        assert 'statcan' in providers
        assert 'cmhc' in providers
        
        # Use the registry to get a provider dynamically
        dataset_refs = [
            DatasetRef(
                provider='statcan',
                id='18100004',
                metadata={'title': 'CPI'}
            ),
            DatasetRef(
                provider='cmhc',
                id='housing-starts',
                params={'direct_url': 'https://example.com/housing.xlsx'},
                metadata={'title': 'Housing Starts'}
            ),
        ]
        
        # Process each dataset using the appropriate provider
        results = []
        for ref in dataset_refs:
            provider = registry.get_provider(ref.provider)
            metadata = provider.resolve(ref)
            results.append({
                'ref': ref,
                'metadata': metadata
            })
        
        # Verify results
        assert len(results) == 2
        assert results[0]['metadata']['provider'] == 'statcan'
        assert results[1]['metadata']['provider'] == 'cmhc'
    
    def test_provider_abstraction_allows_generic_code(self):
        """Test that provider abstraction allows writing generic code."""
        # Create a registry with both providers
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        registry.register('cmhc', CMHCProvider)
        
        # Generic function that works with any provider
        def resolve_dataset(provider_name: str, dataset_id: str, **params):
            """Generic function to resolve any dataset."""
            provider = registry.get_provider(provider_name)
            ref = DatasetRef(
                provider=provider_name,
                id=dataset_id,
                params=params
            )
            return provider.resolve(ref)
        
        # Use the generic function with different providers
        statcan_metadata = resolve_dataset('statcan', '18100004', language='en')
        cmhc_metadata = resolve_dataset(
            'cmhc',
            'rental-market',
            direct_url='https://example.com/data.xlsx'
        )
        
        # Verify both worked
        assert statcan_metadata['provider'] == 'statcan'
        assert cmhc_metadata['provider'] == 'cmhc'


class TestDatasetRefUseCases:
    """Test DatasetRef in various use cases."""
    
    def test_dataset_ref_serialization(self):
        """Test that DatasetRef can be easily serialized."""
        ref = DatasetRef(
            provider='statcan',
            id='18100004',
            params={'language': 'en', 'format': 'csv'},
            metadata={'title': 'CPI', 'description': 'Consumer Price Index'}
        )
        
        # Convert to dict for serialization
        as_dict = {
            'provider': ref.provider,
            'id': ref.id,
            'params': ref.params,
            'metadata': ref.metadata,
        }
        
        # Reconstruct from dict
        reconstructed = DatasetRef(**as_dict)
        
        assert reconstructed.provider == ref.provider
        assert reconstructed.id == ref.id
        assert reconstructed.params == ref.params
        assert reconstructed.metadata == ref.metadata
    
    def test_dataset_ref_comparison(self):
        """Test comparing dataset references."""
        ref1 = DatasetRef(provider='statcan', id='18100004')
        ref2 = DatasetRef(provider='statcan', id='18100004')
        ref3 = DatasetRef(provider='cmhc', id='housing-starts')
        
        # Same canonical IDs
        assert ref1.canonical_id == ref2.canonical_id
        assert ref1.canonical_id != ref3.canonical_id
    
    def test_dataset_ref_with_complex_params(self):
        """Test DatasetRef with complex parameters."""
        ref = DatasetRef(
            provider='cmhc',
            id='multi-asset-dataset',
            params={
                'page_url': 'https://example.com/landing',
                'asset_filter': 'xlsx',
                'max_retries': 5,
                'custom_headers': {'User-Agent': 'MyApp/1.0'}
            }
        )
        
        # All params should be preserved
        assert ref.params['page_url'] == 'https://example.com/landing'
        assert ref.params['asset_filter'] == 'xlsx'
        assert ref.params['max_retries'] == 5
        assert 'custom_headers' in ref.params


class TestProviderExtensibility:
    """Test that the provider interface supports extension."""
    
    def test_custom_provider_implementation(self):
        """Test creating a custom provider."""
        
        class CustomProvider(Provider):
            """Custom data provider for testing."""
            
            def search(self, query: str, **kwargs):
                return [
                    DatasetRef(
                        provider=self.name,
                        id='test-dataset-1',
                        metadata={'title': 'Test Dataset 1'}
                    )
                ]
            
            def resolve(self, ref: DatasetRef):
                return {
                    'url': f'https://custom.example.com/{ref.id}',
                    'format': 'json',
                    'provider': self.name,
                }
            
            def fetch(self, ref, output_dir, **kwargs):
                return {
                    'files': [],
                    'dataset_id': ref.id,
                    'provider': self.name,
                }
        
        # Register and use the custom provider
        registry = ProviderRegistry()
        registry.register('custom', CustomProvider)
        
        provider = registry.get_provider('custom')
        
        # Test search
        results = provider.search('test')
        assert len(results) == 1
        assert results[0].id == 'test-dataset-1'
        
        # Test resolve
        ref = DatasetRef(provider='custom', id='my-dataset')
        metadata = provider.resolve(ref)
        assert metadata['provider'] == 'custom'
        assert 'my-dataset' in metadata['url']
    
    def test_provider_can_override_initialization(self):
        """Test that providers can customize initialization."""
        
        class ConfigurableProvider(Provider):
            """Provider with custom configuration."""
            
            def __init__(self, name: str, api_key: str = None):
                super().__init__(name)
                self.api_key = api_key
            
            def search(self, query: str, **kwargs):
                return []
            
            def resolve(self, ref: DatasetRef):
                return {'provider': self.name, 'api_key': self.api_key}
            
            def fetch(self, ref, output_dir, **kwargs):
                return {'provider': self.name}
        
        # Can create with custom initialization
        provider = ConfigurableProvider('custom', api_key='test-key-123')
        assert provider.api_key == 'test-key-123'
        
        # Resolve includes the configuration
        ref = DatasetRef(provider='custom', id='test')
        metadata = provider.resolve(ref)
        assert metadata['api_key'] == 'test-key-123'


class TestBackwardCompatibility:
    """Test that the new interface doesn't break existing patterns."""
    
    def test_can_still_use_functional_api(self):
        """Test that existing function-based API still works."""
        from publicdata_ca.providers.statcan import download_statcan_table, _normalize_pid, _build_wds_url
        
        # The old functional API should still work
        pid = _normalize_pid('18-10-0004')
        assert pid == '18100004'
        
        url = _build_wds_url(pid, 'en')
        assert '18100004' in url
    
    def test_can_mix_old_and_new_apis(self):
        """Test that old and new APIs can be used together."""
        from publicdata_ca.providers.statcan import _normalize_pid
        from publicdata_ca.providers import StatCanProvider
        
        # Use old API for normalization
        pid = _normalize_pid('18-10-0004')
        
        # Use new API for provider operations
        provider = StatCanProvider()
        ref = DatasetRef(provider='statcan', id=pid)
        metadata = provider.resolve(ref)
        
        assert metadata['pid'] == '18100004'
