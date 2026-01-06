"""
Provider smoke tests - optional live endpoint testing.

These tests make actual HTTP requests to live provider endpoints to verify
that the providers still work with real-world APIs. They are:

1. Disabled by default (marked with @pytest.mark.smoke)
2. Should be minimal and fast (only test basic connectivity)
3. Should not download large datasets
4. May fail due to network issues or API changes

To run smoke tests:
    pytest tests/test_provider_smoke.py -v -m smoke

To run ALL tests including smoke tests:
    pytest tests/ -v -o addopts="-ra"

To skip smoke tests explicitly (default behavior):
    pytest tests/ -v

Environment variables:
    SKIP_SMOKE_TESTS=1  - Skip smoke tests even if explicitly requested
"""

import os
import tempfile
from pathlib import Path

import pytest

from publicdata_ca.provider import DatasetRef
from publicdata_ca.providers import (
    StatCanProvider,
    CMHCProvider,
    CKANProvider,
    SocrataProvider,
    SDMXProvider,
    ValetProvider,
    OpenCanadaProvider,
)


# Mark all tests in this module as smoke tests
pytestmark = pytest.mark.smoke


def skip_if_smoke_disabled():
    """Skip test if SKIP_SMOKE_TESTS environment variable is set."""
    if os.getenv('SKIP_SMOKE_TESTS', '').lower() in ('1', 'true', 'yes'):
        pytest.skip("Smoke tests disabled via SKIP_SMOKE_TESTS environment variable")


class TestStatCanProviderSmoke:
    """Smoke tests for StatsCan provider with live endpoints."""
    

    def test_resolve_live_endpoint(self):
        """Test resolve with a real StatsCan table ID."""
        skip_if_smoke_disabled()
        
        provider = StatCanProvider()
        ref = DatasetRef(provider='statcan', id='18100004')  # CPI table
        
        metadata = provider.resolve(ref)
        
        # Basic validation
        assert metadata['provider'] == 'statcan'
        assert metadata['pid'] == '18100004'
        assert 'url' in metadata
        assert 'statcan.gc.ca' in metadata['url']
    

    def test_fetch_small_dataset(self):
        """Test fetching a small dataset from live endpoint."""
        skip_if_smoke_disabled()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = StatCanProvider()
            ref = DatasetRef(provider='statcan', id='18100004')
            
            result = provider.fetch(ref, tmpdir, skip_existing=True)
            
            # Verify download succeeded
            assert result['provider'] == 'statcan'
            assert len(result['files']) > 0
            assert Path(result['files'][0]).exists()


class TestBOCValetProviderSmoke:
    """Smoke tests for Bank of Canada Valet provider with live endpoints."""
    

    def test_resolve_live_endpoint(self):
        """Test resolve with a real Valet series."""
        skip_if_smoke_disabled()
        
        provider = ValetProvider()
        ref = DatasetRef(provider='boc_valet', id='FXUSDCAD')  # USD exchange rate
        
        metadata = provider.resolve(ref)
        
        # Basic validation
        assert metadata['provider'] == 'boc_valet'
        assert metadata['series_name'] == 'FXUSDCAD'
        assert 'bankofcanada.ca' in metadata['url']
    

    def test_fetch_recent_data(self):
        """Test fetching recent exchange rate data."""
        skip_if_smoke_disabled()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = ValetProvider()
            ref = DatasetRef(
                provider='boc_valet',
                id='FXUSDCAD',
                params={
                    'start_date': '2024-01-01',
                    'end_date': '2024-01-31'
                }
            )
            
            result = provider.fetch(ref, tmpdir)
            
            # Verify download succeeded
            assert result['provider'] == 'boc_valet'
            assert len(result['files']) > 0
            assert Path(result['files'][0]).exists()


class TestCKANProviderSmoke:
    """Smoke tests for generic CKAN provider with live endpoints."""
    

    def test_search_live_portal(self):
        """Test search on a live CKAN portal."""
        skip_if_smoke_disabled()
        
        # Use data.gov as a test CKAN portal
        provider = CKANProvider(base_url='https://catalog.data.gov')
        
        try:
            results = provider.search('climate', rows=5)
            
            # Basic validation
            assert isinstance(results, list)
            # May have 0 results if API changes, but should not error
            if len(results) > 0:
                assert all(r.provider == 'ckan' for r in results)
        except Exception as e:
            pytest.skip(f"CKAN portal unavailable or changed: {e}")


class TestOpenCanadaProviderSmoke:
    """Smoke tests for Open Canada provider with live endpoints."""
    

    def test_search_live_portal(self):
        """Test search on Open Canada portal."""
        skip_if_smoke_disabled()
        
        provider = OpenCanadaProvider()
        
        try:
            results = provider.search('housing', rows=5)
            
            # Basic validation
            assert isinstance(results, list)
            # May have 0 results if API changes, but should not error
            if len(results) > 0:
                assert all(r.provider == 'open_canada' for r in results)
        except Exception as e:
            pytest.skip(f"Open Canada portal unavailable or changed: {e}")


class TestSocrataProviderSmoke:
    """Smoke tests for Socrata provider with live endpoints."""
    

    def test_search_live_portal(self):
        """Test search on a live Socrata portal."""
        skip_if_smoke_disabled()
        
        # Use data.ontario.ca as a test Socrata portal
        provider = SocrataProvider(base_url='https://data.ontario.ca')
        
        try:
            results = provider.search('health', limit=5)
            
            # Basic validation
            assert isinstance(results, list)
            # May have 0 results if API changes, but should not error
            if len(results) > 0:
                assert all(r.provider == 'socrata' for r in results)
        except Exception as e:
            pytest.skip(f"Socrata portal unavailable or changed: {e}")


class TestSDMXProviderSmoke:
    """Smoke tests for SDMX provider with live endpoints."""
    

    def test_resolve_live_dataflow(self):
        """Test resolve with a live SDMX endpoint."""
        skip_if_smoke_disabled()
        
        # Use OECD SDMX endpoint as test
        provider = SDMXProvider(base_url='https://sdmx.oecd.org/public/rest')
        ref = DatasetRef(
            provider='sdmx',
            id='QNA',  # Quarterly National Accounts
            params={'agency_id': 'OECD'}
        )
        
        try:
            metadata = provider.resolve(ref)
            
            # Basic validation
            assert metadata['provider'] == 'sdmx'
            assert 'dataflow_metadata' in metadata
        except Exception as e:
            pytest.skip(f"SDMX endpoint unavailable or changed: {e}")


class TestCMHCProviderSmoke:
    """Smoke tests for CMHC provider with live endpoints."""
    

    def test_resolve_direct_url(self):
        """Test resolve with direct URL (no network required)."""
        skip_if_smoke_disabled()
        
        provider = CMHCProvider()
        ref = DatasetRef(
            provider='cmhc',
            id='test-dataset',
            params={'direct_url': 'https://www.cmhc-schl.gc.ca/sites/default/files/test.xlsx'}
        )
        
        metadata = provider.resolve(ref)
        
        # Basic validation (doesn't actually fetch, just resolves)
        assert metadata['provider'] == 'cmhc'
        assert metadata['format'] == 'xlsx'


class TestProviderSmokeConsistency:
    """Cross-provider smoke tests."""
    

    def test_all_providers_can_be_instantiated(self):
        """Verify all providers can be instantiated without errors."""
        skip_if_smoke_disabled()
        
        providers = [
            StatCanProvider(),
            CMHCProvider(),
            CKANProvider(base_url='https://example.com'),
            SocrataProvider(base_url='https://data.example.com'),
            SDMXProvider(base_url='https://example.org/rest'),
            ValetProvider(),
            OpenCanadaProvider(),
        ]
        
        # All should instantiate successfully
        assert len(providers) == 7
        assert all(p is not None for p in providers)
