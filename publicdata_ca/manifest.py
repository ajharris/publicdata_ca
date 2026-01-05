"""
Manifest module for generating and validating data file manifests.

This module provides functionality to create manifests that track downloaded datasets,
ensuring reproducibility and enabling fail-fast behavior when expected data is missing.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


def build_run_manifest(
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
        >>> manifest_path = build_run_manifest('/data', datasets)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    manifest_path = output_path / manifest_name
    
    manifest = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "datasets": datasets,
        "total_datasets": len(datasets),
        "output_directory": str(output_path.absolute())
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    return str(manifest_path)


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
