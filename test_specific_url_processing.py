#!/usr/bin/env python3
"""
Test the specific URL that was failing to ensure it works with both structures.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor
from wikipedia_crawler.core.page_processor import PageProcessor


def test_specific_url():
    """Test the specific URL that was previously failing."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    print("🎯 Testing Specific URL Processing")
    print("=" * 50)
    print(f"URL: {url}")
    
    # Initialize processors
    page_processor = PageProcessor(delay_between_requests=1.0, max_retries=3)
    content_processor = ContentProcessor()
    
    try:
        # Fetch the page
        print("\n📡 Fetching page...")
        page_result = page_processor.process_page(url)
        
        if not page_result.success:
            print(f"❌ Failed to fetch page: {page_result.error_message}")
            return
        
        print(f"✅ Page fetched successfully")
        print(f"📄 HTML length: {len(page_result.content)} characters")
        print(f"📄 Page type: {page_result.page_type}")
        
        # Process content
        print("\n🔄 Processing content...")
        processed_content = content_processor.process_content(page_result.content)
        
        print(f"✅ Content processed successfully")
        print(f"📄 Processed length: {len(processed_content)} characters")
        print(f"📄 Content preview:")
        print("-" * 40)
        print(processed_content[:500])
        print("-" * 40)
        
        # Check content quality
        print("\n🔍 Content Quality Check:")
        
        # Check for title
        if "History of the Jews in Singapore" in processed_content:
            print("✅ Title found in content")
        else:
            print("❌ Title not found in content")
        
        # Check for substantial content
        if len(processed_content) > 10000:
            print(f"✅ Substantial content: {len(processed_content)} characters")
        else:
            print(f"❌ Content too short: {len(processed_content)} characters")
        
        # Check for key content elements
        key_elements = [
            "Baghdadi",
            "synagogue", 
            "Manasseh Meyer",
            "David Marshall",
            "Singapore"
        ]
        
        found_elements = []
        for element in key_elements:
            if element in processed_content:
                found_elements.append(element)
        
        print(f"✅ Key elements found: {len(found_elements)}/{len(key_elements)}")
        print(f"   Found: {', '.join(found_elements)}")
        
        # Get processing stats
        stats = content_processor.get_content_stats(page_result.content, processed_content)
        print(f"\n📊 Processing Statistics:")
        print(f"   Original size: {stats['original_size']} characters")
        print(f"   Processed size: {stats['processed_size']} characters")
        print(f"   Compression ratio: {stats['compression_ratio']:.2%}")
        print(f"   Has headers: {stats['has_headers']}")
        print(f"   Has lists: {stats['has_lists']}")
        print(f"   Has links: {stats['has_links']}")
        
        print(f"\n✅ URL processing test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_specific_url()