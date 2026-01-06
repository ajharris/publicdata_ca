"""
Demonstration of the Socrata provider for accessing open data portals.

This script shows how to use the SocrataProvider to search, discover, and download
datasets from any Socrata-powered open data portal. Socrata (SODA API) is used by
many governments worldwide for their open data platforms.

Examples include:
- Seattle: https://data.seattle.gov
- San Francisco: https://data.sfgov.org
- NYC Open Data: https://data.cityofnewyork.us
- Chicago Data Portal: https://data.cityofchicago.org
- Many others worldwide

This demo uses mock data to avoid making real API calls during testing.
"""

from publicdata_ca.providers.socrata import SocrataProvider
from publicdata_ca.provider import DatasetRef


def demo_basic_search():
    """Demonstrate basic dataset search in a Socrata portal."""
    print("=" * 80)
    print("1. Basic Dataset Search")
    print("=" * 80)
    
    # Initialize provider with a Socrata portal
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    print(f"\nSearching Seattle Open Data for 'police' datasets...")
    print("(This would normally make an API call to data.seattle.gov)")
    
    # In a real scenario, this would return actual datasets
    # results = provider.search('police', limit=5)
    # 
    # print(f"\nFound {len(results)} datasets:")
    # for ref in results:
    #     print(f"\n  ID: {ref.id}")
    #     print(f"  Name: {ref.metadata.get('name', 'N/A')}")
    #     print(f"  Description: {ref.metadata.get('description', 'N/A')[:100]}...")
    #     print(f"  Tags: {', '.join(ref.tags[:5])}")
    
    print("\nExample output would show datasets like:")
    print("  - Seattle Police 911 Calls (abcd-1234)")
    print("  - Crime Statistics (wxyz-5678)")
    print("  - Police Reports Archive (efgh-9012)")


def demo_search_with_filters():
    """Demonstrate searching with additional filters."""
    print("\n" + "=" * 80)
    print("2. Search with Filters")
    print("=" * 80)
    
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    print("\nSearching with pagination and category filters...")
    print("(limit=10, offset=0, categories=['Public Safety'])")
    
    # In a real scenario:
    # results = provider.search(
    #     'crime',
    #     limit=10,
    #     offset=0,
    #     categories=['Public Safety']
    # )
    
    print("\nThis would return up to 10 Public Safety datasets starting from offset 0")


def demo_column_selection():
    """Demonstrate downloading with column selection."""
    print("\n" + "=" * 80)
    print("3. Download with Column Selection (SoQL $select)")
    print("=" * 80)
    
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    # Create a dataset reference with column selection
    ref = DatasetRef(
        provider='seattle',
        id='abcd-1234',  # Example dataset ID
        params={
            'format': 'csv',
            'select': 'call_date, offense_type, count',  # Only these columns
        }
    )
    
    print("\nDataset Reference:")
    print(f"  Provider: {ref.provider}")
    print(f"  Dataset ID: {ref.id}")
    print(f"  Format: {ref.params['format']}")
    print(f"  Columns: {ref.params['select']}")
    
    print("\nIn a real scenario, this would download only the selected columns:")
    # result = provider.fetch(ref, './data/seattle')
    # print(f"Downloaded to: {result['files'][0]}")
    
    print("  Example URL: https://data.seattle.gov/resource/abcd-1234.csv?$select=call_date,offense_type,count")


def demo_where_filters():
    """Demonstrate downloading with WHERE clause filters."""
    print("\n" + "=" * 80)
    print("4. Download with WHERE Filters (SoQL $where)")
    print("=" * 80)
    
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    # Create a dataset reference with WHERE filter
    ref = DatasetRef(
        provider='seattle',
        id='abcd-1234',
        params={
            'format': 'csv',
            'where': 'count > 10 AND offense_type = "THEFT"',  # Filter condition
        }
    )
    
    print("\nDataset Reference:")
    print(f"  Provider: {ref.provider}")
    print(f"  Dataset ID: {ref.id}")
    print(f"  Format: {ref.params['format']}")
    print(f"  Filter: {ref.params['where']}")
    
    print("\nIn a real scenario, this would download only rows matching the filter:")
    # result = provider.fetch(ref, './data/seattle')
    # print(f"Downloaded filtered data to: {result['files'][0]}")
    
    print("  Example URL: https://data.seattle.gov/resource/abcd-1234.csv?$where=count>10 AND offense_type='THEFT'")


def demo_paging():
    """Demonstrate downloading with paging (limit and offset)."""
    print("\n" + "=" * 80)
    print("5. Download with Paging ($limit and $offset)")
    print("=" * 80)
    
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    # Create a dataset reference with paging
    ref = DatasetRef(
        provider='seattle',
        id='abcd-1234',
        params={
            'format': 'csv',
            'limit': 1000,   # Get 1000 rows
            'offset': 500,   # Starting from row 500
        }
    )
    
    print("\nDataset Reference:")
    print(f"  Provider: {ref.provider}")
    print(f"  Dataset ID: {ref.id}")
    print(f"  Format: {ref.params['format']}")
    print(f"  Limit: {ref.params['limit']}")
    print(f"  Offset: {ref.params['offset']}")
    
    print("\nIn a real scenario, this would download rows 500-1500:")
    # result = provider.fetch(ref, './data/seattle')
    # print(f"Downloaded page to: {result['files'][0]}")
    
    print("  Example URL: https://data.seattle.gov/resource/abcd-1234.csv?$limit=1000&$offset=500")
    print("\nUseful for:")
    print("  - Processing large datasets in chunks")
    print("  - Parallel downloads of different pages")
    print("  - Incremental data updates")


def demo_combined_filters():
    """Demonstrate combining all filter types."""
    print("\n" + "=" * 80)
    print("6. Combined Filters (SELECT + WHERE + LIMIT)")
    print("=" * 80)
    
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    # Create a dataset reference with all filter types
    ref = DatasetRef(
        provider='seattle',
        id='abcd-1234',
        params={
            'format': 'csv',
            'select': 'call_date, offense_type, count',
            'where': 'count > 10',
            'limit': 500,
            'offset': 0,
        }
    )
    
    print("\nDataset Reference with Combined Filters:")
    print(f"  Provider: {ref.provider}")
    print(f"  Dataset ID: {ref.id}")
    print(f"  Format: {ref.params['format']}")
    print(f"  Select: {ref.params['select']}")
    print(f"  Where: {ref.params['where']}")
    print(f"  Limit: {ref.params['limit']}")
    print(f"  Offset: {ref.params['offset']}")
    
    print("\nIn a real scenario, this would download:")
    # result = provider.fetch(ref, './data/seattle')
    # print(f"Downloaded to: {result['files'][0]}")
    
    print("  - Only columns: call_date, offense_type, count")
    print("  - Only rows where: count > 10")
    print("  - Maximum 500 rows")
    print("  - Starting from row 0")
    
    print("\n  Example URL:")
    print("    https://data.seattle.gov/resource/abcd-1234.csv")
    print("      ?$select=call_date,offense_type,count")
    print("      &$where=count>10")
    print("      &$limit=500")
    print("      &$offset=0")


def demo_json_export():
    """Demonstrate JSON export format."""
    print("\n" + "=" * 80)
    print("7. JSON Export Format")
    print("=" * 80)
    
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    # Create a dataset reference with JSON format
    ref = DatasetRef(
        provider='seattle',
        id='abcd-1234',
        params={
            'format': 'json',  # JSON instead of CSV
            'limit': 100,
        }
    )
    
    print("\nDataset Reference:")
    print(f"  Provider: {ref.provider}")
    print(f"  Dataset ID: {ref.id}")
    print(f"  Format: {ref.params['format']}")
    print(f"  Limit: {ref.params['limit']}")
    
    print("\nIn a real scenario, this would download in JSON format:")
    # result = provider.fetch(ref, './data/seattle')
    # print(f"Downloaded to: {result['files'][0]}")
    
    print("  Example URL: https://data.seattle.gov/resource/abcd-1234.json?$limit=100")
    print("\nJSON format is useful for:")
    print("  - Nested data structures")
    print("  - Direct import into JavaScript/Python")
    print("  - API integrations")


def demo_multiple_portals():
    """Demonstrate working with multiple Socrata portals."""
    print("\n" + "=" * 80)
    print("8. Working with Multiple Socrata Portals")
    print("=" * 80)
    
    # Different Socrata portals
    portals = {
        'Seattle': 'https://data.seattle.gov',
        'San Francisco': 'https://data.sfgov.org',
        'NYC': 'https://data.cityofnewyork.us',
        'Chicago': 'https://data.cityofchicago.org',
    }
    
    print("\nYou can use the same provider with different portals:")
    
    for city, url in portals.items():
        provider = SocrataProvider(
            name=city.lower().replace(' ', '_'),
            base_url=url
        )
        print(f"\n  {city}:")
        print(f"    Provider: {provider.name}")
        print(f"    Base URL: {provider.base_url}")
        # In a real scenario, you would search each portal
        # results = provider.search('crime', limit=5)
        # print(f"    Datasets found: {len(results)}")
    
    print("\nOr use base_url in DatasetRef params:")
    ref = DatasetRef(
        provider='socrata',
        id='abcd-1234',
        params={
            'base_url': 'https://data.seattle.gov',
            'format': 'csv'
        }
    )
    print(f"\n  Provider: {ref.provider}")
    print(f"  Base URL: {ref.params['base_url']}")


def demo_metadata_discovery():
    """Demonstrate metadata discovery."""
    print("\n" + "=" * 80)
    print("9. Metadata Discovery")
    print("=" * 80)
    
    provider = SocrataProvider(
        name='seattle',
        base_url='https://data.seattle.gov'
    )
    
    ref = DatasetRef(
        provider='seattle',
        id='abcd-1234'
    )
    
    print("\nResolving dataset metadata...")
    print("(This would normally call the Socrata metadata API)")
    
    # In a real scenario:
    # metadata = provider.resolve(ref)
    # print(f"\nDataset: {metadata['name']}")
    # print(f"Description: {metadata['description'][:100]}...")
    # print(f"\nColumns ({len(metadata['columns'])}):")
    # for col in metadata['columns'][:5]:
    #     print(f"  - {col['name']}: {col['dataTypeName']}")
    #     print(f"    {col.get('description', 'No description')}")
    
    print("\nExample metadata output:")
    print("  Dataset: Seattle Police 911 Calls")
    print("  Description: All police 911 calls in Seattle...")
    print("  Columns (3):")
    print("    - call_date: calendar_date")
    print("      Date of the call")
    print("    - offense_type: text")
    print("      Type of offense")
    print("    - count: number")
    print("      Number of incidents")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print("SOCRATA PROVIDER DEMONSTRATION")
    print("=" * 80)
    print("\nThis script demonstrates the capabilities of the Socrata provider")
    print("for accessing open data from Socrata-powered portals.")
    print("\nNote: This demo uses mock data to avoid making real API calls.")
    
    # Run all demos
    demo_basic_search()
    demo_search_with_filters()
    demo_column_selection()
    demo_where_filters()
    demo_paging()
    demo_combined_filters()
    demo_json_export()
    demo_multiple_portals()
    demo_metadata_discovery()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nThe Socrata provider supports:")
    print("  ✓ Dataset discovery via catalog search")
    print("  ✓ Column selection via SoQL $select parameter")
    print("  ✓ Row filtering via SoQL $where parameter")
    print("  ✓ Paging via $limit and $offset parameters")
    print("  ✓ Export to CSV and JSON formats")
    print("  ✓ Multiple Socrata portals via configurable base URL")
    print("\nFor more information on SoQL syntax:")
    print("  https://dev.socrata.com/docs/queries/")
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
