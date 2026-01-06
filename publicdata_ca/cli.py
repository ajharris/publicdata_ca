"""
Command-line interface for publicdata_ca.

This module provides CLI commands for searching and fetching Canadian public datasets.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from publicdata_ca.catalog import Catalog
from publicdata_ca.providers.statcan import download_statcan_table, search_statcan_tables
from publicdata_ca.providers.cmhc import download_cmhc_asset
from publicdata_ca.manifest import build_manifest_file
from publicdata_ca.datasets import refresh_datasets, DEFAULT_DATASETS


def cmd_search(args):
    """
    Search for datasets by keyword.
    
    Args:
        args: Parsed command-line arguments.
    """
    query = args.query
    provider = args.provider
    
    print(f"Searching for: {query}")
    if provider:
        print(f"Provider filter: {provider}")
    
    # Search in catalog
    catalog = Catalog()
    results = catalog.search(query)
    
    # If searching StatsCan specifically, use StatsCan search
    if provider == 'statcan' or not provider:
        statcan_results = search_statcan_tables(query)
        # In a real implementation, this would return actual results
    
    if results:
        print(f"\nFound {len(results)} datasets:")
        for i, dataset in enumerate(results, 1):
            print(f"\n{i}. {dataset.get('title', 'Untitled')}")
            print(f"   ID: {dataset.get('dataset_id', 'N/A')}")
            print(f"   Provider: {dataset.get('provider', 'N/A')}")
            if 'description' in dataset:
                print(f"   Description: {dataset['description'][:100]}...")
    else:
        print("\nNo datasets found matching your query.")
        print("\nNote: The catalog is currently empty. Use 'fetch' to download datasets,")
        print("or the catalog will be populated with available datasets in future versions.")


def cmd_fetch(args):
    """
    Fetch/download a dataset.
    
    Args:
        args: Parsed command-line arguments.
    """
    provider = args.provider
    dataset_id = args.dataset_id
    output_dir = args.output or './data'
    
    print(f"Fetching dataset: {dataset_id}")
    print(f"Provider: {provider}")
    print(f"Output directory: {output_dir}")
    
    try:
        if provider == 'statcan':
            result = download_statcan_table(
                table_id=dataset_id,
                output_dir=output_dir,
                file_format=args.format or 'csv'
            )
        elif provider == 'cmhc':
            result = download_cmhc_asset(
                landing_url=dataset_id,
                output_dir=output_dir,
                asset_filter=args.format
            )
        else:
            print(f"Error: Unknown provider '{provider}'")
            print("Supported providers: statcan, cmhc")
            sys.exit(1)
        
        print("\n✓ Download complete!")
        print(f"  Dataset ID: {result['dataset_id']}")
        print(f"  Files downloaded: {len(result['files'])}")
        for file_path in result['files']:
            print(f"    - {file_path}")
        
        # Create manifest if requested
        if args.manifest:
            manifest_path = build_manifest_file(
                output_dir=output_dir,
                datasets=[result],
                manifest_name='manifest.json'
            )
            print(f"\n  Manifest created: {manifest_path}")
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)


def cmd_refresh(args):
    """
    Refresh/download all datasets from the catalog.
    
    Args:
        args: Parsed command-line arguments.
    """
    print("Refreshing datasets...")
    
    # Filter datasets by provider if specified
    datasets_to_refresh = None
    if args.provider:
        datasets_to_refresh = [d for d in DEFAULT_DATASETS if d.provider == args.provider]
        print(f"Filtering to {args.provider} datasets only ({len(datasets_to_refresh)} datasets)")
    else:
        print(f"Processing all datasets ({len(DEFAULT_DATASETS)} datasets)")
    
    # Run the refresh
    try:
        report = refresh_datasets(
            datasets=datasets_to_refresh,
            force_download=args.force
        )
        
        # Display results summary
        print("\n" + "="*60)
        print("REFRESH SUMMARY")
        print("="*60)
        
        # Count results by status
        status_counts = report['result'].value_counts()
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Show detailed results if verbose or if there are errors
        if args.verbose or 'error' in status_counts:
            print("\n" + "="*60)
            print("DETAILED RESULTS")
            print("="*60)
            for row in report.itertuples():
                status_symbol = "✓" if row.result in ['downloaded', 'exists'] else "✗"
                print(f"\n{status_symbol} {row.dataset} ({row.provider})")
                print(f"  Status: {row.result}")
                if row.notes:
                    print(f"  Notes: {row.notes}")
                if row.target_file:
                    print(f"  File: {row.target_file}")
        
        # Create manifest if requested
        if args.manifest:
            # Convert report to datasets list for manifest
            manifest_datasets = []
            for row in report.itertuples():
                if row.result in ['downloaded', 'exists'] and row.target_file:
                    manifest_datasets.append({
                        'dataset_id': row.dataset,
                        'provider': row.provider,
                        'files': [row.target_file],
                        'status': row.result,
                        'notes': row.notes
                    })
            
            manifest_path = build_manifest_file(
                output_dir=args.output or './data',
                datasets=manifest_datasets,
                manifest_name='refresh_manifest.json'
            )
            print(f"\n✓ Manifest created: {manifest_path}")
        
        # Exit with error if there were any download failures
        if 'error' in status_counts:
            print("\n⚠ Some downloads failed. See detailed results above.")
            sys.exit(1)
        else:
            print("\n✓ Refresh complete!")
    
    except Exception as e:
        print(f"\n✗ Error during refresh: {str(e)}")
        sys.exit(1)


def cmd_manifest(args):
    """
    Create or validate a manifest file.
    
    Args:
        args: Parsed command-line arguments.
    """
    if args.action == 'create':
        # Load dataset metadata from JSON file if provided
        datasets = []
        if args.datasets_file:
            with open(args.datasets_file, 'r') as f:
                datasets = json.load(f)
        
        manifest_path = build_manifest_file(
            output_dir=args.output or './data',
            datasets=datasets
        )
        print(f"Manifest created: {manifest_path}")
    
    elif args.action == 'validate':
        from publicdata_ca.manifest import validate_manifest
        
        manifest_file = args.manifest_file or './data/manifest.json'
        print(f"Validating manifest: {manifest_file}")
        
        if validate_manifest(manifest_file):
            print("✓ All files in manifest are present")
        else:
            print("✗ Some files in manifest are missing")
            sys.exit(1)


def main():
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(
        prog='publicdata',
        description='publicdata_ca - Tools for discovering and downloading Canadian public datasets'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for datasets')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument(
        '-p', '--provider',
        choices=['statcan', 'cmhc'],
        help='Filter by data provider'
    )
    search_parser.set_defaults(func=cmd_search)
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Download a dataset')
    fetch_parser.add_argument('provider', choices=['statcan', 'cmhc'], help='Data provider')
    fetch_parser.add_argument('dataset_id', help='Dataset identifier or URL')
    fetch_parser.add_argument('-o', '--output', help='Output directory (default: ./data)')
    fetch_parser.add_argument('-f', '--format', help='File format filter (e.g., csv, xlsx)')
    fetch_parser.add_argument('-m', '--manifest', action='store_true', help='Create manifest file')
    fetch_parser.set_defaults(func=cmd_fetch)
    
    # Refresh command
    refresh_parser = subparsers.add_parser('refresh', help='Refresh/download all datasets')
    refresh_parser.add_argument(
        '-p', '--provider',
        choices=['statcan', 'cmhc'],
        help='Filter by data provider (default: all)'
    )
    refresh_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force re-download even if files exist'
    )
    refresh_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed results for all datasets'
    )
    refresh_parser.add_argument(
        '-m', '--manifest',
        action='store_true',
        help='Create manifest file after refresh'
    )
    refresh_parser.add_argument(
        '-o', '--output',
        help='Output directory for manifest (default: ./data)'
    )
    refresh_parser.set_defaults(func=cmd_refresh)
    
    # Manifest command
    manifest_parser = subparsers.add_parser('manifest', help='Create or validate manifest')
    manifest_parser.add_argument(
        'action',
        choices=['create', 'validate'],
        help='Action to perform'
    )
    manifest_parser.add_argument('-o', '--output', help='Output directory for manifest')
    manifest_parser.add_argument('-d', '--datasets-file', help='JSON file with datasets metadata')
    manifest_parser.add_argument('-f', '--manifest-file', help='Manifest file to validate')
    manifest_parser.set_defaults(func=cmd_manifest)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
