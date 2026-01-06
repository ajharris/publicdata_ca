# Adding a New Provider

This guide shows how to implement a new data provider module for publicdata_ca. By the end, you'll understand how to:

1. Implement the `Provider` interface
2. Register your provider
3. Add test fixtures and contract tests
4. Create a profile to use your provider

## Table of Contents

- [Overview](#overview)
- [Quick Start Example](#quick-start-example)
- [Step-by-Step Guide](#step-by-step-guide)
  - [Step 1: Implement the Provider Class](#step-1-implement-the-provider-class)
  - [Step 2: Add Helper Functions (Optional)](#step-2-add-helper-functions-optional)
  - [Step 3: Register Your Provider](#step-3-register-your-provider)
  - [Step 4: Create Test Fixtures](#step-4-create-test-fixtures)
  - [Step 5: Add Contract Tests](#step-5-add-contract-tests)
  - [Step 6: Create a Profile](#step-6-create-a-profile)
- [Complete Working Example](#complete-working-example)
- [Testing Your Provider](#testing-your-provider)
- [Best Practices](#best-practices)

## Overview

The publicdata_ca package uses a **provider pattern** to support multiple data sources. Each provider implements a standard interface (`Provider` ABC) with three core methods:

- **`search(query)`** - Find datasets matching a query
- **`resolve(ref)`** - Convert a dataset reference into download metadata
- **`fetch(ref, output_dir)`** - Download a dataset to local storage

This standardized interface allows the system to work with any data source without hardcoding provider-specific logic.

## Quick Start Example

Here's a minimal provider implementation:

```python
from publicdata_ca.provider import Provider, DatasetRef
from typing import List, Dict, Any

class MyProvider(Provider):
    def __init__(self, name: str = 'my_provider'):
        super().__init__(name)
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        # Search for datasets and return DatasetRef objects
        return []
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        # Return download metadata for the dataset
        return {
            'url': f'https://api.example.com/data/{ref.id}',
            'format': 'json',
            'title': ref.metadata.get('title', 'Dataset'),
            'provider': self.name,
        }
    
    def fetch(self, ref: DatasetRef, output_dir: str, **kwargs) -> Dict[str, Any]:
        # Download the dataset and return results
        from publicdata_ca.http import download_file
        from pathlib import Path
        
        metadata = self.resolve(ref)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        output_file = output_path / f"{ref.id}.json"
        
        download_file(metadata['url'], str(output_file))
        
        return {
            'dataset_id': ref.id,
            'provider': self.name,
            'files': [str(output_file)],
            'url': metadata['url'],
        }
```

## Step-by-Step Guide

Let's walk through creating a complete provider for a fictional "Canadian Weather API".

### Step 1: Implement the Provider Class

Create a new file `publicdata_ca/providers/weather.py`:

```python
"""
Canadian Weather API data provider.

This module provides functionality to fetch weather data from the
Canadian Weather Service API (fictional example).
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from publicdata_ca.http import retry_request, download_file
from publicdata_ca.provider import Provider, DatasetRef
from publicdata_ca.provenance import write_provenance_metadata


def get_weather_metadata(station_id: str) -> Dict[str, Any]:
    """
    Get metadata for a weather station.
    
    Args:
        station_id: Station identifier (e.g., 'YYZ', 'YVR')
    
    Returns:
        Dictionary containing station metadata
    
    Example:
        >>> metadata = get_weather_metadata('YYZ')
        >>> print(metadata['name'])
        'Toronto Pearson International Airport'
    """
    url = f"https://weather.gc.ca/api/stations/{station_id}"
    
    try:
        response = retry_request(url)
        data = json.loads(response.read().decode('utf-8'))
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to get metadata for station {station_id}: {str(e)}")


def fetch_weather_data(
    station_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch weather observations from a station.
    
    Args:
        station_id: Station identifier (e.g., 'YYZ')
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
    
    Returns:
        Dictionary containing observations and metadata
    
    Example:
        >>> data = fetch_weather_data('YYZ', '2023-01-01', '2023-01-31')
        >>> print(len(data['observations']))
    """
    # Build query parameters
    params = []
    if start_date:
        params.append(f"start={start_date}")
    if end_date:
        params.append(f"end={end_date}")
    
    query_string = '&'.join(params) if params else ''
    url = f"https://weather.gc.ca/api/observations/{station_id}"
    if query_string:
        url = f"{url}?{query_string}"
    
    try:
        response = retry_request(url)
        data = json.loads(response.read().decode('utf-8'))
        
        return {
            'station_id': station_id,
            'observations': data.get('observations', []),
            'metadata': data.get('station', {}),
            'url': url,
        }
    except Exception as e:
        raise RuntimeError(f"Failed to fetch data for station {station_id}: {str(e)}")


def download_weather_data(
    station_id: str,
    output_dir: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip_existing: bool = True,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Download weather data to a CSV file.
    
    Args:
        station_id: Station identifier
        output_dir: Directory where the file will be saved
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        skip_existing: If True, skip download if file exists (default: True)
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Dictionary containing download results
    
    Example:
        >>> result = download_weather_data('YYZ', './data')
        >>> print(result['files'])
        ['./data/YYZ.csv']
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Define output file
    output_file = output_path / f"{station_id}.csv"
    
    # Skip if file exists and skip_existing is True
    if skip_existing and output_file.exists():
        return {
            'dataset_id': f'weather_{station_id}',
            'provider': 'weather',
            'files': [str(output_file)],
            'url': f"https://weather.gc.ca/api/observations/{station_id}",
            'station_id': station_id,
            'skipped': True
        }
    
    # Fetch the data
    data = fetch_weather_data(station_id, start_date, end_date)
    
    # Convert to DataFrame and save as CSV
    observations = data['observations']
    if not observations:
        raise RuntimeError(f"No observations returned for station {station_id}")
    
    df = pd.DataFrame(observations)
    df.to_csv(output_file, index=False)
    
    # Write provenance metadata
    write_provenance_metadata(
        str(output_file),
        data['url'],
        content_type='text/csv',
        provider_name='weather',
        provider_specific={
            'station_id': station_id,
            'station_metadata': data['metadata'],
            'start_date': start_date,
            'end_date': end_date,
            'observations': len(observations),
        }
    )
    
    return {
        'dataset_id': f'weather_{station_id}',
        'provider': 'weather',
        'files': [str(output_file)],
        'url': data['url'],
        'station_id': station_id,
        'metadata': data['metadata'],
        'observations': len(observations),
        'skipped': False
    }


class WeatherProvider(Provider):
    """
    Canadian Weather API data provider implementation.
    
    Example:
        >>> provider = WeatherProvider()
        >>> ref = DatasetRef(
        ...     provider='weather',
        ...     id='YYZ',
        ...     params={'start_date': '2023-01-01', 'end_date': '2023-12-31'}
        ... )
        >>> result = provider.fetch(ref, './data/raw')
        >>> print(result['files'])
    """
    
    def __init__(self, name: str = 'weather'):
        """Initialize the Weather provider."""
        super().__init__(name)
    
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for weather stations by keyword.
        
        Args:
            query: Search query string (e.g., 'Toronto', 'Vancouver')
            **kwargs: Additional search parameters
        
        Returns:
            List of DatasetRef objects matching the query
        
        Example:
            >>> provider = WeatherProvider()
            >>> results = provider.search('Toronto')
            >>> for ref in results:
            ...     print(ref.canonical_id, ref.metadata.get('name'))
        """
        # Make API call to search endpoint
        url = f"https://weather.gc.ca/api/stations/search?q={query}"
        
        try:
            response = retry_request(url)
            data = json.loads(response.read().decode('utf-8'))
            
            # Convert API results to DatasetRef objects
            results = []
            for station in data.get('stations', []):
                ref = DatasetRef(
                    provider=self.name,
                    id=station['id'],
                    metadata={
                        'title': station.get('name', ''),
                        'location': station.get('location', ''),
                        'province': station.get('province', ''),
                    },
                    tags=['weather', 'climate']
                )
                results.append(ref)
            
            return results
        except Exception:
            # Return empty list if search fails
            return []
    
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve a weather dataset reference into download metadata.
        
        Args:
            ref: Dataset reference with station identifier
        
        Returns:
            Dictionary containing download URL, format, and metadata
        
        Example:
            >>> ref = DatasetRef(provider='weather', id='YYZ')
            >>> metadata = provider.resolve(ref)
            >>> print(metadata['url'])
        """
        station_id = ref.id
        
        # Get date range from params
        start_date = ref.params.get('start_date')
        end_date = ref.params.get('end_date')
        
        # Build URL with date range
        params = []
        if start_date:
            params.append(f"start={start_date}")
        if end_date:
            params.append(f"end={end_date}")
        
        query_string = '&'.join(params) if params else ''
        url = f"https://weather.gc.ca/api/observations/{station_id}"
        if query_string:
            url = f"{url}?{query_string}"
        
        return {
            'url': url,
            'format': 'json',
            'station_id': station_id,
            'title': ref.metadata.get('title', f'Weather Station {station_id}'),
            'provider': self.name,
            'start_date': start_date,
            'end_date': end_date,
        }
    
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download weather data to the specified output directory.
        
        Args:
            ref: Dataset reference with station identifier
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters (skip_existing, max_retries)
        
        Returns:
            Dictionary containing downloaded files and metadata
        
        Example:
            >>> ref = DatasetRef(
            ...     provider='weather',
            ...     id='YYZ',
            ...     params={'start_date': '2023-01-01', 'end_date': '2023-12-31'}
            ... )
            >>> result = provider.fetch(ref, './data/raw')
            >>> print(result['files'])
        """
        # Extract parameters
        skip_existing = kwargs.get('skip_existing', True)
        max_retries = kwargs.get('max_retries', 3)
        start_date = ref.params.get('start_date')
        end_date = ref.params.get('end_date')
        
        # Use the existing download function
        result = download_weather_data(
            station_id=ref.id,
            output_dir=output_dir,
            start_date=start_date,
            end_date=end_date,
            skip_existing=skip_existing,
            max_retries=max_retries
        )
        
        return result
```

### Step 2: Add Helper Functions (Optional)

The helper functions (`get_weather_metadata`, `fetch_weather_data`, `download_weather_data`) are optional but recommended. They provide:

- **Standalone functionality** - Users can call these directly without using the Provider interface
- **Easier testing** - You can test individual functions independently
- **Better code organization** - Separates API interaction from the Provider interface

See examples in `publicdata_ca/providers/boc_valet.py` or `publicdata_ca/providers/statcan.py`.

### Step 3: Register Your Provider

Update `publicdata_ca/providers/__init__.py` to export your provider:

```python
from publicdata_ca.providers.weather import (
    get_weather_metadata,
    fetch_weather_data,
    download_weather_data,
    WeatherProvider,
)

__all__ = [
    # ... existing exports ...
    "get_weather_metadata",
    "fetch_weather_data", 
    "download_weather_data",
    "WeatherProvider",
]
```

Now users can import your provider:

```python
from publicdata_ca.providers import WeatherProvider
from publicdata_ca.provider import DatasetRef

provider = WeatherProvider()
ref = DatasetRef(provider='weather', id='YYZ')
result = provider.fetch(ref, './data')
```

### Step 4: Create Test Fixtures

Create test fixtures by capturing real API responses:

1. **Create fixture directory**:
   ```bash
   mkdir -p tests/fixtures/weather
   ```

2. **Capture real API responses**:
   ```python
   # Run this script to capture real API responses
   import json
   import urllib.request
   
   # Capture station metadata
   url = "https://weather.gc.ca/api/stations/YYZ"
   response = urllib.request.urlopen(url)
   data = json.loads(response.read())
   
   with open('tests/fixtures/weather/YYZ_metadata.json', 'w') as f:
       json.dump(data, f, indent=2)
   
   # Capture observations
   url = "https://weather.gc.ca/api/observations/YYZ?start=2023-01-01&end=2023-01-03"
   response = urllib.request.urlopen(url)
   data = json.loads(response.read())
   
   with open('tests/fixtures/weather/YYZ_observations.json', 'w') as f:
       json.dump(data, f, indent=2)
   ```

3. **Create minimal but realistic fixtures**:
   
   `tests/fixtures/weather/YYZ_metadata.json`:
   ```json
   {
     "id": "YYZ",
     "name": "Toronto Pearson International Airport",
     "location": "Toronto",
     "province": "Ontario",
     "latitude": 43.6777,
     "longitude": -79.6248
   }
   ```
   
   `tests/fixtures/weather/YYZ_observations.json`:
   ```json
   {
     "station": {
       "id": "YYZ",
       "name": "Toronto Pearson International Airport"
     },
     "observations": [
       {"date": "2023-01-01", "temp_c": -5.2, "precip_mm": 0.0},
       {"date": "2023-01-02", "temp_c": -3.1, "precip_mm": 2.5},
       {"date": "2023-01-03", "temp_c": -1.0, "precip_mm": 0.0}
     ]
   }
   ```

### Step 5: Add Contract Tests

Add tests to `tests/test_provider_contracts.py`:

```python
class TestWeatherProviderContract:
    """Contract tests for Weather provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify WeatherProvider implements the Provider interface."""
        provider = WeatherProvider()
        assert isinstance(provider, Provider)
        assert hasattr(provider, 'search')
        assert hasattr(provider, 'resolve')
        assert hasattr(provider, 'fetch')
    
    def test_resolve_contract(self):
        """Test resolve returns correct metadata structure."""
        provider = WeatherProvider()
        ref = DatasetRef(
            provider='weather',
            id='YYZ',
            params={'start_date': '2023-01-01', 'end_date': '2023-12-31'}
        )
        
        metadata = provider.resolve(ref)
        
        # Verify contract: metadata must have these keys
        assert 'url' in metadata
        assert 'format' in metadata
        assert 'station_id' in metadata
        assert 'provider' in metadata
        assert metadata['station_id'] == 'YYZ'
        assert metadata['format'] == 'json'
        assert metadata['provider'] == 'weather'
        assert '2023-01-01' in metadata['url']
        assert '2023-12-31' in metadata['url']
    
    @patch('publicdata_ca.providers.weather.retry_request')
    def test_fetch_with_fixture(self, mock_retry):
        """Test fetching data using fixture."""
        fixture_data = load_fixture('weather', 'YYZ_observations.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = WeatherProvider()
        ref = DatasetRef(provider='weather', id='YYZ')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = provider.fetch(ref, tmpdir)
            
            # Verify contract
            assert 'dataset_id' in result
            assert 'provider' in result
            assert 'files' in result
            assert result['provider'] == 'weather'
            assert len(result['files']) == 1
            
            # Verify file was created
            output_file = Path(result['files'][0])
            assert output_file.exists()
            
            # Verify CSV content
            df = pd.read_csv(output_file)
            assert len(df) == 3
            assert 'date' in df.columns
            assert 'temp_c' in df.columns
    
    @patch('publicdata_ca.providers.weather.retry_request')
    def test_search_with_fixture(self, mock_retry):
        """Test search returns DatasetRef objects."""
        search_results = {
            "stations": [
                {
                    "id": "YYZ",
                    "name": "Toronto Pearson International Airport",
                    "location": "Toronto",
                    "province": "Ontario"
                },
                {
                    "id": "YTZ",
                    "name": "Billy Bishop Toronto City Airport",
                    "location": "Toronto",
                    "province": "Ontario"
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(search_results).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = WeatherProvider()
        results = provider.search('Toronto')
        
        # Verify contract
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(ref, DatasetRef) for ref in results)
        assert results[0].provider == 'weather'
        assert results[0].id == 'YYZ'
        assert 'title' in results[0].metadata
```

### Step 6: Create a Profile

Create a profile in `profiles/weather.yaml`:

```yaml
name: weather
description: Canadian weather station observations for major cities

datasets:
  - provider: weather
    id: YYZ
    output: data/raw/weather_toronto_yyz.csv
    params:
      start_date: "2023-01-01"
      end_date: "2023-12-31"
  
  - provider: weather
    id: YVR
    output: data/raw/weather_vancouver_yvr.csv
    params:
      start_date: "2023-01-01"
      end_date: "2023-12-31"
  
  - provider: weather
    id: YUL
    output: data/raw/weather_montreal_yul.csv
    params:
      start_date: "2023-01-01"
      end_date: "2023-12-31"

output_dir: data/raw
options:
  skip_existing: true
```

Now users can run:

```bash
# List profiles
publicdata profile list

# Run the weather profile
publicdata profile run weather

# Or use the Python API
from publicdata_ca import run_profile
report = run_profile("weather")
print(report[['dataset', 'result', 'notes']])
```

## Complete Working Example

Here's how to use your new provider:

**Python API:**

```python
from publicdata_ca.providers import WeatherProvider
from publicdata_ca.provider import DatasetRef

# Initialize provider
provider = WeatherProvider()

# Search for stations
results = provider.search('Toronto')
for ref in results:
    print(f"{ref.id}: {ref.metadata['title']}")

# Download specific station data
ref = DatasetRef(
    provider='weather',
    id='YYZ',
    params={
        'start_date': '2023-01-01',
        'end_date': '2023-12-31'
    }
)

result = provider.fetch(ref, './data/raw')
print(f"Downloaded: {result['files']}")
print(f"Observations: {result['observations']}")

# Or use helper functions directly
from publicdata_ca.providers import download_weather_data

result = download_weather_data(
    'YYZ',
    './data/raw',
    start_date='2023-01-01',
    end_date='2023-12-31'
)
```

**CLI (via profile):**

```bash
publicdata profile run weather
```

## Testing Your Provider

Run your tests:

```bash
# Run all contract tests
pytest tests/test_provider_contracts.py -v

# Run only your provider's tests
pytest tests/test_provider_contracts.py::TestWeatherProviderContract -v

# Run a specific test
pytest tests/test_provider_contracts.py::TestWeatherProviderContract::test_resolve_contract -v
```

Optional: Add smoke tests in `tests/test_provider_smoke.py`:

```python
class TestWeatherProviderSmoke:
    """Smoke tests for Weather provider (live API calls)."""
    
    @pytest.mark.smoke
    def test_fetch_live_data(self):
        """Test fetching data from live API."""
        skip_if_smoke_disabled()
        
        provider = WeatherProvider()
        ref = DatasetRef(
            provider='weather',
            id='YYZ',
            params={'start_date': '2023-01-01', 'end_date': '2023-01-03'}
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = provider.fetch(ref, tmpdir)
            
            assert result['provider'] == 'weather'
            assert len(result['files']) > 0
            assert Path(result['files'][0]).exists()
```

Run smoke tests:

```bash
pytest tests/test_provider_smoke.py::TestWeatherProviderSmoke -v -m smoke
```

## Best Practices

### Code Organization

1. **One provider per file** - Keep each provider in its own module (e.g., `providers/weather.py`)
2. **Helper functions** - Provide standalone functions for common operations
3. **Docstrings** - Document all public functions and classes with examples
4. **Type hints** - Use type hints for better IDE support and documentation

### Error Handling

1. **Raise descriptive errors** - Use `RuntimeError` with clear messages
2. **Handle API failures gracefully** - Catch exceptions and provide context
3. **Validate input** - Check required parameters before making API calls

### Metadata and Provenance

1. **Write provenance metadata** - Use `write_provenance_metadata()` for all downloads
2. **Include provider-specific metadata** - Add useful context to the `provider_specific` field
3. **Support skip_existing** - Allow users to avoid re-downloading unchanged files

### Testing

1. **Use real API responses** - Fixtures should be actual responses from the provider's API
2. **Test all interface methods** - Ensure search, resolve, and fetch are all tested
3. **Keep fixtures minimal** - Use small but realistic data
4. **Add contract tests** - These run by default and have no network dependencies
5. **Add smoke tests** - Optional, for verifying live API connectivity

### Documentation

1. **Provider docstring** - Explain what the provider does and link to API docs
2. **Function examples** - Show how to use each function
3. **Profile example** - Create a sample profile in `profiles/`
4. **Update README** - Add a section about your provider if it's widely useful

## Reference Examples

Look at existing providers for inspiration:

- **Simple provider**: `publicdata_ca/providers/boc_valet.py` - Time series data
- **CKAN-based**: `publicdata_ca/providers/ckan.py` - Generic portal support
- **StatsCan**: `publicdata_ca/providers/statcan.py` - ZIP file handling
- **CMHC**: `publicdata_ca/providers/cmhc.py` - Landing page resolution

## Additional Resources

- **Provider Interface**: See `publicdata_ca/provider.py` for the base `Provider` class
- **Testing Guide**: See `tests/TESTING.md` for detailed testing strategies
- **Profiles Guide**: See `profiles/README.md` for profile creation examples
- **HTTP Utilities**: See `publicdata_ca/http.py` for download helpers
- **Provenance**: See `publicdata_ca/provenance.py` for metadata utilities
