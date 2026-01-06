"""
Profile system for multi-project dataset refresh.

This module provides a YAML-based profiles system that allows users to define
collections of datasets to refresh together. Profiles can specify datasets by:
- Direct DatasetRef references (provider:id)
- Search queries with filters
- Custom output directories and options

Example profile (profiles/economics.yaml):
    name: economics
    description: Economic indicators for Canada
    datasets:
      - provider: statcan
        id: "18100004"
        output: data/raw/cpi_all_items.csv
      - provider: statcan
        id: "14100459"
        output: data/raw/unemployment_rate.csv
    
Example profile with search (profiles/housing.yaml):
    name: housing
    description: Housing market data
    search:
      provider: cmhc
      query: "housing starts"
      filters:
        frequency: Monthly
    output_dir: data/raw/housing
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def _resolve_profiles_dir() -> Path:
    """Resolve the profiles directory, creating it if necessary."""
    # Try to find project root
    cwd = Path.cwd().resolve()
    if (cwd / "profiles").exists():
        profiles_dir = cwd / "profiles"
    elif (cwd / "data").exists():
        profiles_dir = cwd / "profiles"
    else:
        # Use directory relative to this file's parent
        profiles_dir = Path(__file__).resolve().parents[1] / "profiles"
    
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir


PROFILES_DIR = _resolve_profiles_dir()


@dataclass
class ProfileDataset:
    """
    A dataset specification within a profile.
    
    Attributes:
        provider: Provider name (e.g., 'statcan', 'cmhc')
        id: Dataset identifier
        output: Optional output path for this dataset
        params: Additional parameters for the dataset
    """
    provider: str
    id: str
    output: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileSearch:
    """
    A search specification within a profile.
    
    Attributes:
        provider: Provider name to search
        query: Search query string
        filters: Filters to apply to search results
        limit: Maximum number of results to include
    """
    provider: Optional[str] = None
    query: str = ""
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None


@dataclass
class Profile:
    """
    A profile defining a collection of datasets to refresh.
    
    Attributes:
        name: Profile name
        description: Profile description
        datasets: List of dataset specifications
        search: Optional search specification
        output_dir: Default output directory for all datasets
        options: Additional options for refresh operation
    """
    name: str
    description: str = ""
    datasets: List[ProfileDataset] = field(default_factory=list)
    search: Optional[ProfileSearch] = None
    output_dir: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Profile:
        """
        Create a Profile from a dictionary.
        
        Args:
            data: Dictionary representation of a profile
        
        Returns:
            Profile instance
        """
        # Parse datasets
        datasets = []
        for ds_data in data.get("datasets", []):
            datasets.append(ProfileDataset(
                provider=ds_data["provider"],
                id=ds_data["id"],
                output=ds_data.get("output"),
                params=ds_data.get("params", {})
            ))
        
        # Parse search
        search = None
        if "search" in data:
            search_data = data["search"]
            search = ProfileSearch(
                provider=search_data.get("provider"),
                query=search_data.get("query", ""),
                filters=search_data.get("filters", {}),
                limit=search_data.get("limit")
            )
        
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            datasets=datasets,
            search=search,
            output_dir=data.get("output_dir"),
            options=data.get("options", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert profile to dictionary representation.
        
        Returns:
            Dictionary representation of the profile
        """
        result: Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
        }
        
        if self.datasets:
            result["datasets"] = [
                {
                    "provider": ds.provider,
                    "id": ds.id,
                    **({"output": ds.output} if ds.output else {}),
                    **({"params": ds.params} if ds.params else {})
                }
                for ds in self.datasets
            ]
        
        if self.search:
            result["search"] = {
                **({"provider": self.search.provider} if self.search.provider else {}),
                **({"query": self.search.query} if self.search.query else {}),
                **({"filters": self.search.filters} if self.search.filters else {}),
                **({"limit": self.search.limit} if self.search.limit else {})
            }
        
        if self.output_dir:
            result["output_dir"] = self.output_dir
        
        if self.options:
            result["options"] = self.options
        
        return result


def load_profile(profile_path: str | Path) -> Profile:
    """
    Load a profile from a YAML file.
    
    Args:
        profile_path: Path to the profile YAML file
    
    Returns:
        Profile instance
    
    Raises:
        ImportError: If PyYAML is not installed
        FileNotFoundError: If the profile file doesn't exist
        ValueError: If the profile is invalid
    
    Example:
        >>> profile = load_profile("profiles/economics.yaml")
        >>> print(profile.name)
        'economics'
    """
    if yaml is None:
        raise ImportError(
            "PyYAML is required to load profiles. "
            "Install it with: pip install pyyaml"
        )
    
    path = Path(profile_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile file not found: {path}")
    
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Invalid profile format in {path}")
    
    if "name" not in data:
        raise ValueError(f"Profile must have a 'name' field: {path}")
    
    return Profile.from_dict(data)


def save_profile(profile: Profile, profile_path: str | Path) -> Path:
    """
    Save a profile to a YAML file.
    
    Args:
        profile: Profile to save
        profile_path: Path where the profile will be saved
    
    Returns:
        Path to the saved profile file
    
    Raises:
        ImportError: If PyYAML is not installed
    
    Example:
        >>> profile = Profile(name="test", description="Test profile")
        >>> save_profile(profile, "profiles/test.yaml")
    """
    if yaml is None:
        raise ImportError(
            "PyYAML is required to save profiles. "
            "Install it with: pip install pyyaml"
        )
    
    path = Path(profile_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f:
        yaml.safe_dump(profile.to_dict(), f, default_flow_style=False, sort_keys=False)
    
    return path


def list_profiles(profiles_dir: str | Path | None = None) -> List[str]:
    """
    List all available profiles in the profiles directory.
    
    Args:
        profiles_dir: Directory containing profile files. If None, uses PROFILES_DIR.
    
    Returns:
        List of profile names (without .yaml extension)
    
    Example:
        >>> profiles = list_profiles()
        >>> print(profiles)
        ['economics', 'housing', 'population']
    """
    search_dir = Path(profiles_dir) if profiles_dir else PROFILES_DIR
    
    if not search_dir.exists():
        return []
    
    profile_files = list(search_dir.glob("*.yaml")) + list(search_dir.glob("*.yml"))
    return [p.stem for p in sorted(profile_files)]


def run_profile(
    profile: Profile | str | Path,
    force_download: bool = False,
    skip_existing: bool = True,
) -> pd.DataFrame:
    """
    Execute a profile to refresh datasets.
    
    This function loads a profile (or accepts a Profile object), resolves the
    datasets specified in the profile, and executes a refresh operation.
    
    Args:
        profile: Profile object, profile name, or path to profile YAML file
        force_download: If True, re-download files even if they exist
        skip_existing: If True, skip downloads for files that already exist
    
    Returns:
        DataFrame with refresh results, including:
            - dataset: Dataset identifier
            - provider: Provider name
            - target_file: Target file path
            - result: Status (downloaded, exists, error, etc.)
            - notes: Additional information
            - run_started_utc: Timestamp when the refresh started
    
    Example:
        >>> # Run by profile name
        >>> report = run_profile("economics")
        >>> print(report[['dataset', 'result']])
        
        >>> # Run with force download
        >>> report = run_profile("housing", force_download=True)
        
        >>> # Run from Profile object
        >>> profile = load_profile("profiles/custom.yaml")
        >>> report = run_profile(profile)
    """
    from publicdata_ca.datasets import Dataset, refresh_datasets, ensure_raw_destination
    from publicdata_ca.provider import DatasetRef
    
    # Load profile if it's a string or Path
    if isinstance(profile, (str, Path)):
        profile_path = profile if isinstance(profile, Path) else Path(profile)
        
        # If it's just a name (no path separator), look in PROFILES_DIR
        if not profile_path.suffix and "/" not in str(profile) and "\\" not in str(profile):
            profile_path = PROFILES_DIR / f"{profile}.yaml"
        
        profile = load_profile(profile_path)
    
    # Build list of datasets to refresh
    datasets_to_refresh: List[Dataset] = []
    
    # Process direct dataset references
    for ds_spec in profile.datasets:
        # Determine output path
        if ds_spec.output:
            target_file = Path(ds_spec.output)
        elif profile.output_dir:
            # Use profile output_dir with a default filename
            target_file = Path(profile.output_dir) / f"{ds_spec.provider}_{ds_spec.id}.csv"
        else:
            # Use default raw data directory
            target_file = Path(f"data/raw/{ds_spec.provider}_{ds_spec.id}.csv")
        
        # Create Dataset object
        # Note: Some fields are set to defaults since we don't have full metadata
        dataset = Dataset(
            dataset=f"{ds_spec.provider}_{ds_spec.id}",
            provider=ds_spec.provider,
            metric=ds_spec.params.get("metric", f"Dataset {ds_spec.id}"),
            pid=ds_spec.id if ds_spec.provider == "statcan" else None,
            frequency=ds_spec.params.get("frequency", "Unknown"),
            geo_scope=ds_spec.params.get("geo_scope", "Unknown"),
            delivery=ds_spec.params.get("delivery", "auto"),
            target_file=target_file,
            automation_status="automatic",
            status_note=ds_spec.params.get("note", f"From profile: {profile.name}"),
            page_url=ds_spec.params.get("page_url"),
            direct_url=ds_spec.params.get("direct_url"),
        )
        datasets_to_refresh.append(dataset)
    
    # TODO: Process search specifications when provider search is implemented
    # For now, we'll skip search-based dataset resolution
    if profile.search:
        # This would require implementing search across providers
        # For MVP, we'll just log a note
        pass
    
    # Execute refresh
    return refresh_datasets(
        datasets=datasets_to_refresh,
        force_download=force_download,
        skip_existing=skip_existing,
    )


__all__ = [
    "Profile",
    "ProfileDataset",
    "ProfileSearch",
    "load_profile",
    "save_profile",
    "list_profiles",
    "run_profile",
    "PROFILES_DIR",
]
