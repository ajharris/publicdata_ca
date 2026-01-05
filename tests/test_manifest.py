from publicdata_ca.manifest import build_run_manifest, load_manifest, validate_manifest


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

    manifest_path = build_run_manifest(str(output_dir), datasets)
    manifest = load_manifest(manifest_path)

    assert manifest["total_datasets"] == 1
    assert manifest["datasets"][0]["dataset_id"] == "statcan_table"
    assert validate_manifest(manifest_path) is True
