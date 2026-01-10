# Quick Migration Guide

This guide helps existing users of publicdata_ca adapt to the updated documentation structure and modern API patterns.

## Documentation Location Changes

If you were reading the old README and looking for specific topics, here's where to find them now:

| Old README Section | New Location |
|-------------------|--------------|
| StatCan Provider details | [docs/PROVIDERS.md#statcan-provider](docs/PROVIDERS.md#statcan-provider) |
| CMHC Provider details | [docs/PROVIDERS.md#cmhc-provider](docs/PROVIDERS.md#cmhc-provider) |
| CMHC Troubleshooting | [docs/CMHC_TROUBLESHOOTING.md](docs/CMHC_TROUBLESHOOTING.md) |
| Open Canada Provider | [docs/PROVIDERS.md#open-canada-provider](docs/PROVIDERS.md#open-canada-provider) |
| CKAN Provider | [docs/PROVIDERS.md#ckan-provider-generic](docs/PROVIDERS.md#ckan-provider-generic) |
| HTTP Caching | [docs/ADVANCED_FEATURES.md#http-caching](docs/ADVANCED_FEATURES.md#http-caching) |
| Provenance Tracking | [docs/ADVANCED_FEATURES.md#provenance-tracking](docs/ADVANCED_FEATURES.md#provenance-tracking) |
| Run Reports | [docs/ADVANCED_FEATURES.md#run-reports](docs/ADVANCED_FEATURES.md#run-reports) |
| Profiles System | [docs/ADVANCED_FEATURES.md#profiles-system](docs/ADVANCED_FEATURES.md#profiles-system) |
| Normalization | [docs/ADVANCED_FEATURES.md#normalization-utilities](docs/ADVANCED_FEATURES.md#normalization-utilities) |
| Publishing to PyPI | [docs/PYPI_PUBLISHING.md](docs/PYPI_PUBLISHING.md) |

## Code Changes Required

### Old Pattern (Legacy - Don't use)

```python
# ❌ Old function-based approach
from publicdata_ca.providers.statcan import download_statcan_table

download_statcan_table("18100004", "./data/raw/cpi.csv")
```

### New Pattern (Modern - Use this)

```python
# ✅ Modern Provider pattern
from publicdata_ca.providers import StatCanProvider
from publicdata_ca.provider import DatasetRef

provider = StatCanProvider()
ref = DatasetRef(provider='statcan', id='18100004')
result = provider.fetch(ref, './data')
print(f"Downloaded: {result['files']}")
```

## Why the Change?

The modern Provider pattern offers several advantages:

1. **Consistency** - All providers work the same way
2. **Flexibility** - Easier to switch between providers
3. **Extensibility** - Simpler to add custom providers
4. **Type Safety** - Better IDE support and autocomplete
5. **Testing** - Easier to mock and test

## Backward Compatibility

**Good news:** The old function-based API still works! You don't need to change your existing code immediately.

However, we recommend migrating to the new pattern for:
- Better long-term support
- Access to new features
- Improved error handling

## Need Help?

- **New to publicdata_ca?** Start with [README.md](README.md)
- **Looking for examples?** Check [examples/](examples/)
- **Implementing a custom provider?** See [docs/ADDING_A_PROVIDER.md](docs/ADDING_A_PROVIDER.md)
- **Questions or issues?** Open an issue at https://github.com/ajharris/publicdata_ca/issues
