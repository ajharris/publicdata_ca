# Provider Testing Strategy

This document describes the testing strategy for provider implementations in publicdata_ca.

## Overview

Provider testing is organized into two complementary approaches:

1. **Contract Tests**: Offline tests using fixtures that validate provider implementations against the Provider interface
2. **Smoke Tests**: Optional live tests that verify basic connectivity to real provider endpoints

## Contract Tests

Contract tests are the primary testing mechanism for providers. They use saved API response fixtures to ensure:

- Providers correctly implement the Provider interface (search, resolve, fetch methods)
- Providers correctly parse real API responses
- Provider behavior is consistent and predictable
- Changes to providers don't break existing functionality

### Location and Structure

- **Test file**: `tests/test_provider_contracts.py`
- **Fixtures**: `tests/fixtures/<provider_name>/`

Each provider has:
- A test class (e.g., `TestBOCValetProviderContract`)
- One or more fixture files with real API responses
- Tests for each Provider interface method (search, resolve, fetch)

### Running Contract Tests

Contract tests run by default as part of the test suite:

```bash
# Run all contract tests
pytest tests/test_provider_contracts.py -v

# Run tests for a specific provider
pytest tests/test_provider_contracts.py::TestStatCanProviderContract -v

# Run a specific test
pytest tests/test_provider_contracts.py::TestStatCanProviderContract::test_resolve_contract -v
```

### Adding Fixtures for a New Provider

1. Create a fixture directory: `tests/fixtures/<provider_name>/`
2. Save real API responses as JSON or XML files
3. Reference fixtures in contract tests using `load_fixture()`

Example fixture structure:
```
tests/fixtures/
├── boc_valet/
│   ├── FXUSDCAD_metadata.json
│   └── FXUSDCAD_observations.json
├── ckan/
│   ├── search_response.json
│   └── package_response.json
├── sdmx/
│   ├── dataflow_response.xml
│   └── data_response.xml
└── socrata/
    ├── search_response.json
    └── metadata_response.json
```

## Smoke Tests

Smoke tests are **optional** integration tests that make actual HTTP requests to live provider endpoints. They verify:

- Basic connectivity to provider APIs
- Provider endpoints are still accessible
- Core functionality works end-to-end

**Important**: Smoke tests:
- Are **disabled by default** to avoid network dependencies
- May fail due to network issues or API changes
- Should be minimal and fast (avoid large downloads)
- Are marked with `@pytest.mark.smoke`

### Location

- **Test file**: `tests/test_provider_smoke.py`

### Running Smoke Tests

Smoke tests are deselected by default. To run them:

```bash
# Run all smoke tests
pytest tests/test_provider_smoke.py -v -m smoke

# Run smoke tests for a specific provider
pytest tests/test_provider_smoke.py::TestStatCanProviderSmoke -v -m smoke

# Run ALL tests including smoke tests
pytest tests/ -v -m "smoke or not smoke"

# Skip smoke tests explicitly (default behavior)
pytest tests/ -v -m "not smoke"
```

### Disabling Smoke Tests via Environment Variable

You can skip smoke tests even when explicitly requested:

```bash
# Set environment variable to skip smoke tests
export SKIP_SMOKE_TESTS=1
pytest tests/test_provider_smoke.py -v -m smoke
# All tests will be skipped
```

## Provider Coverage

Current provider test coverage:

| Provider | Contract Tests | Fixtures | Smoke Tests |
|----------|----------------|----------|-------------|
| StatsCan | ✅ | ✅ (ZIP) | ✅ |
| CMHC | ✅ | ✅ (HTML) | ✅ |
| BOC Valet | ✅ | ✅ (JSON) | ✅ |
| CKAN | ✅ | ✅ (JSON) | ✅ |
| Open Canada | ✅ | ✅ (JSON) | ✅ |
| SDMX | ✅ | ✅ (XML/JSON) | ✅ |
| Socrata | ✅ | ✅ (JSON) | ✅ |

## Best Practices

### For Contract Tests

1. **Use Real API Responses**: Fixtures should be actual responses from provider APIs, not simplified mocks
2. **Test All Interface Methods**: Ensure search, resolve, and fetch are all tested
3. **Validate Contract Compliance**: Check return types, required fields, and error handling
4. **Keep Fixtures Small**: Use minimal but realistic data in fixtures

### For Smoke Tests

1. **Keep Tests Minimal**: Only test basic connectivity, not full functionality
2. **Use Small Datasets**: Avoid downloading large files
3. **Handle Failures Gracefully**: Use `pytest.skip()` if endpoints are unavailable
4. **Don't Rely on External Data**: Tests may fail if datasets are removed/changed

## Adding Tests for a New Provider

When adding a new provider, follow these steps:

1. **Create Contract Tests**:
   - Add a test class in `tests/test_provider_contracts.py`
   - Create fixture directory `tests/fixtures/<provider_name>/`
   - Add fixture files with real API responses
   - Implement tests for search, resolve, and fetch

2. **Create Smoke Tests** (optional):
   - Add a test class in `tests/test_provider_smoke.py`
   - Mark all tests with `@pytest.mark.smoke`
   - Test basic connectivity only
   - Use `skip_if_smoke_disabled()` at start of each test

3. **Run Tests**:
   ```bash
   # Run contract tests
   pytest tests/test_provider_contracts.py::TestYourProviderContract -v
   
   # Run smoke tests
   pytest tests/test_provider_smoke.py::TestYourProviderSmoke -v -m smoke
   ```

## Continuous Integration

In CI environments:

- **Contract tests** always run (fast, no network dependencies)
- **Smoke tests** are skipped by default (to avoid network dependencies)
- Smoke tests can be run on a schedule to verify API health

Example CI configuration:
```yaml
# Regular test run (excludes smoke)
- name: Run tests
  run: pytest tests/ -v

# Optional: Run smoke tests on schedule
- name: Run smoke tests
  run: pytest tests/ -v -m smoke
  if: github.event_name == 'schedule'
```
