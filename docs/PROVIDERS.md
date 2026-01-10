# Provider Documentation

This document provides detailed information about the data providers supported by publicdata_ca.

## Table of Contents

- [StatCan Provider](#statcan-provider)
- [CMHC Provider](#cmhc-provider)
- [Open Canada Provider](#open-canada-provider)
- [CKAN Provider (Generic)](#ckan-provider-generic)
- [Socrata Provider](#socrata-provider)
- [SDMX Provider](#sdmx-provider)
- [Bank of Canada Valet Provider](#bank-of-canada-valet-provider)

## StatCan Provider

The StatCan provider enables downloading tables from Statistics Canada's data portal.

### Basic Usage

```python
from publicdata_ca.providers import StatCanProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = StatCanProvider()

# Download a table
ref = DatasetRef(provider='statcan', id='18100004')
result = provider.fetch(ref, './data/statcan')
print(f"Downloaded: {result['files']}")
```

### Finding Table IDs

Browse Statistics Canada tables at: https://www150.statcan.gc.ca/

Table IDs are 8-digit numbers like `18100004` (Consumer Price Index).

## CMHC Provider

The CMHC (Canada Mortgage and Housing Corporation) provider handles housing data downloads with automatic landing page resolution.

### Basic Usage

```python
from publicdata_ca.providers import CMHCProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = CMHCProvider()

# Download from a landing page
ref = DatasetRef(
    provider='cmhc',
    id='rental-market',
    params={'page_url': 'https://www.cmhc-schl.gc.ca/data-page'}
)
result = provider.fetch(ref, './data/cmhc')
```

### Landing Page Resolution

CMHC landing pages can change frequently. The provider includes:
- **Ranking**: Prioritizes file formats (XLSX > CSV > XLS > ZIP)
- **Validation**: Verifies URLs return data files, not HTML
- **Caching**: Stores resolved URLs to reduce churn

### Troubleshooting

For detailed troubleshooting information, see [CMHC_TROUBLESHOOTING.md](CMHC_TROUBLESHOOTING.md).

## Open Canada Provider

The Open Canada provider is a convenience wrapper for accessing the Open Government Canada portal.

### Basic Usage

```python
from publicdata_ca.providers import OpenCanadaProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = OpenCanadaProvider()

# Search for datasets
results = provider.search('census', rows=5)
for ref in results:
    print(f"{ref.id}: {ref.metadata['title']}")

# Download specific resources by format
ref = DatasetRef(
    provider='open_canada',
    id='census-2021-population',
    params={'format': 'CSV'}
)
result = provider.fetch(ref, './data/open_canada')
```

### Search Tips

```python
# Search by keyword
results = provider.search('census population', rows=10)

# Search by organization
results = provider.search('organization:statcan', rows=20)

# Search with tags
results = provider.search('tags:environment', rows=15)

# Boolean operators
results = provider.search('environment AND climate', rows=5)
```

**Browse datasets at**: https://open.canada.ca/en/open-data

## CKAN Provider (Generic)

The CKAN provider works with any CKAN-based data portal.

### Basic Usage

```python
from publicdata_ca.providers import CKANProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider with portal URL
provider = CKANProvider(
    name='data_gov',
    base_url='https://catalog.data.gov'
)

# Search for datasets
results = provider.search('housing', rows=5)

# Download resources
ref = DatasetRef(
    provider='data_gov',
    id='housing-data',
    params={'format': 'CSV'}
)
result = provider.fetch(ref, './data/ckan')
```

### Multiple CKAN Portals

```python
# Open Canada
provider_ca = CKANProvider(
    name='open_canada',
    base_url='https://open.canada.ca/data'
)

# Data.gov (US)
provider_us = CKANProvider(
    name='data_gov',
    base_url='https://catalog.data.gov'
)

# BC Data Catalogue
provider_bc = CKANProvider(
    name='bc_data',
    base_url='https://catalogue.data.gov.bc.ca'
)
```

### Helper Functions

```python
from publicdata_ca.providers import (
    search_ckan_datasets,
    get_ckan_package,
    list_ckan_resources,
    download_ckan_resource
)

# Search datasets directly
results = search_ckan_datasets(
    'https://open.canada.ca/data',
    'census',
    rows=10
)

# Get detailed package information
package = get_ckan_package(
    'https://open.canada.ca/data',
    'census-2021'
)

# List resources with format filter
resources = list_ckan_resources(
    'https://open.canada.ca/data',
    'census-2021',
    format_filter='CSV'
)
```

## Socrata Provider

The Socrata provider supports Socrata-based open data portals.

### Basic Usage

```python
from publicdata_ca.providers import SocrataProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = SocrataProvider(
    name='my_portal',
    base_url='https://data.example.com'
)

# Search for datasets
results = provider.search('permits', rows=5)

# Download dataset
ref = DatasetRef(provider='my_portal', id='dataset-id')
result = provider.fetch(ref, './data/socrata')
```

For detailed examples, see `examples/socrata_provider_demo.py`.

## SDMX Provider

The SDMX provider enables downloading data in SDMX (Statistical Data and Metadata eXchange) format.

### Basic Usage

```python
from publicdata_ca.providers import SDMXProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = SDMXProvider(
    name='oecd',
    base_url='https://stats.oecd.org/sdmx-json'
)

# Download data
ref = DatasetRef(
    provider='oecd',
    id='PRICES_CPI',
    params={'key': 'CAN...'}
)
result = provider.fetch(ref, './data/sdmx')
```

For detailed examples, see `examples/sdmx_provider_demo.py`.

## Bank of Canada Valet Provider

The Valet provider downloads time series data from the Bank of Canada's Valet API.

### Basic Usage

```python
from publicdata_ca.providers import ValetProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = ValetProvider()

# Download a series
ref = DatasetRef(
    provider='valet',
    id='FX_RATES_DAILY',
    params={'format': 'csv'}
)
result = provider.fetch(ref, './data/valet')
```

### Available Series

Browse available series at: https://www.bankofcanada.ca/valet/

For detailed examples, see `examples/boc_valet_provider_demo.py`.

## Adding Custom Providers

For information on implementing custom data providers, see [ADDING_A_PROVIDER.md](ADDING_A_PROVIDER.md).
