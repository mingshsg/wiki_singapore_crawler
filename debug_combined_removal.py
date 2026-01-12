#!/usr/bin/env python3
"""
Debug the combined removal process.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup, Comment

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def debug_combined_removal():
    """Debug the combined removal process."""
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
    
    print("🔍 Debugging Combined Removal Process")
    print("=" * 60)
    
    # Parse the article HTML
    soup = BeautifulSoup(article_html, 'html.parser')
    print(f"📄 Starting: {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    processor = ContentProcessor()
    
    # Step 1: Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    print(f"   After comments: {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    # Step 2: Apply all selectors
    total_removed = 0
    for selector in processor.remove_elements:
        elements = soup.select(selector)
        if elements:
            print(f"   Removing {len(elements)} elements with '{selector}'")
            for element in elements:
                element.decompose()
            total_removed += len(elements)
    
    print(f"   After all selectors ({total_removed} removed): {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    # Step 3: Remove HTML link tags
    total_link_removed = 0
    for selector in processor.remove_link_tags:
        elements = soup.select(selector)
        if elements:
            print(f"   Removing {len(elements)} link elements with '{selector}'")
            for element in elements:
                element.decompose()
            total_link_removed += len(elements)
    
    print(f"   After link tags ({total_link_removed} removed): {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    # Step 4: Test _remove_wikipedia_specific_elements
    print(f"   Testing _remove_wikipedia_specific_elements...")
    
    # 4a: Infoboxes
    infoboxes = soup.find_all('table', class_=lambda x: x and 'infobox' in x)
    print(f"     Infoboxes to remove: {len(infoboxes)}")
    for infobox in infoboxes:
        infobox.decompose()
    
    # 4b: Navigation boxes
    navboxes = soup.find_all('div', class_=lambda x: x and 'navbox' in x)
    print(f"     Navboxes to remove: {len(navboxes)}")
    for navbox in navboxes:
        navbox.decompose()
    
    # 4c: Reference sections
    ref_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'reflist' in x)
    print(f"     Reference sections to remove: {len(ref_sections)}")
    for ref_section in ref_sections:
        ref_section.decompose()
    
    print(f"   After Wikipedia-specific: {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    # 4d: The problematic section removal
    print(f"   Testing problematic section removal...")
    sections_removed = 0
    headings_found = []
    
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        if heading_text in ['see also', 'references', 'external links', 'further reading']:
            headings_found.append((heading.name, heading_text))
            
            # Count what will be removed
            elements_to_remove = []
            current = heading
            while current and current.next_sibling:
                next_elem = current.next_sibling
                if (hasattr(next_elem, 'name') and next_elem.name in ['h1', 'h2', 'h3', 'h4'] and 
                    int(next_elem.name[1:]) <= int(heading.name[1:])):
                    break
                if hasattr(next_elem, 'decompose'):
                    elements_to_remove.append(next_elem)
                current = next_elem
            
            print(f"     Found {heading.name} '{heading_text}', will remove {len(elements_to_remove)} elements")
            
            # Actually remove them
            current = heading
            while current and current.next_sibling:
                next_elem = current.next_sibling
                if (hasattr(next_elem, 'name') and next_elem.name in ['h1', 'h2', 'h3', 'h4'] and 
                    int(next_elem.name[1:]) <= int(heading.name[1:])):
                    break
                if hasattr(next_elem, 'decompose'):
                    next_elem.decompose()
                else:
                    current = next_elem
            heading.decompose()
            sections_removed += 1
    
    print(f"   After section removal ({sections_removed} sections): {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    # 4e: Images and media
    images = soup.find_all(['img', 'figure', 'audio', 'video'])
    print(f"     Images/media to remove: {len(images)}")
    for img in images:
        img.decompose()
    
    # 4f: File links
    file_links = []
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if any(prefix in href.lower() for prefix in ['/wiki/file:', '/wiki/image:', '/wiki/media:']):
            file_links.append(link)
            link.decompose()
    print(f"     File links to remove: {len(file_links)}")
    
    print(f"   Final result: {len(soup.find_all())} elements, {len(soup.get_text().strip())} text chars")
    
    # Show what's left
    remaining_elements = soup.find_all()
    print(f"   Remaining elements:")
    for elem in remaining_elements:
        elem_text = elem.get_text().strip()
        print(f"     {elem.name}: {len(elem_text)} chars - '{elem_text[:50]}...'")


if __name__ == "__main__":
    debug_combined_removal()