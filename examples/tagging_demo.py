#!/usr/bin/env python3
"""
Demo script for dataset tagging and metadata search functionality.

This script demonstrates how to use tags to discover and filter datasets
in the publicdata_ca catalog.
"""

from publicdata_ca import build_dataset_catalog, DEFAULT_DATASETS
from publicdata_ca.catalog import Catalog
from publicdata_ca.provider import DatasetRef


def main():
    print("=" * 80)
    print("Dataset Tagging and Metadata Search Demo")
    print("=" * 80)
    print()
    
    # Demo 1: Show all datasets with their tags
    print("📊 Demo 1: Viewing all datasets with tags")
    print("-" * 80)
    catalog_df = build_dataset_catalog()
    print(catalog_df[['dataset', 'provider', 'metric', 'tags']].to_string())
    print()
    
    # Demo 2: Filter datasets by specific domain
    print("🏠 Demo 2: Finding housing-related datasets")
    print("-" * 80)
    housing_datasets = catalog_df[
        catalog_df['tags'].apply(lambda x: x is not None and 'housing' in x)
    ]
    for idx, row in housing_datasets.iterrows():
        print(f"  • {row['dataset']}")
        print(f"    Provider: {row['provider']}")
        print(f"    Metric: {row['metric']}")
        print(f"    Tags: {', '.join(row['tags'])}")
        print()
    
    # Demo 3: Filter datasets by multiple tags
    print("💼 Demo 3: Finding economics AND labour datasets")
    print("-" * 80)
    labour_economics = catalog_df[
        catalog_df['tags'].apply(
            lambda x: x is not None and 'labour' in x and 'economics' in x
        )
    ]
    for idx, row in labour_economics.iterrows():
        print(f"  • {row['dataset']}: {row['metric']}")
        print(f"    Tags: {', '.join(row['tags'])}")
        print()
    
    # Demo 4: Using the Catalog class for tag-based search
    print("🔍 Demo 4: Using Catalog class for tag-based filtering")
    print("-" * 80)
    catalog = Catalog()
    
    # Register datasets from DEFAULT_DATASETS
    for ds in DEFAULT_DATASETS:
        catalog.register_dataset(ds.dataset, {
            'dataset_id': ds.dataset,
            'provider': ds.provider,
            'title': ds.metric,
            'description': ds.status_note,
            'tags': ds.tags or []
        })
    
    # List datasets by tag
    finance_datasets = catalog.list_datasets(tags=['finance'])
    print(f"Finance datasets found: {len(finance_datasets)}")
    for ds in finance_datasets:
        print(f"  • {ds['dataset_id']}: {ds['title']}")
    print()
    
    # Demo 5: Search with keyword and tag filter
    print("🔎 Demo 5: Keyword search with tag filtering")
    print("-" * 80)
    results = catalog.search("rate", tags=['labour'])
    print(f"Datasets matching 'rate' with tag 'labour': {len(results)}")
    for ds in results:
        print(f"  • {ds['dataset_id']}: {ds['title']}")
    print()
    
    # Demo 6: Creating DatasetRef with tags
    print("📋 Demo 6: Creating DatasetRef with tags")
    print("-" * 80)
    ref = DatasetRef(
        provider='statcan',
        id='18100004',
        metadata={'title': 'Consumer Price Index'},
        tags=['finance', 'economics', 'inflation']
    )
    print(f"  DatasetRef ID: {ref.canonical_id}")
    print(f"  Title: {ref.metadata['title']}")
    print(f"  Tags: {', '.join(ref.tags)}")
    print()
    
    # Demo 7: Summary of available tags
    print("🏷️  Demo 7: Summary of all available tags")
    print("-" * 80)
    all_tags = set()
    for ds in DEFAULT_DATASETS:
        if ds.tags:
            all_tags.update(ds.tags)
    
    print(f"Total unique tags: {len(all_tags)}")
    print(f"Available tags: {', '.join(sorted(all_tags))}")
    print()
    
    # Tag usage statistics
    tag_counts = {}
    for ds in DEFAULT_DATASETS:
        if ds.tags:
            for tag in ds.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    print("Tag usage frequency:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  • {tag}: {count} dataset(s)")
    print()
    
    print("=" * 80)
    print("✅ Demo complete!")
    print()
    print("Tips for using tags:")
    print("  • Use tags to quickly find datasets in a specific domain")
    print("  • Combine multiple tags to narrow your search")
    print("  • Tags are domain-agnostic and can be customized per project")
    print("  • Common tags: housing, labour, finance, economics, demographics")
    print("=" * 80)


if __name__ == "__main__":
    main()
