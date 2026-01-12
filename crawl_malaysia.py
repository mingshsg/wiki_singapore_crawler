#!/usr/bin/env python3
"""
Crawl Wikipedia Category:Malaysia and save files to Category_Malaysia folder.
"""

import json
import sys
import time
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.core.wikipedia_crawler import WikipediaCrawler
from wikipedia_crawler.utils.logging_config import setup_logging


def load_config():
    """Load configuration from config.json."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def main():
    """Main function to crawl Malaysia category."""
    print("🇲🇾 Starting Malaysia Wikipedia Crawler")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    if not config:
        print("❌ Failed to load configuration")
        return
    
    # Setup logging
    setup_logging(
        log_level=config.get('log_level', 'INFO'),
        log_file=config.get('log_file', 'crawler.log')
    )
    
    # Display configuration
    print(f"📍 Start URL: {config['start_url']}")
    print(f"📁 Output Directory: {config['output_dir']}")
    print(f"📂 Folder Name: {config['folder_organization']['category_folder_name']}")
    print(f"🔄 Max Depth: {config['max_depth']}")
    print(f"⏱️  Request Delay: {config['request_delay']}s")
    print(f"🌐 Supported Languages: {', '.join(config['supported_languages'])}")
    
    try:
        # Initialize crawler
        crawler = WikipediaCrawler(
            start_url=config['start_url'],
            output_dir=config['output_dir'],
            max_depth=config['max_depth'],
            delay_between_requests=config['request_delay'],
            max_retries=config['max_retries']
        )
        
        print(f"\n🚀 Starting crawl process...")
        print("Press Ctrl+C to stop gracefully")
        
        # Start crawling
        crawler.start_crawling()
        
        # Monitor progress
        try:
            while True:
                status = crawler.get_status()
                
                print(f"\r📊 Progress: {status.completed_urls} completed, "
                      f"{status.pending_urls} pending, "
                      f"{status.error_urls} errors", end="", flush=True)
                
                # Check if crawling is still running
                if not crawler._running:
                    break
                
                time.sleep(5)  # Update every 5 seconds
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Stopping crawler gracefully...")
            crawler.stop_crawling()
        
        # Final statistics
        print(f"\n\n📈 Final Statistics:")
        final_status = crawler.get_status()
        print(f"✅ Completed URLs: {final_status.completed_urls}")
        print(f"❌ Error URLs: {final_status.error_urls}")
        print(f"🔄 Pending URLs: {final_status.pending_urls}")
        print(f"🌐 Languages processed: {', '.join(final_status.languages_processed)}")
        
        # Get detailed stats
        detailed_stats = crawler.get_detailed_stats()
        storage_stats = crawler.file_storage.get_storage_stats()
        
        print(f"\n📁 File Storage Statistics:")
        print(f"   Total files: {storage_stats['total_files']}")
        print(f"   Category files: {storage_stats['category_files']}")
        print(f"   Article files: {storage_stats['article_files']}")
        print(f"   Total size: {storage_stats['total_size_bytes'] / (1024*1024):.1f} MB")
        print(f"   Output directory: {storage_stats['output_directory']}")
        
        print(f"\n🎉 Malaysia crawling completed!")
        
    except Exception as e:
        print(f"\n❌ Error during crawling: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()