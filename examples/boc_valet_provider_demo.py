"""
Example demonstrating the Bank of Canada Valet API provider.

This example shows how to use the Valet provider to:
1. Fetch time series data with date ranges
2. Get series metadata
3. Download series to CSV with provenance
4. Use the Provider interface for standardized access

The Bank of Canada Valet API provides access to economic and financial data
including exchange rates, interest rates, and other key economic indicators.

API Documentation: https://www.bankofcanada.ca/valet/docs
"""

from publicdata_ca.providers import ValetProvider, fetch_valet_series, download_valet_series
from publicdata_ca.provider import DatasetRef


def example_fetch_series():
    """Example: Fetch time series data from Bank of Canada Valet API."""
    print("=" * 70)
    print("Example 1: Fetching time series data")
    print("=" * 70)
    
    print("\nFetching USD/CAD exchange rate data...")
    
    # Note: This is a demonstration. Uncomment to fetch actual data:
    # 
    # # Fetch exchange rate data for a specific date range
    # data = fetch_valet_series(
    #     series_name='FXUSDCAD',
    #     start_date='2023-01-01',
    #     end_date='2023-01-31'
    # )
    # 
    # print(f"\nSeries: {data['series_name']}")
    # print(f"Observations: {len(data['observations'])}")
    # print(f"URL: {data['url']}")
    # 
    # # Display series metadata
    # if data['metadata']:
    #     metadata = data['metadata']
    #     print(f"\nMetadata:")
    #     print(f"  Label: {metadata.get('label', 'N/A')}")
    #     print(f"  Type: {metadata.get('type', 'N/A')}")
    # 
    # # Display first few observations
    # print(f"\nFirst 5 observations:")
    # for obs in data['observations'][:5]:
    #     print(f"  {obs['d']}: {obs['v']}")
    
    print("\nNote: Uncomment the code above to fetch actual data from the API")


def example_download_series():
    """Example: Download series to CSV file."""
    print("\n" + "=" * 70)
    print("Example 2: Downloading series to CSV")
    print("=" * 70)
    
    print("\nDownloading USD/CAD exchange rate to CSV...")
    
    # Note: This is a demonstration. Uncomment to download actual data:
    # 
    # import tempfile
    # import pandas as pd
    # 
    # # Download to temporary directory
    # with tempfile.TemporaryDirectory() as tmpdir:
    #     result = download_valet_series(
    #         series_name='FXUSDCAD',
    #         output_dir=tmpdir,
    #         start_date='2023-01-01',
    #         end_date='2023-12-31',
    #         skip_existing=False
    #     )
    #     
    #     print(f"\nDownload result:")
    #     print(f"  Provider: {result['provider']}")
    #     print(f"  Series: {result['series_name']}")
    #     print(f"  Observations: {result['observations']}")
    #     print(f"  Files: {result['files']}")
    #     
    #     # Read and display the CSV
    #     csv_file = result['files'][0]
    #     df = pd.read_csv(csv_file)
    #     
    #     print(f"\nCSV preview (first 5 rows):")
    #     print(df.head())
    #     
    #     print(f"\nCSV shape: {df.shape}")
    #     print(f"Columns: {', '.join(df.columns)}")
    
    print("\nNote: Uncomment the code above to download actual data")


def example_provider_interface():
    """Example: Using the Provider interface."""
    print("\n" + "=" * 70)
    print("Example 3: Using the Provider interface")
    print("=" * 70)
    
    # Initialize the provider
    provider = ValetProvider()
    
    print(f"\nProvider: {provider.name}")
    
    # Create a dataset reference
    ref = DatasetRef(
        provider='boc_valet',
        id='FXUSDCAD',
        params={
            'start_date': '2023-01-01',
            'end_date': '2023-12-31'
        },
        metadata={
            'title': 'US Dollar to Canadian Dollar Exchange Rate'
        },
        tags=['finance', 'exchange-rate', 'usd']
    )
    
    print(f"\nDataset reference:")
    print(f"  Canonical ID: {ref.canonical_id}")
    print(f"  Series: {ref.id}")
    print(f"  Date range: {ref.params['start_date']} to {ref.params['end_date']}")
    print(f"  Tags: {', '.join(ref.tags)}")
    
    # Resolve the reference to get download metadata
    metadata = provider.resolve(ref)
    
    print(f"\nResolved metadata:")
    print(f"  URL: {metadata['url']}")
    print(f"  Format: {metadata['format']}")
    print(f"  Series name: {metadata['series_name']}")
    
    # Note: This is a demonstration. Uncomment to fetch actual data:
    # 
    # import tempfile
    # 
    # # Fetch the data
    # with tempfile.TemporaryDirectory() as tmpdir:
    #     result = provider.fetch(ref, tmpdir, skip_existing=False)
    #     
    #     print(f"\nFetch result:")
    #     print(f"  Provider: {result['provider']}")
    #     print(f"  Dataset ID: {result['dataset_id']}")
    #     print(f"  Files: {result['files']}")
    #     print(f"  Observations: {result['observations']}")
    
    print("\nNote: Uncomment the code above to fetch actual data")


def example_multiple_series():
    """Example: Fetching multiple series."""
    print("\n" + "=" * 70)
    print("Example 4: Fetching multiple series")
    print("=" * 70)
    
    # Common series available in the Bank of Canada Valet API
    series_list = [
        ('FXUSDCAD', 'US Dollar to CAD exchange rate'),
        ('FXEURCAD', 'Euro to CAD exchange rate'),
        ('FXGBPCAD', 'British Pound to CAD exchange rate'),
        ('FXJPYCAD', 'Japanese Yen to CAD exchange rate'),
    ]
    
    print("\nCommon Bank of Canada series:")
    for series_id, description in series_list:
        print(f"  {series_id}: {description}")
    
    # Note: This is a demonstration. Uncomment to fetch actual data:
    # 
    # import tempfile
    # import pandas as pd
    # 
    # print("\nFetching multiple exchange rate series...")
    # 
    # with tempfile.TemporaryDirectory() as tmpdir:
    #     provider = ValetProvider()
    #     results = []
    #     
    #     for series_id, description in series_list:
    #         ref = DatasetRef(
    #             provider='boc_valet',
    #             id=series_id,
    #             params={
    #                 'start_date': '2023-01-01',
    #                 'end_date': '2023-01-31'
    #             }
    #         )
    #         
    #         try:
    #             result = provider.fetch(ref, tmpdir, skip_existing=False)
    #             results.append(result)
    #             print(f"  ✓ {series_id}: {result['observations']} observations")
    #         except Exception as e:
    #             print(f"  ✗ {series_id}: {e}")
    #     
    #     print(f"\nSuccessfully fetched {len(results)} series")
    #     
    #     # Combine data from multiple series
    #     if results:
    #         print("\nCombining data from all series...")
    #         dfs = []
    #         for result in results:
    #             df = pd.read_csv(result['files'][0])
    #             dfs.append(df)
    #         
    #         combined_df = pd.concat(dfs, ignore_index=True)
    #         print(f"Combined DataFrame shape: {combined_df.shape}")
    #         print(f"\nFirst few rows:")
    #         print(combined_df.head())
    
    print("\nNote: Uncomment the code above to fetch actual data")


def example_tidy_data_format():
    """Example: Understanding the tidy data format."""
    print("\n" + "=" * 70)
    print("Example 5: Understanding tidy data format")
    print("=" * 70)
    
    print("\nThe Valet provider returns data in tidy format:")
    print("  - date: Observation date (YYYY-MM-DD)")
    print("  - series_name: Series identifier")
    print("  - value: Observation value")
    
    print("\nExample tidy format:")
    print("  date,series_name,value")
    print("  2023-01-03,FXUSDCAD,1.3500")
    print("  2023-01-04,FXUSDCAD,1.3525")
    print("  2023-01-05,FXUSDCAD,1.3510")
    
    print("\nBenefits of tidy format:")
    print("  ✓ Easy to combine multiple series")
    print("  ✓ Compatible with pandas groupby/pivot operations")
    print("  ✓ Standard format for time series analysis")
    print("  ✓ Provenance metadata in .meta.json sidecar files")


def main():
    """Run all examples."""
    print("Bank of Canada Valet API Provider Examples")
    print("=" * 70)
    print()
    
    # Run examples
    example_fetch_series()
    example_download_series()
    example_provider_interface()
    example_multiple_series()
    example_tidy_data_format()
    
    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)
    print("\nTo use the Valet provider in your code:")
    print("  from publicdata_ca.providers import ValetProvider")
    print("  from publicdata_ca.provider import DatasetRef")
    print()
    print("For more information:")
    print("  https://www.bankofcanada.ca/valet/docs")
    print()


if __name__ == '__main__':
    main()
