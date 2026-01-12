"""Base page processor for handling Wikipedia page requests and routing."""

import time
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from enum import Enum
from bs4 import BeautifulSoup

from wikipedia_crawler.models.data_models import ProcessResult, URLType
import logging


class PageType(Enum):
    """Types of Wikipedia pages."""
    CATEGORY = "category"
    ARTICLE = "article"
    UNKNOWN = "unknown"


class PageProcessor:
    """
    Base processor for handling Wikipedia page requests and routing.
    
    Features:
    - HTTP request handling with proper error handling
    - Page type detection logic
    - Rate limiting and respectful crawling delays
    - Request retries with exponential backoff
    - User-Agent management
    """
    
    def __init__(self, 
                 delay_between_requests: float = 1.0,
                 max_retries: int = 3,
                 timeout: int = 30,
                 user_agent: Optional[str] = None):
        """
        Initialize the page processor.
        
        Args:
            delay_between_requests: Delay in seconds between requests
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        self.logger = logging.getLogger(__name__)
        self.delay_between_requests = delay_between_requests
        self.max_retries = max_retries
        self.timeout = timeout
        
        # HTTP session configuration
        self.session = requests.Session()
        self.headers = {
            'User-Agent': user_agent or 'WikipediaCrawler/1.0 (Educational Research Project; Contact: researcher@example.com)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache'
        }
        self.session.headers.update(self.headers)
        
        # Track request timing for rate limiting
        self._last_request_time = 0.0
        
        # Statistics
        self._stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retries_attempted': 0,
            'categories_processed': 0,
            'articles_processed': 0,
            'permanent_failures': 0,
            'client_errors': 0,
            'connection_errors': 0,
            'timeout_errors': 0,
            'redirect_errors': 0,
            'other_errors': 0,
            'total_failures': 0,
            'connectivity_tests': 0,
            'connectivity_successes': 0,
            'connectivity_failures': 0,
            'skipped_urls': 0,
            'user_retries': 0,
            'user_retry_successes': 0,
            'user_decisions': {},
            'circuit_breaker_activations': 0
        }
        
        self.logger.info(f"PageProcessor initialized with {delay_between_requests}s delay, {max_retries} max retries")
    
    def process_page(self, url: str) -> ProcessResult:
        """
        Process a Wikipedia page by fetching content and determining type.
        
        Args:
            url: URL to process
            
        Returns:
            ProcessResult with page content and metadata
        """
        try:
            self.logger.info(f"Processing page: {url}")
            
            # Fetch page content
            response = self._fetch_page(url)
            if not response:
                return ProcessResult(
                    success=False,
                    error_message="Failed to fetch page content",
                    url=url
                )
            
            # Parse content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Determine page type
            page_type = self._determine_page_type(response.text, url)
            
            # Update statistics
            if page_type == PageType.CATEGORY:
                self._stats['categories_processed'] += 1
            elif page_type == PageType.ARTICLE:
                self._stats['articles_processed'] += 1
            
            # Create successful result
            result = ProcessResult(
                success=True,
                url=url,
                content=response.text,
                page_type=page_type.value,
                status_code=response.status_code,
                content_length=len(response.text),
                response_headers=dict(response.headers)
            )
            
            self.logger.debug(f"Successfully processed {page_type.value} page: {url}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing page {url}: {e}")
            self._stats['failed_requests'] += 1
            
            return ProcessResult(
                success=False,
                error_message=str(e),
                url=url
            )
    
    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        """
        Fetch a page with rate limiting, retries, and intelligent error handling.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response object if successful, None otherwise
        """
        # Implement rate limiting
        self._enforce_rate_limit()
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                response = self.session.get(url, timeout=self.timeout)
                self._stats['requests_made'] += 1
                
                # Check for successful response
                if response.status_code == 200:
                    self._stats['successful_requests'] += 1
                    self.logger.debug(f"Successfully fetched {url} ({len(response.text)} bytes)")
                    return response
                else:
                    self.logger.warning(f"HTTP {response.status_code} for URL: {url}")
                    self._stats['failed_requests'] += 1
                    
                    # Don't retry for certain status codes (permanent failures)
                    if response.status_code in [404, 403, 410, 451]:  # Not found, forbidden, gone, unavailable for legal reasons
                        self.logger.info(f"Permanent failure HTTP {response.status_code} for URL: {url} - giving up")
                        self._stats['permanent_failures'] += 1
                        return None
                    
                    # Don't retry for client errors (4xx) except rate limiting
                    if 400 <= response.status_code < 500 and response.status_code not in [429, 408]:  # Rate limit, timeout
                        self.logger.info(f"Client error HTTP {response.status_code} for URL: {url} - giving up")
                        self._stats['client_errors'] += 1
                        return None
                    
                    last_exception = requests.HTTPError(f"HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"Connection error for URL {url}: {e}")
                self._stats['connection_errors'] += 1
                last_exception = e
                
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"Timeout for URL {url}: {e}")
                self._stats['timeout_errors'] += 1
                last_exception = e
                
            except requests.exceptions.TooManyRedirects as e:
                self.logger.warning(f"Too many redirects for URL {url}: {e}")
                self._stats['redirect_errors'] += 1
                # Don't retry redirect loops
                return None
                
            except (requests.RequestException, Exception) as e:
                self.logger.warning(f"Request failed for URL {url}: {e}")
                self._stats['other_errors'] += 1
                last_exception = e
            
            # Wait before retry (exponential backoff with jitter)
            if attempt < self.max_retries:
                base_wait = self.delay_between_requests * (2 ** attempt)
                # Add jitter to avoid thundering herd
                jitter = base_wait * 0.1 * (0.5 - hash(url) % 100 / 100.0)  # ±10% jitter based on URL
                wait_time = base_wait + jitter
                self.logger.debug(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
                self._stats['retries_attempted'] += 1
        
        # All retries failed - check network connectivity and ask user
        return self._handle_failed_url_with_connectivity_check(url, last_exception)
    
    def _handle_failed_url_with_connectivity_check(self, url: str, last_exception: Exception) -> Optional[requests.Response]:
        """
        Handle a URL that failed all retry attempts by checking network connectivity
        and prompting user for action.
        
        Args:
            url: The URL that failed
            last_exception: The last exception that occurred
            
        Returns:
            Response object if user chooses to retry and succeeds, None otherwise
        """
        self.logger.error(f"All {self.max_retries + 1} attempts failed for URL: {url}. Last error: {last_exception}")
        
        # Test network connectivity
        if not self._test_network_connectivity():
            self.logger.warning("Network connectivity test failed - prompting user for action")
            
            # Circuit breaker: limit consecutive user retry attempts
            max_user_retry_cycles = 3  # Maximum number of user retry cycles before forcing skip
            user_retry_cycle = 0
            
            while user_retry_cycle < max_user_retry_cycles:
                user_choice = self._prompt_user_for_action(url, user_retry_cycle + 1, max_user_retry_cycles)
                
                if user_choice.lower() == 'skip':
                    self.logger.info(f"User chose to skip URL: {url}")
                    self._stats['skipped_urls'] = self._stats.get('skipped_urls', 0) + 1
                    self._stats['total_failures'] += 1
                    return None
                    
                elif user_choice.lower() == 'continue':
                    user_retry_cycle += 1
                    self.logger.info(f"User chose to retry URL: {url} (cycle {user_retry_cycle}/{max_user_retry_cycles})")
                    self._stats['user_retries'] = self._stats.get('user_retries', 0) + 1
                    
                    # Retry the URL with full retry logic
                    retry_result = self._retry_url_after_user_choice(url)
                    if retry_result is not None:
                        return retry_result
                    
                    # If retry failed, test connectivity again
                    if not self._test_network_connectivity():
                        if user_retry_cycle >= max_user_retry_cycles:
                            self.logger.warning(f"Maximum user retry cycles ({max_user_retry_cycles}) reached for URL: {url} - forcing skip")
                            print(f"\n⚠️  Maximum retry attempts ({max_user_retry_cycles}) reached. Automatically skipping URL to prevent infinite loop.")
                            self._stats['skipped_urls'] = self._stats.get('skipped_urls', 0) + 1
                            self._stats['total_failures'] += 1
                            self._stats['circuit_breaker_activations'] = self._stats.get('circuit_breaker_activations', 0) + 1
                            return None
                        else:
                            self.logger.warning("Retry failed and connectivity test still fails - prompting user again")
                            continue
                    else:
                        # Connectivity is good but URL still fails - treat as permanent failure
                        self.logger.info(f"Connectivity restored but URL still fails - treating as permanent failure: {url}")
                        self._stats['total_failures'] += 1
                        return None
                else:
                    print("Invalid choice. Please enter 'continue' or 'skip'.")
            
            # Circuit breaker triggered - force skip
            self.logger.warning(f"Circuit breaker triggered: Maximum user retry cycles ({max_user_retry_cycles}) reached for URL: {url}")
            print(f"\n🛑 Circuit breaker activated: Maximum retry cycles reached. Automatically skipping URL.")
            self._stats['skipped_urls'] = self._stats.get('skipped_urls', 0) + 1
            self._stats['total_failures'] += 1
            self._stats['circuit_breaker_activations'] = self._stats.get('circuit_breaker_activations', 0) + 1
            return None
        else:
            # Network connectivity is good but URL still fails - treat as permanent failure
            self.logger.info(f"Network connectivity is good but URL still fails - treating as permanent failure: {url}")
            self._stats['total_failures'] += 1
            return None
    
    def _test_network_connectivity(self) -> bool:
        """
        Test network connectivity by attempting to reach Google.
        
        Returns:
            True if connectivity test succeeds, False otherwise
        """
        try:
            self.logger.debug("Testing network connectivity to Google...")
            response = self.session.get("https://www.google.com", timeout=10)
            success = response.status_code == 200
            
            self._stats['connectivity_tests'] = self._stats.get('connectivity_tests', 0) + 1
            if success:
                self._stats['connectivity_successes'] = self._stats.get('connectivity_successes', 0) + 1
                self.logger.debug("Network connectivity test successful")
            else:
                self._stats['connectivity_failures'] = self._stats.get('connectivity_failures', 0) + 1
                self.logger.warning(f"Network connectivity test failed with status: {response.status_code}")
            
            return success
            
        except Exception as e:
            self._stats['connectivity_tests'] = self._stats.get('connectivity_tests', 0) + 1
            self._stats['connectivity_failures'] = self._stats.get('connectivity_failures', 0) + 1
            self.logger.warning(f"Network connectivity test failed with exception: {e}")
            return False
    
    def _prompt_user_for_action(self, url: str, current_cycle: int = 1, max_cycles: int = 3) -> str:
        """
        Prompt user to choose between continuing or skipping a failed URL.
        
        Args:
            url: The URL that failed
            current_cycle: Current retry cycle number
            max_cycles: Maximum retry cycles before circuit breaker activates
            
        Returns:
            User's choice ('continue' or 'skip')
        """
        print(f"\n{'='*60}")
        print("NETWORK CONNECTIVITY ISSUE DETECTED")
        print(f"{'='*60}")
        print(f"Failed to fetch URL after {self.max_retries + 1} attempts:")
        print(f"  {url}")
        print(f"\nConnectivity test to Google also failed.")
        print(f"This may indicate a network connectivity issue.")
        print(f"\nRetry cycle: {current_cycle}/{max_cycles}")
        if current_cycle >= max_cycles:
            print(f"⚠️  WARNING: This is the final retry cycle. After this, the URL will be automatically skipped.")
        print(f"\nOptions:")
        print(f"  continue - Retry this URL (will attempt {self.max_retries + 1} more times)")
        print(f"  skip     - Skip this URL and proceed to the next one")
        print(f"{'='*60}")
        
        while True:
            try:
                choice = input("Enter your choice (continue/skip): ").strip().lower()
                if choice in ['continue', 'skip']:
                    # Log the user's decision
                    self._stats['user_decisions'] = self._stats.get('user_decisions', {})
                    self._stats['user_decisions'][choice] = self._stats['user_decisions'].get(choice, 0) + 1
                    return choice
                else:
                    print("Invalid choice. Please enter 'continue' or 'skip'.")
            except (EOFError, KeyboardInterrupt):
                print("\nReceived interrupt signal. Choosing 'skip' to continue gracefully.")
                self._stats['user_decisions'] = self._stats.get('user_decisions', {})
                self._stats['user_decisions']['skip'] = self._stats['user_decisions'].get('skip', 0) + 1
                return 'skip'
    
    def _retry_url_after_user_choice(self, url: str) -> Optional[requests.Response]:
        """
        Retry a URL after user chose to continue, using the same retry logic as _fetch_page.
        
        Args:
            url: URL to retry
            
        Returns:
            Response object if successful, None otherwise
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"User-requested retry for {url} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                response = self.session.get(url, timeout=self.timeout)
                self._stats['requests_made'] += 1
                
                # Check for successful response
                if response.status_code == 200:
                    self._stats['successful_requests'] += 1
                    self._stats['user_retry_successes'] = self._stats.get('user_retry_successes', 0) + 1
                    self.logger.info(f"User-requested retry successful for {url}")
                    return response
                else:
                    self.logger.warning(f"User-requested retry got HTTP {response.status_code} for URL: {url}")
                    self._stats['failed_requests'] += 1
                    
                    # Don't retry for permanent failures even in user-requested retries
                    if response.status_code in [404, 403, 410, 451]:
                        self.logger.info(f"Permanent failure HTTP {response.status_code} during user retry for URL: {url}")
                        self._stats['permanent_failures'] += 1
                        return None
                    
                    if 400 <= response.status_code < 500 and response.status_code not in [429, 408]:
                        self.logger.info(f"Client error HTTP {response.status_code} during user retry for URL: {url}")
                        self._stats['client_errors'] += 1
                        return None
                    
                    last_exception = requests.HTTPError(f"HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"Connection error during user retry for URL {url}: {e}")
                self._stats['connection_errors'] += 1
                last_exception = e
                
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"Timeout during user retry for URL {url}: {e}")
                self._stats['timeout_errors'] += 1
                last_exception = e
                
            except (requests.RequestException, Exception) as e:
                self.logger.warning(f"Request failed during user retry for URL {url}: {e}")
                self._stats['other_errors'] += 1
                last_exception = e
            
            # Wait before retry (exponential backoff with jitter)
            if attempt < self.max_retries:
                base_wait = self.delay_between_requests * (2 ** attempt)
                jitter = base_wait * 0.1 * (0.5 - hash(url) % 100 / 100.0)
                wait_time = base_wait + jitter
                self.logger.debug(f"Waiting {wait_time:.1f}s before user-requested retry...")
                time.sleep(wait_time)
                self._stats['retries_attempted'] += 1
        
        # All user-requested retries failed
        self.logger.error(f"All user-requested retries failed for URL: {url}. Last error: {last_exception}")
        return None
    
    def _determine_page_type(self, content: str, url: str) -> PageType:
        """
        Determine the type of Wikipedia page based on content and URL.
        
        Args:
            content: HTML content of the page
            url: URL of the page
            
        Returns:
            PageType enum value
        """
        try:
            # Method 1: Check URL pattern
            if '/Category:' in url:
                return PageType.CATEGORY
            
            # Method 2: Parse content to look for category-specific elements
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for category page indicators
            category_indicators = [
                # Category navigation elements
                soup.find('div', {'id': 'mw-category-media'}),
                soup.find('div', {'id': 'mw-subcategories'}),
                soup.find('div', {'id': 'mw-pages'}),
                soup.find('div', class_='CategoryTreeTag'),
                
                # Category-specific headings
                soup.find('h2', string=lambda text: text and 'subcategories' in text.lower()),
                soup.find('h2', string=lambda text: text and 'pages in category' in text.lower()),
            ]
            
            if any(indicator for indicator in category_indicators):
                return PageType.CATEGORY
            
            # Method 3: Look for article-specific elements
            article_indicators = [
                soup.find('div', {'id': 'mw-content-text'}),
                soup.find('div', class_='mw-parser-output'),
                soup.find('p'),  # Articles typically have paragraphs
            ]
            
            if any(indicator for indicator in article_indicators):
                # Additional check: make sure it's not a disambiguation or special page
                if self._is_article_page(soup):
                    return PageType.ARTICLE
            
            # Method 4: Check page title and content structure
            title_element = soup.find('h1', {'id': 'firstHeading'})
            if title_element:
                title_text = title_element.get_text().strip()
                if title_text.startswith('Category:'):
                    return PageType.CATEGORY
            
            # Default to article if we can't determine otherwise
            return PageType.ARTICLE
            
        except Exception as e:
            self.logger.warning(f"Error determining page type for {url}: {e}")
            return PageType.UNKNOWN
    
    def _is_article_page(self, soup: BeautifulSoup) -> bool:
        """
        Check if the page is a regular Wikipedia article.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            True if it's an article page, False otherwise
        """
        # Look for article content indicators
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return False
        
        # Check for substantial text content (not just navigation)
        paragraphs = content_div.find_all('p')
        substantial_paragraphs = [p for p in paragraphs if len(p.get_text().strip()) > 50]
        
        if len(substantial_paragraphs) >= 1:
            return True
        
        # Check for infoboxes (common in articles)
        infobox = soup.find('table', class_=lambda x: x and 'infobox' in x.lower())
        if infobox:
            return True
        
        return False
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.delay_between_requests:
            sleep_time = self.delay_between_requests - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self._stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retries_attempted': 0,
            'categories_processed': 0,
            'articles_processed': 0,
            'permanent_failures': 0,
            'client_errors': 0,
            'connection_errors': 0,
            'timeout_errors': 0,
            'redirect_errors': 0,
            'other_errors': 0,
            'total_failures': 0,
            'connectivity_tests': 0,
            'connectivity_successes': 0,
            'connectivity_failures': 0,
            'skipped_urls': 0,
            'user_retries': 0,
            'user_retry_successes': 0,
            'user_decisions': {},
            'circuit_breaker_activations': 0
        }
        self.logger.info("Processing statistics reset")
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            self.logger.debug("HTTP session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()