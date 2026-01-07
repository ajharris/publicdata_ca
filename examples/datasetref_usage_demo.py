"""
Example demonstrating two ways to use DatasetRef with providers.

This example shows:
1. Using the convenience function fetch_dataset()
2. Using provider instances directly
3. Using the global registry to get providers

Both approaches work equally well - choose based on your use case.
"""

from publicdata_ca import (
    DatasetRef,
    fetch_dataset,
    get_registry,
    OpenCanadaProvider,
)


def example_1_convenience_function():
    """
    Example 1: Using the fetch_dataset() convenience function.
    
    This is the simplest way to fetch datasets - just create a DatasetRef
    and call fetch_dataset(). The function automatically resolves the
    provider from the global registry.
    """
    print("=" * 70)
    print("Example 1: Using fetch_dataset() convenience function")
    print("=" * 70)
    
    # Create a dataset reference
    ref = DatasetRef(
        provider='open_canada',
        id='example-dataset-id',
        params={'format': 'CSV'}
    )
    
    print(f"\nDataset: {ref.canonical_id}")
    print(f"Format filter: {ref.params.get('format')}")
    
    # Note: Uncomment to run actual download:
    # result = fetch_dataset(ref, './data/open_canada')
    # print(f"\nDownloaded {len(result['files'])} files:")
    # for file_path in result['files']:
    #     print(f"  - {file_path}")
    
    print("\nNote: Uncomment the code above to run actual downloads")
    print("\nAdvantages:")
    print("  - Simplest approach - no need to create provider instances")
    print("  - Provider is automatically resolved from the DatasetRef")
    print("  - Works with all registered providers")


def example_2_provider_instance():
    """
    Example 2: Using a provider instance directly.
    
    Create a provider instance and call its fetch() method. This gives
    you more control and is useful when you need to fetch multiple
    datasets from the same provider.
    """
    print("\n" + "=" * 70)
    print("Example 2: Using a provider instance directly")
    print("=" * 70)
    
    # Create a provider instance
    provider = OpenCanadaProvider()
    
    print(f"\nProvider: {provider.name}")
    print(f"Base URL: {provider.base_url}")
    
    # Create a dataset reference
    ref = DatasetRef(
        provider='open_canada',
        id='example-dataset-id',
        params={'format': 'CSV'}
    )
    
    # Note: Uncomment to run actual download:
    # result = provider.fetch(ref, './data/open_canada')
    # print(f"\nDownloaded {len(result['files'])} files:")
    # for file_path in result['files']:
    #     print(f"  - {file_path}")
    
    print("\nNote: Uncomment the code above to run actual downloads")
    print("\nAdvantages:")
    print("  - More control over provider configuration")
    print("  - Efficient when fetching multiple datasets from same provider")
    print("  - Can customize provider settings (e.g., base_url for CKAN)")


def example_3_using_registry():
    """
    Example 3: Using the global registry to get providers.
    
    The global registry has common providers pre-registered. You can
    get a provider from the registry and use it to fetch datasets.
    """
    print("\n" + "=" * 70)
    print("Example 3: Using the global registry")
    print("=" * 70)
    
    # Get the global registry
    registry = get_registry()
    
    # List available providers
    providers = registry.list_providers()
    print(f"\nAvailable providers: {', '.join(sorted(providers))}")
    
    # Get a specific provider
    provider = registry.get_provider('open_canada')
    print(f"\nGot provider: {provider.name}")
    print(f"Provider class: {type(provider).__name__}")
    
    # Create a dataset reference and fetch
    ref = DatasetRef(
        provider='open_canada',
        id='example-dataset-id',
        params={'format': 'CSV'}
    )
    
    # Note: Uncomment to run actual download:
    # result = provider.fetch(ref, './data/open_canada')
    # print(f"\nDownloaded {len(result['files'])} files")
    
    print("\nNote: Uncomment the code above to run actual downloads")
    print("\nAdvantages:")
    print("  - Useful for dynamic provider selection")
    print("  - Can add custom providers to the registry")
    print("  - Good for building provider-agnostic tools")


def example_4_comparison():
    """
    Example 4: Comparison of all three approaches.
    
    Shows when to use each approach.
    """
    print("\n" + "=" * 70)
    print("Example 4: When to use each approach")
    print("=" * 70)
    
    print("\n1. Use fetch_dataset() when:")
    print("   - You have a DatasetRef and just want to download it")
    print("   - You're working with datasets from different providers")
    print("   - You want the simplest possible code")
    
    print("\n2. Use provider instance when:")
    print("   - You're downloading multiple datasets from the same provider")
    print("   - You need to customize provider settings")
    print("   - You want to use search() or resolve() methods")
    
    print("\n3. Use registry when:")
    print("   - You're building provider-agnostic tools")
    print("   - You need to dynamically select providers at runtime")
    print("   - You want to register custom providers")


def example_5_complete_workflow():
    """
    Example 5: Complete workflow - search, resolve, and fetch.
    
    Shows a typical workflow using the provider interface.
    """
    print("\n" + "=" * 70)
    print("Example 5: Complete workflow")
    print("=" * 70)
    
    # Step 1: Create a provider
    provider = OpenCanadaProvider()
    print(f"\nStep 1: Created {provider.name} provider")
    
    # Step 2: Search for datasets (commented out - requires network)
    # results = provider.search('housing', rows=5)
    # print(f"\nStep 2: Found {len(results)} datasets")
    # for ref in results[:3]:
    #     print(f"  - {ref.id}: {ref.metadata.get('title')}")
    
    # Step 3: Create a reference to a specific dataset
    ref = DatasetRef(
        provider='open_canada',
        id='example-dataset-id',
        params={'format': 'CSV'}
    )
    print(f"\nStep 3: Created reference: {ref.canonical_id}")
    
    # Step 4: Resolve to see available resources (commented out)
    # metadata = provider.resolve(ref)
    # print(f"\nStep 4: Found {len(metadata['resources'])} CSV resources")
    
    # Step 5: Fetch the dataset (commented out)
    # result = provider.fetch(ref, './data/open_canada')
    # print(f"\nStep 5: Downloaded {len(result['files'])} files")
    
    print("\nNote: Uncomment steps 2, 4, and 5 to run with real data")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("DatasetRef and Provider Usage Examples")
    print("=" * 70)
    print("\nThese examples show different ways to use DatasetRef with providers.")
    print("All three approaches work equally well - choose based on your needs.")
    
    # Run examples
    example_1_convenience_function()
    example_2_provider_instance()
    example_3_using_registry()
    example_4_comparison()
    example_5_complete_workflow()
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("\nKey improvements in this release:")
    print("  1. All providers exported from top-level package")
    print("  2. New fetch_dataset() convenience function")
    print("  3. Common providers auto-registered in global registry")
    print("\nFor more information, see the documentation at:")
    print("https://github.com/ajharris/publicdata_ca")
    print()


if __name__ == '__main__':
    main()
