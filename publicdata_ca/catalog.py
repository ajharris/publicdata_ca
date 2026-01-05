"""
Catalog module for managing dataset metadata and discovery.

This module provides functionality to catalog and organize Canadian public datasets,
making them discoverable and accessible through a unified interface.
"""

from typing import Dict, List, Optional, Any


class Catalog:
    """
    Manages a catalog of available datasets from various Canadian public data sources.
    
    The catalog provides methods to search, filter, and retrieve metadata about
    datasets from providers like StatsCan and CMHC.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the catalog.
        
        Args:
            data_dir: Optional directory path where data files are stored.
        """
        self.data_dir = data_dir
        self._datasets: Dict[str, Dict[str, Any]] = {}
    
    def register_dataset(self, dataset_id: str, metadata: Dict[str, Any]) -> None:
        """
        Register a dataset in the catalog.
        
        Args:
            dataset_id: Unique identifier for the dataset.
            metadata: Dictionary containing dataset metadata (provider, title, url, etc.).
        """
        self._datasets[dataset_id] = metadata
    
    def list_datasets(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all datasets in the catalog, optionally filtered by provider.
        
        Args:
            provider: Optional provider name to filter datasets (e.g., 'statcan', 'cmhc').
        
        Returns:
            List of dataset metadata dictionaries.
        """
        datasets = list(self._datasets.values())
        if provider:
            datasets = [d for d in datasets if d.get('provider') == provider]
        return datasets
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset.
        
        Returns:
            Dataset metadata dictionary or None if not found.
        """
        return self._datasets.get(dataset_id)
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for datasets by keyword in title or description.
        
        Args:
            query: Search query string.
        
        Returns:
            List of matching dataset metadata dictionaries.
        """
        query_lower = query.lower()
        results = []
        for dataset in self._datasets.values():
            title = dataset.get('title', '').lower()
            description = dataset.get('description', '').lower()
            if query_lower in title or query_lower in description:
                results.append(dataset)
        return results
