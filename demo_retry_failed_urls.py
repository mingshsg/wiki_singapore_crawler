#!/usr/bin/env python3
"""
Demo script to show the retry functionality for failed URLs.

This script demonstrates how to use the FailedURLRetryManager to retry
specific failed URLs from the Singapore Wikipedia crawling operation.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from retry_failed_urls import FailedURLRetryManager


def demo_retry_functionality():
    """Demonstrate the retry functionality with detailed output."""
    print("🔄 Failed URL Retry Demo")
    print("=" * 50)
    
    # Initialize retry manager
    print("\n1. Initializing retry manager...")
    retry_manager = FailedURLRetryManager(
        output_dir="wiki_data",
        delay_between_requests=1.0,
        max_retries=3
    )
    
    try:
        # Load failed URLs
        print("\n2. Loading failed URLs from progress state...")
        failed_urls = retry_manager.load_failed_urls()
        
        if not failed_urls:
            print("   ✅ No failed URLs found!")
            return
        
        print(f"   Found {len(failed_urls)} failed URLs:")
        for i, url in enumerate(failed_urls, 1):
            # Extract just the page name for cleaner display
            page_name = url.split('/')[-1].replace('_', ' ')
            print(f"   {i}. {page_name}")
        
        # Show what the retry would do
        print(f"\n3. Retry process overview:")
        print(f"   - Each URL will be fetched using the same PageProcessor")
        print(f"   - Smart error handling with exponential backoff")
        print(f"   - Circuit breaker protection for connectivity issues")
        print(f"   - Content processing using existing ArticleHandler")
        print(f"   - Automatic file saving to wiki_data/ directory")
        
        # Demo single URL retry (without actually doing it)
        if failed_urls:
            demo_url = failed_urls[0]
            page_name = demo_url.split('/')[-1].replace('_', ' ')
            
            print(f"\n4. Demo: What happens when retrying '{page_name}':")
            print(f"   URL: {demo_url}")
            print(f"   Steps:")
            print(f"   1. PageProcessor.process_page() - Fetch HTML content")
            print(f"   2. ArticleHandler.process_article() - Extract and process content")
            print(f"   3. FileStorage.save_json() - Save to wiki_data/{page_name}.json")
            print(f"   4. Update statistics and logging")
        
        print(f"\n5. Error handling features:")
        print(f"   ✅ Permanent failures (404, 403) - Skip immediately")
        print(f"   ✅ Temporary failures (5xx, timeouts) - Retry with backoff")
        print(f"   ✅ Network connectivity issues - Test Google, prompt user")
        print(f"   ✅ Circuit breaker - Prevent infinite retry loops")
        print(f"   ✅ Detailed logging and statistics")
        
        print(f"\n6. Expected outcomes:")
        print(f"   - Most URLs should succeed on retry (original errors were likely temporary)")
        print(f"   - Any permanent failures will be identified and skipped")
        print(f"   - Comprehensive report will be generated")
        print(f"   - All successful files will be saved to wiki_data/")
        
        print(f"\n📋 To run the actual retry:")
        print(f"   python retry_failed_urls.py")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
    finally:
        retry_manager.close()


def show_failed_url_details():
    """Show details about the specific failed URLs."""
    print("\n" + "=" * 50)
    print("📊 Failed URL Analysis")
    print("=" * 50)
    
    # The 6 failed URLs from the validation report
    failed_urls = [
        "https://en.wikipedia.org/wiki/Energy_Studies_Institute",
        "https://en.wikipedia.org/wiki/Energy_in_Singapore", 
        "https://en.wikipedia.org/wiki/Eng_Aun_Tong_Building",
        "https://en.wikipedia.org/wiki/Eng_Wah_Global",
        "https://en.wikipedia.org/wiki/Enlistment_Act_1970",
        "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    ]
    
    print(f"Total failed URLs: {len(failed_urls)}")
    print(f"Failure rate: 0.2% (6 out of 3,097 total URLs)")
    print(f"Error type: Content processing errors")
    
    print(f"\nFailed URLs by category:")
    
    energy_urls = [url for url in failed_urls if 'Energy' in url or 'Eng_' in url]
    history_urls = [url for url in failed_urls if 'History' in url]
    legal_urls = [url for url in failed_urls if 'Enlistment' in url]
    
    if energy_urls:
        print(f"\n🔋 Energy/Engineering related ({len(energy_urls)}):")
        for url in energy_urls:
            page_name = url.split('/')[-1].replace('_', ' ')
            print(f"   • {page_name}")
    
    if history_urls:
        print(f"\n📚 History related ({len(history_urls)}):")
        for url in history_urls:
            page_name = url.split('/')[-1].replace('_', ' ')
            print(f"   • {page_name}")
    
    if legal_urls:
        print(f"\n⚖️  Legal/Government related ({len(legal_urls)}):")
        for url in legal_urls:
            page_name = url.split('/')[-1].replace('_', ' ')
            print(f"   • {page_name}")
    
    print(f"\n🔍 Likely causes of failure:")
    print(f"   • Complex page structure that caused parsing errors")
    print(f"   • Special characters or encoding issues")
    print(f"   • Large content size that exceeded processing limits")
    print(f"   • Temporary Wikipedia server issues during original crawl")
    
    print(f"\n✅ Why retry should work:")
    print(f"   • Original errors were 'content processing' not 'fetch failures'")
    print(f"   • Pages likely exist and are accessible")
    print(f"   • Improved error handling in retry script")
    print(f"   • Fresh attempt may succeed where original failed")


if __name__ == "__main__":
    demo_retry_functionality()
    show_failed_url_details()