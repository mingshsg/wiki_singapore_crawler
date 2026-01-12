#!/usr/bin/env python3
"""
Debug script to understand why content processing is failing for the specific URL.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def debug_content_processing():
    """Debug the content processing step by step."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    print(f"🔍 Debugging content processing for: {url}")
    print("=" * 80)
    
    # Fetch HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    html_content = response.text
    
    print(f"📥 Fetched HTML: {len(html_content)} characters")
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    print(f"🏗️  Parsed HTML: {len(soup.find_all())} elements")
    
    # Find main content
    main_content = soup.find('div', {'id': 'mw-content-text'})
    if main_content:
        parser_output = main_content.find('div', class_='mw-parser-output')
        if parser_output:
            content_soup = parser_output
        else:
            content_soup = main_content
    else:
        content_soup = soup
    
    print(f"📄 Main content area: {len(content_soup.find_all())} elements")
    print(f"📄 Main content text: {len(content_soup.get_text().strip())} characters")
    
    # Show first few paragraphs before processing
    paragraphs = content_soup.find_all('p')
    print(f"\n📝 Found {len(paragraphs)} paragraphs before processing:")
    for i, p in enumerate(paragraphs[:3]):
        text = p.get_text().strip()
        if text:
            print(f"   P{i+1}: {text[:100]}...")
    
    # Now let's debug the content processor step by step
    processor = ContentProcessor()
    
    # Step 1: Remove unwanted elements
    print(f"\n⚙️  STEP 1: Remove unwanted elements")
    print(f"   Before: {len(content_soup.find_all())} elements")
    
    # Make a copy for processing
    processing_soup = BeautifulSoup(str(content_soup), 'html.parser')
    processor._remove_unwanted_elements(processing_soup)
    
    print(f"   After: {len(processing_soup.find_all())} elements")
    print(f"   Remaining text: {len(processing_soup.get_text().strip())} characters")
    
    # Show what elements remain
    remaining_elements = processing_soup.find_all()
    print(f"   Remaining elements: {[elem.name for elem in remaining_elements[:10]]}")
    
    # Show remaining text
    remaining_text = processing_soup.get_text().strip()
    if remaining_text:
        print(f"   Remaining text preview: {remaining_text[:200]}...")
    else:
        print(f"   ❌ NO TEXT REMAINING!")
    
    # Let's check what specific elements are being removed
    print(f"\n🔍 Analyzing what gets removed:")
    
    # Check for headings that trigger section removal
    original_soup = BeautifulSoup(str(content_soup), 'html.parser')
    headings = original_soup.find_all(['h2', 'h3', 'h4'])
    
    problematic_headings = []
    for heading in headings:
        heading_text = heading.get_text().strip().lower()
        if heading_text in ['see also', 'references', 'external links', 'further reading']:
            problematic_headings.append((heading.name, heading_text))
    
    print(f"   Found {len(problematic_headings)} problematic headings: {problematic_headings}")
    
    # Let's see the structure of headings
    print(f"\n📋 All headings in the page:")
    for i, heading in enumerate(headings):
        heading_text = heading.get_text().strip()
        print(f"   {heading.name}: {heading_text}")
        if i >= 10:  # Limit output
            print(f"   ... and {len(headings) - 10} more")
            break


if __name__ == "__main__":
    debug_content_processing()