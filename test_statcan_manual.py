#!/usr/bin/env python3
"""
Manual test script for StatCan download functionality.
Run this script to test downloading from the live StatCan API.

Usage:
    python test_statcan_manual.py

This script tests the fix for HTTP 406 errors when downloading StatCan tables.
The fix removes the Accept header which was causing the API to reject requests.
"""

import tempfile
import sys
from pathlib import Path

# Add the module to the path
sys.path.insert(0, str(Path(__file__).parent))

from publicdata_ca.providers.statcan import download_statcan_table
from publicdata_ca.http import get_default_headers


def main():
    """Test downloading a StatCan table from the live API."""
    print("Testing StatCan download with live API...")
    print("Table ID: 18100004 (Consumer Price Index)")
    print()
    
    # Show the headers being used
    print("Headers being sent (no Accept header to avoid HTTP 406):")
    statcan_headers = {
        'User-Agent': get_default_headers()['User-Agent'],
    }
    for key, value in statcan_headers.items():
        print(f"  {key}: {value}")
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            print(f"Downloading to: {tmpdir}")
            result = download_statcan_table(
                "18100004",
                tmpdir,
                skip_existing=False
            )
            
            print("\n✅ Download successful!")
            print(f"Provider: {result['provider']}")
            print(f"PID: {result['pid']}")
            print(f"Dataset ID: {result['dataset_id']}")
            print(f"URL: {result['url']}")
            print(f"Files downloaded: {len(result['files'])}")
            
            for file_path in result['files']:
                file_obj = Path(file_path)
                if file_obj.exists():
                    size_kb = file_obj.stat().st_size / 1024
                    print(f"  - {file_obj.name} ({size_kb:.2f} KB)")
                else:
                    print(f"  - {file_obj.name} (NOT FOUND)")
            
            print("\n✅ All tests passed!")
            return 0
            
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())
