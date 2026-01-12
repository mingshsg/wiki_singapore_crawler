#!/usr/bin/env python3
"""
Main entry point for the Wikipedia Singapore Crawler.

This script provides a command-line interface for starting, stopping, and monitoring
the Wikipedia crawling process.
"""

import argparse
import signal
import sys
import time
from pathlib import Path

from wikipedia_crawler.config import CrawlerConfig
from wikipedia_crawler.core.wikipedia_crawler import WikipediaCrawler
from wikipedia_crawler.utils.logging_config import setup_logging, get_logger


def print_status(crawler: WikipediaCrawler) -> None:
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
    print("=" * 22)


def main():
    """Main entry point for the crawler."""
    parser = argparse.ArgumentParser(
        description="Wikipedia Singapore Crawler - Systematically crawl Singapore-related Wikipedia pages"
    )
    
    parser.add_argument(
        "--start-url",
        default="https://en.wikipedia.org/wiki/Category:Singapore",
        help="Starting Wikipedia category URL (default: Singapore category)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="./wiki_data",
        help="Output directory for crawled content (default: ./wiki_data)"
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum depth for subcategory crawling (default: 5)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
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
        "--config",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor crawling progress with periodic status updates"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = get_logger(__name__)
    
    crawler = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        if crawler:
            crawler.stop_crawling()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config = CrawlerConfig.load(args.config) if args.config else CrawlerConfig()
        
        # Override with command line arguments
        start_url = args.start_url
        output_dir = args.output_dir
        max_depth = args.max_depth
        delay = args.delay
        max_retries = args.max_retries
        
        logger.info("Starting Wikipedia Singapore Crawler")
        logger.info(f"Start URL: {start_url}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Maximum crawling depth: {max_depth}")
        logger.info(f"Request delay: {delay}s")
        logger.info(f"Max retries: {max_retries}")
        
        # Create crawler
        crawler = WikipediaCrawler(
            start_url=start_url,
            output_dir=output_dir,
            max_depth=max_depth,
            delay_between_requests=delay,
            max_retries=max_retries
        )
        
        # Start crawling
        crawler.start_crawling()
        
        if args.monitor:
            # Monitor progress
            logger.info("Monitoring mode enabled - press Ctrl+C to stop")
            try:
                while True:
                    status = crawler.get_status()
                    if not status.is_running:
                        break
                    
                    print_status(crawler)
                    time.sleep(10)  # Update every 10 seconds
                    
            except KeyboardInterrupt:
                logger.info("Monitoring interrupted by user")
        else:
            # Wait for completion
            logger.info("Crawling started - press Ctrl+C to stop")
            try:
                while True:
                    status = crawler.get_status()
                    if not status.is_running:
                        break
                    time.sleep(5)
            except KeyboardInterrupt:
                logger.info("Crawling interrupted by user")
        
        # Stop crawler if still running
        if crawler.get_status().is_running:
            logger.info("Stopping crawler...")
            crawler.stop_crawling()
        
        # Final status
        final_status = crawler.get_status()
        logger.info("Crawling session completed")
        logger.info(f"Total processed: {final_status.total_processed}")
        logger.info(f"Categories: {final_status.categories_processed}")
        logger.info(f"Articles: {final_status.articles_processed}")
        logger.info(f"Filtered: {final_status.filtered_count}")
        logger.info(f"Errors: {final_status.error_count}")
        
        # Show detailed stats
        if args.log_level == "DEBUG":
            stats = crawler.get_detailed_stats()
            logger.debug(f"Detailed statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Crawling failed: {e}")
        if crawler:
            crawler.stop_crawling()
        sys.exit(1)


if __name__ == "__main__":
    main()