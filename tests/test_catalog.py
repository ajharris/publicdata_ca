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
