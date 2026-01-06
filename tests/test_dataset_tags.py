"""Tests for dataset tags functionality."""

import pytest
from publicdata_ca.datasets import Dataset, build_dataset_catalog, DEFAULT_DATASETS


def test_dataset_with_tags():
    """Test creating a dataset with tags."""
    dataset = Dataset(
        dataset="test_dataset",
        provider="statcan",
        metric="Test metric",
        pid="18100004",
        frequency="Monthly",
        geo_scope="Canada",
        delivery="download_statcan_table",
        target_file=None,
        automation_status="automatic",
        status_note="Test note",
        tags=["finance", "economics"]
    )
    
    assert dataset.tags == ["finance", "economics"]
    assert "finance" in dataset.tags
    assert "economics" in dataset.tags


def test_dataset_without_tags():
    """Test creating a dataset without tags."""
    dataset = Dataset(
        dataset="test_dataset",
        provider="statcan",
        metric="Test metric",
        pid="18100004",
        frequency="Monthly",
        geo_scope="Canada",
        delivery="download_statcan_table",
        target_file=None,
        automation_status="automatic",
        status_note="Test note"
    )
    
    assert dataset.tags is None


def test_dataset_with_empty_tags():
    """Test creating a dataset with empty tags list."""
    dataset = Dataset(
        dataset="test_dataset",
        provider="statcan",
        metric="Test metric",
        pid="18100004",
        frequency="Monthly",
        geo_scope="Canada",
        delivery="download_statcan_table",
        target_file=None,
        automation_status="automatic",
        status_note="Test note",
        tags=[]
    )
    
    assert dataset.tags == []


def test_default_datasets_have_tags():
    """Test that DEFAULT_DATASETS contain tags."""
    # Check that at least some datasets have tags
    datasets_with_tags = [d for d in DEFAULT_DATASETS if d.tags]
    assert len(datasets_with_tags) > 0
    
    # Check specific datasets for expected tags
    cpi_dataset = next((d for d in DEFAULT_DATASETS if d.dataset == "cpi_all_items"), None)
    assert cpi_dataset is not None
    assert cpi_dataset.tags is not None
    assert "finance" in cpi_dataset.tags
    assert "economics" in cpi_dataset.tags
    
    unemployment_dataset = next((d for d in DEFAULT_DATASETS if d.dataset == "unemployment_rate"), None)
    assert unemployment_dataset is not None
    assert unemployment_dataset.tags is not None
    assert "labour" in unemployment_dataset.tags
    assert "economics" in unemployment_dataset.tags
    
    housing_starts_dataset = next((d for d in DEFAULT_DATASETS if d.dataset == "housing_starts"), None)
    assert housing_starts_dataset is not None
    assert housing_starts_dataset.tags is not None
    assert "housing" in housing_starts_dataset.tags


def test_build_dataset_catalog_includes_tags():
    """Test that build_dataset_catalog includes tags column."""
    catalog_df = build_dataset_catalog()
    
    # Check that tags column exists
    assert "tags" in catalog_df.columns
    
    # Check that tags are preserved
    cpi_row = catalog_df[catalog_df["dataset"] == "cpi_all_items"]
    assert len(cpi_row) == 1
    tags = cpi_row.iloc[0]["tags"]
    assert tags is not None
    assert "finance" in tags
    assert "economics" in tags


def test_build_dataset_catalog_with_custom_datasets():
    """Test build_dataset_catalog with custom datasets including tags."""
    custom_datasets = [
        Dataset(
            dataset="custom_dataset_1",
            provider="statcan",
            metric="Custom metric 1",
            pid="11111111",
            frequency="Annual",
            geo_scope="Canada",
            delivery="download_statcan_table",
            target_file=None,
            automation_status="automatic",
            status_note="Test note",
            tags=["housing", "finance"]
        ),
        Dataset(
            dataset="custom_dataset_2",
            provider="cmhc",
            metric="Custom metric 2",
            pid=None,
            frequency="Monthly",
            geo_scope="CMAs",
            delivery="download_cmhc_asset",
            target_file=None,
            automation_status="semi-automatic",
            status_note="Test note",
            tags=["labour"]
        ),
        Dataset(
            dataset="custom_dataset_3",
            provider="statcan",
            metric="Custom metric 3",
            pid="22222222",
            frequency="Quarterly",
            geo_scope="Provinces",
            delivery="download_statcan_table",
            target_file=None,
            automation_status="automatic",
            status_note="Test note"
            # No tags field
        ),
    ]
    
    catalog_df = build_dataset_catalog(datasets=custom_datasets)
    
    # Check that all datasets are included
    assert len(catalog_df) == 3
    
    # Check tags for first dataset
    row1 = catalog_df[catalog_df["dataset"] == "custom_dataset_1"].iloc[0]
    assert row1["tags"] == ["housing", "finance"]
    
    # Check tags for second dataset
    row2 = catalog_df[catalog_df["dataset"] == "custom_dataset_2"].iloc[0]
    assert row2["tags"] == ["labour"]
    
    # Check that dataset without tags has None
    row3 = catalog_df[catalog_df["dataset"] == "custom_dataset_3"].iloc[0]
    assert row3["tags"] is None


def test_filter_datasets_by_tags():
    """Test filtering datasets by tags using pandas."""
    catalog_df = build_dataset_catalog()
    
    # Filter datasets with 'housing' tag
    housing_datasets = catalog_df[
        catalog_df["tags"].apply(lambda x: x is not None and "housing" in x)
    ]
    assert len(housing_datasets) > 0
    
    # All filtered datasets should have 'housing' tag
    for _, row in housing_datasets.iterrows():
        assert "housing" in row["tags"]
    
    # Filter datasets with 'economics' tag
    economics_datasets = catalog_df[
        catalog_df["tags"].apply(lambda x: x is not None and "economics" in x)
    ]
    assert len(economics_datasets) > 0
    
    # Filter datasets with both 'labour' and 'economics' tags
    labour_economics = catalog_df[
        catalog_df["tags"].apply(
            lambda x: x is not None and "labour" in x and "economics" in x
        )
    ]
    assert len(labour_economics) > 0
    
    # All filtered datasets should have both tags
    for _, row in labour_economics.iterrows():
        assert "labour" in row["tags"]
        assert "economics" in row["tags"]


def test_datasets_tag_consistency():
    """Test that tags are consistent and sensible across DEFAULT_DATASETS."""
    # Get all unique tags
    all_tags = set()
    for dataset in DEFAULT_DATASETS:
        if dataset.tags:
            all_tags.update(dataset.tags)
    
    # Check that we have a reasonable number of unique tags
    assert len(all_tags) > 0
    
    # Common tags should exist
    expected_tags = {"housing", "labour", "economics", "finance"}
    assert expected_tags.issubset(all_tags)
    
    # Check that all tags are lowercase (convention)
    for tag in all_tags:
        assert tag == tag.lower(), f"Tag '{tag}' should be lowercase"
    
    # Check that tags don't have spaces (use hyphens instead)
    for tag in all_tags:
        assert " " not in tag, f"Tag '{tag}' should not contain spaces"
