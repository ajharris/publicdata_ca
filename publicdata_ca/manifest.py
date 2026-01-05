"""
Manifest module for generating and validating data file manifests.

This module provides functionality to create manifests that track downloaded datasets,
ensuring reproducibility and enabling fail-fast behavior when expected data is missing.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from publicdata_ca.datasets import ensure_raw_destination


def build_manifest_file(
    output_dir: str,
    datasets: List[Dict[str, Any]],
    manifest_name: str = "manifest.json"
) -> str:
    """
    Build a manifest file for a data download run.
    
    This function creates a JSON manifest that records metadata about downloaded datasets,
    including file paths, checksums, timestamps, and provenance information. The manifest
    enables downstream analyses to verify that all required data is present and unchanged.
    
    Args:
        output_dir: Directory where the manifest will be saved.
        datasets: List of dataset metadata dictionaries. Each should contain:
            - dataset_id: Unique identifier for the dataset
            - provider: Data provider name (e.g., 'statcan', 'cmhc')
            - files: List of file paths downloaded
            - url: Source URL (optional)
            - title: Dataset title (optional)
        manifest_name: Name of the manifest file (default: 'manifest.json').
    
    Returns:
        Path to the created manifest file.
    
    Example:
        >>> datasets = [
        ...     {
        ...         'dataset_id': 'statcan_12345',
        ...         'provider': 'statcan',
        ...         'files': ['data/table_12345.csv'],
        ...         'title': 'Employment Statistics'
        ...     }
        ... ]
        >>> manifest_path = build_manifest_file('/data', datasets)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    manifest_path = output_path / manifest_name
    
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    manifest = {
        "created_at": created_at,
        "datasets": datasets,
        "total_datasets": len(datasets),
        "output_directory": str(output_path.absolute())
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    return str(manifest_path)


def build_run_manifest(catalog: pd.DataFrame) -> pd.DataFrame:
    """Mirror the notebook's run manifest summary for curated datasets."""

    def action(row: pd.Series) -> str:
        if row["provider"] == "statcan" and row["pid"]:
            return f"download_statcan_table({row['pid']}, target_file)"
        if row["provider"] == "cmhc" and row.get("direct_url"):
            return "download_cmhc_asset(direct_url, target_file)"
        if row["provider"] == "cmhc":
            return "Attempt scrape_cmhc_direct_url(page) or download manually"
        return "Review configuration"

    manifest = catalog.copy()

    def normalize_target(path_value: Any) -> Optional[str]:
        if isinstance(path_value, str):
            return str(ensure_raw_destination(Path(path_value)))
        if isinstance(path_value, Path):
            return str(ensure_raw_destination(path_value))
        return None

    manifest["target_file"] = manifest["target_file"].apply(normalize_target)
    manifest["exists"] = manifest["target_file"].apply(
        lambda p: Path(p).exists() if isinstance(p, str) else False
    )
    manifest["action"] = manifest.apply(action, axis=1)

    return manifest[[
        "dataset",
        "provider",
        "automation_status",
        "action",
        "target_file",
        "exists",
        "status_note",
    ]]


def load_manifest(manifest_path: str) -> Dict[str, Any]:
    """
    Load a manifest file.
    
    Args:
        manifest_path: Path to the manifest JSON file.
    
    Returns:
        Dictionary containing manifest data.
    
    Raises:
        FileNotFoundError: If the manifest file doesn't exist.
        json.JSONDecodeError: If the manifest file is not valid JSON.
    """
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_manifest(manifest_path: str) -> bool:
    """
    Validate that all files listed in a manifest exist.
    
    Args:
        manifest_path: Path to the manifest JSON file.
    
    Returns:
        True if all files exist, False otherwise.
    """
    manifest = load_manifest(manifest_path)
    manifest_dir = Path(manifest_path).parent
    
    all_exist = True
    for dataset in manifest.get('datasets', []):
        for file_path in dataset.get('files', []):
            full_path = manifest_dir / file_path
            if not full_path.exists():
                print(f"Missing file: {full_path}")
                all_exist = False
    
    return all_exist
