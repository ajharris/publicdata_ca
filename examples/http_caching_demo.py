"""
HTTP Caching Example

This example demonstrates the HTTP caching feature with ETag/Last-Modified headers.
The caching feature helps skip re-downloading files that haven't changed on the server.

Note: This example requires an active internet connection.
"""

from publicdata_ca import download_file, load_cache_metadata
import tempfile
import os


def main():
    """Demonstrate HTTP caching functionality."""
    
    print("HTTP Caching Example")
    print("=" * 60)
    print()
    print("This example demonstrates how HTTP caching works with")
    print("ETag and Last-Modified headers to avoid re-downloading")
    print("unchanged files.")
    print()
    
    # Create a temporary directory for the example
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'sample_data.json')
        
        # Example URL (you can replace with any URL that supports caching)
        # For testing, you could use URLs from government data portals
        url = 'https://www.bankofcanada.ca/valet/observations/FXCADUSD/json?recent=10'
        
        print(f"URL: {url}")
        print(f"Output: {output_path}")
        print()
        
        # First download
        print("1. First download (fetches from server)...")
        try:
            download_file(
                url,
                output_path,
                use_cache=True,  # Enable caching (default)
                write_metadata=False
            )
            print("   ✓ File downloaded")
            
            # Show file size
            size = os.path.getsize(output_path)
            print(f"   ✓ Size: {size:,} bytes")
            
            # Check if cache metadata was saved
            cache_meta = load_cache_metadata(output_path)
            if cache_meta:
                print(f"   ✓ Cache metadata saved:")
                if cache_meta.get('etag'):
                    print(f"      - ETag: {cache_meta['etag']}")
                if cache_meta.get('last_modified'):
                    print(f"      - Last-Modified: {cache_meta['last_modified']}")
            else:
                print("   ⚠ Server doesn't support caching headers")
            
        except Exception as e:
            print(f"   ✗ Download failed: {e}")
            return
        
        print()
        
        # Second download (should revalidate)
        print("2. Second download (revalidates with server)...")
        try:
            download_file(
                url,
                output_path,
                use_cache=True,
                write_metadata=False
            )
            print("   ✓ Download completed")
            
            new_size = os.path.getsize(output_path)
            if new_size == size:
                print(f"   ✓ File unchanged (server returned 304 or same content)")
            else:
                print(f"   ✓ File updated (new size: {new_size:,} bytes)")
                
        except Exception as e:
            print(f"   ✗ Download failed: {e}")
            return
        
        print()
        
        # Download with caching disabled
        print("3. Download with caching disabled (forces re-download)...")
        try:
            download_file(
                url,
                output_path,
                use_cache=False,  # Disable caching
                write_metadata=False
            )
            print("   ✓ File downloaded (cache bypassed)")
            
        except Exception as e:
            print(f"   ✗ Download failed: {e}")
            return
        
        print()
        print("=" * 60)
        print("Example completed!")
        print()
        print("Key points:")
        print("  - use_cache=True (default) enables HTTP caching")
        print("  - Cache metadata is saved in .http_cache.json files")
        print("  - Subsequent downloads send conditional headers")
        print("  - 304 Not Modified responses skip the download")
        print("  - use_cache=False forces a fresh download")


if __name__ == '__main__':
    main()
