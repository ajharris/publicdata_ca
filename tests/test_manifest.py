import pandas as pd

from publicdata_ca.manifest import build_manifest_file, build_run_manifest, load_manifest, validate_manifest


def test_build_and_validate_manifest(tmp_path):
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()

    dataset_file = output_dir / "sample.csv"
    dataset_file.write_text("value\n1\n", encoding="utf-8")

    datasets = [
        {
            "dataset_id": "statcan_table",
            "provider": "statcan",
            "files": [dataset_file.name],
            "title": "Sample Table"
        }
    ]

    manifest_path = build_manifest_file(str(output_dir), datasets)
    manifest = load_manifest(manifest_path)

    assert manifest["total_datasets"] == 1
    assert manifest["datasets"][0]["dataset_id"] == "statcan_table"
    assert validate_manifest(manifest_path) is True


def test_build_run_manifest_dataframe(monkeypatch, tmp_path):
    from publicdata_ca import datasets as ds_module

    mock_raw = tmp_path / "raw"
    mock_raw.mkdir()
    monkeypatch.setattr(ds_module, "RAW_DATA_DIR", mock_raw, raising=False)

    catalog = pd.DataFrame(
        [
            {
                "dataset": "statcan_table",
                "provider": "statcan",
                "pid": "18100004",
                "automation_status": "automatic",
                "page_url": None,
                "direct_url": None,
                "target_file": "statcan/table.csv",
                "status_note": "",
            },
            {
                "dataset": "cmhc_asset",
                "provider": "cmhc",
                "pid": None,
                "automation_status": "semi-automatic",
                "page_url": "https://example.com/page",
                "direct_url": None,
                "target_file": "cmhc/asset.xlsx",
                "status_note": "Manual",
            },
        ]
    )

    manifest_df = build_run_manifest(catalog)

    assert list(manifest_df.columns) == [
        "dataset",
        "provider",
        "automation_status",
        "action",
        "target_file",
        "exists",
        "status_note",
    ]
    assert manifest_df.loc[manifest_df["dataset"] == "statcan_table", "action"].item().startswith(
        "download_statcan_table"
    )
    assert manifest_df.loc[manifest_df["dataset"] == "cmhc_asset", "action"].item().startswith(
        "Attempt scrape_cmhc_direct_url"
    )
