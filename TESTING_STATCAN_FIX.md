# Testing the StatCan HTTP 406 Fix

This document explains how to manually test the fix for the HTTP 406 error when downloading Statistics Canada tables.

## Background

The Statistics Canada Web Data Service (WDS) API was returning HTTP 406 "Not Acceptable" errors when downloading tables. This was caused by the `Accept` header being sent in the HTTP request.

## The Fix

The fix removes the `Accept` header from the request, sending only the `User-Agent` header. The StatCan API is sensitive to the Accept header and works best without it.

**Changed headers:**
- Before: `Accept: application/zip` (or `Accept: */*`)
- After: No `Accept` header sent (only `User-Agent`)

## How to Test Manually

### Option 1: Using the Manual Test Script

Run the provided test script:

```bash
python test_statcan_manual.py
```

This will attempt to download table 18100004 (Consumer Price Index) from the live StatCan API.

Expected output if successful:
```
Testing StatCan download with live API...
Table ID: 18100004 (Consumer Price Index)

Headers being sent (no Accept header to avoid HTTP 406):
  User-Agent: publicdata_ca/0.1.0 (Python; Canadian Public Data Client)

Downloading to: /tmp/...
✅ Download successful!
...
```

### Option 2: Using Python REPL

```python
from publicdata_ca.providers.statcan import download_statcan_table

# Download Consumer Price Index data
result = download_statcan_table("18100004", "./data/raw")
print(result)
```

### Option 3: Using the CLI (if available)

```bash
publicdata fetch statcan 18100004
```

## What to Look For

✅ **Success indicators:**
- Download completes without errors
- ZIP file is extracted
- CSV files are created (e.g., `18100004.csv`, `18100004_MetaData.csv`)
- No HTTP 406 error

❌ **Failure indicators:**
- `HTTPError: HTTP Error 406:` message
- No files created
- Exception traceback

## Testing Other Tables

You can test with other StatCan table IDs:
- `14100287` - Labour force characteristics
- `17100005` - Population estimates
- Any valid 8-digit table ID from https://www150.statcan.gc.ca/

## Automated Tests

The fix includes comprehensive unit tests:

```bash
# Run all StatCan tests
pytest tests/test_statcan.py tests/test_statcan_fixtures.py -v

# Run just the header validation test
pytest tests/test_statcan.py::test_download_statcan_table_sets_correct_accept_header -v
```

All tests should pass.
