#!/usr/bin/env python3
"""
Debug the section removal logic specifically.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


def debug_section_removal():
    """Debug the section removal logic."""
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
    
    print("🔍 Debugging section removal logic")
    print("=" * 50)
    
    # Show the structure before removal
    all_elements = list(parser_output.children)
    print(f"📋 Total elements in parser output: {len(all_elements)}")
    
    # Find all headings
    headings = parser_output.find_all(['h2', 'h3', 'h4'])
    print(f"📋 Found {len(headings)} headings:")
    
    for i, heading in enumerate(headings):
        heading_text = heading.get_text().strip()
        print(f"   {i+1}. {heading.name}: '{heading_text}'")
    
    print("\n🔍 Simulating the problematic section removal...")
    
    # Simulate the current logic
    test_soup = BeautifulSoup(str(parser_output), 'html.parser')
    
    for heading in test_soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        if heading_text in ['see also', 'references', 'external links', 'further reading']:
            print(f"\n❌ Found problematic heading: {heading.name} '{heading_text}'")
            
            # Show what the current logic would do
            elements_to_remove = []
            current = heading
            
            while current and current.next_sibling:
                next_elem = current.next_sibling
                
                # Check if it's a heading of same or higher level
                if (hasattr(next_elem, 'name') and next_elem.name in ['h1', 'h2', 'h3', 'h4'] and 
                    int(next_elem.name[1:]) <= int(heading.name[1:])):
                    print(f"   ✅ Would stop at: {next_elem.name} '{next_elem.get_text().strip()}'")
                    break
                
                if hasattr(next_elem, 'decompose'):
                    elements_to_remove.append(f"{next_elem.name}: {next_elem.get_text().strip()[:50] if hasattr(next_elem, 'get_text') else 'N/A'}")
                
                current = next_elem
            
            print(f"   📝 Would remove {len(elements_to_remove)} elements:")
            for elem_desc in elements_to_remove[:5]:  # Show first 5
                print(f"      - {elem_desc}")
            if len(elements_to_remove) > 5:
                print(f"      ... and {len(elements_to_remove) - 5} more")
    
    print(f"\n🔍 Let's see what happens if we DON'T remove these sections...")
    
    # Test without removing these sections
    clean_soup = BeautifulSoup(str(parser_output), 'html.parser')
    
    # Remove only the specific unwanted elements, not entire sections
    for selector in ['script', 'style', 'noscript', 'meta', 'link', 'head',
                    'nav', 'header', 'footer', 'aside']:
        for element in clean_soup.find_all(selector):
            element.decompose()
    
    # Remove infoboxes and navboxes
    for infobox in clean_soup.find_all('table', class_=lambda x: x and 'infobox' in x):
        infobox.decompose()
    
    for navbox in clean_soup.find_all('div', class_=lambda x: x and 'navbox' in x):
        navbox.decompose()
    
    remaining_text = clean_soup.get_text().strip()
    print(f"📏 Text remaining without section removal: {len(remaining_text)} characters")
    
    if remaining_text:
        print(f"📝 Preview: {remaining_text[:300]}...")
    
    # Now let's see what the current logic produces
    print(f"\n🔍 Current logic result:")
    current_logic_soup = BeautifulSoup(str(parser_output), 'html.parser')
    
    # Apply the current problematic logic
    for heading in current_logic_soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        if heading_text in ['see also', 'references', 'external links', 'further reading']:
            # Remove the heading and everything until the next heading of same or higher level
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
    
    current_logic_text = current_logic_soup.get_text().strip()
    print(f"📏 Text remaining with current logic: {len(current_logic_text)} characters")
    
    if current_logic_text:
        print(f"📝 Preview: {current_logic_text[:300]}...")
    else:
        print("❌ NO TEXT REMAINING with current logic!")


if __name__ == "__main__":
    debug_section_removal()