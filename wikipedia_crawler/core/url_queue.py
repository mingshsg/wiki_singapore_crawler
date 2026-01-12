"""URL queue management for Wikipedia crawler."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, Dict, Any, List
from queue import PriorityQueue
from dataclasses import dataclass, asdict
from enum import Enum

from wikipedia_crawler.models.data_models import URLItem, URLType
from wikipedia_crawler.utils.logging_config import get_logger


class URLQueueManager:
    """
    Manages the queue of URLs to be processed with priority ordering and persistence.
    
    Features:
    - Priority-based URL processing (categories before articles)
    - Thread-safe operations
    - State persistence for resumability
    - Automatic deduplication
    - Statistics tracking
    """
    
    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize the URL queue manager.
        
        Args:
            state_file: Path to file for persisting queue state
        """
        self.logger = get_logger(__name__)
        self.state_file = state_file or "crawler_queue_state.json"
        
        # Thread-safe priority queue
        self._queue = PriorityQueue()
        self._lock = threading.RLock()
        
        # Track URLs to prevent duplicates
        self._pending_urls: Set[str] = set()
        self._completed_urls: Set[str] = set()
        
        # Statistics
        self._stats = {
            'urls_added': 0,
            'urls_completed': 0,
            'categories_pending': 0,
            'articles_pending': 0
        }
        
        # Priority mapping for URL types
        self._priority_map = {
            URLType.CATEGORY: 1,  # Higher priority (processed first)
            URLType.ARTICLE: 2    # Lower priority
        }
        
        self.logger.info(f"URLQueueManager initialized with state file: {self.state_file}")
    
    def add_url(self, url: str, url_type: URLType, depth: int = 0) -> bool:
        """
        Add a URL to the processing queue.
        
        Args:
            url: URL to add
            url_type: Type of URL (category or article)
            depth: Crawling depth for this URL
            
        Returns:
            True if URL was added, False if it was already present
        """
        with self._lock:
            # Check for duplicates
            if url in self._pending_urls or url in self._completed_urls:
                self.logger.debug(f"URL already processed or pending: {url}")
                return False
            
            # Create URL item with priority
            priority = self._priority_map.get(url_type, 999)
            url_item = URLItem(
                url=url,
                url_type=url_type,
                priority=priority,
                depth=depth,
                discovered_at=datetime.now()
            )
            
            # Add to queue and tracking sets
            self._queue.put((priority, url, url_item))
            self._pending_urls.add(url)
            
            # Update statistics
            self._stats['urls_added'] += 1
            if url_type == URLType.CATEGORY:
                self._stats['categories_pending'] += 1
            else:
                self._stats['articles_pending'] += 1
            
            self.logger.debug(f"Added {url_type.value} URL to queue: {url} (depth: {depth})")
            return True
    
    def get_next_url(self) -> Optional[URLItem]:
        """
        Get the next URL to process from the queue.
        
        Returns:
            Next URLItem to process, or None if queue is empty
        """
        with self._lock:
            if self._queue.empty():
                return None
            
            try:
                priority, url, url_item = self._queue.get_nowait()
                
                # Remove from pending set (will be added to completed when marked)
                self._pending_urls.discard(url)
                
                # Update statistics
                if url_item.url_type == URLType.CATEGORY:
                    self._stats['categories_pending'] -= 1
                else:
                    self._stats['articles_pending'] -= 1
                
                self.logger.debug(f"Retrieved URL from queue: {url}")
                return url_item
                
            except Exception as e:
                self.logger.error(f"Error retrieving URL from queue: {e}")
                return None
    
    def mark_completed(self, url: str) -> None:
        """
        Mark a URL as completed.
        
        Args:
            url: URL that has been processed
        """
        with self._lock:
            self._completed_urls.add(url)
            self._pending_urls.discard(url)  # Remove if still pending
            self._stats['urls_completed'] += 1
            
            self.logger.debug(f"Marked URL as completed: {url}")
    
    def is_processed(self, url: str) -> bool:
        """
        Check if a URL has already been processed or is pending.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is processed or pending, False otherwise
        """
        with self._lock:
            return url in self._completed_urls or url in self._pending_urls
    
    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            True if queue is empty, False otherwise
        """
        with self._lock:
            return self._queue.empty()
    
    def size(self) -> int:
        """
        Get the current size of the queue.
        
        Returns:
            Number of URLs in the queue
        """
        with self._lock:
            return self._queue.qsize()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                'queue_size': self._queue.qsize(),
                'pending_urls': len(self._pending_urls),
                'completed_urls': len(self._completed_urls),
                'total_discovered': len(self._pending_urls) + len(self._completed_urls)
            })
            return stats
    
    def save_state(self) -> None:
        """
        Save the current queue state to file for resumability.
        """
        with self._lock:
            try:
                # Extract all items from queue to save them
                queue_items = []
                temp_items = []
                
                # Get all items from queue
                while not self._queue.empty():
                    item = self._queue.get_nowait()
                    temp_items.append(item)
                    priority, url, url_item = item
                    
                    # Convert URLItem to dict with enum serialization
                    url_item_dict = asdict(url_item)
                    url_item_dict['url_type'] = url_item.url_type.value  # Convert enum to string
                    url_item_dict['discovered_at'] = url_item.discovered_at.isoformat()  # Convert datetime to string
                    
                    queue_items.append({
                        'priority': priority,
                        'url': url,
                        'url_item': url_item_dict
                    })
                
                # Restore items to queue
                for item in temp_items:
                    self._queue.put(item)
                
                # Prepare state data
                state_data = {
                    'queue_items': queue_items,
                    'pending_urls': list(self._pending_urls),
                    'completed_urls': list(self._completed_urls),
                    'stats': self._stats,
                    'saved_at': datetime.now().isoformat()
                }
                
                # Save to file
                state_path = Path(self.state_file)
                state_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(state_path, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Queue state saved to {self.state_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to save queue state: {e}")
                raise
    
    def load_state(self) -> bool:
        """
        Load queue state from file.
        
        Returns:
            True if state was loaded successfully, False otherwise
        """
        with self._lock:
            try:
                state_path = Path(self.state_file)
                if not state_path.exists():
                    self.logger.info(f"No state file found at {self.state_file}, starting fresh")
                    return False
                
                with open(state_path, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # Clear current state
                while not self._queue.empty():
                    self._queue.get_nowait()
                self._pending_urls.clear()
                self._completed_urls.clear()
                
                # Restore queue items
                for item_data in state_data.get('queue_items', []):
                    priority = item_data['priority']
                    url = item_data['url']
                    url_item_data = item_data['url_item']
                    
                    # Reconstruct URLItem
                    url_item_data['discovered_at'] = datetime.fromisoformat(url_item_data['discovered_at'])
                    url_item_data['url_type'] = URLType(url_item_data['url_type'])
                    url_item = URLItem(**url_item_data)
                    
                    self._queue.put((priority, url, url_item))
                
                # Restore tracking sets
                self._pending_urls = set(state_data.get('pending_urls', []))
                self._completed_urls = set(state_data.get('completed_urls', []))
                
                # Restore statistics
                self._stats = state_data.get('stats', {
                    'urls_added': 0,
                    'urls_completed': 0,
                    'categories_pending': 0,
                    'articles_pending': 0
                })
                
                saved_at = state_data.get('saved_at', 'unknown')
                self.logger.info(f"Queue state loaded from {self.state_file} (saved at: {saved_at})")
                self.logger.info(f"Restored {self._queue.qsize()} pending URLs, {len(self._completed_urls)} completed URLs")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to load queue state: {e}")
                return False
    
    def clear(self) -> None:
        """
        Clear all queue data and statistics.
        """
        with self._lock:
            # Clear queue
            while not self._queue.empty():
                self._queue.get_nowait()
            
            # Clear tracking sets
            self._pending_urls.clear()
            self._completed_urls.clear()
            
            # Reset statistics
            self._stats = {
                'urls_added': 0,
                'urls_completed': 0,
                'categories_pending': 0,
                'articles_pending': 0
            }
            
            self.logger.info("Queue cleared")
    
    def get_pending_urls(self) -> List[str]:
        """
        Get list of all pending URLs.
        
        Returns:
            List of pending URLs
        """
        with self._lock:
            return list(self._pending_urls)
    
    def get_completed_urls(self) -> List[str]:
        """
        Get list of all completed URLs.
        
        Returns:
            List of completed URLs
        """
        with self._lock:
            return list(self._completed_urls)