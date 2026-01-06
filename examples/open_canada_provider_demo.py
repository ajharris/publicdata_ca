"""
Example demonstrating the Open Canada provider for searching and downloading data.

This example shows how to use the OpenCanadaProvider to:
1. Search for datasets in the Open Government Canada portal
2. Resolve dataset resources by format
3. Download specific resources (CSV, JSON, GeoJSON)

The Open Canada portal (open.canada.ca) is CKAN-backed, so this provider
is a thin wrapper around the generic CKAN provider with pre-configured URLs.
"""

from publicdata_ca.providers import OpenCanadaProvider
from publicdata_ca.provider import DatasetRef


def example_open_canada_search():
    """Example: Search for datasets in the Open Canada portal."""
    print("=" * 70)
    print("Example 1: Searching for datasets in Open Canada portal")
    print("=" * 70)
    
    # Initialize the Open Canada provider
    # No need to specify base_url - it's pre-configured
    provider = OpenCanadaProvider()
    
    print(f"\nProvider: {provider.name}")
    print(f"Base URL: {provider.base_url}")
    
    # Note: This is a demonstration. Uncomment to run actual searches:
    # 
    # # Search for housing-related datasets
    # print("\nSearching for 'housing' datasets...")
    # results = provider.search('housing', rows=3)
    # 
    # print(f"Found {len(results)} datasets:\n")
    # for ref in results:
    #     print(f"  ID: {ref.id}")
    #     print(f"  Title: {ref.metadata.get('title', 'N/A')}")
    #     print(f"  Organization: {ref.metadata.get('organization', 'N/A')}")
    #     print(f"  Formats: {', '.join(ref.metadata.get('formats', []))}")
    #     print(f"  Tags: {', '.join(ref.tags[:3])}...")
    #     print()
    
    print("\nNote: Uncomment the code above to run actual API searches")


def example_open_canada_resolve():
    """Example: Resolve dataset resources by format."""
    print("\n" + "=" * 70)
    print("Example 2: Resolving dataset resources by format")
    print("=" * 70)
    
    provider = OpenCanadaProvider()
    
    # Create a dataset reference
    # Note: Replace with an actual dataset ID from Open Canada
    ref = DatasetRef(
        provider='open_canada',
        id='example-dataset-id',
        params={'format': 'CSV'}  # Filter for CSV resources only
    )
    
    print(f"\nDataset: {ref.id}")
    print(f"Format filter: {ref.params.get('format', 'None')}")
    
    # Note: This is a demonstration. Uncomment to run actual resolution:
    # 
    # # Resolve the dataset to get resource metadata
    # try:
    #     metadata = provider.resolve(ref)
    #     print(f"\nFound {len(metadata['resources'])} CSV resources:")
    #     for resource in metadata['resources']:
    #         print(f"  - {resource['name']}")
    #         print(f"    URL: {resource['url']}")
    #         print(f"    Format: {resource['format']}")
    #         print()
    # except Exception as e:
    #     print(f"\nError: {e}")
    
    print("\nNote: Uncomment the code above and use a real dataset ID")


def example_open_canada_fetch():
    """Example: Download dataset resources."""
    print("\n" + "=" * 70)
    print("Example 3: Downloading dataset resources")
    print("=" * 70)
    
    provider = OpenCanadaProvider()
    
    # Create a dataset reference with format filter
    ref = DatasetRef(
        provider='open_canada',
        id='example-dataset-id',
        params={
            'format': 'CSV'  # Download CSV resources only
        }
    )
    
    print(f"\nDataset: {ref.id}")
    print(f"Format filter: CSV")
    print(f"Output directory: ./data/open_canada")
    
    # Note: This is a demonstration. Uncomment to run actual downloads:
    # 
    # # Download the resources
    # import os
    # os.makedirs('./data/open_canada', exist_ok=True)
    # 
    # try:
    #     result = provider.fetch(ref, './data/open_canada')
    #     print(f"\nDownloaded {len(result['files'])} files:")
    #     for file_path in result['files']:
    #         print(f"  - {file_path}")
    # except Exception as e:
    #     print(f"\nError: {e}")
    
    print("\nNote: Uncomment the code above and use a real dataset ID")


def example_multiple_formats():
    """Example: Working with multiple resource formats."""
    print("\n" + "=" * 70)
    print("Example 4: Working with multiple resource formats")
    print("=" * 70)
    
    provider = OpenCanadaProvider()
    
    # Example formats commonly available in Open Canada
    formats = ['CSV', 'JSON', 'GeoJSON', 'XLSX', 'XML']
    
    print("\nSupported formats in Open Canada:")
    for fmt in formats:
        print(f"  - {fmt}")
    
    print("\nTo download a specific format, use params:")
    print("  ref = DatasetRef(..., params={'format': 'GeoJSON'})")
    
    print("\nTo download all formats, omit the format parameter:")
    print("  ref = DatasetRef(..., params={})")


def example_specific_resource():
    """Example: Download a specific resource by ID."""
    print("\n" + "=" * 70)
    print("Example 5: Downloading a specific resource by ID")
    print("=" * 70)
    
    provider = OpenCanadaProvider()
    
    # If you know the specific resource ID, you can download just that one
    ref = DatasetRef(
        provider='open_canada',
        id='example-dataset-id',
        params={
            'resource_id': 'abc123-resource-id'  # Specific resource ID
        }
    )
    
    print(f"\nDataset: {ref.id}")
    print(f"Resource ID: {ref.params.get('resource_id')}")
    print("\nThis will download only the specified resource,")
    print("ignoring all other resources in the dataset.")


def example_open_canada_vs_ckan():
    """Example: Difference between OpenCanadaProvider and generic CKANProvider."""
    print("\n" + "=" * 70)
    print("Example 6: OpenCanadaProvider vs Generic CKANProvider")
    print("=" * 70)
    
    print("\nOpenCanadaProvider is a convenience wrapper around CKANProvider")
    print("that pre-configures the Open Canada portal URL.")
    
    print("\nUsing OpenCanadaProvider (simpler):")
    print("  provider = OpenCanadaProvider()")
    print("  results = provider.search('housing')")
    
    print("\nUsing generic CKANProvider (requires base_url):")
    print("  from publicdata_ca.providers import CKANProvider")
    print("  provider = CKANProvider(")
    print("      name='open_canada',")
    print("      base_url='https://open.canada.ca/data'")
    print("  )")
    print("  results = provider.search('housing')")
    
    print("\nBoth approaches work identically - OpenCanadaProvider just saves")
    print("you from having to remember and type the base URL.")


def example_search_tips():
    """Example: Tips for effective searching in Open Canada."""
    print("\n" + "=" * 70)
    print("Example 7: Tips for searching Open Canada datasets")
    print("=" * 70)
    
    print("\nSearch tips:")
    print("  1. Use specific keywords: 'census population' is better than 'data'")
    print("  2. Search in English or French depending on dataset language")
    print("  3. Use pagination for large result sets (rows and start params)")
    print("  4. Filter by organization using SOLR syntax: 'organization:statcan'")
    print("  5. Search by tags: 'tags:environment' or 'tags:health'")
    
    print("\nExample searches:")
    print("  provider.search('census', rows=10)")
    print("  provider.search('environment AND climate', rows=5)")
    print("  provider.search('organization:statcan', rows=20)")
    print("  provider.search('tags:finance', rows=15)")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Open Canada Provider Examples")
    print("=" * 70)
    print("\nThe Open Canada provider enables searching and downloading data from")
    print("the Open Government Canada portal (open.canada.ca). It's a thin wrapper")
    print("around the generic CKAN provider with pre-configured URLs.")
    
    # Run examples
    example_open_canada_search()
    example_open_canada_resolve()
    example_open_canada_fetch()
    example_multiple_formats()
    example_specific_resource()
    example_open_canada_vs_ckan()
    example_search_tips()
    
    print("\n" + "=" * 70)
    print("End of Examples")
    print("=" * 70)
    print("\nTo use these examples with real data:")
    print("1. Uncomment the code blocks marked with comments")
    print("2. Replace 'example-dataset-id' with real dataset IDs from Open Canada")
    print("3. Run the script")
    print("\nYou can browse datasets at:")
    print("https://open.canada.ca/en/open-data")
    print("\nFor more information, see the documentation at:")
    print("https://github.com/ajharris/publicdata_ca")
    print()


if __name__ == '__main__':
    main()
