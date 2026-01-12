#!/usr/bin/env python3
"""
Debug the ContentProcessor directly with the extracted HTML.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def debug_content_processor_direct():
    """Debug the ContentProcessor directly."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    # Fetch HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    html_content = response.text
    
    # Extract the same content that ArticlePageHandler would extract
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Use the same extraction logic as ArticlePageHandler
    content_div = soup.find('div', {'id': 'mw-content-text'})
    if content_div:
        parser_output = content_div.find('div', class_='mw-parser-output')
        if parser_output:
            article_html = str(parser_output)
        else:
            article_html = str(content_div)
    else:
        article_html = ""
    
    print("🔍 Testing ContentProcessor Directly")
    print("=" * 50)
    print(f"📄 Extracted HTML length: {len(article_html)}")
    
    if article_html:
        # Test text content
        test_soup = BeautifulSoup(article_html, 'html.parser')
        text_content = test_soup.get_text().strip()
        print(f"📄 Extracted text length: {len(text_content)}")
        print(f"📄 Text preview: {text_content[:200]}...")
        
        # Now test the ContentProcessor
        processor = ContentProcessor()
        
        print(f"\n⚙️  Testing ContentProcessor.process_content()...")
        try:
            processed_content = processor.process_content(article_html)
            print(f"✅ Processing succeeded!")
            print(f"📏 Processed content length: {len(processed_content)}")
            
            if processed_content:
                print(f"📝 Processed content preview: {processed_content[:300]}...")
            else:
                print(f"❌ Processed content is empty!")
                
                # Let's debug step by step
                print(f"\n🔍 Debugging step by step...")
                
                # Step 1: Parse HTML
                soup = BeautifulSoup(article_html, 'html.parser')
                print(f"   Step 1 - Parse HTML: {len(soup.find_all())} elements")
                
                # Step 2: Remove unwanted elements
                processor._remove_unwanted_elements(soup)
                print(f"   Step 2 - Remove unwanted: {len(soup.find_all())} elements remaining")
                remaining_text = soup.get_text().strip()
                print(f"   Step 2 - Text remaining: {len(remaining_text)} characters")
                
                if len(remaining_text) == 0:
                    print(f"   ❌ All text removed in step 2!")
                    
                    # Let's see what elements remain
                    remaining_elements = soup.find_all()
                    print(f"   Remaining elements: {[(elem.name, len(elem.get_text().strip())) for elem in remaining_elements[:10]]}")
                else:
                    print(f"   Text preview: {remaining_text[:200]}...")
                
        except Exception as e:
            print(f"❌ Processing failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ No article HTML extracted!")


if __name__ == "__main__":
    debug_content_processor_direct()