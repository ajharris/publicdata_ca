# publicdata_ca

A lightweight Python package for discovering, resolving, and downloading Canadian public datasets.

[![PyPI version](https://img.shields.io/pypi/v/publicdata-ca.svg)](https://pypi.org/project/publicdata-ca/)
[![Python versions](https://img.shields.io/pypi/pyversions/publicdata-ca.svg)](https://pypi.org/project/publicdata-ca/)
[![License](https://img.shields.io/github/license/ajharris/publicdata_ca.svg)](https://github.com/ajharris/publicdata_ca/blob/main/LICENSE)

## Features

- 🇨🇦 **Canadian-focused**: Specialized support for Statistics Canada, CMHC, and Open Canada
- 🔌 **Extensible**: Generic CKAN, Socrata, and SDMX providers work with any compatible portal
- 📦 **Reproducible**: Automatic provenance tracking with metadata sidecar files
- ⚡ **Efficient**: HTTP caching with ETag/Last-Modified to avoid re-downloading unchanged files
- 🔍 **Discoverable**: Search datasets across multiple providers
- 🛠️ **Developer-friendly**: Strong typing, comprehensive documentation, and extensive examples

## Quick Start

### Installation

```bash
# From PyPI (recommended)
pip install publicdata-ca

# From source (for development)
git clone https://github.com/ajharris/publicdata_ca.git
cd publicdata_ca
python -m pip install -e ".[dev]"
```

### Download StatsCan Data

```python
from publicdata_ca.providers import StatCanProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = StatCanProvider()

# Download Consumer Price Index data
ref = DatasetRef(provider='statcan', id='18100004')
result = provider.fetch(ref, './data')
print(f"Downloaded: {result['files']}")
```

### Search Open Canada

```python
from publicdata_ca.providers import OpenCanadaProvider
from publicdata_ca.provider import DatasetRef

# Search for datasets
provider = OpenCanadaProvider()
results = provider.search('housing', rows=5)

for ref in results:
    print(f"{ref.id}: {ref.metadata['title']}")

# Download specific dataset
ref = DatasetRef(
    provider='open_canada',
    id=results[0].id,
    params={'format': 'CSV'}
)
result = provider.fetch(ref, './data')
```

### Use Profiles for Multiple Datasets

Create a profile file `profiles/my_data.yaml`:

```yaml
name: my_data
description: My collection of Canadian datasets

datasets:
  - provider: statcan
    id: "18100004"
    output: data/cpi.csv
  
  - provider: statcan
    id: "14100287"
    output: data/population.csv
```

Run the profile:

```bash
# CLI
publicdata profile run my_data

# Or Python
from publicdata_ca import run_profile
report = run_profile("my_data")
print(report[['dataset', 'result', 'notes']])
```

## Supported Data Providers

| Provider | Description | Documentation |
|----------|-------------|---------------|
| **StatCan** | Statistics Canada tables | [docs/PROVIDERS.md](docs/PROVIDERS.md#statcan-provider) |
| **CMHC** | Canada Mortgage and Housing Corporation | [docs/PROVIDERS.md](docs/PROVIDERS.md#cmhc-provider) |
| **Open Canada** | Open Government Canada portal | [docs/PROVIDERS.md](docs/PROVIDERS.md#open-canada-provider) |
| **CKAN** | Generic CKAN portals (Open Canada, Data.gov, etc.) | [docs/PROVIDERS.md](docs/PROVIDERS.md#ckan-provider-generic) |
| **Socrata** | Socrata-based open data portals | [docs/PROVIDERS.md](docs/PROVIDERS.md#socrata-provider) |
| **SDMX** | Statistical Data and Metadata eXchange | [docs/PROVIDERS.md](docs/PROVIDERS.md#sdmx-provider) |
| **Bank of Canada Valet** | Time series from Bank of Canada | [docs/PROVIDERS.md](docs/PROVIDERS.md#bank-of-canada-valet-provider) |

## Documentation

- **[Provider Documentation](docs/PROVIDERS.md)** - Detailed guide for each data provider
- **[Advanced Features](docs/ADVANCED_FEATURES.md)** - HTTP caching, provenance tracking, normalization, and more
- **[CMHC Troubleshooting](docs/CMHC_TROUBLESHOOTING.md)** - Common CMHC issues and solutions
- **[Profiles Guide](profiles/README.md)** - Organize datasets into collections
- **[Adding a Provider](docs/ADDING_A_PROVIDER.md)** - Implement custom data providers
- **[Examples](examples/)** - Runnable examples for all features

## Command-Line Interface

```bash
# Search for datasets
publicdata search "housing" --provider statcan

# Run a profile
publicdata profile run economics

# List available profiles
publicdata profile list

# Create a manifest
publicdata manifest create --output ./data
```

For full CLI documentation, run `publicdata --help`.

## Key Concepts

### Providers

Providers implement a standard interface for searching, resolving, and downloading datasets from different data sources. Each provider knows how to interact with a specific API or portal.

```python
from publicdata_ca.providers import StatCanProvider, OpenCanadaProvider

# Each provider implements: search(), resolve(), fetch()
statcan = StatCanProvider()
open_canada = OpenCanadaProvider()
```

### DatasetRef

A `DatasetRef` is a lightweight reference to a dataset that can be passed between functions and serialized to YAML/JSON.

```python
from publicdata_ca.provider import DatasetRef

ref = DatasetRef(
    provider='statcan',
    id='18100004',
    params={'format': 'csv'}
)
```

### Profiles

Profiles are YAML files that define collections of datasets to download together. They're perfect for reproducible workflows and team collaboration.

```yaml
name: economics
description: Core economic indicators

datasets:
  - provider: statcan
    id: "18100004"
    output: data/cpi.csv
```

## Project Structure

```
publicdata_ca/
├── publicdata_ca/          # Main package
│   ├── providers/          # Data provider implementations
│   ├── resolvers/          # HTML scrapers for landing pages
│   ├── catalog.py          # Dataset catalog
│   ├── datasets.py         # Curated dataset definitions
│   ├── http.py             # HTTP utilities with caching
│   ├── provenance.py       # Metadata tracking
│   ├── normalize.py        # Data normalization utilities
│   └── cli.py              # Command-line interface
├── docs/                   # Documentation
├── examples/               # Example scripts
├── profiles/               # YAML profile files
├── tests/                  # Test suite
└── README.md               # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_provider_contracts.py

# Run with coverage
pytest --cov=publicdata_ca
```

### Contributing

Contributions are welcome! Please see:

- [ADDING_A_PROVIDER.md](docs/ADDING_A_PROVIDER.md) - Add new data providers
- [GitHub Issues](https://github.com/ajharris/publicdata_ca/issues) - Report bugs or request features
- [Pull Requests](https://github.com/ajharris/publicdata_ca/pulls) - Submit code changes

## Examples

The `examples/` directory contains runnable scripts demonstrating all features:

```bash
# Provider examples
python examples/statcan_provider_demo.py
python examples/open_canada_provider_demo.py
python examples/ckan_provider_demo.py

# Feature examples
python examples/http_caching_demo.py
python examples/normalization_demo.py
python examples/provider_interface_demo.py
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **GitHub**: https://github.com/ajharris/publicdata_ca
- **PyPI**: https://pypi.org/project/publicdata-ca/
- **Documentation**: https://github.com/ajharris/publicdata_ca/tree/main/docs
- **Issues**: https://github.com/ajharris/publicdata_ca/issues

## Acknowledgments

- Statistics Canada for providing comprehensive open data
- Canada Mortgage and Housing Corporation (CMHC) for housing data
- Open Government Canada for the CKAN portal
- All contributors and users of this package
