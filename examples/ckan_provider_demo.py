"""
Example demonstrating the CKAN provider for searching and downloading data.

This example shows how to use the generic CKAN provider to:
1. Search for datasets in a CKAN portal
2. Resolve dataset resources by format
3. Download specific resources (CSV, JSON, GeoJSON)

The CKAN provider works with any CKAN portal by configuring the base URL.
"""

from publicdata_ca.providers import CKANProvider
from publicdata_ca.provider import DatasetRef


def example_ckan_search():
    """Example: Search for datasets in a CKAN portal."""
    print("=" * 70)
    print("Example 1: Searching for datasets in a CKAN portal")
    print("=" * 70)
    
    # Initialize the CKAN provider with a base URL
    # This example uses Open Canada's data portal
    provider = CKANProvider(
        name='open_canada',
        base_url='https://open.canada.ca/data'
    )
    
    print(f"\nProvider: {provider.name}")
    print(f"Base URL: {provider.base_url}")
    
    # Note: This is a demonstration. Uncomment to run actual searches:
    # 
    # # Search for census-related datasets
    # print("\nSearching for 'census' datasets...")
    # results = provider.search('census', rows=3)
    # 
    # print(f"Found {len(results)} datasets:\n")
    # for ref in results:
    #     print(f"  ID: {ref.id}")
    #     print(f"  Title: {ref.metadata.get('title', 'N/A')}")
    #     print(f"  Formats: {', '.join(ref.metadata.get('formats', []))}")
    #     print(f"  Tags: {', '.join(ref.tags[:3])}...")
    #     print()
    
    print("\nNote: Uncomment the code above to run actual API searches")


def example_ckan_resolve():
    """Example: Resolve dataset resources by format."""
    print("\n" + "=" * 70)
    print("Example 2: Resolving dataset resources by format")
    print("=" * 70)
    
    provider = CKANProvider(base_url='https://open.canada.ca/data')
    
    # Create a dataset reference
    # Note: Replace with an actual dataset ID from your CKAN portal
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


def example_ckan_fetch():
    """Example: Download dataset resources."""
    print("\n" + "=" * 70)
    print("Example 3: Downloading dataset resources")
    print("=" * 70)
    
    provider = CKANProvider(base_url='https://open.canada.ca/data')
    
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
    print(f"Output directory: ./data/ckan")
    
    # Note: This is a demonstration. Uncomment to run actual downloads:
    # 
    # # Download the resources
    # import os
    # os.makedirs('./data/ckan', exist_ok=True)
    # 
    # try:
    #     result = provider.fetch(ref, './data/ckan')
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
    
    provider = CKANProvider(base_url='https://open.canada.ca/data')
    
    # Example formats commonly available in CKAN portals
    formats = ['CSV', 'JSON', 'GeoJSON', 'XLSX']
    
    print("\nSupported formats:")
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
    
    provider = CKANProvider(base_url='https://open.canada.ca/data')
    
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


def example_different_portals():
    """Example: Using CKAN provider with different portals."""
    print("\n" + "=" * 70)
    print("Example 6: Using different CKAN portals")
    print("=" * 70)
    
    # The CKAN provider works with any CKAN portal
    portals = {
        'Open Canada': 'https://open.canada.ca/data',
        'Data.gov (US)': 'https://catalog.data.gov',
        'European Data Portal': 'https://data.europa.eu',
        # Add more CKAN portals as needed
    }
    
    print("\nExample CKAN portals you can use:")
    for name, url in portals.items():
        print(f"\n  {name}:")
        print(f"  provider = CKANProvider(")
        print(f"      name='{name.lower().replace(' ', '_')}',")
        print(f"      base_url='{url}'")
        print(f"  )")
    
    print("\n\nYou can also specify base_url in the DatasetRef params:")
    print("  ref = DatasetRef(..., params={'base_url': 'https://your-ckan.example.com'})")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("CKAN Provider Examples")
    print("=" * 70)
    print("\nThe CKAN provider enables searching and downloading data from")
    print("any CKAN portal. CKAN is an open-source data portal platform")
    print("used by governments and organizations worldwide.")
    
    # Run examples
    example_ckan_search()
    example_ckan_resolve()
    example_ckan_fetch()
    example_multiple_formats()
    example_specific_resource()
    example_different_portals()
    
    print("\n" + "=" * 70)
    print("End of Examples")
    print("=" * 70)
    print("\nTo use these examples with real data:")
    print("1. Uncomment the code blocks marked with comments")
    print("2. Replace 'example-dataset-id' with real dataset IDs from your CKAN portal")
    print("3. Run the script")
    print("\nFor more information, see the documentation at:")
    print("https://github.com/ajharris/publicdata_ca")
    print()


if __name__ == '__main__':
    main()
