"""Tests for the profiles system."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from publicdata_ca.profiles import (
    Profile,
    ProfileDataset,
    ProfileSearch,
    load_profile,
    save_profile,
    list_profiles,
    run_profile,
    PROFILES_DIR,
)


# Check if PyYAML is available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@pytest.fixture
def temp_profiles_dir(tmp_path):
    """Create a temporary profiles directory."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    return profiles_dir


@pytest.fixture
def sample_profile():
    """Create a sample profile for testing."""
    return Profile(
        name="test_profile",
        description="Test profile for unit tests",
        datasets=[
            ProfileDataset(
                provider="statcan",
                id="18100004",
                output="data/raw/cpi.csv",
                params={"frequency": "Monthly"}
            ),
            ProfileDataset(
                provider="cmhc",
                id="housing_starts",
                output="data/raw/housing.xlsx",
                params={"page_url": "https://example.com/housing"}
            ),
        ],
        output_dir="data/raw",
        options={"skip_existing": True}
    )


def test_profile_creation():
    """Test creating a Profile object."""
    profile = Profile(
        name="test",
        description="Test profile"
    )
    
    assert profile.name == "test"
    assert profile.description == "Test profile"
    assert profile.datasets == []
    assert profile.search is None
    assert profile.output_dir is None
    assert profile.options == {}


def test_profile_with_datasets():
    """Test creating a Profile with datasets."""
    dataset = ProfileDataset(
        provider="statcan",
        id="18100004",
        output="data/raw/test.csv"
    )
    
    profile = Profile(
        name="test",
        description="Test",
        datasets=[dataset]
    )
    
    assert len(profile.datasets) == 1
    assert profile.datasets[0].provider == "statcan"
    assert profile.datasets[0].id == "18100004"
    assert profile.datasets[0].output == "data/raw/test.csv"


def test_profile_with_search():
    """Test creating a Profile with search specification."""
    search = ProfileSearch(
        provider="statcan",
        query="consumer price",
        filters={"frequency": "Monthly"},
        limit=10
    )
    
    profile = Profile(
        name="test",
        description="Test",
        search=search
    )
    
    assert profile.search is not None
    assert profile.search.provider == "statcan"
    assert profile.search.query == "consumer price"
    assert profile.search.filters == {"frequency": "Monthly"}
    assert profile.search.limit == 10


def test_profile_to_dict(sample_profile):
    """Test converting a Profile to dictionary."""
    data = sample_profile.to_dict()
    
    assert data["name"] == "test_profile"
    assert data["description"] == "Test profile for unit tests"
    assert len(data["datasets"]) == 2
    assert data["datasets"][0]["provider"] == "statcan"
    assert data["datasets"][0]["id"] == "18100004"
    assert data["output_dir"] == "data/raw"
    assert data["options"] == {"skip_existing": True}


def test_profile_from_dict():
    """Test creating a Profile from dictionary."""
    data = {
        "name": "test",
        "description": "Test profile",
        "datasets": [
            {
                "provider": "statcan",
                "id": "18100004",
                "output": "data/raw/test.csv",
                "params": {"frequency": "Monthly"}
            }
        ],
        "output_dir": "data/raw",
        "options": {"skip_existing": True}
    }
    
    profile = Profile.from_dict(data)
    
    assert profile.name == "test"
    assert profile.description == "Test profile"
    assert len(profile.datasets) == 1
    assert profile.datasets[0].provider == "statcan"
    assert profile.datasets[0].id == "18100004"
    assert profile.output_dir == "data/raw"


def test_profile_from_dict_with_search():
    """Test creating a Profile from dictionary with search."""
    data = {
        "name": "test",
        "description": "Test",
        "search": {
            "provider": "statcan",
            "query": "consumer price",
            "filters": {"frequency": "Monthly"},
            "limit": 5
        }
    }
    
    profile = Profile.from_dict(data)
    
    assert profile.search is not None
    assert profile.search.provider == "statcan"
    assert profile.search.query == "consumer price"
    assert profile.search.limit == 5


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_save_profile(sample_profile, temp_profiles_dir):
    """Test saving a profile to YAML file."""
    profile_path = temp_profiles_dir / "test.yaml"
    
    saved_path = save_profile(sample_profile, profile_path)
    
    assert saved_path.exists()
    assert saved_path == profile_path
    
    # Verify the file contains YAML
    with open(profile_path, "r") as f:
        import yaml
        data = yaml.safe_load(f)
    
    assert data["name"] == "test_profile"
    assert len(data["datasets"]) == 2


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_load_profile(sample_profile, temp_profiles_dir):
    """Test loading a profile from YAML file."""
    profile_path = temp_profiles_dir / "test.yaml"
    save_profile(sample_profile, profile_path)
    
    loaded_profile = load_profile(profile_path)
    
    assert loaded_profile.name == sample_profile.name
    assert loaded_profile.description == sample_profile.description
    assert len(loaded_profile.datasets) == len(sample_profile.datasets)
    assert loaded_profile.output_dir == sample_profile.output_dir


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_load_profile_missing_file():
    """Test loading a profile from non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent.yaml")


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_load_profile_invalid_yaml(temp_profiles_dir):
    """Test loading an invalid profile file."""
    profile_path = temp_profiles_dir / "invalid.yaml"
    
    # Create a YAML file without required 'name' field
    with open(profile_path, "w") as f:
        import yaml
        yaml.safe_dump({"description": "Missing name"}, f)
    
    with pytest.raises(ValueError, match="must have a 'name' field"):
        load_profile(profile_path)


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_list_profiles(temp_profiles_dir):
    """Test listing profiles in a directory."""
    # Create some test profiles
    for i in range(3):
        profile = Profile(name=f"profile_{i}", description=f"Profile {i}")
        save_profile(profile, temp_profiles_dir / f"profile_{i}.yaml")
    
    profiles = list_profiles(temp_profiles_dir)
    
    assert len(profiles) == 3
    assert "profile_0" in profiles
    assert "profile_1" in profiles
    assert "profile_2" in profiles


def test_list_profiles_empty_dir(temp_profiles_dir):
    """Test listing profiles in an empty directory."""
    profiles = list_profiles(temp_profiles_dir)
    assert profiles == []


def test_list_profiles_nonexistent_dir():
    """Test listing profiles in a non-existent directory."""
    profiles = list_profiles("/nonexistent/directory")
    assert profiles == []


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_run_profile_with_datasets(sample_profile, temp_profiles_dir, tmp_path, monkeypatch):
    """Test running a profile with dataset specifications."""
    from publicdata_ca import datasets as ds_module
    
    # Mock RAW_DATA_DIR
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", raw_dir)
    
    # Save profile
    profile_path = temp_profiles_dir / "test.yaml"
    save_profile(sample_profile, profile_path)
    
    # Mock the download functions
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_statcan, \
         patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_cmhc:
        
        mock_statcan.return_value = {"files": ["test.csv"], "skipped": False}
        mock_cmhc.return_value = {"files": ["test.xlsx"], "errors": []}
        
        result = run_profile(profile_path)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "dataset" in result.columns
        assert "provider" in result.columns
        assert "result" in result.columns


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_run_profile_by_name(sample_profile, temp_profiles_dir, tmp_path, monkeypatch):
    """Test running a profile by name."""
    from publicdata_ca import datasets as ds_module
    from publicdata_ca import profiles as prof_module
    
    # Mock directories
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", raw_dir)
    monkeypatch.setattr(prof_module, "PROFILES_DIR", temp_profiles_dir)
    
    # Save profile
    save_profile(sample_profile, temp_profiles_dir / "test_profile.yaml")
    
    # Mock the download functions
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_statcan, \
         patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_cmhc:
        
        mock_statcan.return_value = {"files": ["test.csv"], "skipped": False}
        mock_cmhc.return_value = {"files": ["test.xlsx"], "errors": []}
        
        result = run_profile("test_profile")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_run_profile_with_profile_object(tmp_path, monkeypatch):
    """Test running a profile using a Profile object."""
    from publicdata_ca import datasets as ds_module
    
    # Mock RAW_DATA_DIR
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", raw_dir)
    
    # Create profile
    profile = Profile(
        name="direct_test",
        description="Test direct profile",
        datasets=[
            ProfileDataset(
                provider="statcan",
                id="18100004",
                output="data/raw/test.csv"
            )
        ]
    )
    
    # Mock the download function
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_statcan:
        mock_statcan.return_value = {"files": ["test.csv"], "skipped": False}
        
        result = run_profile(profile)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["provider"] == "statcan"


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_run_profile_force_download(sample_profile, temp_profiles_dir, tmp_path, monkeypatch):
    """Test running a profile with force_download option."""
    from publicdata_ca import datasets as ds_module
    
    # Mock RAW_DATA_DIR
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", raw_dir)
    
    # Save profile
    profile_path = temp_profiles_dir / "test.yaml"
    save_profile(sample_profile, profile_path)
    
    # Mock the download functions
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_statcan, \
         patch("publicdata_ca.providers.cmhc.download_cmhc_asset") as mock_cmhc:
        
        mock_statcan.return_value = {"files": ["test.csv"], "skipped": False}
        mock_cmhc.return_value = {"files": ["test.xlsx"], "errors": []}
        
        result = run_profile(profile_path, force_download=True)
        
        assert isinstance(result, pd.DataFrame)
        # Verify that force_download was passed through
        # (would be tested by checking that downloads occur even for existing files)


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_run_profile_with_output_dir(temp_profiles_dir, tmp_path, monkeypatch):
    """Test running a profile with output_dir specified."""
    from publicdata_ca import datasets as ds_module
    
    # Mock RAW_DATA_DIR
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", raw_dir)
    
    # Create profile with output_dir but no individual outputs
    profile = Profile(
        name="output_test",
        description="Test output directory",
        datasets=[
            ProfileDataset(provider="statcan", id="18100004")
        ],
        output_dir="data/custom"
    )
    
    profile_path = temp_profiles_dir / "output_test.yaml"
    save_profile(profile, profile_path)
    
    # Mock the download function
    with patch("publicdata_ca.providers.statcan.download_statcan_table") as mock_statcan:
        mock_statcan.return_value = {"files": ["test.csv"], "skipped": False}
        
        result = run_profile(profile_path)
        
        assert isinstance(result, pd.DataFrame)
        # Verify that output path uses profile output_dir
        assert "custom" in result.iloc[0]["target_file"]


def test_profile_dataset_creation():
    """Test creating a ProfileDataset."""
    dataset = ProfileDataset(
        provider="statcan",
        id="18100004",
        output="data/raw/test.csv",
        params={"frequency": "Monthly"}
    )
    
    assert dataset.provider == "statcan"
    assert dataset.id == "18100004"
    assert dataset.output == "data/raw/test.csv"
    assert dataset.params == {"frequency": "Monthly"}


def test_profile_search_creation():
    """Test creating a ProfileSearch."""
    search = ProfileSearch(
        provider="statcan",
        query="consumer price",
        filters={"frequency": "Monthly"},
        limit=5
    )
    
    assert search.provider == "statcan"
    assert search.query == "consumer price"
    assert search.filters == {"frequency": "Monthly"}
    assert search.limit == 5


def test_profile_search_defaults():
    """Test ProfileSearch with default values."""
    search = ProfileSearch()
    
    assert search.provider is None
    assert search.query == ""
    assert search.filters == {}
    assert search.limit is None


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_profile_roundtrip(sample_profile, temp_profiles_dir):
    """Test saving and loading a profile preserves all data."""
    profile_path = temp_profiles_dir / "roundtrip.yaml"
    
    # Save the profile
    save_profile(sample_profile, profile_path)
    
    # Load it back
    loaded_profile = load_profile(profile_path)
    
    # Compare all fields
    assert loaded_profile.name == sample_profile.name
    assert loaded_profile.description == sample_profile.description
    assert len(loaded_profile.datasets) == len(sample_profile.datasets)
    
    for i, dataset in enumerate(loaded_profile.datasets):
        original = sample_profile.datasets[i]
        assert dataset.provider == original.provider
        assert dataset.id == original.id
        assert dataset.output == original.output
        assert dataset.params == original.params
    
    assert loaded_profile.output_dir == sample_profile.output_dir
    assert loaded_profile.options == sample_profile.options
