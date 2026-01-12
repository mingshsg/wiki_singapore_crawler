#!/usr/bin/env python3
"""
Debug what the link[rel] elements actually are.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


def debug_link_elements():
    """Debug what the link[rel] elements are."""
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
    
    print("🔍 Debugging link[rel] Elements")
    print("=" * 50)
    
    # Parse the article HTML
    soup = BeautifulSoup(article_html, 'html.parser')
    
    # Find all link[rel] elements
    link_rel_elements = soup.select('link[rel]')
    print(f"📄 Found {len(link_rel_elements)} link[rel] elements:")
    
    for i, elem in enumerate(link_rel_elements):
        print(f"\n   Element {i+1}:")
        print(f"     Tag: {elem.name}")
        print(f"     Attributes: {dict(elem.attrs)}")
        print(f"     Text length: {len(elem.get_text().strip())}")
        
        if hasattr(elem, 'get_text'):
            text_content = elem.get_text().strip()
            if text_content:
                print(f"     Text preview: {text_content[:200]}...")
        
        # Check if this element contains a lot of content
        if len(elem.get_text().strip()) > 1000:
            print(f"     ❌ THIS ELEMENT CONTAINS SIGNIFICANT CONTENT!")
            
            # Show its structure
            print(f"     Children: {len(list(elem.children))}")
            child_tags = [child.name for child in elem.children if hasattr(child, 'name')]
            print(f"     Child tags: {child_tags[:10]}")
    
    # Also check link[href] elements
    link_href_elements = soup.select('link[href]')
    print(f"\n📄 Found {len(link_href_elements)} link[href] elements:")
    
    for i, elem in enumerate(link_href_elements[:5]):  # Show first 5
        print(f"\n   Element {i+1}:")
        print(f"     Tag: {elem.name}")
        print(f"     Attributes: {dict(elem.attrs)}")
        print(f"     Text length: {len(elem.get_text().strip())}")
        
        if len(elem.get_text().strip()) > 100:
            text_preview = elem.get_text().strip()[:200]
            print(f"     Text preview: {text_preview}...")


if __name__ == "__main__":
    debug_link_elements()