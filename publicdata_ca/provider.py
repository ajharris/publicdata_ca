"""
Provider interface and registry for Canadian public data sources.

This module defines the core Provider contract (search/resolve/fetch), the DatasetRef
schema for referencing datasets, and the ProviderRegistry for discovery. This is the
foundation for adding many sources without refactoring.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type


@dataclass
class DatasetRef:
    """
    Reference to a dataset with provider namespace, identifier, and parameters.
    
    This is the standard way to refer to a dataset across the publicdata_ca system.
    It encapsulates the provider namespace (e.g., 'statcan', 'cmhc'), the dataset
    identifier within that namespace, and any additional parameters needed to
    locate or download the dataset.
    
    Attributes:
        provider: Provider namespace (e.g., 'statcan', 'cmhc')
        id: Dataset identifier within the provider namespace
        params: Additional parameters for dataset resolution (e.g., format, language)
        metadata: Optional metadata about the dataset (title, description, etc.)
        tags: Optional tags for categorization (e.g., ['housing', 'labour', 'finance'])
    
    Example:
        >>> ref = DatasetRef(
        ...     provider='statcan',
        ...     id='18100004',
        ...     params={'language': 'en'},
        ...     tags=['finance', 'cpi']
        ... )
        >>> print(ref.canonical_id)
        'statcan:18100004'
    """
    
    provider: str
    id: str
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    @property
    def canonical_id(self) -> str:
        """Return the canonical identifier in the format 'provider:id'."""
        return f"{self.provider}:{self.id}"
    
    def __str__(self) -> str:
        """String representation of the dataset reference."""
        return self.canonical_id


class Provider(ABC):
    """
    Abstract base class defining the standard interface for data providers.
    
    All data providers (StatsCan, CMHC, etc.) must implement this interface to
    ensure consistent behavior across different data sources. This allows the
    system to add new providers without refactoring existing code.
    
    The provider contract defines three core operations:
    1. search: Find datasets by keyword or criteria
    2. resolve: Convert a dataset reference into download metadata
    3. fetch: Download a dataset to a local destination
    
    Attributes:
        name: Unique provider identifier (e.g., 'statcan', 'cmhc')
    """
    
    def __init__(self, name: str):
        """
        Initialize the provider.
        
        Args:
            name: Unique provider identifier
        """
        self.name = name
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[DatasetRef]:
        """
        Search for datasets matching the query.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
        
        Returns:
            List of DatasetRef objects matching the query
        
        Example:
            >>> provider = StatCanProvider()
            >>> results = provider.search('consumer price index')
            >>> for ref in results:
            ...     print(ref.canonical_id, ref.metadata.get('title'))
        """
        pass
    
    @abstractmethod
    def resolve(self, ref: DatasetRef) -> Dict[str, Any]:
        """
        Resolve a dataset reference into download metadata.
        
        This method takes a DatasetRef and returns the metadata needed to
        download the dataset, including URLs, file formats, and any other
        provider-specific information.
        
        Args:
            ref: Dataset reference to resolve
        
        Returns:
            Dictionary containing:
                - url: Download URL(s)
                - format: File format (csv, xlsx, etc.)
                - title: Dataset title
                - Additional provider-specific metadata
        
        Example:
            >>> ref = DatasetRef(provider='statcan', id='18100004')
            >>> metadata = provider.resolve(ref)
            >>> print(metadata['url'])
        """
        pass
    
    @abstractmethod
    def fetch(
        self,
        ref: DatasetRef,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download a dataset to the specified output directory.
        
        Args:
            ref: Dataset reference to fetch
            output_dir: Directory where files will be saved
            **kwargs: Additional download parameters (e.g., skip_existing, max_retries)
        
        Returns:
            Dictionary containing:
                - files: List of downloaded file paths
                - dataset_id: Dataset identifier
                - provider: Provider name
                - Additional download metadata
        
        Example:
            >>> ref = DatasetRef(provider='statcan', id='18100004')
            >>> result = provider.fetch(ref, './data/raw')
            >>> print(result['files'])
        """
        pass


class ProviderRegistry:
    """
    Registry for discovering and instantiating data providers.
    
    The registry maintains a mapping of provider names to provider classes,
    allowing the system to dynamically discover and use providers without
    hardcoding provider-specific logic.
    
    Example:
        >>> registry = ProviderRegistry()
        >>> registry.register('statcan', StatCanProvider)
        >>> registry.register('cmhc', CMHCProvider)
        >>> 
        >>> # Get a provider instance
        >>> provider = registry.get_provider('statcan')
        >>> results = provider.search('cpi')
        >>> 
        >>> # List all available providers
        >>> providers = registry.list_providers()
    """
    
    def __init__(self):
        """Initialize an empty provider registry."""
        self._providers: Dict[str, Type[Provider]] = {}
    
    def register(self, name: str, provider_class: Type[Provider]) -> None:
        """
        Register a provider class with the registry.
        
        Args:
            name: Unique provider identifier
            provider_class: Provider class (must inherit from Provider)
        
        Raises:
            ValueError: If the provider class doesn't inherit from Provider
        
        Example:
            >>> registry = ProviderRegistry()
            >>> registry.register('statcan', StatCanProvider)
        """
        if not issubclass(provider_class, Provider):
            raise ValueError(
                f"Provider class {provider_class.__name__} must inherit from Provider"
            )
        self._providers[name] = provider_class
    
    def get_provider(self, name: str) -> Provider:
        """
        Get a provider instance by name.
        
        Args:
            name: Provider identifier
        
        Returns:
            Provider instance
        
        Raises:
            KeyError: If the provider is not registered
        
        Example:
            >>> registry = ProviderRegistry()
            >>> registry.register('statcan', StatCanProvider)
            >>> provider = registry.get_provider('statcan')
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' is not registered")
        
        provider_class = self._providers[name]
        return provider_class(name)
    
    def list_providers(self) -> List[str]:
        """
        List all registered provider names.
        
        Returns:
            List of provider names
        
        Example:
            >>> registry = ProviderRegistry()
            >>> registry.register('statcan', StatCanProvider)
            >>> registry.register('cmhc', CMHCProvider)
            >>> providers = registry.list_providers()
            >>> print(providers)
            ['statcan', 'cmhc']
        """
        return list(self._providers.keys())
    
    def has_provider(self, name: str) -> bool:
        """
        Check if a provider is registered.
        
        Args:
            name: Provider identifier
        
        Returns:
            True if the provider is registered, False otherwise
        
        Example:
            >>> registry = ProviderRegistry()
            >>> registry.register('statcan', StatCanProvider)
            >>> registry.has_provider('statcan')
            True
            >>> registry.has_provider('cmhc')
            False
        """
        return name in self._providers


# Global provider registry instance
_global_registry = ProviderRegistry()


def _register_default_providers() -> None:
    """Register common providers with the global registry on module import."""
    # Import providers here to avoid circular imports
    try:
        from publicdata_ca.providers.statcan import StatCanProvider
        _global_registry.register('statcan', StatCanProvider)
    except ImportError:
        pass
    
    try:
        from publicdata_ca.providers.cmhc import CMHCProvider
        _global_registry.register('cmhc', CMHCProvider)
    except ImportError:
        pass
    
    try:
        from publicdata_ca.providers.open_canada import OpenCanadaProvider
        _global_registry.register('open_canada', OpenCanadaProvider)
    except ImportError:
        pass
    
    try:
        from publicdata_ca.providers.ckan import CKANProvider
        _global_registry.register('ckan', CKANProvider)
    except ImportError:
        pass
    
    try:
        from publicdata_ca.providers.socrata import SocrataProvider
        _global_registry.register('socrata', SocrataProvider)
    except ImportError:
        pass
    
    try:
        from publicdata_ca.providers.sdmx import SDMXProvider
        _global_registry.register('sdmx', SDMXProvider)
    except ImportError:
        pass
    
    try:
        from publicdata_ca.providers.boc_valet import ValetProvider
        _global_registry.register('valet', ValetProvider)
        _global_registry.register('boc_valet', ValetProvider)  # Alias
    except ImportError:
        pass


# Auto-register default providers on module import
_register_default_providers()


def get_registry() -> ProviderRegistry:
    """
    Get the global provider registry instance.
    
    This function provides access to the global provider registry, which is
    used throughout the publicdata_ca system for provider discovery.
    
    Returns:
        Global ProviderRegistry instance
    
    Example:
        >>> from publicdata_ca.provider import get_registry
        >>> registry = get_registry()
        >>> provider = registry.get_provider('statcan')
    """
    return _global_registry


def fetch_dataset(
    ref: DatasetRef,
    output_dir: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to fetch a dataset using its DatasetRef.
    
    This function automatically resolves the provider from the DatasetRef's
    provider field and calls the appropriate provider's fetch() method.
    Providers must be registered with the global registry.
    
    Args:
        ref: Dataset reference with provider namespace and dataset ID
        output_dir: Directory where files will be saved
        **kwargs: Additional parameters passed to provider's fetch() method
    
    Returns:
        Dictionary containing download results (structure depends on provider)
        Typically includes:
            - dataset_id: Dataset identifier
            - provider: Provider name
            - files: List of downloaded file paths
            - Additional provider-specific metadata
    
    Raises:
        KeyError: If the provider specified in ref is not registered
        ValueError: If the dataset reference is invalid
        RuntimeError: If the dataset cannot be fetched
    
    Example:
        >>> from publicdata_ca import DatasetRef, fetch_dataset
        >>> 
        >>> # Fetch from Open Canada
        >>> ref = DatasetRef(
        ...     provider='open_canada',
        ...     id='housing-data',
        ...     params={'format': 'CSV'}
        ... )
        >>> result = fetch_dataset(ref, './data')
        >>> print(f"Downloaded {len(result['files'])} files")
        
        >>> # Fetch from StatsCan
        >>> ref = DatasetRef(provider='statcan', id='18100004')
        >>> result = fetch_dataset(ref, './data')
    
    Notes:
        - The provider must be registered with the global registry
        - Common providers (statcan, cmhc, open_canada, etc.) are auto-registered
        - For custom providers, use get_registry().register() first
    """
    # Get the provider from the global registry
    provider = _global_registry.get_provider(ref.provider)
    
    # Call the provider's fetch method
    return provider.fetch(ref, output_dir, **kwargs)


__all__ = [
    'Provider',
    'DatasetRef',
    'ProviderRegistry',
    'get_registry',
    'fetch_dataset',
]
