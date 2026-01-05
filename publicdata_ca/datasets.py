"""Dataset catalog utilities ported from the ingestion planning notebook.

This module exposes the curated dataset list, a strongly typed `Dataset` dataclass,
and helpers for constructing pandas DataFrames that mirror the original notebook
behavior. Destinations are pinned to ``data/raw`` relative to the project root and
validated to prevent accidental writes elsewhere on disk.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
        ]
    ]


__all__ = [
    "Dataset",
    "DEFAULT_DATASETS",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "ensure_raw_destination",
    "build_dataset_catalog",
]
