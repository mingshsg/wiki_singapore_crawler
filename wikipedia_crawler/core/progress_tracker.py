"""Progress tracking system for the Wikipedia crawler."""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

from wikipedia_crawler.models.data_models import (
    CrawlStatus, ProgressReport, ProcessStatus, URLType
)
from wikipedia_crawler.utils.logging_config import get_logger


class ProgressTracker:
    """
    Tracks crawling progress and enables resumability.
    
    Features:
    - Tracks overall progress statistics
    - Maintains recent activity history
    - Aggregates language and error statistics
    - Saves/loads crawling state for resumability
    - Provides detailed progress reporting
    - Thread-safe operations
    """
    
    def __init__(self, state_file: Optional[Path] = None, max_recent_urls: int = 100):
        """
        Initialize the progress tracker.
        
        Args:
            state_file: Path to save/load state (default: progress_state.json)
            max_recent_urls: Maximum number of recent URLs to track
        """
        self.logger = get_logger(__name__)
        self.state_file = state_file or Path("progress_state.json")
        self.max_recent_urls = max_recent_urls
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Progress tracking
        self._status = CrawlStatus(is_running=False)
        self._recent_urls = deque(maxlen=max_recent_urls)
        self._language_stats = defaultdict(int)
        self._error_summary = defaultdict(int)
        
        # URL tracking by status
        self._url_status = {}  # url -> ProcessStatus
        self._url_types = {}   # url -> URLType
        self._url_timestamps = {}  # url -> datetime
        
        # Statistics
        self._stats = {
            'total_updates': 0,
            'state_saves': 0,
            'state_loads': 0
        }
        
        self.logger.info(f"ProgressTracker initialized with state file: {self.state_file}")
    
    def start_crawling(self, start_url: str) -> None:
        """
        Mark the start of a crawling session.
        
        Args:
            start_url: The starting URL for crawling
        """
        with self._lock:
            self._status = CrawlStatus(
                is_running=True,
                start_time=datetime.now(),
                last_activity=datetime.now()
            )
            self._recent_urls.clear()
            self._recent_urls.append(f"Started crawling from: {start_url}")
            
            self.logger.info(f"Started crawling session from: {start_url}")
    
    def stop_crawling(self) -> None:
        """Mark the end of a crawling session."""
        with self._lock:
            self._status.is_running = False
            self._status.update_activity()
            self._recent_urls.append(f"Stopped crawling at: {datetime.now().isoformat()}")
            
            self.logger.info("Stopped crawling session")
    
    def update_progress(self, url: str, status: ProcessStatus, 
                       url_type: Optional[URLType] = None,
                       language: Optional[str] = None,
                       error_message: Optional[str] = None) -> None:
        """
        Update progress for a processed URL.
        
        Args:
            url: URL that was processed
            status: Processing status
            url_type: Type of URL (category or article)
            language: Detected language (if applicable)
            error_message: Error message (if status is ERROR)
        """
        with self._lock:
            current_time = datetime.now()
            
            # Update URL tracking
            self._url_status[url] = status
            self._url_timestamps[url] = current_time
            if url_type:
                self._url_types[url] = url_type
            
            # Update recent URLs
            status_text = status.value.upper()
            if language:
                status_text += f" ({language})"
            if error_message:
                status_text += f" - {error_message[:50]}..."
            
            self._recent_urls.append(f"{current_time.strftime('%H:%M:%S')} {status_text}: {url}")
            
            # Update statistics
            self._status.total_processed += 1
            self._status.update_activity()
            
            if status == ProcessStatus.COMPLETED:
                if url_type == URLType.CATEGORY:
                    self._status.categories_processed += 1
                elif url_type == URLType.ARTICLE:
                    self._status.articles_processed += 1
                    
                # Track language statistics for articles
                if language and url_type == URLType.ARTICLE:
                    self._language_stats[language] += 1
                    
            elif status == ProcessStatus.FILTERED:
                self._status.filtered_count += 1
                if language:
                    self._language_stats[language] += 1
                    
            elif status == ProcessStatus.ERROR:
                self._status.error_count += 1
                if error_message:
                    # Categorize errors by type
                    error_type = self._categorize_error(error_message)
                    self._error_summary[error_type] += 1
            
            self._stats['total_updates'] += 1
            
            self.logger.debug(f"Updated progress: {url} -> {status.value}")
    
    def update_pending_count(self, pending_count: int) -> None:
        """
        Update the count of pending URLs.
        
        Args:
            pending_count: Number of URLs pending processing
        """
        with self._lock:
            self._status.pending_urls = pending_count
            self._status.update_activity()
    
    def get_progress_report(self) -> ProgressReport:
        """
        Get a detailed progress report.
        
        Returns:
            ProgressReport with current status and statistics
        """
        with self._lock:
            return ProgressReport(
                status=CrawlStatus(
                    is_running=self._status.is_running,
                    total_processed=self._status.total_processed,
                    pending_urls=self._status.pending_urls,
                    categories_processed=self._status.categories_processed,
                    articles_processed=self._status.articles_processed,
                    filtered_count=self._status.filtered_count,
                    error_count=self._status.error_count,
                    start_time=self._status.start_time,
                    last_activity=self._status.last_activity
                ),
                recent_urls=list(self._recent_urls),
                language_stats=dict(self._language_stats),
                error_summary=dict(self._error_summary)
            )
    
    def get_status(self) -> CrawlStatus:
        """
        Get current crawl status.
        
        Returns:
            Current CrawlStatus
        """
        with self._lock:
            return CrawlStatus(
                is_running=self._status.is_running,
                total_processed=self._status.total_processed,
                pending_urls=self._status.pending_urls,
                categories_processed=self._status.categories_processed,
                articles_processed=self._status.articles_processed,
                filtered_count=self._status.filtered_count,
                error_count=self._status.error_count,
                start_time=self._status.start_time,
                last_activity=self._status.last_activity
            )
    
    def get_url_status(self, url: str) -> Optional[ProcessStatus]:
        """
        Get the processing status of a specific URL.
        
        Args:
            url: URL to check
            
        Returns:
            ProcessStatus if URL has been processed, None otherwise
        """
        with self._lock:
            return self._url_status.get(url)
    
    def get_processed_urls_by_status(self, status: ProcessStatus) -> List[str]:
        """
        Get all URLs with a specific processing status.
        
        Args:
            status: ProcessStatus to filter by
            
        Returns:
            List of URLs with the specified status
        """
        with self._lock:
            return [url for url, url_status in self._url_status.items() 
                   if url_status == status]
    
    def save_state(self) -> None:
        """Save current progress state to file."""
        try:
            with self._lock:
                state_data = {
                    'status': self._status.to_dict(),
                    'recent_urls': list(self._recent_urls),
                    'language_stats': dict(self._language_stats),
                    'error_summary': dict(self._error_summary),
                    'url_status': {url: status.value for url, status in self._url_status.items()},
                    'url_types': {url: url_type.value for url, url_type in self._url_types.items()},
                    'url_timestamps': {url: ts.isoformat() for url, ts in self._url_timestamps.items()},
                    'stats': self._stats.copy(),
                    'saved_at': datetime.now().isoformat(),
                    'version': '1.0'
                }
            
            # Atomic write
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.state_file)
            
            with self._lock:
                self._stats['state_saves'] += 1
            
            self.logger.info(f"Saved progress state to {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save progress state: {e}")
            raise
    
    def load_state(self) -> bool:
        """
        Load progress state from file.
        
        Returns:
            True if state was loaded successfully, False otherwise
        """
        if not self.state_file.exists():
            self.logger.info("No existing state file found")
            return False
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            with self._lock:
                # Load status
                status_data = state_data.get('status', {})
                self._status = CrawlStatus(
                    is_running=status_data.get('is_running', False),
                    total_processed=status_data.get('total_processed', 0),
                    pending_urls=status_data.get('pending_urls', 0),
                    categories_processed=status_data.get('categories_processed', 0),
                    articles_processed=status_data.get('articles_processed', 0),
                    filtered_count=status_data.get('filtered_count', 0),
                    error_count=status_data.get('error_count', 0),
                    start_time=datetime.fromisoformat(status_data.get('start_time', datetime.now().isoformat())),
                    last_activity=datetime.fromisoformat(status_data.get('last_activity', datetime.now().isoformat()))
                )
                
                # Load recent URLs
                self._recent_urls.clear()
                for url in state_data.get('recent_urls', []):
                    self._recent_urls.append(url)
                
                # Load statistics
                self._language_stats.clear()
                self._language_stats.update(state_data.get('language_stats', {}))
                
                self._error_summary.clear()
                self._error_summary.update(state_data.get('error_summary', {}))
                
                # Load URL tracking
                self._url_status.clear()
                for url, status_str in state_data.get('url_status', {}).items():
                    self._url_status[url] = ProcessStatus(status_str)
                
                self._url_types.clear()
                for url, type_str in state_data.get('url_types', {}).items():
                    self._url_types[url] = URLType(type_str)
                
                self._url_timestamps.clear()
                for url, ts_str in state_data.get('url_timestamps', {}).items():
                    self._url_timestamps[url] = datetime.fromisoformat(ts_str)
                
                # Load internal stats
                self._stats.update(state_data.get('stats', {}))
                self._stats['state_loads'] += 1
            
            self.logger.info(f"Loaded progress state from {self.state_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load progress state: {e}")
            return False
    
    def reset_state(self) -> None:
        """Reset all progress tracking to initial state."""
        with self._lock:
            self._status = CrawlStatus(is_running=False)
            self._recent_urls.clear()
            self._language_stats.clear()
            self._error_summary.clear()
            self._url_status.clear()
            self._url_types.clear()
            self._url_timestamps.clear()
            
            # Reset stats but keep load/save counts
            saves = self._stats.get('state_saves', 0)
            loads = self._stats.get('state_loads', 0)
            self._stats = {
                'total_updates': 0,
                'state_saves': saves,
                'state_loads': loads
            }
        
        self.logger.info("Reset progress state")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get internal statistics.
        
        Returns:
            Dictionary with internal statistics
        """
        with self._lock:
            return {
                **self._stats,
                'tracked_urls': len(self._url_status),
                'recent_urls_count': len(self._recent_urls),
                'language_types': len(self._language_stats),
                'error_types': len(self._error_summary)
            }
    
    def _categorize_error(self, error_message: str) -> str:
        """
        Categorize error messages into types.
        
        Args:
            error_message: Error message to categorize
            
        Returns:
            Error category string
        """
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'connection' in error_lower:
            return 'network_error'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'page_not_found'
        elif 'permission' in error_lower or 'forbidden' in error_lower:
            return 'access_denied'
        elif 'content' in error_lower or 'processing' in error_lower:
            return 'content_processing_error'
        elif 'save' in error_lower or 'storage' in error_lower:
            return 'storage_error'
        else:
            return 'other_error'
    
    def cleanup_old_data(self, max_age_days: int = 7) -> int:
        """
        Clean up old URL tracking data.
        
        Args:
            max_age_days: Maximum age in days for URL data
            
        Returns:
            Number of URLs cleaned up
        """
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        cleaned_count = 0
        
        with self._lock:
            urls_to_remove = []
            for url, timestamp in self._url_timestamps.items():
                if timestamp.timestamp() < cutoff_time:
                    urls_to_remove.append(url)
            
            for url in urls_to_remove:
                self._url_status.pop(url, None)
                self._url_types.pop(url, None)
                self._url_timestamps.pop(url, None)
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old URL records")
        
        return cleaned_count