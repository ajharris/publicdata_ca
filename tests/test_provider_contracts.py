"""
Provider contract tests using offline fixtures.

This module contains comprehensive contract tests for all providers using
real API response fixtures instead of mocks. These tests validate that:
1. Providers correctly implement the Provider interface (search, resolve, fetch)
2. Providers correctly parse real API responses
3. Provider behavior is consistent and predictable

Each provider has its own test class with fixtures stored in tests/fixtures/<provider>/.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from publicdata_ca.provider import Provider, DatasetRef
from publicdata_ca.providers import (
    StatCanProvider,
    CMHCProvider,
    CKANProvider,
    SocrataProvider,
    SDMXProvider,
    ValetProvider,
    OpenCanadaProvider,
)


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


def load_fixture(provider_name: str, filename: str):
    """Load a fixture file for a given provider."""
    fixture_path = FIXTURES_DIR / provider_name / filename
    
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    
    if fixture_path.suffix == '.json':
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return f.read()


class TestBOCValetProviderContract:
    """Contract tests for Bank of Canada Valet provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify ValetProvider implements the Provider interface."""
        provider = ValetProvider()
        assert isinstance(provider, Provider)
        assert hasattr(provider, 'search')
        assert hasattr(provider, 'resolve')
        assert hasattr(provider, 'fetch')
    
    def test_resolve_with_fixture(self):
        """Test resolve returns correct metadata structure."""
        provider = ValetProvider()
        ref = DatasetRef(provider='boc_valet', id='FXUSDCAD')
        
        metadata = provider.resolve(ref)
        
        # Verify contract: metadata must have these keys
        assert 'series_name' in metadata
        assert 'format' in metadata
        assert 'provider' in metadata
        assert 'url' in metadata
        assert metadata['series_name'] == 'FXUSDCAD'
        assert metadata['format'] == 'json'
        assert metadata['provider'] == 'boc_valet'
    
    @patch('publicdata_ca.providers.boc_valet.retry_request')
    def test_fetch_valet_series_with_fixture(self, mock_retry):
        """Test fetching series data using fixture."""
        fixture_data = load_fixture('boc_valet', 'FXUSDCAD_observations.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        from publicdata_ca.providers.boc_valet import fetch_valet_series
        
        data = fetch_valet_series('FXUSDCAD')
        
        # Verify contract
        assert 'series_name' in data
        assert 'observations' in data
        assert 'metadata' in data
        assert 'url' in data
        assert data['series_name'] == 'FXUSDCAD'
        assert len(data['observations']) == 3
        assert data['observations'][0]['d'] == '2023-01-03'
        assert data['observations'][0]['v'] == '1.3500'
    
    @patch('publicdata_ca.providers.boc_valet.download_valet_series')
    def test_provider_fetch_contract(self, mock_download, tmp_path):
        """Test Provider.fetch() contract is fulfilled."""
        mock_download.return_value = {
            'dataset_id': 'boc_valet_FXUSDCAD',
            'provider': 'boc_valet',
            'files': [str(tmp_path / 'FXUSDCAD.csv')],
            'url': 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json',
            'series_name': 'FXUSDCAD',
            'metadata': {},
            'observations': 3,
            'skipped': False
        }
        
        provider = ValetProvider()
        ref = DatasetRef(provider='boc_valet', id='FXUSDCAD')
        
        result = provider.fetch(ref, str(tmp_path))
        
        # Verify fetch contract
        assert 'provider' in result
        assert 'files' in result
        assert result['provider'] == 'boc_valet'
        assert isinstance(result['files'], list)


class TestCKANProviderContract:
    """Contract tests for CKAN provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify CKANProvider implements the Provider interface."""
        provider = CKANProvider(base_url='https://example.com')
        assert isinstance(provider, Provider)
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_search_with_fixture(self, mock_retry):
        """Test search using fixture data."""
        fixture_data = load_fixture('ckan', 'search_response.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = CKANProvider(base_url='https://example.com')
        results = provider.search('census')
        
        # Verify search contract
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, DatasetRef) for r in results)
        assert results[0].provider == 'ckan'
        assert results[0].id == 'census-2021'
        assert 'title' in results[0].metadata
        assert results[0].metadata['title'] == 'Census 2021 Population Data'
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_resolve_with_fixture(self, mock_retry):
        """Test resolve using fixture data."""
        fixture_data = load_fixture('ckan', 'package_response.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = CKANProvider(base_url='https://example.com')
        ref = DatasetRef(provider='ckan', id='census-2021')
        
        metadata = provider.resolve(ref)
        
        # Verify resolve contract
        assert 'package_id' in metadata
        assert 'title' in metadata
        assert 'provider' in metadata
        assert 'resources' in metadata
        assert metadata['package_id'] == 'census-2021'
        assert metadata['provider'] == 'ckan'
        assert len(metadata['resources']) == 2


class TestSDMXProviderContract:
    """Contract tests for SDMX provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify SDMXProvider implements the Provider interface."""
        provider = SDMXProvider(base_url='https://example.org/rest')
        assert isinstance(provider, Provider)
    
    @patch('publicdata_ca.providers.sdmx.retry_request')
    def test_resolve_with_xml_fixture(self, mock_retry):
        """Test resolve using XML fixture data."""
        fixture_data = load_fixture('sdmx', 'dataflow_response.xml')
        
        mock_response = Mock()
        mock_response.read.return_value = fixture_data.encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = SDMXProvider(base_url='https://example.org/rest')
        ref = DatasetRef(provider='sdmx', id='OECD,QNA,1.0')
        
        metadata = provider.resolve(ref)
        
        # Verify resolve contract
        assert 'dataflow_id' in metadata
        assert 'dataflow_metadata' in metadata
        assert 'provider' in metadata
        assert metadata['dataflow_id'] == 'OECD,QNA,1.0'
        assert metadata['provider'] == 'sdmx'
    
    @patch('publicdata_ca.providers.sdmx.retry_request')
    def test_fetch_sdmx_data_xml_fixture(self, mock_retry):
        """Test fetching SDMX data using XML fixture."""
        fixture_data = load_fixture('sdmx', 'data_response.xml')
        
        mock_response = Mock()
        mock_response.read.return_value = fixture_data.encode('utf-8')
        mock_retry.return_value = mock_response
        
        from publicdata_ca.providers.sdmx import fetch_sdmx_data
        
        result = fetch_sdmx_data(
            'https://example.org/rest',
            'OECD,QNA,1.0',
            key='AUS...'
        )
        
        # Verify fetch contract
        assert 'format' in result
        assert 'dataflow' in result
        assert 'raw_data' in result
        assert result['format'] == 'sdmx-ml'
        assert result['dataflow'] == 'OECD,QNA,1.0'
        assert 'GenericData' in result['raw_data']
    
    @patch('publicdata_ca.providers.sdmx.retry_request')
    def test_fetch_sdmx_data_json_fixture(self, mock_retry):
        """Test fetching SDMX data using JSON fixture."""
        fixture_data = load_fixture('sdmx', 'data_response.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        from publicdata_ca.providers.sdmx import fetch_sdmx_data
        
        result = fetch_sdmx_data(
            'https://example.org/rest',
            'OECD,QNA,1.0',
            format='sdmx-json'
        )
        
        # Verify fetch contract
        assert result['format'] == 'sdmx-json'
        assert isinstance(result['raw_data'], dict)
        assert 'data' in result['raw_data']


class TestSocrataProviderContract:
    """Contract tests for Socrata provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify SocrataProvider implements the Provider interface."""
        provider = SocrataProvider(base_url='https://data.example.com')
        assert isinstance(provider, Provider)
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_search_with_fixture(self, mock_retry):
        """Test search using fixture data."""
        fixture_data = load_fixture('socrata', 'search_response.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = SocrataProvider(base_url='https://data.example.com')
        results = provider.search('housing')
        
        # Verify search contract
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, DatasetRef) for r in results)
        assert results[0].provider == 'socrata'
        assert results[0].id == 'housing-2023'
    
    @patch('publicdata_ca.providers.socrata.retry_request')
    def test_resolve_with_fixture(self, mock_retry):
        """Test resolve using fixture data."""
        fixture_data = load_fixture('socrata', 'metadata_response.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = SocrataProvider(base_url='https://data.example.com')
        ref = DatasetRef(provider='socrata', id='abc-123')
        
        metadata = provider.resolve(ref)
        
        # Verify resolve contract
        assert 'dataset_id' in metadata
        assert 'name' in metadata
        assert 'provider' in metadata
        assert metadata['dataset_id'] == 'abc-123'
        assert metadata['provider'] == 'socrata'


class TestOpenCanadaProviderContract:
    """Contract tests for Open Canada provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify OpenCanadaProvider implements the Provider interface."""
        provider = OpenCanadaProvider()
        assert isinstance(provider, Provider)
        assert provider.name == 'open_canada'
    
    @patch('publicdata_ca.providers.ckan.retry_request')
    def test_search_with_fixture(self, mock_retry):
        """Test search using fixture data."""
        fixture_data = load_fixture('open_canada', 'search_response.json')
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fixture_data).encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = OpenCanadaProvider()
        results = provider.search('housing')
        
        # Verify search contract
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, DatasetRef) for r in results)
        assert results[0].provider == 'open_canada'
        assert results[0].id == 'canadian-housing-data'
        assert results[0].metadata['title'] == 'Canadian Housing Market Data'


class TestStatCanProviderContract:
    """Contract tests for StatsCan provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify StatCanProvider implements the Provider interface."""
        provider = StatCanProvider()
        assert isinstance(provider, Provider)
        assert provider.name == 'statcan'
    
    def test_resolve_contract(self):
        """Test resolve returns correct metadata structure."""
        provider = StatCanProvider()
        ref = DatasetRef(provider='statcan', id='18100004')
        
        metadata = provider.resolve(ref)
        
        # Verify resolve contract
        assert 'provider' in metadata
        assert 'pid' in metadata
        assert 'format' in metadata
        assert 'url' in metadata
        assert metadata['provider'] == 'statcan'
        assert metadata['pid'] == '18100004'
        assert metadata['format'] == 'csv'
        assert '18100004' in metadata['url']
    
    @patch('publicdata_ca.providers.statcan.download_file')
    def test_fetch_contract(self, mock_download, tmp_path):
        """Test Provider.fetch() contract with fixture."""
        # Use the real fixture file
        fixture_path = FIXTURES_DIR / 'statcan' / '18100004.zip'
        
        def mock_download_fn(url, path, max_retries, write_metadata=True, headers=None):
            import shutil
            shutil.copy(fixture_path, path)
            return path
        
        mock_download.side_effect = mock_download_fn
        
        provider = StatCanProvider()
        ref = DatasetRef(provider='statcan', id='18100004')
        
        result = provider.fetch(ref, str(tmp_path))
        
        # Verify fetch contract
        assert 'provider' in result
        assert 'dataset_id' in result
        assert 'files' in result
        assert result['provider'] == 'statcan'
        assert result['dataset_id'] == 'statcan_18100004'
        assert len(result['files']) > 0


class TestCMHCProviderContract:
    """Contract tests for CMHC provider using fixtures."""
    
    def test_provider_implements_interface(self):
        """Verify CMHCProvider implements the Provider interface."""
        provider = CMHCProvider()
        assert isinstance(provider, Provider)
        assert provider.name == 'cmhc'
    
    def test_resolve_with_direct_url(self):
        """Test resolve with direct URL."""
        provider = CMHCProvider()
        ref = DatasetRef(
            provider='cmhc',
            id='housing-data',
            params={'direct_url': 'https://example.com/housing.xlsx'}
        )
        
        metadata = provider.resolve(ref)
        
        # Verify resolve contract
        assert 'provider' in metadata
        assert 'url' in metadata
        assert 'format' in metadata
        assert metadata['provider'] == 'cmhc'
        assert metadata['url'] == 'https://example.com/housing.xlsx'
        assert metadata['format'] == 'xlsx'
    
    @patch('publicdata_ca.resolvers.cmhc_landing.retry_request')
    def test_resolve_with_landing_page_fixture(self, mock_retry):
        """Test resolve with landing page using fixture."""
        fixture_html = load_fixture('cmhc', 'sample_landing_page.html')
        
        mock_response = Mock()
        mock_response.read.return_value = fixture_html.encode('utf-8')
        mock_retry.return_value = mock_response
        
        provider = CMHCProvider()
        ref = DatasetRef(
            provider='cmhc',
            id='housing-data',
            params={'page_url': 'https://example.com/landing'}
        )
        
        metadata = provider.resolve(ref)
        
        # Verify resolve contract
        assert 'provider' in metadata
        assert 'assets' in metadata
        assert metadata['provider'] == 'cmhc'
        assert len(metadata['assets']) > 0


class TestProviderContractConsistency:
    """Cross-provider tests to ensure consistent behavior."""
    
    def test_all_providers_inherit_from_provider_base(self):
        """Verify all providers inherit from Provider base class."""
        providers = [
            StatCanProvider(),
            CMHCProvider(),
            CKANProvider(base_url='https://example.com'),
            SocrataProvider(base_url='https://data.example.com'),
            SDMXProvider(base_url='https://example.org/rest'),
            ValetProvider(),
            OpenCanadaProvider(),
        ]
        
        for provider in providers:
            assert isinstance(provider, Provider)
    
    def test_all_providers_have_name_attribute(self):
        """Verify all providers have a name attribute."""
        providers = [
            (StatCanProvider(), 'statcan'),
            (CMHCProvider(), 'cmhc'),
            (CKANProvider(base_url='https://example.com'), 'ckan'),
            (SocrataProvider(base_url='https://data.example.com'), 'socrata'),
            (SDMXProvider(base_url='https://example.org/rest'), 'sdmx'),
            (ValetProvider(), 'boc_valet'),
            (OpenCanadaProvider(), 'open_canada'),
        ]
        
        for provider, expected_name in providers:
            assert hasattr(provider, 'name')
            assert provider.name == expected_name
    
    def test_all_providers_implement_required_methods(self):
        """Verify all providers implement search, resolve, fetch."""
        providers = [
            StatCanProvider(),
            CMHCProvider(),
            CKANProvider(base_url='https://example.com'),
            SocrataProvider(base_url='https://data.example.com'),
            SDMXProvider(base_url='https://example.org/rest'),
            ValetProvider(),
            OpenCanadaProvider(),
        ]
        
        for provider in providers:
            assert hasattr(provider, 'search')
            assert callable(provider.search)
            assert hasattr(provider, 'resolve')
            assert callable(provider.resolve)
            assert hasattr(provider, 'fetch')
            assert callable(provider.fetch)
    
    def test_resolve_returns_dict_with_provider_key(self):
        """Verify all providers' resolve() returns dict with 'provider' key."""
        test_cases = [
            (StatCanProvider(), DatasetRef(provider='statcan', id='18100004')),
            (CMHCProvider(), DatasetRef(
                provider='cmhc',
                id='test',
                params={'direct_url': 'https://example.com/data.xlsx'}
            )),
            (ValetProvider(), DatasetRef(provider='boc_valet', id='FXUSDCAD')),
        ]
        
        for provider, ref in test_cases:
            metadata = provider.resolve(ref)
            assert isinstance(metadata, dict)
            assert 'provider' in metadata
