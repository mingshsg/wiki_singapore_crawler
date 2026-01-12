#!/usr/bin/env python3
"""
Debug which specific CSS selectors are removing all the content.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def debug_selectors():
    """Debug which selectors are removing content."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    # Fetch HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    html_content = response.text
    
    # Parse and get main content
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content = soup.find('div', {'id': 'mw-content-text'})
    parser_output = main_content.find('div', class_='mw-parser-output')
    
    print("🔍 Debugging CSS Selectors")
    print("=" * 40)
    
    processor = ContentProcessor()
    
    print(f"📄 Starting with: {len(parser_output.find_all())} elements")
    print(f"📄 Starting text: {len(parser_output.get_text().strip())} characters")
    
    # Test each selector individually
    for selector in processor.remove_elements:
        test_soup = BeautifulSoup(str(parser_output), 'html.parser')
        
        elements_found = test_soup.select(selector)
        if elements_found:
            print(f"\n🎯 Selector: '{selector}'")
            print(f"   Found {len(elements_found)} elements:")
            
            for i, elem in enumerate(elements_found[:3]):  # Show first 3
                elem_text = elem.get_text().strip()[:100] if hasattr(elem, 'get_text') else 'N/A'
                print(f"   {i+1}. {elem.name}: {elem_text}...")
            
            if len(elements_found) > 3:
                print(f"   ... and {len(elements_found) - 3} more")
            
            # Remove these elements and see what's left
            for elem in elements_found:
                elem.decompose()
            
            remaining_elements = len(test_soup.find_all())
            remaining_text = len(test_soup.get_text().strip())
            
            print(f"   After removal: {remaining_elements} elements, {remaining_text} text chars")
            
            if remaining_text == 0:
                print(f"   ❌ THIS SELECTOR REMOVES ALL TEXT!")
                
                # Let's see what this selector is actually matching
                original_soup = BeautifulSoup(str(parser_output), 'html.parser')
                matched_elements = original_soup.select(selector)
                
                print(f"   🔍 Detailed analysis of matched elements:")
                for i, elem in enumerate(matched_elements):
                    print(f"      Element {i+1}: {elem.name}")
                    print(f"      Classes: {elem.get('class', [])}")
                    print(f"      ID: {elem.get('id', 'None')}")
                    print(f"      Text length: {len(elem.get_text().strip()) if hasattr(elem, 'get_text') else 0}")
                    print(f"      Children: {len(list(elem.children)) if hasattr(elem, 'children') else 0}")
                    if hasattr(elem, 'get_text'):
                        text_preview = elem.get_text().strip()[:200]
                        print(f"      Text preview: {text_preview}...")
                    print()
                
                break  # Stop here since we found the culprit


if __name__ == "__main__":
    debug_selectors()