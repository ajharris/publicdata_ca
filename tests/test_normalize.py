"""Tests for normalization utilities."""

import pytest
from publicdata_ca.normalize import (
    NormalizedPeriod,
    NormalizedGeo,
    NormalizedUnit,
    normalize_frequency,
    parse_date,
    parse_period,
    normalize_geo,
    normalize_unit,
    normalize_dataset_metadata,
)


class TestNormalizeFrequency:
    """Tests for frequency normalization."""
    
    def test_normalize_monthly_variations(self):
        assert normalize_frequency('Monthly') == 'monthly'
        assert normalize_frequency('monthly') == 'monthly'
        assert normalize_frequency('Month') == 'monthly'
        assert normalize_frequency('M') == 'monthly'
    
    def test_normalize_annual_variations(self):
        assert normalize_frequency('Annual') == 'annual'
        assert normalize_frequency('Yearly') == 'annual'
        assert normalize_frequency('Year') == 'annual'
        assert normalize_frequency('A') == 'annual'
        assert normalize_frequency('Y') == 'annual'
    
    def test_normalize_quarterly_variations(self):
        assert normalize_frequency('Quarterly') == 'quarterly'
        assert normalize_frequency('Quarter') == 'quarterly'
        assert normalize_frequency('Q') == 'quarterly'
        assert normalize_frequency('Q1') == 'quarterly'
        assert normalize_frequency('Q2') == 'quarterly'
    
    def test_normalize_weekly_variations(self):
        assert normalize_frequency('Weekly') == 'weekly'
        assert normalize_frequency('Week') == 'weekly'
        assert normalize_frequency('W') == 'weekly'
    
    def test_normalize_daily_variations(self):
        assert normalize_frequency('Daily') == 'daily'
        assert normalize_frequency('Day') == 'daily'
        assert normalize_frequency('D') == 'daily'
    
    def test_normalize_semi_annual(self):
        assert normalize_frequency('Semi-annual') == 'semi-annual'
        assert normalize_frequency('Semiannual') == 'semi-annual'
        assert normalize_frequency('Biannual') == 'semi-annual'
    
    def test_normalize_unknown_frequency(self):
        result = normalize_frequency('unknown')
        assert result == 'unknown'
    
    def test_normalize_empty_frequency(self):
        assert normalize_frequency('') == 'unknown'
        assert normalize_frequency(None) == 'unknown'
    
    def test_normalize_case_insensitive(self):
        assert normalize_frequency('MONTHLY') == 'monthly'
        assert normalize_frequency('MoNtHlY') == 'monthly'


class TestParseDate:
    """Tests for date parsing."""
    
    def test_parse_iso_format(self):
        assert parse_date('2023-01-15') == '2023-01-15'
        assert parse_date('2024-12-31') == '2024-12-31'
    
    def test_parse_year_month(self):
        assert parse_date('2023-01') == '2023-01-01'
        assert parse_date('2024-12') == '2024-12-01'
    
    def test_parse_year_month_compact(self):
        assert parse_date('202301') == '2023-01-01'
        assert parse_date('202412') == '2024-12-01'
    
    def test_parse_year_only(self):
        assert parse_date('2023') == '2023-01-01'
        assert parse_date('2024') == '2024-01-01'
    
    def test_parse_quarter_format(self):
        assert parse_date('2023-Q1') == '2023-01-01'
        assert parse_date('2023-Q2') == '2023-04-01'
        assert parse_date('2023-Q3') == '2023-07-01'
        assert parse_date('2023-Q4') == '2023-10-01'
    
    def test_parse_quarter_compact(self):
        assert parse_date('2023Q1') == '2023-01-01'
        assert parse_date('2023Q4') == '2023-10-01'
    
    def test_parse_empty_or_none(self):
        assert parse_date('') is None
        assert parse_date(None) is None
    
    def test_parse_invalid_format(self):
        # Invalid formats should return None
        assert parse_date('invalid') is None
        assert parse_date('not-a-date') is None


class TestParsePeriod:
    """Tests for period parsing."""
    
    def test_parse_monthly_period(self):
        period = parse_period('2023-01', 'monthly')
        assert period is not None
        assert period.start_date == '2023-01-01'
        assert period.end_date == '2023-01-31'
        assert period.frequency == 'monthly'
        assert period.raw_value == '2023-01'
    
    def test_parse_february_monthly_period(self):
        period = parse_period('2023-02', 'monthly')
        assert period is not None
        assert period.start_date == '2023-02-01'
        assert period.end_date == '2023-02-28'
    
    def test_parse_december_monthly_period(self):
        period = parse_period('2023-12', 'monthly')
        assert period is not None
        assert period.start_date == '2023-12-01'
        assert period.end_date == '2023-12-31'
    
    def test_parse_quarterly_period(self):
        period = parse_period('2023-Q1', 'quarterly')
        assert period is not None
        assert period.start_date == '2023-01-01'
        assert period.end_date == '2023-03-31'
        assert period.frequency == 'quarterly'
    
    def test_parse_q4_period(self):
        period = parse_period('2023-Q4', 'quarterly')
        assert period is not None
        assert period.start_date == '2023-10-01'
        assert period.end_date == '2023-12-31'
    
    def test_parse_annual_period(self):
        period = parse_period('2023', 'annual')
        assert period is not None
        assert period.start_date == '2023-01-01'
        assert period.end_date == '2023-12-31'
        assert period.frequency == 'annual'
    
    def test_parse_period_without_frequency(self):
        period = parse_period('2023-01-15')
        assert period is not None
        assert period.start_date == '2023-01-15'
        assert period.end_date is None
        assert period.frequency is None
    
    def test_parse_empty_period(self):
        assert parse_period('') is None
        assert parse_period(None) is None
    
    def test_parse_invalid_period(self):
        assert parse_period('invalid') is None


class TestNormalizeGeo:
    """Tests for geographic normalization."""
    
    def test_normalize_canada(self):
        geo = normalize_geo('Canada')
        assert geo is not None
        assert geo.code == 'CA'
        assert geo.name == 'Canada'
        assert geo.level == 'country'
        assert geo.raw_value == 'Canada'
    
    def test_normalize_canada_code(self):
        geo = normalize_geo('CA')
        assert geo is not None
        assert geo.code == 'CA'
        assert geo.level == 'country'
    
    def test_normalize_ontario(self):
        geo = normalize_geo('Ontario')
        assert geo is not None
        assert geo.code == 'CA-ON'
        assert geo.level == 'province'
        assert geo.raw_value == 'Ontario'
    
    def test_normalize_province_code(self):
        geo = normalize_geo('ON')
        assert geo is not None
        assert geo.code == 'CA-ON'
        assert geo.level == 'province'
    
    def test_normalize_quebec(self):
        geo = normalize_geo('Quebec')
        assert geo is not None
        assert geo.code == 'CA-QC'
        assert geo.level == 'province'
    
    def test_normalize_british_columbia(self):
        geo = normalize_geo('British Columbia')
        assert geo is not None
        assert geo.code == 'CA-BC'
        assert geo.level == 'province'
    
    def test_normalize_cma_toronto(self):
        geo = normalize_geo('Toronto CMA')
        assert geo is not None
        assert geo.code == 'CA-CMA-Toronto'
        assert geo.level == 'cma'
        assert 'Toronto' in geo.name
    
    def test_normalize_cma_montreal(self):
        geo = normalize_geo('Montreal census metropolitan area')
        assert geo is not None
        assert geo.level == 'cma'
        assert 'Montreal' in geo.name
    
    def test_normalize_unknown_location(self):
        geo = normalize_geo('Some Random Place')
        assert geo is not None
        assert geo.level == 'unknown'
    
    def test_normalize_empty_geo(self):
        assert normalize_geo('') is None
        assert normalize_geo(None) is None
    
    def test_normalize_case_insensitive(self):
        geo = normalize_geo('ONTARIO')
        assert geo is not None
        assert geo.code == 'CA-ON'


class TestNormalizeUnit:
    """Tests for unit normalization."""
    
    def test_normalize_dollars(self):
        unit = normalize_unit('Dollars')
        assert unit is not None
        assert unit.symbol == '$'
        assert unit.name == 'Canadian dollars'
        assert unit.multiplier == 1.0
        assert unit.raw_value == 'Dollars'
    
    def test_normalize_dollar_symbol(self):
        unit = normalize_unit('$')
        assert unit is not None
        assert unit.symbol == '$'
        assert unit.name == 'Canadian dollars'
    
    def test_normalize_thousands_of_dollars(self):
        unit = normalize_unit('Thousands of dollars')
        assert unit is not None
        assert unit.symbol == '$'
        assert unit.multiplier == 1000.0
    
    def test_normalize_millions_of_dollars(self):
        unit = normalize_unit('Millions of dollars')
        assert unit is not None
        assert unit.symbol == '$'
        assert unit.multiplier == 1000000.0
    
    def test_normalize_percent(self):
        unit = normalize_unit('Percent')
        assert unit is not None
        assert unit.symbol == '%'
        assert unit.name == 'percent'
        assert unit.multiplier == 1.0
    
    def test_normalize_percentage(self):
        unit = normalize_unit('Percentage')
        assert unit is not None
        assert unit.symbol == '%'
    
    def test_normalize_persons(self):
        unit = normalize_unit('Persons')
        assert unit is not None
        assert unit.symbol == 'persons'
        assert unit.name == 'persons'
        assert unit.multiplier == 1.0
    
    def test_normalize_thousands_of_persons(self):
        unit = normalize_unit('Thousands of persons')
        assert unit is not None
        assert unit.symbol == 'persons'
        assert unit.multiplier == 1000.0
    
    def test_normalize_index(self):
        unit = normalize_unit('Index')
        assert unit is not None
        assert unit.symbol == 'index'
        assert unit.name == 'index'
    
    def test_normalize_units(self):
        unit = normalize_unit('Units')
        assert unit is not None
        assert unit.symbol == 'units'
        assert unit.multiplier == 1.0
    
    def test_normalize_empty_unit(self):
        assert normalize_unit('') is None
        assert normalize_unit(None) is None
    
    def test_normalize_unknown_unit(self):
        unit = normalize_unit('CustomMetric')
        assert unit is not None
        assert unit.symbol == 'CustomMetric'
        assert unit.multiplier == 1.0
    
    def test_normalize_case_insensitive(self):
        unit = normalize_unit('DOLLARS')
        assert unit is not None
        assert unit.symbol == '$'


class TestNormalizeDatasetMetadata:
    """Tests for comprehensive metadata normalization."""
    
    def test_normalize_all_fields(self):
        metadata = {
            'frequency': 'Monthly',
            'geo': 'Ontario',
            'unit': 'Dollars',
            'period': '2023-01'
        }
        result = normalize_dataset_metadata(metadata)
        
        assert result['normalized_frequency'] == 'monthly'
        assert result['raw_frequency'] == 'Monthly'
        
        assert result['normalized_geo']['code'] == 'CA-ON'
        assert result['normalized_geo']['level'] == 'province'
        assert result['raw_geo'] == 'Ontario'
        
        assert result['normalized_unit']['symbol'] == '$'
        assert result['normalized_unit']['multiplier'] == 1.0
        assert result['raw_unit'] == 'Dollars'
        
        assert result['normalized_period']['start_date'] == '2023-01-01'
        assert result['normalized_period']['end_date'] == '2023-01-31'
    
    def test_normalize_preserves_original_fields(self):
        metadata = {
            'frequency': 'Monthly',
            'geo': 'Ontario',
            'provider_specific_field': 'value123'
        }
        result = normalize_dataset_metadata(metadata)
        
        # Original fields should be preserved
        assert result['frequency'] == 'Monthly'
        assert result['geo'] == 'Ontario'
        assert result['provider_specific_field'] == 'value123'
    
    def test_normalize_without_preserve_raw(self):
        metadata = {
            'frequency': 'Monthly',
            'geo': 'Ontario'
        }
        result = normalize_dataset_metadata(metadata, preserve_raw=False)
        
        assert 'raw_frequency' not in result
        assert 'raw_geo' not in result
        assert result['normalized_frequency'] == 'monthly'
    
    def test_normalize_date_field(self):
        metadata = {
            'date': '2023-01-15'
        }
        result = normalize_dataset_metadata(metadata)
        
        assert result['normalized_date'] == '2023-01-15'
        assert result['raw_date'] == '2023-01-15'
    
    def test_normalize_period_with_frequency_hint(self):
        metadata = {
            'period': '2023-01',
            'frequency': 'Monthly'
        }
        result = normalize_dataset_metadata(metadata)
        
        assert result['normalized_period']['start_date'] == '2023-01-01'
        assert result['normalized_period']['end_date'] == '2023-01-31'
        assert result['normalized_period']['frequency'] == 'monthly'
    
    def test_normalize_empty_metadata(self):
        result = normalize_dataset_metadata({})
        assert result == {}
    
    def test_normalize_partial_metadata(self):
        metadata = {
            'frequency': 'Annual',
            'some_other_field': 'value'
        }
        result = normalize_dataset_metadata(metadata)
        
        assert result['normalized_frequency'] == 'annual'
        assert result['some_other_field'] == 'value'
        assert 'normalized_geo' not in result
        assert 'normalized_unit' not in result


class TestNormalizedPeriod:
    """Tests for NormalizedPeriod dataclass."""
    
    def test_create_normalized_period(self):
        period = NormalizedPeriod(
            start_date='2023-01-01',
            end_date='2023-01-31',
            frequency='monthly',
            raw_value='2023-01'
        )
        assert period.start_date == '2023-01-01'
        assert period.end_date == '2023-01-31'
        assert period.frequency == 'monthly'
        assert period.raw_value == '2023-01'
    
    def test_create_period_without_end_date(self):
        period = NormalizedPeriod(start_date='2023-01-15')
        assert period.start_date == '2023-01-15'
        assert period.end_date is None
        assert period.frequency is None


class TestNormalizedGeo:
    """Tests for NormalizedGeo dataclass."""
    
    def test_create_normalized_geo(self):
        geo = NormalizedGeo(
            code='CA-ON',
            name='Ontario',
            level='province',
            raw_value='Ontario'
        )
        assert geo.code == 'CA-ON'
        assert geo.name == 'Ontario'
        assert geo.level == 'province'
        assert geo.raw_value == 'Ontario'


class TestNormalizedUnit:
    """Tests for NormalizedUnit dataclass."""
    
    def test_create_normalized_unit(self):
        unit = NormalizedUnit(
            symbol='$',
            name='Canadian dollars',
            multiplier=1000.0,
            raw_value='Thousands of dollars'
        )
        assert unit.symbol == '$'
        assert unit.name == 'Canadian dollars'
        assert unit.multiplier == 1000.0
        assert unit.raw_value == 'Thousands of dollars'
    
    def test_create_unit_with_default_multiplier(self):
        unit = NormalizedUnit(symbol='%', name='percent')
        assert unit.multiplier == 1.0


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_normalize_frequency_with_whitespace(self):
        assert normalize_frequency('  Monthly  ') == 'monthly'
        assert normalize_frequency('\tAnnual\n') == 'annual'
    
    def test_parse_date_with_whitespace(self):
        assert parse_date('  2023-01-15  ') == '2023-01-15'
    
    def test_normalize_geo_with_whitespace(self):
        geo = normalize_geo('  Ontario  ')
        assert geo is not None
        assert geo.code == 'CA-ON'
    
    def test_normalize_unit_with_whitespace(self):
        unit = normalize_unit('  Dollars  ')
        assert unit is not None
        assert unit.symbol == '$'
    
    def test_normalize_metadata_with_missing_frequency_for_period(self):
        metadata = {
            'period': '2023-01'
        }
        result = normalize_dataset_metadata(metadata)
        
        # Should still parse the period, but without end date
        assert result['normalized_period']['start_date'] == '2023-01-01'
    
    def test_parse_period_with_invalid_frequency(self):
        period = parse_period('2023-01-15', 'invalid_frequency')
        assert period is not None
        assert period.start_date == '2023-01-15'
        # End date should be None for unknown frequency
        assert period.end_date is None
