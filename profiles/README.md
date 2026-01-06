# Profiles

This directory contains YAML profile files that define collections of datasets to refresh together. Profiles are useful for organizing datasets by project, topic, or workflow.

## What is a Profile?

A profile is a YAML file that specifies:
- A collection of datasets to download
- Where to save each dataset
- Optional metadata about datasets (frequency, scope, etc.)
- Refresh options (e.g., whether to skip existing files)

## Example Profiles

This directory includes three example profiles:

### economics.yaml
Core economic indicators including CPI, unemployment rate, and median household income.

**Use case:** Economic analysis and forecasting projects

### housing.yaml
Housing market data from CMHC including rental market reports and housing starts.

**Use case:** Housing market analysis and real estate research

### population.yaml
Population estimates and demographic data.

**Use case:** Demographic studies and population forecasting

## Creating Your Own Profile

Create a new YAML file in this directory with the following structure:

```yaml
name: my_profile
description: Brief description of what this profile contains

datasets:
  # StatsCan dataset
  - provider: statcan
    id: "18100004"
    output: data/raw/cpi_all_items.csv
    params:
      metric: "Consumer Price Index, all-items (NSA)"
      frequency: "Monthly"
      geo_scope: "Canada + provinces"
  
  # CMHC dataset with landing page URL
  - provider: cmhc
    id: rental_market
    output: data/raw/rental_market.xlsx
    params:
      metric: "Rental Market Report data tables"
      frequency: "Annual"
      page_url: "https://www.cmhc-schl.gc.ca/..."
  
  # CMHC dataset with direct download URL
  - provider: cmhc
    id: housing_starts
    output: data/raw/housing_starts.xlsx
    params:
      metric: "Monthly housing starts"
      frequency: "Monthly"
      direct_url: "https://assets.cmhc-schl.gc.ca/..."

output_dir: data/raw
options:
  skip_existing: true
```

## Profile Fields

### Required Fields
- `name`: Unique identifier for the profile (lowercase, no spaces)
- `description`: Human-readable description

### Dataset Fields
- `provider`: Data provider ("statcan" or "cmhc")
- `id`: Dataset identifier
  - For StatsCan: 8-digit table number (e.g., "18100004")
  - For CMHC: Any unique identifier
- `output`: Path where the dataset will be saved (relative to project root)

### Optional Dataset Fields
- `params`: Additional metadata
  - `metric`: Dataset description
  - `frequency`: Update frequency (Monthly, Annual, etc.)
  - `geo_scope`: Geographic coverage
  - `page_url`: CMHC landing page URL (for CMHC datasets)
  - `direct_url`: Direct download URL (for CMHC datasets)

### Optional Profile Fields
- `output_dir`: Default output directory for all datasets
- `options`: Refresh options
  - `skip_existing`: Skip downloads for files that already exist (default: true)

## Using Profiles

### Command Line

```bash
# List all available profiles
publicdata profile list

# Run a profile
publicdata profile run my_profile

# Run with force re-download
publicdata profile run my_profile --force

# Run with detailed output
publicdata profile run my_profile --verbose

# Create a manifest after running
publicdata profile run my_profile --manifest
```

### Python API

```python
from publicdata_ca import run_profile, load_profile, list_profiles

# List all available profiles
profiles = list_profiles()
print(f"Available profiles: {profiles}")

# Run a profile
report = run_profile("my_profile")
print(report[['dataset', 'result', 'notes']])

# Load and inspect a profile
profile = load_profile("profiles/my_profile.yaml")
print(f"Profile: {profile.name}")
print(f"Datasets: {len(profile.datasets)}")

# Run with custom options
report = run_profile("my_profile", force_download=True)
```

## Best Practices

1. **Use descriptive names**: Choose clear, lowercase names without spaces
2. **Group related datasets**: Organize datasets by project, topic, or analysis type
3. **Document your profiles**: Add meaningful descriptions and dataset metadata
4. **Version control**: Keep your profiles in version control to track changes
5. **Test before sharing**: Run your profile to ensure all datasets download correctly
6. **Use relative paths**: Keep output paths relative to the project root for portability

## Tips

- **StatsCan datasets**: Find table numbers at https://www150.statcan.gc.ca/
- **CMHC datasets**: Use `page_url` for landing pages or `direct_url` for known URLs
- **Output paths**: Organize by provider or topic (e.g., `data/raw/statcan/`, `data/raw/cmhc/`)
- **Skip existing**: Set `skip_existing: true` to avoid re-downloading unchanged files
- **Force refresh**: Use `--force` flag to re-download all files

## Need Help?

- See the main README.md for more examples
- Check existing profiles for reference
- Run `publicdata profile --help` for CLI options
- Use `publicdata --help` for general CLI documentation
