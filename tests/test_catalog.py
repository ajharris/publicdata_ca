from publicdata_ca.catalog import Catalog


def test_catalog_register_and_filter():
    catalog = Catalog(data_dir="./data")
    metadata = {
        "dataset_id": "statcan_14-10-0287-01",
        "provider": "statcan",
        "title": "Employment by industry",
        "description": "Labour force survey table"
    }
    catalog.register_dataset(metadata["dataset_id"], metadata)

    all_datasets = catalog.list_datasets()
    assert len(all_datasets) == 1
    assert all_datasets[0]["title"] == "Employment by industry"

    statcan_only = catalog.list_datasets(provider="statcan")
    assert len(statcan_only) == 1
    cmhc_only = catalog.list_datasets(provider="cmhc")
    assert cmhc_only == []


def test_catalog_search_matches_title_and_description():
    catalog = Catalog()
    catalog.register_dataset(
        "cmhc_housing_starts",
        {
            "title": "Housing starts by region",
            "provider": "cmhc",
            "description": "Monthly summary of housing starts for major cities"
        }
    )

    title_match = catalog.search("housing starts")
    assert len(title_match) == 1

    desc_match = catalog.search("monthly summary")
    assert len(desc_match) == 1

    missing = catalog.search("nonexistent keyword")
    assert missing == []


def test_catalog_list_datasets_with_tags():
    """Test filtering datasets by tags."""
    catalog = Catalog()
    
    # Register datasets with tags
    catalog.register_dataset(
        "cpi_data",
        {
            "title": "Consumer Price Index",
            "provider": "statcan",
            "tags": ["finance", "economics", "inflation"]
        }
    )
    catalog.register_dataset(
        "housing_starts",
        {
            "title": "Housing Starts",
            "provider": "cmhc",
            "tags": ["housing", "construction"]
        }
    )
    catalog.register_dataset(
        "unemployment",
        {
            "title": "Unemployment Rate",
            "provider": "statcan",
            "tags": ["labour", "economics"]
        }
    )
    
    # Test filtering by single tag
    housing_datasets = catalog.list_datasets(tags=["housing"])
    assert len(housing_datasets) == 1
    assert housing_datasets[0]["title"] == "Housing Starts"
    
    # Test filtering by multiple tags (AND operation)
    economics_datasets = catalog.list_datasets(tags=["economics"])
    assert len(economics_datasets) == 2
    
    finance_economics = catalog.list_datasets(tags=["finance", "economics"])
    assert len(finance_economics) == 1
    assert finance_economics[0]["title"] == "Consumer Price Index"
    
    # Test non-matching tags
    climate_datasets = catalog.list_datasets(tags=["climate"])
    assert climate_datasets == []


def test_catalog_list_datasets_with_provider_and_tags():
    """Test filtering datasets by both provider and tags."""
    catalog = Catalog()
    
    catalog.register_dataset(
        "cpi_data",
        {
            "title": "Consumer Price Index",
            "provider": "statcan",
            "tags": ["finance", "economics"]
        }
    )
    catalog.register_dataset(
        "housing_starts",
        {
            "title": "Housing Starts",
            "provider": "cmhc",
            "tags": ["housing", "economics"]
        }
    )
    
    # Filter by provider and tag
    statcan_economics = catalog.list_datasets(provider="statcan", tags=["economics"])
    assert len(statcan_economics) == 1
    assert statcan_economics[0]["title"] == "Consumer Price Index"
    
    cmhc_economics = catalog.list_datasets(provider="cmhc", tags=["economics"])
    assert len(cmhc_economics) == 1
    assert cmhc_economics[0]["title"] == "Housing Starts"


def test_catalog_search_with_tags():
    """Test searching datasets with tag filtering."""
    catalog = Catalog()
    
    catalog.register_dataset(
        "cpi_data",
        {
            "title": "Consumer Price Index",
            "description": "Monthly CPI data",
            "provider": "statcan",
            "tags": ["finance", "economics"]
        }
    )
    catalog.register_dataset(
        "housing_cpi",
        {
            "title": "Housing Component CPI",
            "description": "CPI for housing",
            "provider": "statcan",
            "tags": ["housing", "finance"]
        }
    )
    
    # Search without tag filter
    all_cpi = catalog.search("cpi")
    assert len(all_cpi) == 2
    
    # Search with tag filter
    finance_cpi = catalog.search("cpi", tags=["finance"])
    assert len(finance_cpi) == 2
    
    housing_cpi = catalog.search("cpi", tags=["housing"])
    assert len(housing_cpi) == 1
    assert housing_cpi[0]["title"] == "Housing Component CPI"
    
    # Search with multiple tags
    housing_finance_cpi = catalog.search("cpi", tags=["housing", "finance"])
    assert len(housing_finance_cpi) == 1
    assert housing_finance_cpi[0]["title"] == "Housing Component CPI"


def test_catalog_datasets_without_tags():
    """Test that datasets without tags field are handled correctly."""
    catalog = Catalog()
    
    catalog.register_dataset(
        "no_tags",
        {
            "title": "Dataset without tags",
            "provider": "statcan"
        }
    )
    catalog.register_dataset(
        "with_tags",
        {
            "title": "Dataset with tags",
            "provider": "statcan",
            "tags": ["finance"]
        }
    )
    
    # List all datasets
    all_datasets = catalog.list_datasets()
    assert len(all_datasets) == 2
    
    # Filter by tags should exclude datasets without tags
    finance_datasets = catalog.list_datasets(tags=["finance"])
    assert len(finance_datasets) == 1
    assert finance_datasets[0]["title"] == "Dataset with tags"
    
    # Search with tags should exclude datasets without tags
    search_results = catalog.search("dataset", tags=["finance"])
    assert len(search_results) == 1
    assert search_results[0]["title"] == "Dataset with tags"
