"""
SDMX Provider Demo

This script demonstrates how to use the SDMX provider to fetch statistical data
and metadata from SDMX REST API endpoints.

SDMX (Statistical Data and Metadata eXchange) is an ISO standard used by many
statistical organizations worldwide including:
- OECD (Organisation for Economic Co-operation and Development)
- ECB (European Central Bank)
- Eurostat (Statistical Office of the European Union)
- IMF (International Monetary Fund)
- World Bank
- Statistics Canada (some datasets)
- And many others

This demo shows:
1. Creating an SDMX provider instance
2. Fetching metadata about a dataflow
3. Fetching metadata about a data structure definition (DSD)
4. Downloading data series with filters
5. Downloading data in different formats (XML and JSON)
"""

from pathlib import Path
from publicdata_ca.providers import SDMXProvider
from publicdata_ca.provider import DatasetRef


def demo_oecd_quarterly_national_accounts():
    """
    Demo: Fetch OECD Quarterly National Accounts data.
    
    This example fetches GDP data for Australia from the OECD SDMX endpoint.
    """
    print("\n" + "="*80)
    print("Example 1: OECD Quarterly National Accounts")
    print("="*80)
    
    # Create SDMX provider for OECD
    provider = SDMXProvider(
        name='oecd',
        base_url='https://sdmx.oecd.org/public/rest'
    )
    
    print(f"\nProvider: {provider.name}")
    print(f"Base URL: {provider.base_url}")
    
    # 1. Get dataflow metadata
    print("\n--- Step 1: Retrieve dataflow metadata ---")
    ref = DatasetRef(
        provider='oecd',
        id='OECD,QNA,1.0',
        params={}
    )
    
    try:
        metadata = provider.resolve(ref)
        print(f"Dataflow ID: {metadata['dataflow_id']}")
        print(f"Dataflow metadata:")
        if 'name' in metadata['dataflow_metadata']:
            names = metadata['dataflow_metadata']['name']
            for lang, name in names.items():
                print(f"  {lang}: {name}")
    except Exception as e:
        print(f"Note: Could not fetch metadata (this is a demo without network access): {e}")
    
    # 2. Fetch data with filters (Australia GDP, 2020-2023)
    print("\n--- Step 2: Download data series ---")
    output_dir = Path('./data/sdmx_demo')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ref = DatasetRef(
        provider='oecd',
        id='OECD,QNA,1.0',
        params={
            'key': 'AUS.GDP...',  # Australia, GDP indicator
            'start_period': '2020-Q1',
            'end_period': '2023-Q4',
            'format': 'sdmx-ml'  # SDMX-ML (XML) format
        }
    )
    
    print(f"Fetching data for: {ref.id}")
    print(f"Filter: Australia GDP, 2020-Q1 to 2023-Q4")
    print(f"Output directory: {output_dir}")
    
    try:
        result = provider.fetch(ref, str(output_dir))
        print(f"\nSuccess!")
        print(f"Downloaded to: {result['files'][0]}")
        print(f"Format: {result['format']}")
        print(f"Download URL: {result['download_url']}")
    except Exception as e:
        print(f"Note: Demo mode - would download from: {e}")


def demo_ecb_exchange_rates():
    """
    Demo: Fetch ECB Exchange Rates data.
    
    This example shows fetching exchange rate data from the European Central Bank.
    """
    print("\n" + "="*80)
    print("Example 2: ECB Exchange Rates")
    print("="*80)
    
    # Create SDMX provider for ECB
    provider = SDMXProvider(
        name='ecb',
        base_url='https://sdmx.ecb.europa.eu/service'
    )
    
    print(f"\nProvider: {provider.name}")
    print(f"Base URL: {provider.base_url}")
    
    # Fetch EUR/USD exchange rates
    output_dir = Path('./data/sdmx_demo')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ref = DatasetRef(
        provider='ecb',
        id='ECB,EXR,1.0',  # Exchange Rates dataflow
        params={
            'key': 'D.USD.EUR.SP00.A',  # Daily USD/EUR spot rate
            'start_period': '2023-01-01',
            'end_period': '2023-12-31',
            'format': 'sdmx-json'  # JSON format
        }
    )
    
    print(f"\nFetching data for: {ref.id}")
    print(f"Filter: Daily EUR/USD rates for 2023")
    print(f"Format: SDMX-JSON")
    
    try:
        result = provider.fetch(ref, str(output_dir))
        print(f"\nSuccess!")
        print(f"Downloaded to: {result['files'][0]}")
    except Exception as e:
        print(f"Note: Demo mode - would download from ECB")


def demo_metadata_retrieval():
    """
    Demo: Retrieve detailed metadata about data structures.
    
    This example shows how to get comprehensive metadata including
    dimensions, attributes, and measures.
    """
    print("\n" + "="*80)
    print("Example 3: Metadata Retrieval (Data Structure Definition)")
    print("="*80)
    
    provider = SDMXProvider(
        name='oecd',
        base_url='https://sdmx.oecd.org/public/rest'
    )
    
    # Fetch dataflow metadata with DSD included
    ref = DatasetRef(
        provider='oecd',
        id='OECD,QNA,1.0',
        params={
            'include_dsd': True  # Include Data Structure Definition
        }
    )
    
    print(f"\nRetrieving metadata for: {ref.id}")
    print("Including: Data Structure Definition (DSD)")
    
    try:
        metadata = provider.resolve(ref)
        
        print("\nDataflow Information:")
        print(f"  ID: {metadata['dataflow_metadata']['id']}")
        print(f"  Agency: {metadata['dataflow_metadata']['agency_id']}")
        
        if 'dsd_metadata' in metadata:
            dsd = metadata['dsd_metadata']
            print(f"\nData Structure Definition:")
            print(f"  Dimensions: {len(dsd['dimensions'])}")
            for dim in dsd['dimensions'][:3]:  # Show first 3
                print(f"    - {dim['id']}: {dim.get('name', {}).get('en', 'N/A')}")
            
            print(f"  Attributes: {len(dsd['attributes'])}")
            for attr in dsd['attributes'][:3]:  # Show first 3
                print(f"    - {attr['id']}: {attr.get('name', {}).get('en', 'N/A')}")
            
            print(f"  Measures: {len(dsd['measures'])}")
            for measure in dsd['measures']:
                print(f"    - {measure['id']}: {measure.get('name', {}).get('en', 'N/A')}")
    except Exception as e:
        print(f"Note: Demo mode - would fetch detailed metadata")


def demo_different_formats():
    """
    Demo: Download data in different formats (XML vs JSON).
    
    SDMX supports multiple formats. This example shows how to request
    data in different formats.
    """
    print("\n" + "="*80)
    print("Example 4: Different Data Formats")
    print("="*80)
    
    provider = SDMXProvider(
        name='oecd',
        base_url='https://sdmx.oecd.org/public/rest'
    )
    
    output_dir = Path('./data/sdmx_demo')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download in SDMX-ML (XML) format
    print("\n--- Format 1: SDMX-ML (XML) ---")
    ref_xml = DatasetRef(
        provider='oecd',
        id='OECD,MEI,1.0',  # Main Economic Indicators
        params={
            'key': 'CAN.PRINTO01.IXOB.M',
            'start_period': '2023-01',
            'format': 'sdmx-ml'
        }
    )
    
    print(f"Format: SDMX-ML (XML)")
    print(f"File extension: .xml")
    print("Use case: Maximum compatibility, standard SDMX format")
    
    # Download in SDMX-JSON format
    print("\n--- Format 2: SDMX-JSON ---")
    ref_json = DatasetRef(
        provider='oecd',
        id='OECD,MEI,1.0',
        params={
            'key': 'CAN.PRINTO01.IXOB.M',
            'start_period': '2023-01',
            'format': 'sdmx-json'
        }
    )
    
    print(f"Format: SDMX-JSON")
    print(f"File extension: .json")
    print("Use case: Easier parsing in JavaScript/Python, smaller file size")


def demo_advanced_filters():
    """
    Demo: Advanced filtering and query options.
    
    This example shows various SDMX query parameters for filtering
    and customizing the data response.
    """
    print("\n" + "="*80)
    print("Example 5: Advanced Filtering")
    print("="*80)
    
    provider = SDMXProvider(
        name='oecd',
        base_url='https://sdmx.oecd.org/public/rest'
    )
    
    output_dir = Path('./data/sdmx_demo')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Example with multiple filters
    ref = DatasetRef(
        provider='oecd',
        id='OECD,QNA,1.0',
        params={
            'key': 'AUS+CAN+USA.GDP...',  # Multiple countries (Australia, Canada, USA)
            'start_period': '2020-Q1',
            'end_period': '2023-Q4',
            'format': 'sdmx-json',
            'dimensionAtObservation': 'AllDimensions',  # Flat structure
            'detail': 'Full'  # Include all attributes
        }
    )
    
    print("\nAdvanced query parameters:")
    print(f"  Countries: Australia, Canada, USA")
    print(f"  Indicator: GDP")
    print(f"  Time range: 2020-Q1 to 2023-Q4")
    print(f"  Dimension structure: AllDimensions (flat)")
    print(f"  Detail level: Full (all attributes)")
    print(f"\nKey pattern: AUS+CAN+USA.GDP...")
    print("  - '+' means OR (multiple values)")
    print("  - '.' separates dimensions")
    print("  - '...' means all values for remaining dimensions")


def main():
    """Run all demo examples."""
    print("\n" + "="*80)
    print("SDMX Provider Demo")
    print("="*80)
    print("\nThis demo shows how to use the SDMX provider to fetch statistical data")
    print("from SDMX REST API endpoints used by international organizations.")
    print("\nNote: This is a demonstration of the API. Actual data downloads require")
    print("network access to the respective SDMX endpoints.")
    
    # Run all examples
    demo_oecd_quarterly_national_accounts()
    demo_ecb_exchange_rates()
    demo_metadata_retrieval()
    demo_different_formats()
    demo_advanced_filters()
    
    print("\n" + "="*80)
    print("Demo completed!")
    print("="*80)
    print("\nKey takeaways:")
    print("1. SDMX provider works with any SDMX REST API endpoint")
    print("2. Supports both metadata retrieval and data download")
    print("3. Flexible filtering with data keys and time ranges")
    print("4. Multiple formats: SDMX-ML (XML) and SDMX-JSON")
    print("5. Advanced query options for customizing responses")
    print("\nFor more information:")
    print("- SDMX website: https://sdmx.org")
    print("- OECD SDMX: https://data.oecd.org/api/sdmx-json-documentation/")
    print("- ECB SDMX: https://sdmx.ecb.europa.eu/")


if __name__ == '__main__':
    main()
