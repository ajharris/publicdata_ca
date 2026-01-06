"""Dataset catalog utilities ported from the ingestion planning notebook.

This module exposes the curated dataset list, a strongly typed `Dataset` dataclass,
and helpers for constructing pandas DataFrames that mirror the original notebook
behavior. Destinations are pinned to ``data/raw`` relative to the project root and
validated to prevent accidental writes elsewhere on disk.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd


def _resolve_project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "data").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = _resolve_project_root()
DATA_ROOT = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_ROOT / "raw"
PROCESSED_DATA_DIR = DATA_ROOT / "processed"
for path in (RAW_DATA_DIR, PROCESSED_DATA_DIR):
    path.mkdir(parents=True, exist_ok=True)


def ensure_raw_destination(path: str | Path) -> Path:
    """Resolve a destination inside ``data/raw`` and create parent directories."""

    dest = Path(path)
    if not dest.is_absolute():
        dest = RAW_DATA_DIR / dest
    dest = dest.resolve()
    if RAW_DATA_DIR not in dest.parents and dest != RAW_DATA_DIR:
        raise ValueError(f"Destination {dest} must live under {RAW_DATA_DIR}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


@dataclass
class Dataset:
    dataset: str
    provider: str
    metric: str
    pid: str | None
    frequency: str
    geo_scope: str
    delivery: str
    target_file: Path | None
    automation_status: str
    status_note: str
    page_url: str | None = None
    direct_url: str | None = None
    tags: list[str] | None = None

    def destination(self) -> Path | None:
        if self.target_file is None:
            return None
        return ensure_raw_destination(self.target_file)

    @property
    def table_number(self) -> str | None:
        if not self.pid:
            return None
        pid = str(self.pid)
        if len(pid) == 8:
            return f"{pid[:2]}-{pid[2:4]}-{pid[4:]}"
        return pid


DEFAULT_DATASETS: Sequence[Dataset] = (
    Dataset(
        dataset="cpi_all_items",
        provider="statcan",
        metric="Consumer Price Index, all-items (NSA)",
        pid="18100004",
        frequency="Monthly",
        geo_scope="Canada + provinces (CMA deflators derived downstream)",
        delivery="download_statcan_table",
        target_file=RAW_DATA_DIR / "cpi_all_items_18100004.csv",
        automation_status="automatic",
        status_note="Verify the latest CPI release (usually mid-month) before re-running.",
        tags=["finance", "economics", "inflation"],
    ),
    Dataset(
        dataset="median_household_income",
        provider="statcan",
        metric="Median after-tax income by economic family type (CIS)",
        pid="11100035",
        frequency="Annual",
        geo_scope="Canada, provinces, and major CMAs",
        delivery="download_statcan_table",
        target_file=RAW_DATA_DIR / "median_household_income_11100035.csv",
        automation_status="automatic",
        status_note="CIS table provides CMA-level coverage for major metros; confirm vector availability for smaller metros before modeling.",
        tags=["economics", "labour", "income"],
    ),
    Dataset(
        dataset="population_estimates",
        provider="statcan",
        metric="Population estimates, July 1 (CMA/CA, 2021 boundaries)",
        pid="17100148",
        frequency="Annual",
        geo_scope="Census metropolitan areas and agglomerations",
        delivery="download_statcan_table",
        target_file=RAW_DATA_DIR / "population_estimates_17100148.csv",
        automation_status="automatic",
        status_note="Release every February; used to scale metrics per 100k residents.",
        tags=["demographics", "population"],
    ),
    Dataset(
        dataset="unemployment_rate",
        provider="statcan",
        metric="Labour force characteristics by CMA (3-month moving avg, SA)",
        pid="14100459",
        frequency="Monthly",
        geo_scope="Census metropolitan areas",
        delivery="download_statcan_table",
        target_file=RAW_DATA_DIR / "unemployment_rate_14100459.csv",
        automation_status="automatic",
        status_note="Seasonally adjusted 3-month moving average preferred for stability.",
        tags=["labour", "economics", "employment"],
    ),
    Dataset(
        dataset="rental_market_rents",
        provider="cmhc",
        metric="Rental Market Report data tables",
        pid=None,
        frequency="Annual",
        geo_scope="Canada + major CMAs",
        delivery="download_cmhc_asset",
        target_file=RAW_DATA_DIR / "rental_market_report_latest.xlsx",
        automation_status="semi-automatic",
        status_note="Uses the last verified CMHC Azure blob URL; update when the 2026 release ships.",
        page_url="https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/rental-market/rental-market-report-data-tables",
        tags=["housing", "rental", "real-estate"],
    ),
    Dataset(
        dataset="housing_starts",
        provider="cmhc",
        metric="Monthly housing starts + under construction",
        pid=None,
        frequency="Monthly",
        geo_scope="Canada + CMAs",
        delivery="download_cmhc_asset",
        target_file=RAW_DATA_DIR / "housing_starts_latest.xlsx",
        automation_status="semi-automatic",
        status_note="Pinned to the November 2025 CMHC housing starts release; refresh when the next workbook is published.",
        page_url="https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/housing-market-data/monthly-housing-starts-construction-data-tables",
        tags=["housing", "construction", "real-estate"],
    ),
)


def build_dataset_catalog(datasets: Iterable[Dataset] | None = None) -> pd.DataFrame:
    """Construct the curated dataset catalog as a pandas DataFrame."""

    source = list(datasets or DEFAULT_DATASETS)
    catalog_records: list[dict[str, object]] = []
    for ds in source:
        record = asdict(ds)
        record["table_number"] = ds.table_number
        destination = ds.destination()
        record["target_file"] = str(destination) if destination else None
        catalog_records.append(record)

    return (
        pd.DataFrame(catalog_records)
        .sort_values("dataset")
        .reset_index(drop=True)
    )[
        [
            "dataset",
            "provider",
            "metric",
            "pid",
            "table_number",
            "frequency",
            "geo_scope",
            "delivery",
            "automation_status",
            "page_url",
            "direct_url",
            "target_file",
            "status_note",
            "tags",
        ]
    ]


def refresh_datasets(
    datasets: Iterable[Dataset] | None = None,
    force_download: bool = False,
    skip_existing: bool = True,
) -> pd.DataFrame:
    """
    Refresh dataset downloads by iterating through the catalog and downloading missing files.
    
    This function mirrors the notebook automation pattern: it iterates through the dataset
    catalog, checks which files exist, and downloads missing files using the appropriate
    provider (StatsCan or CMHC). Returns a detailed run report as a DataFrame.
    
    Args:
        datasets: Iterable of Dataset objects to refresh. If None, uses DEFAULT_DATASETS.
        force_download: If True, re-download files even if they already exist (default: False).
        skip_existing: If True, skip downloads for files that already exist (default: True).
            This is the inverse of force_download and is kept for backward compatibility.
    
    Returns:
        pandas DataFrame with columns:
            - dataset: Dataset identifier
            - provider: Provider name (statcan, cmhc)
            - target_file: Target file path
            - result: Status (skipped, exists, downloaded, manual_required, error, etc.)
            - notes: Additional information about the result
            - run_started_utc: Timestamp when the refresh started (ISO format)
    
    Example:
        >>> # Refresh all default datasets
        >>> report = refresh_datasets()
        >>> print(report[['dataset', 'result', 'notes']])
        
        >>> # Force re-download of all datasets
        >>> report = refresh_datasets(force_download=True)
        
        >>> # Refresh specific datasets
        >>> from publicdata_ca.datasets import DEFAULT_DATASETS
        >>> statcan_only = [d for d in DEFAULT_DATASETS if d.provider == 'statcan']
        >>> report = refresh_datasets(datasets=statcan_only)
    
    Notes:
        - For StatsCan datasets, uses download_statcan_table from providers.statcan
        - For CMHC datasets, uses resolve and download from providers.cmhc
        - Files are downloaded to their configured target_file locations
        - The function is idempotent: running it multiple times is safe
    """
    from publicdata_ca.http import download_file
    from publicdata_ca.providers.cmhc import download_cmhc_asset
    from publicdata_ca.providers.statcan import download_statcan_table
    
    # Use default datasets if none provided
    source_datasets = list(datasets or DEFAULT_DATASETS)
    
    # Track results
    refresh_records = []
    run_started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Resolve force_download vs skip_existing
    should_skip_existing = skip_existing and not force_download
    
    for ds in source_datasets:
        dest = ds.destination()
        record = {
            "dataset": ds.dataset,
            "provider": ds.provider,
            "target_file": str(dest) if dest else None,
            "run_started_utc": run_started,
            "result": "skipped",
            "notes": "",
        }
        
        # Check if target file is configured
        if dest is None:
            record["result"] = "missing_target"
            record["notes"] = "No target_file configured"
            refresh_records.append(record)
            continue
        
        # Process StatsCan datasets
        if ds.provider == "statcan" and ds.pid:
            try:
                # Download the table (download_statcan_table handles skip_existing internally)
                result = download_statcan_table(
                    ds.pid,
                    str(dest.parent),
                    skip_existing=should_skip_existing
                )
                if result.get("skipped"):
                    record["result"] = "exists"
                    record["notes"] = "File already present"
                else:
                    record["result"] = "downloaded"
                    record["notes"] = f"Downloaded {len(result.get('files', []))} file(s)"
            except Exception as exc:
                record["result"] = "error"
                record["notes"] = f"Download failed: {str(exc)}"
        
        # Process CMHC datasets
        elif ds.provider == "cmhc":
            if dest.exists() and should_skip_existing:
                record["result"] = "exists"
                record["notes"] = "File already present"
            else:
                # If we have a direct_url, download directly
                # Otherwise, use the landing page resolver
                if ds.direct_url:
                    # Have a direct URL - download it directly
                    try:
                        download_file(
                            ds.direct_url,
                            str(dest),
                            max_retries=3,
                            validate_content_type=True
                        )
                        record["result"] = "downloaded"
                        record["notes"] = "Downloaded from direct URL"
                    except Exception as exc:
                        record["result"] = "error"
                        record["notes"] = f"Download error: {str(exc)}"
                elif ds.page_url:
                    # Have a landing page URL - resolve and download
                    try:
                        result = download_cmhc_asset(
                            ds.page_url,
                            str(dest.parent),
                            max_retries=3
                        )
                        
                        # Check if download was successful
                        if result.get("files"):
                            record["result"] = "downloaded"
                            record["notes"] = f"Downloaded {len(result['files'])} file(s) from landing page"
                        elif result.get("errors"):
                            record["result"] = "error"
                            # Include first 2 errors
                            error_msgs = result["errors"][:2]
                            record["notes"] = "; ".join(error_msgs)
                        else:
                            record["result"] = "error"
                            record["notes"] = "No files downloaded from landing page"
                    except Exception as exc:
                        record["result"] = "error"
                        record["notes"] = f"Download error: {str(exc)}"
                else:
                    # No URL available
                    record["result"] = "manual_required"
                    record["notes"] = "No direct_url or page_url available — manual download required"
        
        else:
            record["result"] = "unknown_provider"
            record["notes"] = f"Unhandled provider: {ds.provider}"
        
        refresh_records.append(record)
    
    # Build DataFrame and return
    return pd.DataFrame(refresh_records)


__all__ = [
    "Dataset",
    "DEFAULT_DATASETS",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "ensure_raw_destination",
    "build_dataset_catalog",
    "refresh_datasets",
]
