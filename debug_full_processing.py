#!/usr/bin/env python3
"""
Debug the full content processing pipeline step by step.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def debug_full_processing():
    """Debug each step of the content processing pipeline."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    # Fetch HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    html_content = response.text
    
    print("🔍 Full Content Processing Pipeline Debug")
    print("=" * 60)
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    print(f"📥 Original HTML: {len(html_content)} chars, {len(soup.find_all())} elements")
    
    # Get main content area (same as ContentProcessor does)
    main_content = soup.find('div', {'id': 'mw-content-text'})
    if not main_content:
        main_content = soup.find('div', class_='mw-parser-output')
    if not main_content:
        main_content = soup.find('div', {'id': 'bodyContent'})
    if not main_content:
        main_content = soup.find('body') or soup
    
    print(f"📄 Main content area: {len(main_content.find_all())} elements, {len(main_content.get_text().strip())} text chars")
    
    # Now let's manually step through the ContentProcessor logic
    processor = ContentProcessor()
    
    # Step 1: Parse HTML (already done)
    processing_soup = BeautifulSoup(str(main_content), 'html.parser')
    print(f"\n⚙️  STEP 1: Parse HTML")
    print(f"   Elements: {len(processing_soup.find_all())}")
    print(f"   Text chars: {len(processing_soup.get_text().strip())}")
    
    # Step 2: Remove unwanted elements
    print(f"\n⚙️  STEP 2: Remove unwanted elements")
    print(f"   Before: {len(processing_soup.find_all())} elements")
    
    # Let's break down _remove_unwanted_elements into its parts
    
    # 2a: Remove comments
    from bs4 import Comment
    comments_removed = 0
    for comment in processing_soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        comments_removed += 1
    print(f"   2a. Removed {comments_removed} comments")
    print(f"       After comments: {len(processing_soup.find_all())} elements")
    
    # 2b: Remove elements by selector
    selectors_removed = {}
    for selector in processor.remove_elements:
        elements = processing_soup.select(selector)
        selectors_removed[selector] = len(elements)
        for element in elements:
            element.decompose()
    
    print(f"   2b. Removed elements by selector:")
    for selector, count in selectors_removed.items():
        if count > 0:
            print(f"       {selector}: {count} elements")
    print(f"       After selectors: {len(processing_soup.find_all())} elements")
    
    # 2c: Remove Wikipedia-specific elements
    print(f"   2c. Remove Wikipedia-specific elements...")
    
    # Infoboxes
    infoboxes = processing_soup.find_all('table', class_=lambda x: x and 'infobox' in x)
    for infobox in infoboxes:
        infobox.decompose()
    print(f"       Removed {len(infoboxes)} infoboxes")
    
    # Navigation boxes
    navboxes = processing_soup.find_all('div', class_=lambda x: x and 'navbox' in x)
    for navbox in navboxes:
        navbox.decompose()
    print(f"       Removed {len(navboxes)} navboxes")
    
    # Reference sections
    ref_sections = processing_soup.find_all(['div', 'section'], class_=lambda x: x and 'reflist' in x)
    for ref_section in ref_sections:
        ref_section.decompose()
    print(f"       Removed {len(ref_sections)} reference sections")
    
    print(f"       After Wikipedia-specific: {len(processing_soup.find_all())} elements")
    
    # The problematic section removal
    print(f"   2d. Remove problematic sections...")
    sections_removed = 0
    for heading in processing_soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        if heading_text in ['see also', 'references', 'external links', 'further reading']:
            print(f"       Found: {heading.name} '{heading_text}'")
            
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
            
            print(f"       Will remove {len(elements_to_remove)} elements after this heading")
            
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
    
    print(f"       Removed {sections_removed} problematic sections")
    print(f"       After section removal: {len(processing_soup.find_all())} elements")
    
    # Images and media
    images = processing_soup.find_all(['img', 'figure', 'audio', 'video'])
    for img in images:
        img.decompose()
    print(f"       Removed {len(images)} images/media")
    
    # File links
    file_links = []
    for link in processing_soup.find_all('a', href=True):
        href = link.get('href', '')
        if any(prefix in href.lower() for prefix in ['/wiki/file:', '/wiki/image:', '/wiki/media:']):
            file_links.append(link)
            link.decompose()
    print(f"       Removed {len(file_links)} file links")
    
    print(f"   Final after step 2: {len(processing_soup.find_all())} elements")
    print(f"   Text remaining: {len(processing_soup.get_text().strip())} characters")
    
    remaining_text = processing_soup.get_text().strip()
    if remaining_text:
        print(f"   Preview: {remaining_text[:200]}...")
    else:
        print(f"   ❌ NO TEXT REMAINING!")
        
        # Let's see what elements are left
        remaining_elements = processing_soup.find_all()
        print(f"   Remaining elements: {[(elem.name, elem.get_text().strip()[:50] if hasattr(elem, 'get_text') else 'N/A') for elem in remaining_elements]}")


if __name__ == "__main__":
    debug_full_processing()