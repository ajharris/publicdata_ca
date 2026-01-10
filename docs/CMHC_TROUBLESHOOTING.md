# CMHC Troubleshooting Guide

CMHC (Canada Mortgage and Housing Corporation) landing pages can change frequently, causing download failures. This guide helps diagnose and handle common issues.

## Table of Contents

- [Landing Page Resolution](#landing-page-resolution)
- [URL Caching](#url-caching)
- [Common Problems](#common-problems)
- [Best Practices](#best-practices)

## Landing Page Resolution

The CMHC landing page resolver includes advanced URL resolution with:

- **Ranking**: Automatically prioritizes candidates based on file format (XLSX > CSV > XLS > ZIP), URL structure, and other quality indicators
- **Validation**: Checks URLs to reject HTML responses and verify actual file types before download
- **Robust extraction**: Handles various HTML structures and link patterns on CMHC websites
- **Caching**: Caches resolved URLs to reduce churn and make refresh runs stable

### Example Usage

```python
from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page

# Resolve with validation and caching (default)
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page')
for asset in assets:
    print(f"{asset['title']}: {asset['url']} (rank: {asset['rank']})")
    
# Disable validation for faster resolution
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page', validate=False)

# Disable caching to always fetch fresh URLs
assets = resolve_cmhc_landing_page('https://www.cmhc-schl.gc.ca/data-page', use_cache=False)
```

## URL Caching

Resolved CMHC URLs are automatically cached in `publicdata_ca/.cache/` to reduce unnecessary HTTP requests and ensure stability across runs.

**Cache features:**
- Stores resolved URLs per landing page in JSON format
- Validates cached URLs before use (checks if they still return data files)
- Automatically refreshes when cached URLs become invalid
- Can be disabled with `use_cache=False` parameter
- Can be cleared using the `clear_cache()` function

**Clear cache:**
```python
from publicdata_ca.url_cache import clear_cache

clear_cache(landing_url)  # Clear specific URL cache
clear_cache()             # Clear all CMHC caches
```

## Common Problems

### Problem: "No files downloaded from landing page"

**Cause:** The landing page structure changed, or no data file links were found.

**Solutions:**

1. **Inspect the landing page manually** - Visit the URL in a browser to see what changed

2. **Disable caching temporarily** to force fresh resolution:
   ```python
   from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page
   assets = resolve_cmhc_landing_page(url, use_cache=False)
   ```

3. **Clear the cache** if stale URLs are causing issues:
   ```python
   from publicdata_ca.url_cache import clear_cache
   clear_cache(landing_url)  # Clear specific URL cache
   clear_cache()             # Clear all CMHC caches
   ```

4. **Check if the page uses JavaScript** - Some CMHC pages load content dynamically, requiring manual URL extraction

### Problem: Landing page returns HTML instead of data file

**Cause:** The resolver extracted a link that points to another HTML page, not a direct file.

**Solutions:**

1. **Validation is enabled by default** - The resolver will detect and skip HTML responses

2. **Check the resolved assets** to see what was found:
   ```python
   assets = resolve_cmhc_landing_page(url, validate=True)
   for asset in assets:
       print(f"{asset['title']}: {asset['url']} (rank: {asset['rank']}, validated: {asset['validated']})")
   ```

3. **Look for validation errors** in the asset metadata:
   ```python
   if 'validation_error' in asset:
       print(f"Validation failed: {asset['validation_error']}")
   ```

### Problem: Download succeeds but gets wrong file format

**Cause:** Multiple file formats available; ranking selected a lower-quality format.

**Solutions:**

1. **Check asset rankings** - XLSX is ranked highest, followed by CSV, then XLS

2. **Filter by format** in the CMHC provider:
   ```python
   from publicdata_ca.providers.cmhc import download_cmhc_asset
   result = download_cmhc_asset(url, output_dir, asset_filter='xlsx')
   ```

3. **Manually select from resolved assets**:
   ```python
   assets = resolve_cmhc_landing_page(url)
   xlsx_assets = [a for a in assets if a['format'] == 'xlsx']
   ```

### Problem: Cache contains outdated URLs

**Cause:** CMHC updated their file URLs but cache still has old URLs.

**Solutions:**

1. **The cache auto-validates** - If the cached URL returns HTML, it's automatically refreshed

2. **Force refresh by clearing cache**:
   ```python
   from publicdata_ca.url_cache import clear_cache
   clear_cache()  # Clear all CMHC caches
   ```

3. **Disable caching when calling the resolver directly**:
   ```python
   from publicdata_ca.resolvers.cmhc_landing import resolve_cmhc_landing_page
   # Force fresh resolution by disabling cache
   assets = resolve_cmhc_landing_page(url, use_cache=False)
   ```

### Problem: "Manual download required" in refresh report

**Cause:** Dataset has neither `direct_url` nor `page_url` configured.

**Solutions:**

1. **Find the correct URL** - Visit CMHC's website to locate the dataset

2. **Update the dataset definition** in your profile or code:
   ```python
   ref = DatasetRef(
       provider='cmhc',
       id='my_dataset',
       params={'page_url': 'https://www.cmhc-schl.gc.ca/...'}
   )
   ```

3. **Or provide a direct URL** if known:
   ```python
   ref = DatasetRef(
       provider='cmhc',
       id='my_dataset',
       params={'direct_url': 'https://assets.cmhc-schl.gc.ca/...'}
   )
   ```

## Best Practices

1. **Use caching in production** - Reduces load on CMHC servers and improves reliability

2. **Validate during development** - Set `validate=True` to catch broken links early

3. **Monitor refresh reports** - Check `result` and `notes` columns for issues:
   ```python
   from publicdata_ca import refresh_datasets
   
   report = refresh_datasets()
   errors = report[report['result'] == 'error']
   if not errors.empty:
       print("Failed downloads:")
       print(errors[['dataset', 'notes']])
   ```

4. **Pin working direct URLs** - If you find a stable Azure blob URL, add it as `direct_url` to skip landing page resolution

5. **Test after CMHC releases** - Major CMHC data releases (e.g., annual reports) often come with website redesigns

## Getting Help

If you continue to experience issues:

1. Check the [GitHub Issues](https://github.com/ajharris/publicdata_ca/issues) for known problems
2. Open a new issue with:
   - The landing page URL
   - Error messages
   - Output from `resolve_cmhc_landing_page()` with `validate=True`
3. Consider contributing a fix if you identify the root cause
