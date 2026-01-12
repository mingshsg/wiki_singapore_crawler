#!/usr/bin/env python3
"""
Debug the priority issue to understand why newer structure is not preferred.
"""

import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def debug_priority():
    """Debug the extraction priority issue."""
    
    # Create HTML with both structures present
    html_with_both = """
    <html>
    <body>
        <div class="mw-content-container">
            <div id="mw-content-text">
                <div class="mw-parser-output">
                    <h1>Newer Structure Content</h1>
                    <p>This content should be preferred because it's in the newer mw-content-container structure.</p>
                </div>
            </div>
        </div>
        <div id="mw-content-text">
            <div class="mw-parser-output">
                <h1>Older Structure Content</h1>
                <p>This content should NOT be used when newer structure is available.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    print("🔍 Debugging Priority Issue")
    print("=" * 40)
    
    soup = BeautifulSoup(html_with_both, 'html.parser')
    
    # Test the extraction logic step by step
    print("Step 1: Check for mw-content-container")
    content_container = soup.find('div', class_='mw-content-container')
    if content_container:
        print("✅ Found mw-content-container")
        print(f"   Content preview: {content_container.get_text()[:100]}...")
        
        # Check for mw-content-text within container
        mw_content_text = content_container.find('div', {'id': 'mw-content-text'})
        if mw_content_text:
            print("✅ Found mw-content-text within container")
            
            # Check for mw-parser-output within it
            parser_output = mw_content_text.find('div', class_='mw-parser-output')
            if parser_output:
                print("✅ Found mw-parser-output within mw-content-text")
                print(f"   Parser output content: {parser_output.get_text()[:100]}...")
                
                # This should be returned
                print("🎯 This should be the selected content (newer structure)")
            else:
                print("❌ No mw-parser-output found")
        else:
            print("❌ No mw-content-text found within container")
    else:
        print("❌ No mw-content-container found")
    
    print("\nStep 2: Check traditional mw-content-text elements")
    all_mw_content_text = soup.find_all('div', {'id': 'mw-content-text'})
    print(f"Found {len(all_mw_content_text)} mw-content-text elements")
    
    for i, mw_content_text in enumerate(all_mw_content_text):
        print(f"\nElement {i+1}:")
        print(f"   Content preview: {mw_content_text.get_text()[:100]}...")
        
        # Check if inside container
        parent_container = mw_content_text.find_parent('div', class_='mw-content-container')
        if parent_container:
            print("   ⚠️  Inside mw-content-container (should be skipped)")
        else:
            print("   ✅ NOT inside mw-content-container (could be used)")
            
            parser_output = mw_content_text.find('div', class_='mw-parser-output')
            if parser_output:
                print(f"   Contains parser output: {parser_output.get_text()[:100]}...")
    
    # Test the actual processor
    print("\nStep 3: Test actual ContentProcessor")
    processor = ContentProcessor()
    
    # Manually test the _extract_main_content method
    extracted = processor._extract_main_content(soup)
    print(f"Extracted content preview: {extracted.get_text()[:100]}...")
    
    if "Newer Structure Content" in extracted.get_text():
        print("✅ Correctly extracted newer structure content")
    elif "Older Structure Content" in extracted.get_text():
        print("❌ Incorrectly extracted older structure content")
    else:
        print("❌ Extracted unexpected content")
    
    # Test full processing
    print("\nStep 4: Test full processing")
    processed = processor.process_content(html_with_both)
    print(f"Processed content preview: {processed[:100]}...")
    
    if "Newer Structure Content" in processed:
        print("✅ Full processing correctly used newer structure")
        return True
    elif "Older Structure Content" in processed:
        print("❌ Full processing incorrectly used older structure")
        return False
    else:
        print("❌ Full processing produced unexpected content")
        return False


if __name__ == "__main__":
    debug_priority()