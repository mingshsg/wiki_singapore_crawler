#!/usr/bin/env python3
"""
Test that both old and new Wikipedia document structures work as alternatives.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def test_both_structures():
    """Test both document structures work correctly."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    # Fetch HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    html_content = response.text
    
    print("🧪 Testing Both Document Structures")
    print("=" * 50)
    
    # Initialize content processor
    processor = ContentProcessor()
    
    # Test 1: Full HTML (should use newer mw-content-container structure)
    print("\n📋 Test 1: Full HTML (newer structure preferred)")
    try:
        processed_content = processor.process_content(html_content)
        print(f"✅ Success: {len(processed_content)} characters processed")
        print(f"📄 Content preview: {processed_content[:200]}...")
        
        # Check if content looks good
        if len(processed_content) > 10000 and "History of the Jews in Singapore" in processed_content:
            print("✅ Content quality: Good (contains title and substantial content)")
        else:
            print("❌ Content quality: Poor (too short or missing title)")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Simulate older structure by removing mw-content-container
    print("\n📋 Test 2: Simulated older structure (mw-content-container removed)")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove mw-content-container to simulate older structure
    content_container = soup.find('div', class_='mw-content-container')
    if content_container:
        # Extract the mw-content-text and move it up
        mw_content_text = content_container.find('div', {'id': 'mw-content-text'})
        if mw_content_text:
            # Insert mw-content-text before the container
            content_container.insert_before(mw_content_text.extract())
        # Remove the container
        content_container.decompose()
        
        # Test processing with older structure
        modified_html = str(soup)
        try:
            processed_content = processor.process_content(modified_html)
            print(f"✅ Success: {len(processed_content)} characters processed")
            print(f"📄 Content preview: {processed_content[:200]}...")
            
            # Check if content looks good
            if len(processed_content) > 10000 and "History of the Jews in Singapore" in processed_content:
                print("✅ Content quality: Good (contains title and substantial content)")
            else:
                print("❌ Content quality: Poor (too short or missing title)")
                
        except Exception as e:
            print(f"❌ Failed: {e}")
    else:
        print("❌ No mw-content-container found to remove")
    
    # Test 3: Test direct mw-parser-output extraction
    print("\n📋 Test 3: Direct mw-parser-output extraction")
    soup = BeautifulSoup(html_content, 'html.parser')
    parser_output = soup.find('div', class_='mw-parser-output')
    if parser_output:
        # Create minimal HTML with just parser output
        minimal_html = f"<html><body>{str(parser_output)}</body></html>"
        try:
            processed_content = processor.process_content(minimal_html)
            print(f"✅ Success: {len(processed_content)} characters processed")
            print(f"📄 Content preview: {processed_content[:200]}...")
            
            # Check if content looks good
            if len(processed_content) > 10000 and "History of the Jews in Singapore" in processed_content:
                print("✅ Content quality: Good (contains title and substantial content)")
            else:
                print("❌ Content quality: Poor (too short or missing title)")
                
        except Exception as e:
            print(f"❌ Failed: {e}")
    else:
        print("❌ No mw-parser-output found")
    
    # Test 4: Compare content extraction methods
    print("\n📋 Test 4: Compare extraction methods")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Method 1: mw-content-container (newer)
    content_container = soup.find('div', class_='mw-content-container')
    if content_container:
        mw_content_text = content_container.find('div', {'id': 'mw-content-text'})
        if mw_content_text:
            parser_output = mw_content_text.find('div', class_='mw-parser-output')
            if parser_output:
                method1_text = parser_output.get_text().strip()
                print(f"📊 Method 1 (newer): {len(method1_text)} characters")
    
    # Method 2: mw-content-text (traditional)
    mw_content_text = soup.find('div', {'id': 'mw-content-text'})
    if mw_content_text:
        parser_output = mw_content_text.find('div', class_='mw-parser-output')
        if parser_output:
            method2_text = parser_output.get_text().strip()
            print(f"📊 Method 2 (traditional): {len(method2_text)} characters")
    
    # Method 3: Direct mw-parser-output
    parser_output = soup.find('div', class_='mw-parser-output')
    if parser_output:
        method3_text = parser_output.get_text().strip()
        print(f"📊 Method 3 (direct): {len(method3_text)} characters")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    test_both_structures()