#!/usr/bin/env python3
"""
Debug the _remove_unwanted_elements step specifically.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup, Comment

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def debug_remove_elements_step():
    """Debug the _remove_unwanted_elements step."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    # Fetch and extract HTML (same as ArticlePageHandler)
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    html_content = response.text
    
    soup = BeautifulSoup(html_content, 'html.parser')
    content_div = soup.find('div', {'id': 'mw-content-text'})
    parser_output = content_div.find('div', class_='mw-parser-output')
    article_html = str(parser_output)
    
    print("🔍 Debugging _remove_unwanted_elements Step")
    print("=" * 60)
    
    # Parse the article HTML
    soup = BeautifulSoup(article_html, 'html.parser')
    print(f"📄 Starting with: {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    processor = ContentProcessor()
    
    # Step 2a: Remove comments
    comments_removed = 0
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        comments_removed += 1
    print(f"   2a. Removed {comments_removed} comments")
    print(f"       After: {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    # Step 2b: Remove elements by selector (test each one individually)
    print(f"   2b. Testing each selector individually:")
    
    for selector in processor.remove_elements:
        # Make a copy to test this selector
        test_soup = BeautifulSoup(str(soup), 'html.parser')
        elements_found = test_soup.select(selector)
        
        if elements_found:
            print(f"       '{selector}': {len(elements_found)} elements")
            
            # Remove them and see the impact
            for elem in elements_found:
                elem.decompose()
            
            remaining_text = len(test_soup.get_text().strip())
            print(f"         After removal: {len(test_soup.find_all())} elements, {remaining_text} text chars")
            
            if remaining_text == 0:
                print(f"         ❌ THIS SELECTOR REMOVES ALL TEXT!")
                
                # Show what was removed
                original_soup = BeautifulSoup(str(soup), 'html.parser')
                matched = original_soup.select(selector)
                for i, elem in enumerate(matched[:3]):
                    elem_text = elem.get_text().strip()
                    print(f"           Element {i+1}: {elem.name}, {len(elem_text)} chars")
                    if len(elem_text) > 0:
                        print(f"             Text: {elem_text[:100]}...")
                
                break  # Stop here since we found the culprit
    
    # Step 2c: Test the new link tag selectors
    print(f"   2c. Testing link tag selectors:")
    for selector in processor.remove_link_tags:
        test_soup = BeautifulSoup(str(soup), 'html.parser')
        elements_found = test_soup.select(selector)
        print(f"       '{selector}': {len(elements_found)} elements")


if __name__ == "__main__":
    debug_remove_elements_step()