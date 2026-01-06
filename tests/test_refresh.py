"""Tests for the refresh_datasets function."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from publicdata_ca.datasets import Dataset, refresh_datasets


@pytest.fixture
def mock_datasets(tmp_path, monkeypatch):
    """Create mock datasets for testing."""
    from publicdata_ca import datasets as ds_module
    
    # Mock RAW_DATA_DIR to use tmp_path
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", raw_dir)
    
    return [
        Dataset(
            dataset="test_statcan_table",
            provider="statcan",
            metric="Test StatsCan metric",
            pid="12345678",
            frequency="Annual",
            geo_scope="Canada",
            delivery="download_statcan_table",
            target_file=raw_dir / "test_statcan.csv",
            automation_status="automatic",
            status_note="Test dataset",
        ),
        Dataset(
            dataset="test_cmhc_direct",
            provider="cmhc",
            metric="Test CMHC metric",
            pid=None,
            frequency="Annual",
            geo_scope="Canada",
            delivery="download_cmhc_asset",
            target_file=raw_dir / "test_cmhc.xlsx",
            automation_status="semi-automatic",
            status_note="Test CMHC dataset",
            direct_url="https://example.com/data.xlsx",
        ),
        Dataset(
            dataset="test_cmhc_page",
            provider="cmhc",
            metric="Test CMHC page metric",
            pid=None,
            frequency="Annual",
            geo_scope="Canada",
            delivery="download_cmhc_asset",
            target_file=raw_dir / "test_cmhc_page.xlsx",
            automation_status="semi-automatic",
            status_note="Test CMHC dataset with page URL",
            page_url="https://example.com/landing",
        ),
        Dataset(
            dataset="test_missing_target",
            provider="statcan",
            metric="Test missing target",
            pid="87654321",
            frequency="Annual",
            geo_scope="Canada",
            delivery="download_statcan_table",
            target_file=None,
            automation_status="manual",
            status_note="No target configured",
        ),
    ]


def test_refresh_datasets_returns_dataframe(mock_datasets):
    """Test that refresh_datasets returns a DataFrame with correct structure."""
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_statcan, \
         patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_cmhc, \
         patch("publicdata_ca.resolvers.cmhc_landing.resolve_cmhc_landing_page") as mock_resolve:
        
        # Setup mocks
        mock_statcan.return_value = {"files": ["test.csv"], "skipped": False}
        mock_cmhc.return_value = {"files": ["test.xlsx"], "errors": []}
        mock_resolve.return_value = [{"url": "https://example.com/resolved.xlsx"}]
        
        result = refresh_datasets(datasets=mock_datasets[:1])
        
        assert isinstance(result, pd.DataFrame)
        assert "dataset" in result.columns
        assert "provider" in result.columns
        assert "target_file" in result.columns
        assert "result" in result.columns
        assert "notes" in result.columns
        assert "run_started_utc" in result.columns


def test_refresh_datasets_downloads_missing_statcan_files(mock_datasets):
    """Test that refresh_datasets downloads missing StatsCan files."""
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_download:
        mock_download.return_value = {"files": ["test.csv"], "skipped": False}
        
        result = refresh_datasets(datasets=mock_datasets[:1])
        
        # Should attempt download since file doesn't exist
        mock_download.assert_called_once()
        assert result.iloc[0]["result"] == "downloaded"


def test_refresh_datasets_skips_existing_statcan_files(mock_datasets, tmp_path):
    """Test that refresh_datasets skips existing StatsCan files by default."""
    # Create the file
    statcan_dataset = mock_datasets[0]
    statcan_dataset.target_file.parent.mkdir(parents=True, exist_ok=True)
    statcan_dataset.target_file.write_text("existing data")
    
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_download:
        mock_download.return_value = {"files": ["test.csv"], "skipped": True}
        
        result = refresh_datasets(datasets=[statcan_dataset])
        
        # Should skip download since file exists
        assert result.iloc[0]["result"] == "exists"
        assert "already present" in result.iloc[0]["notes"].lower()


def test_refresh_datasets_force_download_statcan(mock_datasets, tmp_path):
    """Test that force_download re-downloads existing StatsCan files."""
    # Create the file
    statcan_dataset = mock_datasets[0]
    statcan_dataset.target_file.parent.mkdir(parents=True, exist_ok=True)
    statcan_dataset.target_file.write_text("existing data")
    
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_download:
        mock_download.return_value = {"files": ["test.csv"], "skipped": False}
        
        result = refresh_datasets(datasets=[statcan_dataset], force_download=True)
        
        # Should download even though file exists
        mock_download.assert_called_once()
        assert result.iloc[0]["result"] == "downloaded"


def test_refresh_datasets_handles_cmhc_direct_url(mock_datasets):
    """Test that refresh_datasets handles CMHC datasets with direct URLs."""
    with patch("publicdata_ca.http.download_file") as mock_download:
        mock_download.return_value = str(mock_datasets[1].target_file)
        
        result = refresh_datasets(datasets=[mock_datasets[1]])
        
        mock_download.assert_called_once()
        assert result.iloc[0]["result"] == "downloaded"
        assert "direct URL" in result.iloc[0]["notes"]


def test_refresh_datasets_resolves_cmhc_landing_page(mock_datasets):
    """Test that refresh_datasets resolves CMHC landing pages."""
    with patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_download:
        mock_download.return_value = {"files": ["test.xlsx"], "errors": []}
        
        result = refresh_datasets(datasets=[mock_datasets[2]])
        
        # Should call download_cmhc_asset with the landing page URL
        mock_download.assert_called_once()
        assert result.iloc[0]["result"] == "downloaded"
        assert "landing page" in result.iloc[0]["notes"]


def test_refresh_datasets_handles_missing_target(mock_datasets):
    """Test that refresh_datasets handles datasets with missing target files."""
    result = refresh_datasets(datasets=[mock_datasets[3]])
    
    assert result.iloc[0]["result"] == "missing_target"
    assert "No target_file configured" in result.iloc[0]["notes"]


def test_refresh_datasets_handles_statcan_errors(mock_datasets):
    """Test that refresh_datasets handles StatsCan download errors gracefully."""
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_download:
        mock_download.side_effect = RuntimeError("Network error")
        
        result = refresh_datasets(datasets=[mock_datasets[0]])
        
        assert result.iloc[0]["result"] == "error"
        assert "Network error" in result.iloc[0]["notes"]


def test_refresh_datasets_handles_cmhc_errors(mock_datasets):
    """Test that refresh_datasets handles CMHC download errors gracefully."""
    with patch("publicdata_ca.http.download_file") as mock_download:
        mock_download.side_effect = RuntimeError("Download failed")
        
        result = refresh_datasets(datasets=[mock_datasets[1]])
        
        assert result.iloc[0]["result"] == "error"
        assert "Download failed" in result.iloc[0]["notes"]


def test_refresh_datasets_handles_cmhc_no_files(mock_datasets):
    """Test that refresh_datasets handles CMHC downloads with no files."""
    with patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_download:
        mock_download.return_value = {"files": [], "errors": []}
        
        result = refresh_datasets(datasets=[mock_datasets[2]])
        
        assert result.iloc[0]["result"] == "error"
        assert "No files downloaded" in result.iloc[0]["notes"]


def test_refresh_datasets_handles_cmhc_with_errors(mock_datasets):
    """Test that refresh_datasets handles CMHC downloads with errors."""
    with patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_download:
        mock_download.return_value = {
            "files": [],
            "errors": ["Error 1: Failed to download", "Error 2: Invalid URL"]
        }
        
        result = refresh_datasets(datasets=[mock_datasets[2]])
        
        assert result.iloc[0]["result"] == "error"
        # Should include first 2 errors
        assert "Error 1" in result.iloc[0]["notes"]


def test_refresh_datasets_handles_resolution_failure(mock_datasets, monkeypatch):
    """Test that refresh_datasets handles CMHC datasets with no URLs."""
    from publicdata_ca import datasets as ds_module
    
    # Create a CMHC dataset with no URLs
    raw_dir = mock_datasets[0].target_file.parent
    no_url_dataset = Dataset(
        dataset="test_cmhc_no_url",
        provider="cmhc",
        metric="Test CMHC metric",
        pid=None,
        frequency="Annual",
        geo_scope="Canada",
        delivery="download_cmhc_asset",
        target_file=raw_dir / "test_cmhc_no_url.xlsx",
        automation_status="manual",
        status_note="No URL configured",
        page_url=None,
        direct_url=None,
    )
    
    result = refresh_datasets(datasets=[no_url_dataset])
    
    assert result.iloc[0]["result"] == "manual_required"
    assert "No direct_url or page_url available" in result.iloc[0]["notes"]


def test_refresh_datasets_handles_resolution_exception(mock_datasets):
    """Test that refresh_datasets handles CMHC download exceptions from landing pages."""
    with patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_download:
        mock_download.side_effect = Exception("Failed to fetch page")
        
        result = refresh_datasets(datasets=[mock_datasets[2]])
        
        assert result.iloc[0]["result"] == "error"
        assert "Failed to fetch page" in result.iloc[0]["notes"]


def test_refresh_datasets_uses_default_datasets():
    """Test that refresh_datasets uses DEFAULT_DATASETS when no datasets provided."""
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_statcan, \
         patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_cmhc, \
         patch("publicdata_ca.http.download_file") as mock_download_file:
        
        mock_statcan.return_value = {"files": ["test.csv"], "skipped": True}
        mock_cmhc.return_value = {"files": ["test.xlsx"], "errors": []}
        mock_download_file.return_value = "/path/to/file.xlsx"
        
        result = refresh_datasets()
        
        # Should process all default datasets
        assert len(result) > 0
        assert "dataset" in result.columns


def test_refresh_datasets_handles_unknown_provider(tmp_path, monkeypatch):
    """Test that refresh_datasets handles unknown providers."""
    from publicdata_ca import datasets as ds_module
    
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", raw_dir)
    
    unknown_dataset = Dataset(
        dataset="test_unknown",
        provider="unknown_provider",
        metric="Test unknown",
        pid=None,
        frequency="Annual",
        geo_scope="Canada",
        delivery="unknown",
        target_file=raw_dir / "test.csv",
        automation_status="manual",
        status_note="Unknown provider",
    )
    
    result = refresh_datasets(datasets=[unknown_dataset])
    
    assert result.iloc[0]["result"] == "unknown_provider"
    assert "Unhandled provider" in result.iloc[0]["notes"]


def test_refresh_datasets_timestamp_format(mock_datasets):
    """Test that refresh_datasets includes properly formatted timestamps."""
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_download:
        mock_download.return_value = {"files": ["test.csv"], "skipped": False}
        
        result = refresh_datasets(datasets=mock_datasets[:1])
        
        timestamp = result.iloc[0]["run_started_utc"]
        assert isinstance(timestamp, str)
        # Should be ISO format with Z suffix
        assert timestamp.endswith("Z")
        # Should contain date and time
        assert "T" in timestamp
