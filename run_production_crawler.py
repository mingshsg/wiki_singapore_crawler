#!/usr/bin/env python3
"""Production script to run the Wikipedia Singapore Crawler with improved error handling."""

import argparse
import os
import signal
import sys
import time
from pathlib import Path

from wikipedia_crawler.core.wikipedia_crawler import WikipediaCrawler
from wikipedia_crawler.utils.logging_config import setup_logging
import logging


def print_status(crawler: WikipediaCrawler, show_details: bool = False) -> None:
    """Print current crawler status."""
    status = crawler.get_status()
    print(f"\n=== Crawler Status ===")
    print(f"Running: {status.is_running}")
    print(f"Total processed: {status.total_processed}")
    print(f"Pending URLs: {status.pending_urls}")
    print(f"Categories processed: {status.categories_processed}")
    print(f"Articles processed: {status.articles_processed}")
    print(f"Filtered count: {status.filtered_count}")
    print(f"Error count: {status.error_count}")
    if status.start_time:
        print(f"Started: {status.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if status.last_activity:
        print(f"Last activity: {status.last_activity.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if show_details:
        stats = crawler.get_detailed_stats()
        page_stats = stats.get('page_processor', {})
        print(f"\n=== HTTP Request Stats ===")
        print(f"Total requests: {page_stats.get('requests_made', 0)}")
        print(f"Successful: {page_stats.get('successful_requests', 0)}")
        print(f"Failed: {page_stats.get('failed_requests', 0)}")
        print(f"Retries attempted: {page_stats.get('retries_attempted', 0)}")
        
        # Show error breakdown
        print(f"\n=== Error Breakdown ===")
        print(f"Permanent failures (404/403): {page_stats.get('permanent_failures', 0)}")
        print(f"Client errors (4xx): {page_stats.get('client_errors', 0)}")
        print(f"Connection errors: {page_stats.get('connection_errors', 0)}")
        print(f"Timeout errors: {page_stats.get('timeout_errors', 0)}")
        print(f"Redirect errors: {page_stats.get('redirect_errors', 0)}")
        print(f"Other errors: {page_stats.get('other_errors', 0)}")
        print(f"Total failures: {page_stats.get('total_failures', 0)}")
    
    print("=" * 22)


def main():
    """Main entry point for the production crawler."""
    parser = argparse.ArgumentParser(
        description="Wikipedia Singapore Crawler - Production Version with Smart Error Handling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic crawl with monitoring
  python run_production_crawler.py --monitor
  
  # Crawl with custom settings
  python run_production_crawler.py --max-depth 3 --delay 2.0 --output-dir ./singapore_data
  
  # Resume previous crawl
  python run_production_crawler.py --output-dir ./singapore_data
  
  # Crawl specific category
  python run_production_crawler.py --start-url "https://en.wikipedia.org/wiki/Category:Singapore_history"

Error Handling Features:
  ✅ 404/403 errors: Give up immediately (no retries)
  ✅ 5xx/timeout/connection errors: Retry with exponential backoff
  ✅ Detailed error statistics and categorization
  ✅ Jitter added to prevent thundering herd problems
"""
    )
    
    parser.add_argument(
        "--start-url",
        default="https://en.wikipedia.org/wiki/Category:Singapore",
        help="Starting Wikipedia category URL (default: Singapore category)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="./singapore_wiki_data",
        help="Output directory for crawled content (default: ./singapore_wiki_data)"
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum depth for subcategory crawling (default: 3)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts for failed requests (default: 3)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor crawling progress with periodic status updates"
    )
    
    parser.add_argument(
        "--status-interval",
        type=int,
        default=30,
        help="Status update interval in seconds when monitoring (default: 30)"
    )
    
    parser.add_argument(
        "--max-errors",
        type=int,
        default=100,
        help="Maximum errors before stopping crawler (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    crawler = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        if crawler:
            print("\nShutting down crawler...")
            crawler.stop_crawling()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("=" * 70)
        print("Wikipedia Singapore Crawler - Production Version")
        print("Smart Error Handling: 404s give up, others retry with backoff")
        print("=" * 70)
        print(f"Start URL: {args.start_url}")
        print(f"Output directory: {args.output_dir}")
        print(f"Maximum crawling depth: {args.max_depth}")
        print(f"Request delay: {args.delay}s")
        print(f"Max retries: {args.max_retries}")
        print(f"Max errors before stopping: {args.max_errors}")
        print("=" * 70)
        
        # Create output directory
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Check if this is a resume
        state_dir = output_path / "state"
        if state_dir.exists() and any(state_dir.iterdir()):
            print("Found existing state files - resuming previous crawl")
        else:
            print("Starting fresh crawl")
        
        # Create crawler
        crawler = WikipediaCrawler(
            start_url=args.start_url,
            output_dir=args.output_dir,
            max_depth=args.max_depth,
            delay_between_requests=args.delay,
            max_retries=args.max_retries
        )
        
        # Start crawling
        logger.info("Starting Wikipedia crawler...")
        crawler.start_crawling()
        
        if args.monitor:
            # Monitor progress
            print(f"\nMonitoring mode enabled (updates every {args.status_interval}s)")
            print("Press Ctrl+C to stop gracefully\n")
            
            last_processed = 0
            stall_count = 0
            
            try:
                while True:
                    status = crawler.get_status()
                    
                    if not status.is_running:
                        print("\nCrawler has stopped")
                        break
                    
                    # Check for progress
                    if status.total_processed == last_processed:
                        stall_count += 1
                    else:
                        stall_count = 0
                        last_processed = status.total_processed
                    
                    # Print status
                    print_status(crawler, show_details=True)
                    
                    # Check for too many errors
                    if status.error_count >= args.max_errors:
                        print(f"\nToo many errors ({status.error_count}), stopping crawler...")
                        break
                    
                    # Check for stalled progress
                    if stall_count >= 5:  # 5 intervals without progress
                        print(f"\nNo progress for {stall_count * args.status_interval}s, checking if crawler is stuck...")
                        if status.pending_urls == 0:
                            print("No pending URLs - crawl appears complete")
                            break
                    
                    time.sleep(args.status_interval)
                    
            except KeyboardInterrupt:
                print("\nMonitoring interrupted by user")
        else:
            # Wait for completion without monitoring
            print("Crawling started - press Ctrl+C to stop")
            print("Use --monitor flag for progress updates")
            
            try:
                while True:
                    status = crawler.get_status()
                    if not status.is_running:
                        break
                    
                    # Check for too many errors
                    if status.error_count >= args.max_errors:
                        logger.error(f"Too many errors ({status.error_count}), stopping crawler")
                        break
                    
                    time.sleep(10)  # Check every 10 seconds
                    
            except KeyboardInterrupt:
                print("\nCrawling interrupted by user")
        
        # Stop crawler if still running
        if crawler.get_status().is_running:
            print("Stopping crawler...")
            crawler.stop_crawling()
        
        # Final status
        print("\n" + "=" * 70)
        print("CRAWLING SESSION COMPLETED")
        print("=" * 70)
        
        final_status = crawler.get_status()
        print_status(crawler, show_details=True)
        
        # Show output summary
        print(f"\n=== Output Summary ===")
        if output_path.exists():
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(output_path):
                for file in files:
                    if not file.endswith('.json'):
                        continue
                    filepath = Path(root) / file
                    size = filepath.stat().st_size
                    total_size += size
                    file_count += 1
            
            print(f"Output directory: {output_path}")
            print(f"Files created: {file_count}")
            print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
        
        # Success/failure summary
        if final_status.error_count == 0:
            print("\n✅ Crawling completed successfully with no errors!")
        elif final_status.error_count < args.max_errors:
            print(f"\n⚠️  Crawling completed with {final_status.error_count} errors (within acceptable limit)")
        else:
            print(f"\n❌ Crawling stopped due to too many errors ({final_status.error_count})")
        
        print("\nTo resume this crawl later, run:")
        print(f"python run_production_crawler.py --output-dir {args.output_dir}")
        
        # Show error handling summary
        stats = crawler.get_detailed_stats()
        page_stats = stats.get('page_processor', {})
        permanent_failures = page_stats.get('permanent_failures', 0)
        total_retries = page_stats.get('retries_attempted', 0)
        
        print(f"\n=== Error Handling Summary ===")
        print(f"Permanent failures (404/403) skipped: {permanent_failures}")
        print(f"Retry attempts made: {total_retries}")
        print("✅ Smart error handling prevented wasted retry attempts on permanent failures")
        
    except Exception as e:
        logger.error(f"Crawling failed: {e}")
        if crawler:
            crawler.stop_crawling()
        sys.exit(1)


if __name__ == "__main__":
    main()