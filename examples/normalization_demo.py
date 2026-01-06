#!/usr/bin/env python
"""
Example demonstrating normalization utilities in publicdata_ca.

This script shows how to use the normalization functions to standardize
time, geography, frequency, and unit metadata from Canadian public datasets.
"""

from publicdata_ca import (
    normalize_frequency,
    parse_date,
    parse_period,
    normalize_geo,
    normalize_unit,
    normalize_dataset_metadata,
)


def main():
    print("=" * 70)
    print("publicdata_ca Normalization Utilities Demo")
    print("=" * 70)
    
    # Frequency normalization
    print("\n1. Frequency Normalization")
    print("-" * 70)
    frequencies = ["Monthly", "Annual", "Q", "Quarterly", "weekly", "M"]
    for freq in frequencies:
        normalized = normalize_frequency(freq)
        print(f"  {freq:15s} -> {normalized}")
    
    # Date parsing
    print("\n2. Date Parsing")
    print("-" * 70)
    dates = ["2023-01-15", "2023-01", "2023", "2023-Q1", "202301"]
    for date in dates:
        parsed = parse_date(date)
        print(f"  {date:15s} -> {parsed}")
    
    # Period parsing
    print("\n3. Period Parsing (with frequency hints)")
    print("-" * 70)
    periods = [
        ("2023-01", "monthly"),
        ("2023-Q1", "quarterly"),
        ("2023", "annual"),
    ]
    for period, freq in periods:
        parsed = parse_period(period, freq)
        if parsed:
            print(f"  {period:15s} ({freq:10s}) -> {parsed.start_date} to {parsed.end_date}")
    
    # Geographic normalization
    print("\n4. Geographic Normalization")
    print("-" * 70)
    locations = ["Canada", "Ontario", "ON", "Toronto CMA", "Montreal census metropolitan area"]
    for loc in locations:
        geo = normalize_geo(loc)
        if geo:
            print(f"  {loc:40s} -> {geo.code:20s} ({geo.level})")
    
    # Unit normalization
    print("\n5. Unit Normalization")
    print("-" * 70)
    units = [
        "Dollars",
        "Thousands of dollars",
        "Millions of dollars",
        "Percent",
        "Persons",
        "Thousands of persons",
        "Index",
    ]
    for unit in units:
        normalized = normalize_unit(unit)
        if normalized:
            multiplier_str = f"{normalized.multiplier:,.0f}" if normalized.multiplier != 1.0 else "1"
            print(f"  {unit:30s} -> {normalized.symbol:10s} (x{multiplier_str})")
    
    # Comprehensive metadata normalization
    print("\n6. Comprehensive Dataset Metadata Normalization")
    print("-" * 70)
    metadata = {
        "dataset_id": "cpi_example",
        "provider": "statcan",
        "frequency": "Monthly",
        "geo": "Ontario",
        "unit": "Thousands of dollars",
        "period": "2023-01",
        "custom_field": "This field is preserved",
    }
    
    print("\nOriginal metadata:")
    for key, value in metadata.items():
        print(f"  {key:20s}: {value}")
    
    normalized = normalize_dataset_metadata(metadata)
    
    print("\nNormalized metadata (additions):")
    for key, value in sorted(normalized.items()):
        if key.startswith('normalized_') or key.startswith('raw_'):
            if isinstance(value, dict):
                print(f"  {key:20s}:")
                for k, v in value.items():
                    print(f"    {k:18s}: {v}")
            else:
                print(f"  {key:20s}: {value}")
    
    print("\n" + "=" * 70)
    print("All original provider-specific fields are preserved!")
    print("Normalized fields are added with 'normalized_' prefix.")
    print("Raw values are stored with 'raw_' prefix for reference.")
    print("=" * 70)


if __name__ == "__main__":
    main()
