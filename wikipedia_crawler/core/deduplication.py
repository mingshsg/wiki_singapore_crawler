"""Deduplication system for preventing duplicate URL processing."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from wikipedia_crawler.utils.logging_config import get_logger


class DeduplicationSystem:
    """
    Prevents processing duplicate URLs with fast lookup and persistence.
    
    Features:
    - Fast O(1) URL lookup using sets
    - URL normalization to catch variations
    - Thread-safe operations
    - State persistence for resumability
    - Statistics tracking
    - Memory-efficient storage
    """
    
    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize the deduplication system.
        
        Args:
            state_file: Path to file for persisting processed URLs
        """
        self.logger = get_logger(__name__)
        self.state_file = state_file or "crawler_deduplication_state.json"
        
        # Thread-safe set of processed URLs
        self._lock = threading.RLock()
        self._processed_urls: Set[str] = set()
        
        # Statistics
        self._stats = {
            'urls_processed': 0,
            'duplicates_prevented': 0,
            'last_updated': None
        }
        
        # URL normalization settings
        self._normalize_urls = True
        self._remove_fragments = True
        self._sort_query_params = True
        
        self.logger.info(f"DeduplicationSystem initialized with state file: {self.state_file}")
    
    def is_processed(self, url: str) -> bool:
        """
        Check if a URL has already been processed.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL has been processed, False otherwise
        """
        with self._lock:
            normalized_url = self._normalize_url(url) if self._normalize_urls else url
            is_duplicate = normalized_url in self._processed_urls
            
            if is_duplicate:
                self._stats['duplicates_prevented'] += 1
                self.logger.debug(f"Duplicate URL detected: {url}")
            
            return is_duplicate
    
    def mark_processed(self, url: str) -> bool:
        """
        Mark a URL as processed.
        
        Args:
            url: URL to mark as processed
            
        Returns:
            True if URL was newly marked, False if it was already processed
        """
        with self._lock:
            normalized_url = self._normalize_url(url) if self._normalize_urls else url
            
            if normalized_url in self._processed_urls:
                self._stats['duplicates_prevented'] += 1
                self.logger.debug(f"URL already processed: {url}")
                return False
            
            self._processed_urls.add(normalized_url)
            self._stats['urls_processed'] += 1
            self._stats['last_updated'] = datetime.now().isoformat()
            
            self.logger.debug(f"Marked URL as processed: {url}")
            return True
    
    def add_processed_urls(self, urls: List[str]) -> int:
        """
        Add multiple URLs as processed in batch.
        
        Args:
            urls: List of URLs to mark as processed
            
        Returns:
            Number of new URLs added (excluding duplicates)
        """
        with self._lock:
            new_count = 0
            for url in urls:
                if self.mark_processed(url):
                    new_count += 1
            
            self.logger.info(f"Batch added {new_count} new URLs out of {len(urls)} total")
            return new_count
    
    def get_processed_count(self) -> int:
        """
        Get the number of processed URLs.
        
        Returns:
            Number of processed URLs
        """
        with self._lock:
            return len(self._processed_urls)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.
        
        Returns:
            Dictionary with deduplication statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats['total_processed_urls'] = len(self._processed_urls)
            return stats
    
    def contains_pattern(self, pattern: str) -> List[str]:
        """
        Find processed URLs that contain a specific pattern.
        
        Args:
            pattern: Pattern to search for in URLs
            
        Returns:
            List of URLs containing the pattern
        """
        with self._lock:
            matching_urls = [url for url in self._processed_urls if pattern in url]
            self.logger.debug(f"Found {len(matching_urls)} URLs containing pattern: {pattern}")
            return matching_urls
    
    def save_state(self) -> None:
        """
        Save the processed URLs to file for resumability.
        """
        with self._lock:
            try:
                state_data = {
                    'processed_urls': list(self._processed_urls),
                    'stats': self._stats,
                    'settings': {
                        'normalize_urls': self._normalize_urls,
                        'remove_fragments': self._remove_fragments,
                        'sort_query_params': self._sort_query_params
                    },
                    'saved_at': datetime.now().isoformat()
                }
                
                # Save to file
                state_path = Path(self.state_file)
                state_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(state_path, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Deduplication state saved to {self.state_file} ({len(self._processed_urls)} URLs)")
                
            except Exception as e:
                self.logger.error(f"Failed to save deduplication state: {e}")
                raise
    
    def load_state(self) -> bool:
        """
        Load processed URLs from file.
        
        Returns:
            True if state was loaded successfully, False otherwise
        """
        with self._lock:
            try:
                state_path = Path(self.state_file)
                if not state_path.exists():
                    self.logger.info(f"No deduplication state file found at {self.state_file}, starting fresh")
                    return False
                
                with open(state_path, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # Load processed URLs
                self._processed_urls = set(state_data.get('processed_urls', []))
                
                # Load statistics
                self._stats = state_data.get('stats', {
                    'urls_processed': len(self._processed_urls),
                    'duplicates_prevented': 0,
                    'last_updated': None
                })
                
                # Load settings
                settings = state_data.get('settings', {})
                self._normalize_urls = settings.get('normalize_urls', True)
                self._remove_fragments = settings.get('remove_fragments', True)
                self._sort_query_params = settings.get('sort_query_params', True)
                
                saved_at = state_data.get('saved_at', 'unknown')
                self.logger.info(f"Deduplication state loaded from {self.state_file} (saved at: {saved_at})")
                self.logger.info(f"Loaded {len(self._processed_urls)} processed URLs")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to load deduplication state: {e}")
                return False
    
    def clear(self) -> None:
        """
        Clear all processed URLs and statistics.
        """
        with self._lock:
            self._processed_urls.clear()
            self._stats = {
                'urls_processed': 0,
                'duplicates_prevented': 0,
                'last_updated': None
            }
            self.logger.info("Deduplication state cleared")
    
    def get_processed_urls(self) -> List[str]:
        """
        Get list of all processed URLs.
        
        Returns:
            List of processed URLs
        """
        with self._lock:
            return list(self._processed_urls)
    
    def remove_processed_url(self, url: str) -> bool:
        """
        Remove a URL from the processed set (for testing or error recovery).
        
        Args:
            url: URL to remove
            
        Returns:
            True if URL was removed, False if it wasn't in the set
        """
        with self._lock:
            normalized_url = self._normalize_url(url) if self._normalize_urls else url
            
            if normalized_url in self._processed_urls:
                self._processed_urls.remove(normalized_url)
                self._stats['urls_processed'] = max(0, self._stats['urls_processed'] - 1)
                self.logger.debug(f"Removed URL from processed set: {url}")
                return True
            
            return False
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize a URL to catch variations that should be considered duplicates.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        try:
            # Parse the URL
            parsed = urlparse(url.strip())
            
            # Normalize scheme and netloc
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            
            # Normalize path (remove trailing slash for non-root paths)
            path = parsed.path
            if path != '/' and path.endswith('/'):
                path = path.rstrip('/')
            
            # Handle query parameters
            query = parsed.query
            if query and self._sort_query_params:
                # Parse, sort, and rebuild query string
                params = parse_qs(query, keep_blank_values=True)
                sorted_params = sorted(params.items())
                query = urlencode(sorted_params, doseq=True)
            
            # Remove fragment if configured
            fragment = '' if self._remove_fragments else parsed.fragment
            
            # Rebuild URL
            normalized = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
            
            return normalized
            
        except Exception as e:
            self.logger.warning(f"Failed to normalize URL '{url}': {e}")
            return url  # Return original URL if normalization fails
    
    def set_normalization_options(self, 
                                normalize_urls: bool = True,
                                remove_fragments: bool = True, 
                                sort_query_params: bool = True) -> None:
        """
        Configure URL normalization options.
        
        Args:
            normalize_urls: Whether to normalize URLs
            remove_fragments: Whether to remove URL fragments (#section)
            sort_query_params: Whether to sort query parameters
        """
        with self._lock:
            self._normalize_urls = normalize_urls
            self._remove_fragments = remove_fragments
            self._sort_query_params = sort_query_params
            
            self.logger.info(f"Normalization options updated: normalize={normalize_urls}, "
                           f"remove_fragments={remove_fragments}, sort_params={sort_query_params}")
    
    def get_memory_usage_estimate(self) -> Dict[str, Any]:
        """
        Get an estimate of memory usage.
        
        Returns:
            Dictionary with memory usage estimates
        """
        with self._lock:
            import sys
            
            # Estimate memory usage
            url_count = len(self._processed_urls)
            avg_url_length = sum(len(url) for url in self._processed_urls) / max(url_count, 1)
            estimated_bytes = url_count * (avg_url_length * 2 + 64)  # Rough estimate
            
            return {
                'url_count': url_count,
                'average_url_length': round(avg_url_length, 1),
                'estimated_memory_bytes': int(estimated_bytes),
                'estimated_memory_mb': round(estimated_bytes / (1024 * 1024), 2)
            }