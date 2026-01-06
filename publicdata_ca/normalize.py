"""
Normalization utilities for time, geo, frequency, and units.

This module provides minimal normalization helpers to standardize common data attributes
while keeping provider-specific fields intact. It supports:
- Time: Parse and standardize dates or periods
- Frequency: Attach and normalize frequency labels
- Geography: Normalize geographic labels
- Units: Carry and standardize measurement units

These utilities support a common minimal schema when possible while preserving
provider-specific metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union


@dataclass
class NormalizedPeriod:
    """
    Standardized representation of a time period.
    
    Attributes:
        start_date: ISO 8601 formatted start date (YYYY-MM-DD)
        end_date: ISO 8601 formatted end date (YYYY-MM-DD), None for point-in-time
        frequency: Normalized frequency label (e.g., 'monthly', 'annual')
        raw_value: Original period string before normalization
    """
    start_date: str
    end_date: Optional[str] = None
    frequency: Optional[str] = None
    raw_value: Optional[str] = None


@dataclass
class NormalizedGeo:
    """
    Standardized representation of a geographic location.
    
    Attributes:
        code: Standardized geographic code (e.g., 'CA', 'CA-ON', 'CA-QC-Montreal')
        name: Standardized geographic name
        level: Geographic level (e.g., 'country', 'province', 'cma', 'municipality')
        raw_value: Original geographic label before normalization
    """
    code: str
    name: str
    level: str
    raw_value: Optional[str] = None


@dataclass
class NormalizedUnit:
    """
    Standardized representation of measurement units.
    
    Attributes:
        symbol: Standard unit symbol (e.g., '$', '%', 'persons')
        name: Full unit name (e.g., 'Canadian dollars', 'percent', 'persons')
        multiplier: Multiplier for the unit (e.g., 1000 for thousands)
        raw_value: Original unit string before normalization
    """
    symbol: str
    name: str
    multiplier: float = 1.0
    raw_value: Optional[str] = None


# Frequency normalization mappings
FREQUENCY_MAPPINGS = {
    # Annual variations
    'annual': 'annual',
    'yearly': 'annual',
    'annually': 'annual',
    'year': 'annual',
    'a': 'annual',
    'y': 'annual',
    
    # Quarterly variations
    'quarterly': 'quarterly',
    'quarter': 'quarterly',
    'q': 'quarterly',
    'q1': 'quarterly',
    'q2': 'quarterly',
    'q3': 'quarterly',
    'q4': 'quarterly',
    
    # Monthly variations
    'monthly': 'monthly',
    'month': 'monthly',
    'm': 'monthly',
    
    # Weekly variations
    'weekly': 'weekly',
    'week': 'weekly',
    'w': 'weekly',
    
    # Daily variations
    'daily': 'daily',
    'day': 'daily',
    'd': 'daily',
    
    # Other common frequencies
    'semi-annual': 'semi-annual',
    'semiannual': 'semi-annual',
    'biannual': 'semi-annual',
    'bi-annual': 'semi-annual',
}


# Geographic level patterns
GEO_LEVEL_PATTERNS = {
    'country': [
        r'^canada$',
        r'^ca$',
    ],
    'province': [
        r'^(ontario|quebec|british columbia|alberta|manitoba|saskatchewan|nova scotia|new brunswick|newfoundland and labrador|prince edward island|northwest territories|yukon|nunavut)$',
        r'^ca-(on|qc|bc|ab|mb|sk|ns|nb|nl|pe|nt|yt|nu)$',
    ],
    'cma': [
        r'census metropolitan area',
        r'\bcma\b',
        r'(toronto|montreal|vancouver|calgary|edmonton|ottawa|winnipeg|quebec city|hamilton)(\s+cma)?',
    ],
    'municipality': [
        r'city',
        r'town',
        r'municipality',
    ],
}


# Province code mappings
PROVINCE_CODES = {
    'ontario': 'CA-ON',
    'on': 'CA-ON',
    'quebec': 'CA-QC',
    'qc': 'CA-QC',
    'british columbia': 'CA-BC',
    'bc': 'CA-BC',
    'alberta': 'CA-AB',
    'ab': 'CA-AB',
    'manitoba': 'CA-MB',
    'mb': 'CA-MB',
    'saskatchewan': 'CA-SK',
    'sk': 'CA-SK',
    'nova scotia': 'CA-NS',
    'ns': 'CA-NS',
    'new brunswick': 'CA-NB',
    'nb': 'CA-NB',
    'newfoundland and labrador': 'CA-NL',
    'nl': 'CA-NL',
    'prince edward island': 'CA-PE',
    'pe': 'CA-PE',
    'northwest territories': 'CA-NT',
    'nt': 'CA-NT',
    'yukon': 'CA-YT',
    'yt': 'CA-YT',
    'nunavut': 'CA-NU',
    'nu': 'CA-NU',
}


# Unit mappings
UNIT_MAPPINGS = {
    # Currency
    'dollars': ('$', 'Canadian dollars', 1.0),
    'dollar': ('$', 'Canadian dollars', 1.0),
    '$': ('$', 'Canadian dollars', 1.0),
    'cad': ('$', 'Canadian dollars', 1.0),
    'thousands of dollars': ('$', 'Canadian dollars', 1000.0),
    'millions of dollars': ('$', 'Canadian dollars', 1000000.0),
    
    # Percentage
    'percent': ('%', 'percent', 1.0),
    'percentage': ('%', 'percent', 1.0),
    '%': ('%', 'percent', 1.0),
    
    # Count
    'persons': ('persons', 'persons', 1.0),
    'people': ('persons', 'persons', 1.0),
    'person': ('persons', 'persons', 1.0),
    'units': ('units', 'units', 1.0),
    'unit': ('units', 'units', 1.0),
    'number': ('units', 'units', 1.0),
    'count': ('units', 'units', 1.0),
    'thousands': ('units', 'units', 1000.0),
    'thousands of units': ('units', 'units', 1000.0),
    'thousands of persons': ('persons', 'persons', 1000.0),
    
    # Index
    'index': ('index', 'index', 1.0),
    'index (2002=100)': ('index', 'index (2002=100)', 1.0),
}


def normalize_frequency(frequency: str) -> str:
    """
    Normalize frequency labels to standard values.
    
    Args:
        frequency: Raw frequency string (e.g., 'Monthly', 'Annual', 'Q')
    
    Returns:
        Normalized frequency string (e.g., 'monthly', 'annual', 'quarterly')
    
    Examples:
        >>> normalize_frequency('Monthly')
        'monthly'
        >>> normalize_frequency('Annual')
        'annual'
        >>> normalize_frequency('Q')
        'quarterly'
    """
    if not frequency:
        return 'unknown'
    
    # Convert to lowercase and strip whitespace
    freq_lower = frequency.lower().strip()
    
    # Try direct mapping
    if freq_lower in FREQUENCY_MAPPINGS:
        return FREQUENCY_MAPPINGS[freq_lower]
    
    # Try to extract from longer strings (but only for whole word matches to avoid false positives)
    for pattern, normalized in FREQUENCY_MAPPINGS.items():
        # Only match if pattern is a word boundary or the entire string
        if len(pattern) > 1 and (f' {pattern} ' in f' {freq_lower} ' or freq_lower == pattern):
            return normalized
    
    # Return original if no match found
    return freq_lower


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse a date string to ISO 8601 format (YYYY-MM-DD).
    
    Supports various common date formats:
    - ISO format: 2023-01-15
    - Year-month: 2023-01, 202301
    - Year only: 2023
    - Quarter: 2023-Q1, 2023Q1
    
    Args:
        date_str: Date string to parse
    
    Returns:
        ISO 8601 formatted date string (YYYY-MM-DD) or None if parsing fails
    
    Examples:
        >>> parse_date('2023-01-15')
        '2023-01-15'
        >>> parse_date('2023-01')
        '2023-01-01'
        >>> parse_date('2023')
        '2023-01-01'
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # ISO format: YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Year-month: YYYY-MM or YYYYMM
    if re.match(r'^\d{4}-\d{2}$', date_str):
        return f"{date_str}-01"
    
    if re.match(r'^\d{6}$', date_str):
        return f"{date_str[:4]}-{date_str[4:6]}-01"
    
    # Year only: YYYY
    if re.match(r'^\d{4}$', date_str):
        return f"{date_str}-01-01"
    
    # Quarter: 2023-Q1 or 2023Q1
    quarter_match = re.match(r'^(\d{4})-?Q([1-4])$', date_str, re.IGNORECASE)
    if quarter_match:
        year = quarter_match.group(1)
        quarter = int(quarter_match.group(2))
        month = (quarter - 1) * 3 + 1
        return f"{year}-{month:02d}-01"
    
    # Try to parse with datetime
    try:
        # Try common formats
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y%m%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except Exception:
        pass
    
    return None


def parse_period(period_str: str, frequency: Optional[str] = None) -> Optional[NormalizedPeriod]:
    """
    Parse a period string into a normalized period object.
    
    Args:
        period_str: Period string (e.g., '2023-01', '2023-Q1', '2023')
        frequency: Optional frequency hint to aid parsing
    
    Returns:
        NormalizedPeriod object or None if parsing fails
    
    Examples:
        >>> period = parse_period('2023-01', 'monthly')
        >>> period.start_date
        '2023-01-01'
        >>> period.end_date
        '2023-01-31'
        >>> period = parse_period('2023', 'annual')
        >>> period.start_date
        '2023-01-01'
        >>> period.end_date
        '2023-12-31'
    """
    if not period_str:
        return None
    
    period_str = str(period_str).strip()
    normalized_freq = normalize_frequency(frequency) if frequency else None
    
    # Parse start date
    start_date = parse_date(period_str)
    if not start_date:
        return None
    
    # Determine end date based on frequency
    end_date = None
    if normalized_freq == 'monthly':
        # End of month
        year, month = map(int, start_date.split('-')[:2])
        if month == 12:
            end_date = f"{year}-12-31"
        else:
            next_month = month + 1
            # Last day of current month = day before first of next month
            end_date = f"{year}-{next_month:02d}-01"
            # Adjust to last day of previous month
            dt = datetime.strptime(end_date, '%Y-%m-%d')
            from datetime import timedelta
            dt = dt - timedelta(days=1)
            end_date = dt.strftime('%Y-%m-%d')
    
    elif normalized_freq == 'quarterly':
        # End of quarter
        year, month = map(int, start_date.split('-')[:2])
        quarter = (month - 1) // 3 + 1
        end_month = quarter * 3
        if end_month == 12:
            end_date = f"{year}-12-31"
        else:
            # Last day of quarter = day before first of next quarter
            end_date = f"{year}-{end_month + 1:02d}-01"
            dt = datetime.strptime(end_date, '%Y-%m-%d')
            from datetime import timedelta
            dt = dt - timedelta(days=1)
            end_date = dt.strftime('%Y-%m-%d')
    
    elif normalized_freq == 'annual':
        # End of year
        year = int(start_date.split('-')[0])
        end_date = f"{year}-12-31"
    
    return NormalizedPeriod(
        start_date=start_date,
        end_date=end_date,
        frequency=normalized_freq,
        raw_value=period_str
    )


def normalize_geo(geo_str: str) -> Optional[NormalizedGeo]:
    """
    Normalize geographic labels to standard codes and names.
    
    Args:
        geo_str: Raw geographic label (e.g., 'Ontario', 'Toronto CMA', 'Canada')
    
    Returns:
        NormalizedGeo object or None if normalization fails
    
    Examples:
        >>> geo = normalize_geo('Ontario')
        >>> geo.code
        'CA-ON'
        >>> geo.level
        'province'
        >>> geo = normalize_geo('Canada')
        >>> geo.code
        'CA'
        >>> geo.level
        'country'
    """
    if not geo_str:
        return None
    
    geo_lower = geo_str.lower().strip()
    
    # Check for Canada
    if geo_lower in ['canada', 'ca']:
        return NormalizedGeo(
            code='CA',
            name='Canada',
            level='country',
            raw_value=geo_str
        )
    
    # Check for provinces
    if geo_lower in PROVINCE_CODES:
        return NormalizedGeo(
            code=PROVINCE_CODES[geo_lower],
            name=geo_str.title(),
            level='province',
            raw_value=geo_str
        )
    
    # Determine geographic level
    level = 'unknown'
    for geo_level, patterns in GEO_LEVEL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, geo_lower, re.IGNORECASE):
                level = geo_level
                break
        if level != 'unknown':
            break
    
    # For CMAs, try to extract the city name
    if level == 'cma':
        # Extract CMA name
        cma_match = re.search(
            r'(toronto|montreal|vancouver|calgary|edmonton|ottawa|winnipeg|quebec city|hamilton)',
            geo_lower
        )
        if cma_match:
            cma_name = cma_match.group(1).title()
            return NormalizedGeo(
                code=f'CA-CMA-{cma_name.replace(" ", "")}',
                name=f'{cma_name} CMA',
                level='cma',
                raw_value=geo_str
            )
    
    # Generic normalization
    return NormalizedGeo(
        code=geo_str.upper().replace(' ', '-'),
        name=geo_str,
        level=level,
        raw_value=geo_str
    )


def normalize_unit(unit_str: str) -> Optional[NormalizedUnit]:
    """
    Normalize unit labels to standard symbols and names.
    
    Args:
        unit_str: Raw unit string (e.g., 'Dollars', 'Percent', 'Persons')
    
    Returns:
        NormalizedUnit object or None if normalization fails
    
    Examples:
        >>> unit = normalize_unit('Dollars')
        >>> unit.symbol
        '$'
        >>> unit.name
        'Canadian dollars'
        >>> unit = normalize_unit('Thousands of dollars')
        >>> unit.multiplier
        1000.0
    """
    if not unit_str:
        return None
    
    unit_lower = unit_str.lower().strip()
    
    # Try direct mapping
    if unit_lower in UNIT_MAPPINGS:
        symbol, name, multiplier = UNIT_MAPPINGS[unit_lower]
        return NormalizedUnit(
            symbol=symbol,
            name=name,
            multiplier=multiplier,
            raw_value=unit_str
        )
    
    # Try partial matching for common patterns (prioritize longer patterns)
    # Sort by pattern length descending to match longer patterns first
    sorted_patterns = sorted(UNIT_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)
    for pattern, (symbol, name, multiplier) in sorted_patterns:
        if len(pattern) > 3 and pattern in unit_lower:  # Only match longer patterns to avoid false positives
            return NormalizedUnit(
                symbol=symbol,
                name=name,
                multiplier=multiplier,
                raw_value=unit_str
            )
    
    # Return generic normalization
    return NormalizedUnit(
        symbol=unit_str,
        name=unit_str,
        multiplier=1.0,
        raw_value=unit_str
    )


def normalize_dataset_metadata(
    metadata: Dict[str, Any],
    preserve_raw: bool = True
) -> Dict[str, Any]:
    """
    Normalize common dataset metadata fields while preserving provider-specific data.
    
    This function normalizes time, geography, frequency, and units while keeping
    the original provider-specific fields intact (prefixed with 'raw_' if preserve_raw=True).
    
    Args:
        metadata: Dataset metadata dictionary with fields like:
            - frequency: Frequency label
            - geo: Geographic label
            - unit: Unit label
            - period: Period string
            - date: Date string
        preserve_raw: If True, preserve original values with 'raw_' prefix
    
    Returns:
        Dictionary with normalized fields added/updated
    
    Examples:
        >>> metadata = {
        ...     'frequency': 'Monthly',
        ...     'geo': 'Ontario',
        ...     'unit': 'Dollars',
        ...     'period': '2023-01'
        ... }
        >>> normalized = normalize_dataset_metadata(metadata)
        >>> normalized['normalized_frequency']
        'monthly'
        >>> normalized['normalized_geo']['code']
        'CA-ON'
    """
    result = metadata.copy()
    
    # Normalize frequency
    if 'frequency' in metadata:
        freq = metadata['frequency']
        result['normalized_frequency'] = normalize_frequency(freq)
        if preserve_raw and 'raw_frequency' not in result:
            result['raw_frequency'] = freq
    
    # Normalize geography
    if 'geo' in metadata:
        geo = metadata['geo']
        normalized_geo = normalize_geo(geo)
        if normalized_geo:
            result['normalized_geo'] = {
                'code': normalized_geo.code,
                'name': normalized_geo.name,
                'level': normalized_geo.level
            }
            if preserve_raw and 'raw_geo' not in result:
                result['raw_geo'] = geo
    
    # Normalize unit
    if 'unit' in metadata:
        unit = metadata['unit']
        normalized_unit = normalize_unit(unit)
        if normalized_unit:
            result['normalized_unit'] = {
                'symbol': normalized_unit.symbol,
                'name': normalized_unit.name,
                'multiplier': normalized_unit.multiplier
            }
            if preserve_raw and 'raw_unit' not in result:
                result['raw_unit'] = unit
    
    # Parse period
    if 'period' in metadata:
        period = metadata['period']
        freq_hint = metadata.get('frequency') or metadata.get('normalized_frequency')
        normalized_period = parse_period(period, freq_hint)
        if normalized_period:
            result['normalized_period'] = {
                'start_date': normalized_period.start_date,
                'end_date': normalized_period.end_date,
                'frequency': normalized_period.frequency
            }
            if preserve_raw and 'raw_period' not in result:
                result['raw_period'] = period
    
    # Parse date
    if 'date' in metadata and 'period' not in metadata:
        date = metadata['date']
        parsed_date = parse_date(date)
        if parsed_date:
            result['normalized_date'] = parsed_date
            if preserve_raw and 'raw_date' not in result:
                result['raw_date'] = date
    
    return result


__all__ = [
    'NormalizedPeriod',
    'NormalizedGeo',
    'NormalizedUnit',
    'normalize_frequency',
    'parse_date',
    'parse_period',
    'normalize_geo',
    'normalize_unit',
    'normalize_dataset_metadata',
]
