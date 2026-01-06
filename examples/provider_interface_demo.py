#!/usr/bin/env python
"""
Example demonstrating the Provider interface, DatasetRef schema, and ProviderRegistry.

This example shows how to:
1. Create dataset references using DatasetRef
2. Use the ProviderRegistry to discover and instantiate providers
3. Use providers to resolve and fetch datasets
4. Write provider-agnostic code that works with any data source

The provider interface enables adding new data sources without refactoring existing code.
"""

from publicdata_ca import (
    DatasetRef,
    ProviderRegistry,
    get_registry,
    StatCanProvider,
    CMHCProvider,
)


def example_1_basic_usage():
    """Example 1: Basic usage of the provider interface."""
    print("=" * 80)
    print("Example 1: Basic Provider Usage")
    print("=" * 80)
    
    # Create a StatsCan provider
    statcan = StatCanProvider()
    
    # Create a dataset reference
    ref = DatasetRef(
        provider='statcan',
        id='18100004',
        params={'language': 'en'},
        metadata={'title': 'Consumer Price Index'}
    )
    
    print(f"\nDataset Reference: {ref.canonical_id}")
    print(f"Provider: {ref.provider}")
    print(f"ID: {ref.id}")
    print(f"Params: {ref.params}")
    
    # Resolve the reference to get download metadata
    metadata = statcan.resolve(ref)
    
    print(f"\nResolved Metadata:")
    print(f"  URL: {metadata['url']}")
    print(f"  Format: {metadata['format']}")
    print(f"  PID: {metadata['pid']}")
    print(f"  Table Number: {metadata['table_number']}")


def example_2_using_registry():
    """Example 2: Using the ProviderRegistry for discovery."""
    print("\n" + "=" * 80)
    print("Example 2: Provider Registry")
    print("=" * 80)
    
    # Create and populate a registry
    registry = ProviderRegistry()
    registry.register('statcan', StatCanProvider)
    registry.register('cmhc', CMHCProvider)
    
    # List available providers
    print(f"\nAvailable providers: {registry.list_providers()}")
    
    # Get a provider dynamically
    provider_name = 'statcan'
    provider = registry.get_provider(provider_name)
    
    print(f"\nGot provider: {provider.name} ({type(provider).__name__})")
    
    # Use the provider
    ref = DatasetRef(provider='statcan', id='18100004')
    metadata = provider.resolve(ref)
    print(f"Resolved dataset: {metadata['table_number']}")


def example_3_multiple_providers():
    """Example 3: Working with multiple providers."""
    print("\n" + "=" * 80)
    print("Example 3: Multiple Providers")
    print("=" * 80)
    
    # Create a registry
    registry = ProviderRegistry()
    registry.register('statcan', StatCanProvider)
    registry.register('cmhc', CMHCProvider)
    
    # Define dataset references from different providers
    datasets = [
        DatasetRef(
            provider='statcan',
            id='18100004',
            metadata={'title': 'Consumer Price Index'}
        ),
        DatasetRef(
            provider='statcan',
            id='14100287',
            metadata={'title': 'Employment by industry'}
        ),
        DatasetRef(
            provider='cmhc',
            id='rental-market-report',
            params={'direct_url': 'https://example.com/rental.xlsx'},
            metadata={'title': 'Rental Market Report'}
        ),
    ]
    
    print(f"\nProcessing {len(datasets)} datasets from multiple providers:")
    
    # Process each dataset using the appropriate provider
    for ref in datasets:
        provider = registry.get_provider(ref.provider)
        metadata = provider.resolve(ref)
        
        title = ref.metadata.get('title', 'Unknown')
        print(f"\n  [{ref.provider}] {title}")
        print(f"    Canonical ID: {ref.canonical_id}")
        if 'pid' in metadata:
            print(f"    PID: {metadata['pid']}")
        if 'url' in metadata:
            print(f"    URL: {metadata['url'][:60]}...")


def example_4_provider_agnostic_code():
    """Example 4: Writing provider-agnostic code."""
    print("\n" + "=" * 80)
    print("Example 4: Provider-Agnostic Code")
    print("=" * 80)
    
    def resolve_any_dataset(provider_name: str, dataset_id: str, **params):
        """
        Generic function that works with any provider.
        
        This demonstrates how the provider interface enables writing
        code that doesn't need to know provider-specific details.
        """
        # Get the global registry
        registry = get_registry()
        
        # Ensure provider is registered (in real code, this would be done at startup)
        if not registry.has_provider(provider_name):
            if provider_name == 'statcan':
                registry.register('statcan', StatCanProvider)
            elif provider_name == 'cmhc':
                registry.register('cmhc', CMHCProvider)
        
        # Get the appropriate provider
        provider = registry.get_provider(provider_name)
        
        # Create dataset reference
        ref = DatasetRef(
            provider=provider_name,
            id=dataset_id,
            params=params
        )
        
        # Resolve using the provider
        return provider.resolve(ref)
    
    # Use the generic function with different providers
    print("\nUsing generic resolve function:")
    
    print("\n  StatsCan dataset:")
    statcan_result = resolve_any_dataset('statcan', '18100004', language='en')
    print(f"    URL: {statcan_result['url'][:60]}...")
    
    print("\n  CMHC dataset:")
    cmhc_result = resolve_any_dataset(
        'cmhc',
        'rental-market',
        direct_url='https://example.com/data.xlsx'
    )
    print(f"    URL: {cmhc_result['url']}")


def example_5_extending_with_custom_provider():
    """Example 5: Creating a custom provider."""
    print("\n" + "=" * 80)
    print("Example 5: Custom Provider")
    print("=" * 80)
    
    from publicdata_ca.provider import Provider
    
    class CustomProvider(Provider):
        """
        Custom provider for a hypothetical data source.
        
        This demonstrates how easy it is to add new data sources
        by implementing the Provider interface.
        """
        
        def search(self, query: str, **kwargs):
            """Search for datasets (placeholder)."""
            return []
        
        def resolve(self, ref: DatasetRef):
            """Resolve a dataset reference."""
            return {
                'url': f'https://custom.example.com/api/datasets/{ref.id}',
                'format': 'json',
                'provider': self.name,
                'title': ref.metadata.get('title', ref.id),
            }
        
        def fetch(self, ref: DatasetRef, output_dir: str, **kwargs):
            """Fetch a dataset (placeholder)."""
            return {
                'dataset_id': ref.id,
                'provider': self.name,
                'files': [],
            }
    
    # Register the custom provider
    registry = ProviderRegistry()
    registry.register('custom', CustomProvider)
    
    print("\nCreated custom provider")
    print(f"Available providers: {registry.list_providers()}")
    
    # Use the custom provider
    provider = registry.get_provider('custom')
    ref = DatasetRef(
        provider='custom',
        id='my-dataset-123',
        metadata={'title': 'My Custom Dataset'}
    )
    
    metadata = provider.resolve(ref)
    print(f"\nResolved custom dataset:")
    print(f"  URL: {metadata['url']}")
    print(f"  Format: {metadata['format']}")
    print(f"  Title: {metadata['title']}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("Provider Interface Examples")
    print("=" * 80)
    print("\nThis script demonstrates the Provider interface, DatasetRef schema,")
    print("and ProviderRegistry for working with Canadian public datasets.")
    
    example_1_basic_usage()
    example_2_using_registry()
    example_3_multiple_providers()
    example_4_provider_agnostic_code()
    example_5_extending_with_custom_provider()
    
    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)
    print("\nKey takeaways:")
    print("  1. DatasetRef provides a standard way to reference datasets")
    print("  2. Provider interface (search/resolve/fetch) enables consistent access")
    print("  3. ProviderRegistry allows dynamic provider discovery")
    print("  4. Easy to write provider-agnostic code")
    print("  5. Simple to add new data sources by implementing Provider")
    print()


if __name__ == '__main__':
    main()
