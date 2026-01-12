#!/usr/bin/env python3
"""
Test the fixed URL processing.
"""

import sys
import requests
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.article_handler import ArticlePageHandler
from wikipedia_crawler.processors.language_filter import LanguageFilter
from wikipedia_crawler.core.file_storage import FileStorage


def test_fixed_url():
    """Test the fixed URL processing."""
    url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    print(f"🧪 Testing fixed URL processing: {url}")
    print("=" * 60)
    
    # Fetch content first
    print("📥 Fetching HTML content...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
        print(f"✅ Fetched {len(html_content)} characters of HTML")
        
        # Initialize components
        file_storage = FileStorage("test_output")
        article_handler = ArticlePageHandler(file_storage)
        
        # Process the article
        print("📥 Processing article...")
        result = article_handler.process_article(url, html_content)
        
        if result.success:
            print(f"✅ Article processing succeeded!")
            print(f"📄 URL: {result.url}")
            print(f"📄 Page type: {result.page_type}")
            if result.content:
                print(f"📏 Content length: {len(result.content)} characters")
                print(f"📝 Content preview: {result.content[:200]}...")
            if result.data:
                print(f"📊 Data keys: {list(result.data.keys())}")
                if 'content_length' in result.data:
                    print(f"📏 Processed content length: {result.data['content_length']} characters")
                if 'title' in result.data:
                    print(f"📄 Title: {result.data['title']}")
                if 'language' in result.data:
                    print(f"🌐 Language: {result.data['language']}")
                if 'filtered' in result.data:
                    print(f"🔍 Filtered: {result.data['filtered']}")
            
        else:
            print(f"❌ Article processing failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_fixed_url()