"""Tests for the provider interface and registry."""

import pytest
from publicdata_ca.provider import (
    Provider,
    DatasetRef,
    ProviderRegistry,
    get_registry,
)
from publicdata_ca.providers import StatCanProvider, CMHCProvider


class TestDatasetRef:
    """Test the DatasetRef schema."""
    
    def test_dataset_ref_creation(self):
        """Test creating a dataset reference."""
        ref = DatasetRef(
            provider='statcan',
            id='18100004',
            params={'language': 'en'},
            metadata={'title': 'Consumer Price Index'}
        )
        
        assert ref.provider == 'statcan'
        assert ref.id == '18100004'
        assert ref.params['language'] == 'en'
        assert ref.metadata['title'] == 'Consumer Price Index'
    
    def test_dataset_ref_canonical_id(self):
        """Test canonical ID generation."""
        ref = DatasetRef(provider='statcan', id='18100004')
        assert ref.canonical_id == 'statcan:18100004'
    
    def test_dataset_ref_str_representation(self):
        """Test string representation."""
        ref = DatasetRef(provider='cmhc', id='housing-starts')
        assert str(ref) == 'cmhc:housing-starts'
    
    def test_dataset_ref_default_params(self):
        """Test default parameters."""
        ref = DatasetRef(provider='statcan', id='18100004')
        assert ref.params == {}
        assert ref.metadata == {}
    
    def test_dataset_ref_with_params(self):
        """Test dataset reference with parameters."""
        ref = DatasetRef(
            provider='cmhc',
            id='rental-market',
            params={'page_url': 'https://example.com', 'format': 'xlsx'}
        )
        assert ref.params['page_url'] == 'https://example.com'
        assert ref.params['format'] == 'xlsx'


class TestProviderRegistry:
    """Test the provider registry."""
    
    def test_registry_creation(self):
        """Test creating a provider registry."""
        registry = ProviderRegistry()
        assert registry.list_providers() == []
    
    def test_register_provider(self):
        """Test registering a provider."""
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        
        assert 'statcan' in registry.list_providers()
        assert registry.has_provider('statcan')
    
    def test_register_multiple_providers(self):
        """Test registering multiple providers."""
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        registry.register('cmhc', CMHCProvider)
        
        providers = registry.list_providers()
        assert 'statcan' in providers
        assert 'cmhc' in providers
        assert len(providers) == 2
    
    def test_get_provider_instance(self):
        """Test getting a provider instance."""
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        
        provider = registry.get_provider('statcan')
        assert isinstance(provider, StatCanProvider)
        assert provider.name == 'statcan'
    
    def test_get_unregistered_provider_raises_error(self):
        """Test getting an unregistered provider raises KeyError."""
        registry = ProviderRegistry()
        
        with pytest.raises(KeyError, match="Provider 'nonexistent' is not registered"):
            registry.get_provider('nonexistent')
    
    def test_register_invalid_provider_raises_error(self):
        """Test registering an invalid provider class raises ValueError."""
        registry = ProviderRegistry()
        
        class NotAProvider:
            pass
        
        with pytest.raises(ValueError, match="must inherit from Provider"):
            registry.register('invalid', NotAProvider)
    
    def test_has_provider(self):
        """Test checking if a provider is registered."""
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        
        assert registry.has_provider('statcan') is True
        assert registry.has_provider('cmhc') is False
    
    def test_global_registry(self):
        """Test accessing the global registry."""
        registry = get_registry()
        assert isinstance(registry, ProviderRegistry)
        
        # Global registry should be the same instance
        registry2 = get_registry()
        assert registry is registry2


class TestStatCanProvider:
    """Test the StatsCan provider implementation."""
    
    def test_statcan_provider_creation(self):
        """Test creating a StatsCan provider."""
        provider = StatCanProvider()
        assert provider.name == 'statcan'
        assert isinstance(provider, Provider)
    
    def test_statcan_search_placeholder(self):
        """Test StatsCan search (placeholder implementation)."""
        provider = StatCanProvider()
        results = provider.search('consumer price index')
        
        # Placeholder returns empty list
        assert results == []
    
    def test_statcan_resolve(self):
        """Test resolving a StatsCan dataset reference."""
        provider = StatCanProvider()
        ref = DatasetRef(
            provider='statcan',
            id='18100004',
            params={'language': 'en'}
        )
        
        metadata = provider.resolve(ref)
        
        assert 'url' in metadata
        assert metadata['provider'] == 'statcan'
        assert metadata['format'] == 'csv'
        assert metadata['pid'] == '18100004'
        assert '18100004' in metadata['url']
    
    def test_statcan_resolve_with_metadata(self):
        """Test resolving with metadata."""
        provider = StatCanProvider()
        ref = DatasetRef(
            provider='statcan',
            id='18-10-0004',
            metadata={'title': 'Consumer Price Index'}
        )
        
        metadata = provider.resolve(ref)
        
        assert metadata['title'] == 'Consumer Price Index'
        assert metadata['pid'] == '18100004'  # Normalized
        assert metadata['table_number'] == '18-10-0004'
    
    def test_statcan_resolve_normalizes_table_id(self):
        """Test that resolve normalizes different table ID formats."""
        provider = StatCanProvider()
        
        # Test hyphenated format
        ref1 = DatasetRef(provider='statcan', id='18-10-0004')
        metadata1 = provider.resolve(ref1)
        assert metadata1['pid'] == '18100004'
        
        # Test non-hyphenated format
        ref2 = DatasetRef(provider='statcan', id='18100004')
        metadata2 = provider.resolve(ref2)
        assert metadata2['pid'] == '18100004'


class TestCMHCProvider:
    """Test the CMHC provider implementation."""
    
    def test_cmhc_provider_creation(self):
        """Test creating a CMHC provider."""
        provider = CMHCProvider()
        assert provider.name == 'cmhc'
        assert isinstance(provider, Provider)
    
    def test_cmhc_search_placeholder(self):
        """Test CMHC search (placeholder implementation)."""
        provider = CMHCProvider()
        results = provider.search('housing starts')
        
        # Placeholder returns empty list
        assert results == []
    
    def test_cmhc_resolve_with_direct_url(self):
        """Test resolving a CMHC dataset with direct URL."""
        provider = CMHCProvider()
        ref = DatasetRef(
            provider='cmhc',
            id='rental-market',
            params={'direct_url': 'https://example.com/data.xlsx'},
            metadata={'title': 'Rental Market Report'}
        )
        
        metadata = provider.resolve(ref)
        
        assert metadata['url'] == 'https://example.com/data.xlsx'
        assert metadata['format'] == 'xlsx'
        assert metadata['title'] == 'Rental Market Report'
        assert metadata['provider'] == 'cmhc'
    
    def test_cmhc_resolve_without_url_raises_error(self):
        """Test that resolve raises error without URL."""
        provider = CMHCProvider()
        ref = DatasetRef(provider='cmhc', id='housing-starts')
        
        with pytest.raises(ValueError, match="must include 'page_url' or 'direct_url'"):
            provider.resolve(ref)
    
    def test_cmhc_detect_format(self):
        """Test file format detection."""
        provider = CMHCProvider()
        
        assert provider._detect_format('https://example.com/data.xlsx') == 'xlsx'
        assert provider._detect_format('https://example.com/data.csv') == 'csv'
        assert provider._detect_format('https://example.com/data.xls') == 'xls'
        assert provider._detect_format('https://example.com/data.zip') == 'zip'
        assert provider._detect_format('https://example.com/data.unknown') == 'dat'


class TestProviderIntegration:
    """Test provider integration with registry."""
    
    def test_register_and_use_providers(self):
        """Test registering and using providers via registry."""
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        registry.register('cmhc', CMHCProvider)
        
        # Get StatsCan provider and use it
        statcan = registry.get_provider('statcan')
        ref1 = DatasetRef(provider='statcan', id='18100004')
        metadata1 = statcan.resolve(ref1)
        assert metadata1['provider'] == 'statcan'
        
        # Get CMHC provider and use it
        cmhc = registry.get_provider('cmhc')
        ref2 = DatasetRef(
            provider='cmhc',
            id='rental-market',
            params={'direct_url': 'https://example.com/data.xlsx'}
        )
        metadata2 = cmhc.resolve(ref2)
        assert metadata2['provider'] == 'cmhc'
    
    def test_provider_instances_are_independent(self):
        """Test that provider instances from registry are independent."""
        registry = ProviderRegistry()
        registry.register('statcan', StatCanProvider)
        
        provider1 = registry.get_provider('statcan')
        provider2 = registry.get_provider('statcan')
        
        # Should be different instances
        assert provider1 is not provider2
        # But same type
        assert type(provider1) is type(provider2)
