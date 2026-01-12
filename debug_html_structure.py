#!/usr/bin/env python3
"""
Debug the HTML structure to find where the content actually is.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


def debug_html_structure():
    """Debug the HTML structure to find content containers."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    # Fetch HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    html_content = response.text
    
    print("🔍 Debugging HTML Structure")
    print("=" * 50)
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Check various content containers
    containers_to_check = [
        ('div#mw-content-text', 'mw-content-text ID'),
        ('div.mw-content-container', 'mw-content-container class'),
        ('div.mw-parser-output', 'mw-parser-output class'),
        ('div#bodyContent', 'bodyContent ID'),
        ('main', 'main tag'),
        ('article', 'article tag'),
    ]
    
    print(f"📄 Total HTML length: {len(html_content)} characters")
    print(f"📄 Total elements: {len(soup.find_all())}")
    
    for selector, description in containers_to_check:
        elements = soup.select(selector)
        print(f"\n🎯 {description} ('{selector}'):")
        print(f"   Found: {len(elements)} elements")
        
        for i, element in enumerate(elements):
            if element:
                text_content = element.get_text().strip()
                print(f"   Element {i+1}:")
                print(f"     HTML length: {len(str(element))}")
                print(f"     Text length: {len(text_content)}")
                print(f"     Text preview: {text_content[:100]}...")
                
                # Check for nested mw-parser-output
                parser_output = element.find('div', class_='mw-parser-output')
                if parser_output:
                    parser_text = parser_output.get_text().strip()
                    print(f"     Contains mw-parser-output: {len(str(parser_output))} HTML, {len(parser_text)} text")
                    print(f"     Parser output preview: {parser_text[:100]}...")
    
    # Let's also check what the current ArticlePageHandler logic would find
    print(f"\n🔍 Testing ArticlePageHandler extraction logic:")
    
    # Method 1: Look for the main content div
    content_div = soup.find('div', {'id': 'mw-content-text'})
    if content_div:
        print(f"✅ Found mw-content-text div")
        # Look for the parser output within the content
        parser_output = content_div.find('div', class_='mw-parser-output')
        if parser_output:
            print(f"✅ Found mw-parser-output within mw-content-text")
            text_content = parser_output.get_text().strip()
            print(f"   HTML length: {len(str(parser_output))}")
            print(f"   Text length: {len(text_content)}")
            print(f"   Text preview: {text_content[:200]}...")
        else:
            print(f"❌ No mw-parser-output found within mw-content-text")
            text_content = content_div.get_text().strip()
            print(f"   Using mw-content-text directly:")
            print(f"   HTML length: {len(str(content_div))}")
            print(f"   Text length: {len(text_content)}")
            print(f"   Text preview: {text_content[:200]}...")
    else:
        print(f"❌ No mw-content-text div found")
    
    # Check if mw-content-container exists and what it contains
    content_container = soup.find('div', class_='mw-content-container')
    if content_container:
        print(f"\n✅ Found mw-content-container!")
        text_content = content_container.get_text().strip()
        print(f"   HTML length: {len(str(content_container))}")
        print(f"   Text length: {len(text_content)}")
        print(f"   Text preview: {text_content[:200]}...")
        
        # Check what's inside
        mw_content_text = content_container.find('div', {'id': 'mw-content-text'})
        if mw_content_text:
            print(f"   Contains mw-content-text: YES")
            parser_output = mw_content_text.find('div', class_='mw-parser-output')
            if parser_output:
                print(f"   Contains mw-parser-output: YES")
                parser_text = parser_output.get_text().strip()
                print(f"   Parser output text length: {len(parser_text)}")
        else:
            print(f"   Contains mw-content-text: NO")


if __name__ == "__main__":
    debug_html_structure()