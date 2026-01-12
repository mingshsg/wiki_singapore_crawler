"""Unit tests for ProgressTracker."""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from wikipedia_crawler.core.progress_tracker import ProgressTracker
from wikipedia_crawler.models.data_models import ProcessStatus, URLType, CrawlStatus


class TestProgressTracker:
    """Test suite for ProgressTracker."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_file = self.temp_dir / "test_progress.json"
        self.tracker = ProgressTracker(state_file=self.state_file, max_recent_urls=5)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test ProgressTracker initialization."""
        assert not self.tracker.get_status().is_running
        assert self.tracker.get_status().total_processed == 0
        assert len(self.tracker.get_progress_report().recent_urls) == 0
    
    def test_start_stop_crawling(self):
        """Test starting and stopping crawling sessions."""
        start_url = "https://en.wikipedia.org/wiki/Category:Singapore"
        
        # Start crawling
        self.tracker.start_crawling(start_url)
        status = self.tracker.get_status()
        
        assert status.is_running
        assert status.start_time is not None
        assert status.last_activity is not None
        
        # Check recent URLs contains start message
        report = self.tracker.get_progress_report()
        assert len(report.recent_urls) == 1
        assert start_url in report.recent_urls[0]
        
        # Stop crawling
        self.tracker.stop_crawling()
        status = self.tracker.get_status()
        
        assert not status.is_running
        
        # Check recent URLs contains stop message
        report = self.tracker.get_progress_report()
        assert len(report.recent_urls) == 2
        assert "Stopped crawling" in report.recent_urls[1]
    
    def test_update_progress_completed_category(self):
        """Test updating progress for completed category processing."""
        url = "https://en.wikipedia.org/wiki/Category:Singapore"
        
        self.tracker.update_progress(
            url=url,
            status=ProcessStatus.COMPLETED,
            url_type=URLType.CATEGORY
        )
        
        status = self.tracker.get_status()
        assert status.total_processed == 1
        assert status.categories_processed == 1
        assert status.articles_processed == 0
        
        # Check URL status tracking
        assert self.tracker.get_url_status(url) == ProcessStatus.COMPLETED
        
        # Check recent URLs
        report = self.tracker.get_progress_report()
        assert len(report.recent_urls) == 1
        assert url in report.recent_urls[0]
        assert "COMPLETED" in report.recent_urls[0]
    
    def test_update_progress_completed_article(self):
        """Test updating progress for completed article processing."""
        url = "https://en.wikipedia.org/wiki/Singapore"
        language = "en"
        
        self.tracker.update_progress(
            url=url,
            status=ProcessStatus.COMPLETED,
            url_type=URLType.ARTICLE,
            language=language
        )
        
        status = self.tracker.get_status()
        assert status.total_processed == 1
        assert status.categories_processed == 0
        assert status.articles_processed == 1
        
        # Check language statistics
        report = self.tracker.get_progress_report()
        assert report.language_stats[language] == 1
        
        # Check recent URLs includes language
        assert language in report.recent_urls[0]
    
    def test_update_progress_filtered(self):
        """Test updating progress for filtered content."""
        url = "https://fr.wikipedia.org/wiki/Paris"
        language = "fr"
        
        self.tracker.update_progress(
            url=url,
            status=ProcessStatus.FILTERED,
            language=language
        )
        
        status = self.tracker.get_status()
        assert status.total_processed == 1
        assert status.filtered_count == 1
        
        # Check language statistics for filtered content
        report = self.tracker.get_progress_report()
        assert report.language_stats[language] == 1
    
    def test_update_progress_error(self):
        """Test updating progress for error cases."""
        url = "https://en.wikipedia.org/wiki/NonExistent"
        error_message = "Page not found (404)"
        
        self.tracker.update_progress(
            url=url,
            status=ProcessStatus.ERROR,
            error_message=error_message
        )
        
        status = self.tracker.get_status()
        assert status.total_processed == 1
        assert status.error_count == 1
        
        # Check error categorization
        report = self.tracker.get_progress_report()
        assert "page_not_found" in report.error_summary
        assert report.error_summary["page_not_found"] == 1
        
        # Check recent URLs includes error message
        assert "ERROR" in report.recent_urls[0]
        assert error_message[:20] in report.recent_urls[0]  # Truncated error message
    
    def test_error_categorization(self):
        """Test error message categorization."""
        test_cases = [
            ("Connection timeout", "network_error"),
            ("Page not found (404)", "page_not_found"),
            ("Permission denied", "access_denied"),
            ("Content processing failed", "content_processing_error"),
            ("Failed to save file", "storage_error"),
            ("Unknown error occurred", "other_error")
        ]
        
        for i, (error_message, expected_category) in enumerate(test_cases):
            url = f"https://en.wikipedia.org/wiki/Test{i}"
            self.tracker.update_progress(
                url=url,
                status=ProcessStatus.ERROR,
                error_message=error_message
            )
        
        report = self.tracker.get_progress_report()
        for error_message, expected_category in test_cases:
            assert expected_category in report.error_summary
            assert report.error_summary[expected_category] >= 1
    
    def test_update_pending_count(self):
        """Test updating pending URL count."""
        self.tracker.update_pending_count(42)
        
        status = self.tracker.get_status()
        assert status.pending_urls == 42
    
    def test_recent_urls_limit(self):
        """Test that recent URLs are limited to max_recent_urls."""
        # Add more URLs than the limit (5)
        for i in range(10):
            url = f"https://en.wikipedia.org/wiki/Test{i}"
            self.tracker.update_progress(url, ProcessStatus.COMPLETED)
        
        report = self.tracker.get_progress_report()
        assert len(report.recent_urls) == 5  # Should be limited to max_recent_urls
        
        # Should contain the most recent URLs
        assert "Test9" in report.recent_urls[-1]
        assert "Test5" in report.recent_urls[0]
    
    def test_get_processed_urls_by_status(self):
        """Test getting URLs filtered by processing status."""
        # Add URLs with different statuses
        completed_urls = [
            "https://en.wikipedia.org/wiki/Singapore",
            "https://en.wikipedia.org/wiki/Malaysia"
        ]
        error_urls = [
            "https://en.wikipedia.org/wiki/NonExistent1",
            "https://en.wikipedia.org/wiki/NonExistent2"
        ]
        
        for url in completed_urls:
            self.tracker.update_progress(url, ProcessStatus.COMPLETED)
        
        for url in error_urls:
            self.tracker.update_progress(url, ProcessStatus.ERROR, error_message="Test error")
        
        # Test filtering
        completed_results = self.tracker.get_processed_urls_by_status(ProcessStatus.COMPLETED)
        error_results = self.tracker.get_processed_urls_by_status(ProcessStatus.ERROR)
        
        assert set(completed_results) == set(completed_urls)
        assert set(error_results) == set(error_urls)
    
    def test_save_state(self):
        """Test saving progress state to file."""
        # Set up some state
        self.tracker.start_crawling("https://en.wikipedia.org/wiki/Category:Singapore")
        self.tracker.update_progress(
            "https://en.wikipedia.org/wiki/Singapore",
            ProcessStatus.COMPLETED,
            URLType.ARTICLE,
            "en"
        )
        self.tracker.update_pending_count(10)
        
        # Save state
        self.tracker.save_state()
        
        # Verify file was created
        assert self.state_file.exists()
        
        # Verify file content
        with open(self.state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        assert 'status' in state_data
        assert 'recent_urls' in state_data
        assert 'language_stats' in state_data
        assert 'url_status' in state_data
        assert state_data['version'] == '1.0'
        
        # Check specific values
        assert state_data['status']['total_processed'] == 1
        assert state_data['status']['pending_urls'] == 10
        assert state_data['language_stats']['en'] == 1
    
    def test_load_state(self):
        """Test loading progress state from file."""
        # Create state data
        state_data = {
            'status': {
                'is_running': False,
                'total_processed': 5,
                'pending_urls': 3,
                'categories_processed': 2,
                'articles_processed': 3,
                'filtered_count': 1,
                'error_count': 1,
                'start_time': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            },
            'recent_urls': ['Test URL 1', 'Test URL 2'],
            'language_stats': {'en': 2, 'zh': 1},
            'error_summary': {'network_error': 1},
            'url_status': {
                'https://en.wikipedia.org/wiki/Test1': 'completed',
                'https://en.wikipedia.org/wiki/Test2': 'error'
            },
            'url_types': {
                'https://en.wikipedia.org/wiki/Test1': 'article'
            },
            'url_timestamps': {
                'https://en.wikipedia.org/wiki/Test1': datetime.now().isoformat()
            },
            'stats': {'total_updates': 10},
            'version': '1.0'
        }
        
        # Write state file
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f)
        
        # Load state
        result = self.tracker.load_state()
        assert result is True
        
        # Verify loaded state
        status = self.tracker.get_status()
        assert status.total_processed == 5
        assert status.pending_urls == 3
        assert status.categories_processed == 2
        assert status.articles_processed == 3
        
        report = self.tracker.get_progress_report()
        assert len(report.recent_urls) == 2
        assert report.language_stats['en'] == 2
        assert report.language_stats['zh'] == 1
        assert report.error_summary['network_error'] == 1
        
        # Check URL status tracking
        assert self.tracker.get_url_status('https://en.wikipedia.org/wiki/Test1') == ProcessStatus.COMPLETED
        assert self.tracker.get_url_status('https://en.wikipedia.org/wiki/Test2') == ProcessStatus.ERROR
    
    def test_load_state_no_file(self):
        """Test loading state when no file exists."""
        result = self.tracker.load_state()
        assert result is False
        
        # State should remain unchanged
        status = self.tracker.get_status()
        assert status.total_processed == 0
    
    def test_load_state_corrupted_file(self):
        """Test loading state from corrupted file."""
        # Write invalid JSON
        with open(self.state_file, 'w') as f:
            f.write("invalid json content")
        
        result = self.tracker.load_state()
        assert result is False
    
    def test_reset_state(self):
        """Test resetting progress state."""
        # Set up some state
        self.tracker.start_crawling("https://en.wikipedia.org/wiki/Category:Singapore")
        self.tracker.update_progress(
            "https://en.wikipedia.org/wiki/Singapore",
            ProcessStatus.COMPLETED,
            URLType.ARTICLE,
            "en"
        )
        
        # Reset state
        self.tracker.reset_state()
        
        # Verify state is reset
        status = self.tracker.get_status()
        assert not status.is_running
        assert status.total_processed == 0
        assert status.categories_processed == 0
        assert status.articles_processed == 0
        
        report = self.tracker.get_progress_report()
        assert len(report.recent_urls) == 0
        assert len(report.language_stats) == 0
        assert len(report.error_summary) == 0
    
    def test_get_stats(self):
        """Test getting internal statistics."""
        # Add some activity
        self.tracker.update_progress("https://en.wikipedia.org/wiki/Test", ProcessStatus.COMPLETED)
        self.tracker.save_state()
        
        stats = self.tracker.get_stats()
        
        assert 'total_updates' in stats
        assert 'state_saves' in stats
        assert 'tracked_urls' in stats
        assert 'recent_urls_count' in stats
        
        assert stats['total_updates'] == 1
        assert stats['state_saves'] == 1
        assert stats['tracked_urls'] == 1
    
    def test_cleanup_old_data(self):
        """Test cleaning up old URL tracking data."""
        # Add some URLs with different timestamps
        current_time = datetime.now()
        old_time = current_time - timedelta(days=10)
        
        # Mock timestamps for testing
        with patch.object(self.tracker, '_url_timestamps', {
            'https://en.wikipedia.org/wiki/Old': old_time,
            'https://en.wikipedia.org/wiki/New': current_time
        }):
            # Add corresponding status data
            self.tracker._url_status['https://en.wikipedia.org/wiki/Old'] = ProcessStatus.COMPLETED
            self.tracker._url_status['https://en.wikipedia.org/wiki/New'] = ProcessStatus.COMPLETED
            
            # Clean up data older than 7 days
            cleaned_count = self.tracker.cleanup_old_data(max_age_days=7)
            
            assert cleaned_count == 1
            assert 'https://en.wikipedia.org/wiki/Old' not in self.tracker._url_status
            assert 'https://en.wikipedia.org/wiki/New' in self.tracker._url_status
    
    def test_state_persistence_round_trip(self):
        """Test complete save/load cycle preserves state."""
        # Set up complex state
        self.tracker.start_crawling("https://en.wikipedia.org/wiki/Category:Singapore")
        
        # Add various types of progress updates
        test_data = [
            ("https://en.wikipedia.org/wiki/Singapore", ProcessStatus.COMPLETED, URLType.ARTICLE, "en"),
            ("https://en.wikipedia.org/wiki/Category:Culture", ProcessStatus.COMPLETED, URLType.CATEGORY, None),
            ("https://fr.wikipedia.org/wiki/Paris", ProcessStatus.FILTERED, None, "fr"),
            ("https://en.wikipedia.org/wiki/NotFound", ProcessStatus.ERROR, None, None)
        ]
        
        for url, status, url_type, language in test_data:
            error_msg = "Test error" if status == ProcessStatus.ERROR else None
            self.tracker.update_progress(url, status, url_type, language, error_msg)
        
        self.tracker.update_pending_count(25)
        
        # Get original state
        original_report = self.tracker.get_progress_report()
        original_status = self.tracker.get_status()
        
        # Save and create new tracker
        self.tracker.save_state()
        new_tracker = ProgressTracker(state_file=self.state_file)
        
        # Load state
        load_result = new_tracker.load_state()
        assert load_result is True
        
        # Compare states
        loaded_report = new_tracker.get_progress_report()
        loaded_status = new_tracker.get_status()
        
        # Check status
        assert loaded_status.total_processed == original_status.total_processed
        assert loaded_status.pending_urls == original_status.pending_urls
        assert loaded_status.categories_processed == original_status.categories_processed
        assert loaded_status.articles_processed == original_status.articles_processed
        assert loaded_status.filtered_count == original_status.filtered_count
        assert loaded_status.error_count == original_status.error_count
        
        # Check statistics
        assert loaded_report.language_stats == original_report.language_stats
        assert loaded_report.error_summary == original_report.error_summary
        
        # Check URL status tracking
        for url, expected_status, _, _ in test_data:
            assert new_tracker.get_url_status(url) == expected_status
    
    def test_thread_safety_basic(self):
        """Test basic thread safety of progress updates."""
        import threading
        import time
        
        def update_progress(thread_id):
            for i in range(10):
                url = f"https://en.wikipedia.org/wiki/Thread{thread_id}_URL{i}"
                self.tracker.update_progress(url, ProcessStatus.COMPLETED)
                time.sleep(0.001)  # Small delay to encourage race conditions
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_progress, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all updates were recorded
        status = self.tracker.get_status()
        assert status.total_processed == 30  # 3 threads * 10 updates each
    
    def test_progress_report_consistency(self):
        """Test that progress reports are consistent and complete."""
        # Add diverse data
        self.tracker.start_crawling("https://en.wikipedia.org/wiki/Category:Singapore")
        
        # Add different types of content
        self.tracker.update_progress(
            "https://en.wikipedia.org/wiki/Singapore",
            ProcessStatus.COMPLETED,
            URLType.ARTICLE,
            "en"
        )
        self.tracker.update_progress(
            "https://zh.wikipedia.org/wiki/新加坡",
            ProcessStatus.COMPLETED,
            URLType.ARTICLE,
            "zh"
        )
        self.tracker.update_progress(
            "https://fr.wikipedia.org/wiki/Singapour",
            ProcessStatus.FILTERED,
            URLType.ARTICLE,
            "fr"
        )
        
        report = self.tracker.get_progress_report()
        
        # Verify report structure
        assert hasattr(report, 'status')
        assert hasattr(report, 'recent_urls')
        assert hasattr(report, 'language_stats')
        assert hasattr(report, 'error_summary')
        
        # Verify data consistency
        assert report.status.total_processed == 3
        assert report.status.articles_processed == 2
        assert report.status.filtered_count == 1
        
        # Verify language stats
        assert report.language_stats['en'] == 1
        assert report.language_stats['zh'] == 1
        assert report.language_stats['fr'] == 1
        
        # Verify recent URLs
        assert len(report.recent_urls) == 4  # 3 updates + 1 start message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])