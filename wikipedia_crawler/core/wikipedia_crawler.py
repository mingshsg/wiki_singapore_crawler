"""Main Wikipedia crawler orchestration class."""

import signal
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from wikipedia_crawler.models.data_models import (
    URLItem, URLType, ProcessStatus, CrawlStatus
)
from wikipedia_crawler.core.url_queue import URLQueueManager
from wikipedia_crawler.core.deduplication import DeduplicationSystem
from wikipedia_crawler.core.page_processor import PageProcessor, PageType
from wikipedia_crawler.core.progress_tracker import ProgressTracker
from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.processors.category_handler import CategoryPageHandler
from wikipedia_crawler.processors.article_handler import ArticlePageHandler
from wikipedia_crawler.processors.content_processor import ContentProcessor
from wikipedia_crawler.processors.language_filter import LanguageFilter
from wikipedia_crawler.utils.logging_config import get_logger


class WikipediaCrawler:
    """
    Main Wikipedia crawler that orchestrates the entire crawling process.
    
    Features:
    - Integrates all components into main crawling loop
    - Implements recursive processing logic with depth management
    - Provides graceful shutdown and error recovery
    - Supports resumability through state persistence
    - Thread-safe operations with proper synchronization
    """
    
    def __init__(self, 
                 start_url: str,
                 output_dir: str = "wikipedia_data",
                 max_depth: int = 5,
                 delay_between_requests: float = 1.0,
                 max_retries: int = 3):
        """
        Initialize the Wikipedia crawler.
        
        Args:
            start_url: Starting Wikipedia category URL
            output_dir: Directory to save crawled data
            max_depth: Maximum crawling depth for subcategories
            delay_between_requests: Delay between HTTP requests (seconds)
            max_retries: Maximum retry attempts for failed requests
        """
        self.start_url = start_url
        self.output_dir = Path(output_dir)
        self.max_depth = max_depth
        self.logger = get_logger(__name__)
        
        # Validate start URL
        if not self._is_valid_wikipedia_url(start_url):
            raise ValueError(f"Invalid Wikipedia URL: {start_url}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._initialize_components(delay_between_requests, max_retries)
        
        # Crawling control
        self._running = False
        self._shutdown_requested = False
        self._crawl_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Statistics
        self._session_stats = {
            'session_start': None,
            'session_end': None,
            'urls_processed_this_session': 0,
            'errors_this_session': 0
        }
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        self.logger.info(f"WikipediaCrawler initialized for: {start_url}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Max depth: {max_depth}, Delay: {delay_between_requests}s")
    
    def _initialize_components(self, delay_between_requests: float, max_retries: int) -> None:
        """Initialize all crawler components."""
        # Create state file paths
        state_dir = self.output_dir / "state"
        state_dir.mkdir(exist_ok=True)
        
        queue_state_file = state_dir / "queue_state.json"
        dedup_state_file = state_dir / "deduplication_state.json"
        progress_state_file = state_dir / "progress_state.json"
        
        # Initialize core components
        self.url_queue = URLQueueManager(str(queue_state_file))
        self.deduplication = DeduplicationSystem(str(dedup_state_file))
        self.progress_tracker = ProgressTracker(progress_state_file)
        
        # Initialize file storage with folder configuration
        folder_config = {
            'organize_by': 'category',
            'category_folder_name': self._extract_category_name_from_url(self.start_url),
            'create_subfolders': False
        }
        self.file_storage = FileStorage(str(self.output_dir), folder_config)
        
        # Initialize page processor
        self.page_processor = PageProcessor(
            delay_between_requests=delay_between_requests,
            max_retries=max_retries
        )
        
        # Initialize content processors
        self.content_processor = ContentProcessor()
        self.language_filter = LanguageFilter()
        
        # Initialize page handlers
        self.category_handler = CategoryPageHandler(
            file_storage=self.file_storage,
            max_depth=self.max_depth
        )
        self.article_handler = ArticlePageHandler(
            file_storage=self.file_storage,
            content_processor=self.content_processor,
            language_filter=self.language_filter
        )
        
        self.logger.info("All components initialized successfully")
    
    def start_crawling(self) -> None:
        """
        Start the crawling process.
        
        This method starts crawling in a separate thread and returns immediately.
        Use get_status() to monitor progress or stop_crawling() to stop.
        """
        with self._lock:
            if self._running:
                self.logger.warning("Crawler is already running")
                return
            
            self._running = True
            self._shutdown_requested = False
            
            # Start crawling in a separate thread
            self._crawl_thread = threading.Thread(
                target=self._crawl_loop,
                name="WikipediaCrawler",
                daemon=False
            )
            self._crawl_thread.start()
            
            self.logger.info("Crawling started in background thread")
    
    def stop_crawling(self) -> None:
        """
        Stop the crawling process gracefully.
        
        This method requests shutdown and waits for the crawling thread to finish.
        """
        with self._lock:
            if not self._running:
                self.logger.info("Crawler is not running")
                return
            
            self.logger.info("Requesting crawler shutdown...")
            self._shutdown_requested = True
        
        # Wait for crawling thread to finish (outside the lock)
        if self._crawl_thread and self._crawl_thread.is_alive():
            self.logger.info("Waiting for crawling thread to finish...")
            self._crawl_thread.join(timeout=30)  # Wait up to 30 seconds
            
            if self._crawl_thread.is_alive():
                self.logger.warning("Crawling thread did not finish within timeout")
            else:
                self.logger.info("Crawling thread finished successfully")
        
        with self._lock:
            self._running = False
            self._crawl_thread = None
        
        self.logger.info("Crawler stopped")
    
    def _crawl_loop(self) -> None:
        """Main crawling loop that processes URLs from the queue."""
        try:
            self.logger.info("Starting crawl loop")
            self._session_stats['session_start'] = time.time()
            
            # Load existing state
            self._load_state()
            
            # Add start URL if queue is empty
            if self.url_queue.is_empty() and not self.deduplication.is_processed(self.start_url):
                self.logger.info(f"Adding start URL to queue: {self.start_url}")
                start_url_type = URLType.CATEGORY if '/Category:' in self.start_url else URLType.ARTICLE
                self.url_queue.add_url(self.start_url, start_url_type, depth=0)
            
            # Start progress tracking
            self.progress_tracker.start_crawling(self.start_url)
            
            # Main processing loop
            processed_any_url = False
            consecutive_empty_checks = 0
            max_empty_checks = 10  # Allow some time for URLs to be added
            
            while not self._shutdown_requested:
                try:
                    # Get next URL to process
                    url_item = self.url_queue.get_next_url()
                    if not url_item:
                        consecutive_empty_checks += 1
                        if consecutive_empty_checks >= max_empty_checks and processed_any_url:
                            # We've processed at least one URL and queue has been empty for a while
                            self.logger.info("No more URLs to process, finishing crawl")
                            break
                        
                        self.logger.debug(f"No URLs available, waiting... (check {consecutive_empty_checks}/{max_empty_checks})")
                        time.sleep(0.5)
                        continue
                    
                    # Reset empty check counter since we got a URL
                    consecutive_empty_checks = 0
                    processed_any_url = True
                    
                    # Check if already processed (double-check for thread safety)
                    if self.deduplication.is_processed(url_item.url):
                        self.logger.debug(f"URL already processed: {url_item.url}")
                        continue
                    
                    # Process the URL
                    self._process_url(url_item)
                    
                    # Update progress
                    self.progress_tracker.update_pending_count(self.url_queue.size())
                    
                    # Periodic state saving
                    if self._session_stats['urls_processed_this_session'] % 10 == 0:
                        self._save_state()
                    
                except Exception as e:
                    self.logger.error(f"Error in crawl loop: {e}")
                    self._session_stats['errors_this_session'] += 1
                    time.sleep(5)  # Brief pause before continuing
            
            # Crawling completed
            if self._shutdown_requested:
                self.logger.info("Crawling stopped due to shutdown request")
            else:
                self.logger.info("Crawling completed - no more URLs to process")
            
        except Exception as e:
            self.logger.error(f"Fatal error in crawl loop: {e}")
        finally:
            # Clean up
            self._session_stats['session_end'] = time.time()
            self.progress_tracker.stop_crawling()
            self._save_state()
            
            with self._lock:
                self._running = False
            
            self.logger.info("Crawl loop finished")
    
    def _process_url(self, url_item: URLItem) -> None:
        """
        Process a single URL.
        
        Args:
            url_item: URLItem to process
        """
        url = url_item.url
        self.logger.info(f"Processing URL: {url} (type: {url_item.url_type.value}, depth: {url_item.depth})")
        
        try:
            # Mark as being processed
            self.deduplication.mark_processed(url)
            self.url_queue.mark_completed(url)
            
            # Fetch and process the page
            page_result = self.page_processor.process_page(url)
            
            if not page_result.success:
                error_msg = page_result.error_message or "Unknown error"
                self.logger.warning(f"Failed to fetch page: {url} - {error_msg}")
                self.progress_tracker.update_progress(
                    url, ProcessStatus.ERROR, url_item.url_type, error_message=error_msg
                )
                return
            
            # Route to appropriate handler based on page type
            if page_result.page_type == PageType.CATEGORY.value:
                self._process_category_page(url, page_result.content, url_item.depth)
            elif page_result.page_type == PageType.ARTICLE.value:
                self._process_article_page(url, page_result.content)
            else:
                self.logger.warning(f"Unknown page type for URL: {url}")
                self.progress_tracker.update_progress(
                    url, ProcessStatus.ERROR, url_item.url_type, 
                    error_message="Unknown page type"
                )
            
            self._session_stats['urls_processed_this_session'] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing URL {url}: {e}")
            self.progress_tracker.update_progress(
                url, ProcessStatus.ERROR, url_item.url_type, error_message=str(e)
            )
            self._session_stats['errors_this_session'] += 1
    
    def _process_category_page(self, url: str, content: str, depth: int) -> None:
        """
        Process a category page.
        
        Args:
            url: Category page URL
            content: HTML content
            depth: Current crawling depth
        """
        try:
            result = self.category_handler.process_category(url, content, depth)
            
            if result.success:
                # Add discovered URLs to queue
                if result.discovered_urls:
                    for discovered_url in result.discovered_urls:
                        if not self.deduplication.is_processed(discovered_url):
                            # Determine URL type and depth
                            if '/Category:' in discovered_url:
                                url_type = URLType.CATEGORY
                                new_depth = depth + 1
                            else:
                                url_type = URLType.ARTICLE
                                new_depth = depth  # Articles don't increase depth
                            
                            self.url_queue.add_url(discovered_url, url_type, new_depth)
                
                self.progress_tracker.update_progress(
                    url, ProcessStatus.COMPLETED, URLType.CATEGORY
                )
                
                self.logger.info(f"Successfully processed category: {url} "
                               f"(found {len(result.discovered_urls or [])} new URLs)")
            else:
                error_msg = result.error_message or "Category processing failed"
                self.progress_tracker.update_progress(
                    url, ProcessStatus.ERROR, URLType.CATEGORY, error_message=error_msg
                )
                
        except Exception as e:
            self.logger.error(f"Error processing category page {url}: {e}")
            self.progress_tracker.update_progress(
                url, ProcessStatus.ERROR, URLType.CATEGORY, error_message=str(e)
            )
    
    def _process_article_page(self, url: str, content: str) -> None:
        """
        Process an article page.
        
        Args:
            url: Article page URL
            content: HTML content
        """
        try:
            result = self.article_handler.process_article(url, content)
            
            if result.success:
                if result.data and result.data.get('filtered', False):
                    # Article was filtered due to language
                    language = result.data.get('language', 'unknown')
                    self.progress_tracker.update_progress(
                        url, ProcessStatus.FILTERED, URLType.ARTICLE, language=language
                    )
                    self.logger.info(f"Article filtered ({language}): {url}")
                else:
                    # Article was processed and saved
                    language = result.data.get('language', 'unknown') if result.data else 'unknown'
                    self.progress_tracker.update_progress(
                        url, ProcessStatus.COMPLETED, URLType.ARTICLE, language=language
                    )
                    self.logger.info(f"Successfully processed article ({language}): {url}")
            else:
                error_msg = result.error_message or "Article processing failed"
                self.progress_tracker.update_progress(
                    url, ProcessStatus.ERROR, URLType.ARTICLE, error_message=error_msg
                )
                
        except Exception as e:
            self.logger.error(f"Error processing article page {url}: {e}")
            self.progress_tracker.update_progress(
                url, ProcessStatus.ERROR, URLType.ARTICLE, error_message=str(e)
            )
    
    def _load_state(self) -> None:
        """Load crawler state from files."""
        try:
            self.logger.info("Loading crawler state...")
            
            # Load component states
            queue_loaded = self.url_queue.load_state()
            dedup_loaded = self.deduplication.load_state()
            progress_loaded = self.progress_tracker.load_state()
            
            if queue_loaded or dedup_loaded or progress_loaded:
                self.logger.info("Crawler state loaded successfully")
                
                # Log state summary
                queue_stats = self.url_queue.get_stats()
                dedup_stats = self.deduplication.get_stats()
                
                self.logger.info(f"Queue: {queue_stats['queue_size']} pending, "
                               f"{queue_stats['completed_urls']} completed")
                self.logger.info(f"Deduplication: {dedup_stats['total_processed_urls']} processed URLs")
            else:
                self.logger.info("No existing state found, starting fresh")
                
        except Exception as e:
            self.logger.error(f"Error loading crawler state: {e}")
    
    def _save_state(self) -> None:
        """Save crawler state to files."""
        try:
            self.logger.debug("Saving crawler state...")
            
            # Save component states
            self.url_queue.save_state()
            self.deduplication.save_state()
            self.progress_tracker.save_state()
            
            self.logger.debug("Crawler state saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving crawler state: {e}")
    
    def get_status(self) -> CrawlStatus:
        """
        Get current crawling status.
        
        Returns:
            CrawlStatus with current progress information
        """
        with self._lock:
            status = self.progress_tracker.get_status()
            status.pending_urls = self.url_queue.size()
            return status
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """
        Get detailed statistics from all components.
        
        Returns:
            Dictionary with comprehensive statistics
        """
        return {
            'crawler': {
                'running': self._running,
                'shutdown_requested': self._shutdown_requested,
                'session_stats': self._session_stats.copy()
            },
            'queue': self.url_queue.get_stats(),
            'deduplication': self.deduplication.get_stats(),
            'progress': self.progress_tracker.get_stats(),
            'page_processor': self.page_processor.get_stats(),
            'category_handler': self.category_handler.get_stats(),
            'article_handler': self.article_handler.get_stats(),
            'language_filter': self.language_filter.get_language_stats()
        }
    
    def _is_valid_wikipedia_url(self, url: str) -> bool:
        """
        Validate that the URL is a valid Wikipedia URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid Wikipedia URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ['http', 'https'] and
                'wikipedia.org' in parsed.netloc and
                parsed.path.startswith('/wiki/')
            )
        except Exception:
            return False
    
    def _extract_category_name_from_url(self, url: str) -> str:
        """
        Extract category name from Wikipedia URL for folder naming.
        
        Args:
            url: Wikipedia URL
            
        Returns:
            Category folder name
        """
        try:
            if 'Category:' in url:
                # Extract category name from URL
                category_part = url.split('Category:')[-1]
                # Clean up the category name for folder use
                folder_name = f"Category_{category_part.replace('%20', '_').replace(' ', '_')}"
                return folder_name
            else:
                return "General_Crawl"
        except Exception:
            return "Category_Unknown"
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.stop_crawling()
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            self.logger.debug("Signal handlers registered")
        except Exception as e:
            self.logger.warning(f"Could not register signal handlers: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._running:
            self.stop_crawling()
        
        # Close page processor session
        if hasattr(self.page_processor, 'close'):
            self.page_processor.close()