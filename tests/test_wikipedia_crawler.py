"""Tests for the main WikipediaCrawler class."""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from wikipedia_crawler.core.wikipedia_crawler import WikipediaCrawler
from wikipedia_crawler.models.data_models import URLType, ProcessStatus


class TestWikipediaCrawler:
    """Test cases for WikipediaCrawler class."""
    
    def test_initialization_valid_url(self):
        """Test crawler initialization with valid Wikipedia URL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir,
                max_depth=3
            )
            
            assert crawler.start_url == "https://en.wikipedia.org/wiki/Category:Singapore"
            assert crawler.output_dir == Path(temp_dir)
            assert crawler.max_depth == 3
            assert not crawler._running
            assert not crawler._shutdown_requested
    
    def test_initialization_invalid_url(self):
        """Test crawler initialization with invalid URL raises ValueError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Invalid Wikipedia URL"):
                WikipediaCrawler(
                    start_url="https://example.com/invalid",
                    output_dir=temp_dir
                )
    
    def test_components_initialization(self):
        """Test that all components are properly initialized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Check that all components exist
            assert crawler.url_queue is not None
            assert crawler.deduplication is not None
            assert crawler.progress_tracker is not None
            assert crawler.file_storage is not None
            assert crawler.page_processor is not None
            assert crawler.content_processor is not None
            assert crawler.language_filter is not None
            assert crawler.category_handler is not None
            assert crawler.article_handler is not None
    
    def test_output_directory_creation(self):
        """Test that output directory is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"
            
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=str(output_dir)
            )
            
            assert output_dir.exists()
            assert output_dir.is_dir()
            
            # Check state directory is created
            state_dir = output_dir / "state"
            assert state_dir.exists()
    
    def test_get_status_initial(self):
        """Test getting initial crawler status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            status = crawler.get_status()
            assert not status.is_running
            assert status.total_processed == 0
            assert status.pending_urls == 0
            assert status.categories_processed == 0
            assert status.articles_processed == 0
            assert status.filtered_count == 0
            assert status.error_count == 0
    
    def test_get_detailed_stats(self):
        """Test getting detailed statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            stats = crawler.get_detailed_stats()
            
            # Check that all component stats are included
            assert 'crawler' in stats
            assert 'queue' in stats
            assert 'deduplication' in stats
            assert 'progress' in stats
            assert 'page_processor' in stats
            assert 'category_handler' in stats
            assert 'article_handler' in stats
            assert 'language_filter' in stats
            
            # Check crawler-specific stats
            assert 'running' in stats['crawler']
            assert 'shutdown_requested' in stats['crawler']
            assert 'session_stats' in stats['crawler']
    
    @patch('wikipedia_crawler.core.wikipedia_crawler.WikipediaCrawler._crawl_loop')
    def test_start_stop_crawling(self, mock_crawl_loop):
        """Test starting and stopping the crawler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Mock the crawl loop to avoid actual crawling
            mock_crawl_loop.return_value = None
            
            # Start crawling
            crawler.start_crawling()
            assert crawler._running
            assert not crawler._shutdown_requested
            assert crawler._crawl_thread is not None
            
            # Give thread a moment to start
            time.sleep(0.1)
            
            # Stop crawling
            crawler.stop_crawling()
            assert not crawler._running
            assert crawler._crawl_thread is None
    
    def test_start_crawling_already_running(self):
        """Test starting crawler when already running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Simulate already running
            crawler._running = True
            
            # Should not start again
            crawler.start_crawling()
            assert crawler._crawl_thread is None
    
    def test_stop_crawling_not_running(self):
        """Test stopping crawler when not running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Should handle gracefully
            crawler.stop_crawling()
            assert not crawler._running
    
    def test_url_validation(self):
        """Test URL validation logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Valid URLs
            assert crawler._is_valid_wikipedia_url("https://en.wikipedia.org/wiki/Singapore")
            assert crawler._is_valid_wikipedia_url("https://zh.wikipedia.org/wiki/Category:Singapore")
            
            # Invalid URLs
            assert not crawler._is_valid_wikipedia_url("http://example.com")
            assert not crawler._is_valid_wikipedia_url("https://example.com/wiki/Test")
            assert not crawler._is_valid_wikipedia_url("https://en.wikipedia.org/")
            assert not crawler._is_valid_wikipedia_url("invalid-url")
    
    @patch('wikipedia_crawler.core.page_processor.PageProcessor.process_page')
    def test_process_url_category(self, mock_process_page):
        """Test processing a category URL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Mock successful page processing
            mock_result = Mock()
            mock_result.success = True
            mock_result.content = "<html><body>Test category content</body></html>"
            mock_result.page_type = "category"
            mock_process_page.return_value = mock_result
            
            # Mock category handler
            with patch.object(crawler.category_handler, 'process_category') as mock_category:
                mock_category_result = Mock()
                mock_category_result.success = True
                mock_category_result.discovered_urls = ["https://en.wikipedia.org/wiki/Test_Article"]
                mock_category.return_value = mock_category_result
                
                # Create URL item
                from wikipedia_crawler.models.data_models import URLItem
                url_item = URLItem(
                    url="https://en.wikipedia.org/wiki/Category:Test",
                    url_type=URLType.CATEGORY,
                    priority=1,
                    depth=0
                )
                
                # Process the URL
                crawler._process_url(url_item)
                
                # Verify calls
                mock_process_page.assert_called_once()
                mock_category.assert_called_once()
    
    @patch('wikipedia_crawler.core.page_processor.PageProcessor.process_page')
    def test_process_url_article(self, mock_process_page):
        """Test processing an article URL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Mock successful page processing
            mock_result = Mock()
            mock_result.success = True
            mock_result.content = "<html><body>Test article content</body></html>"
            mock_result.page_type = "article"
            mock_process_page.return_value = mock_result
            
            # Mock article handler
            with patch.object(crawler.article_handler, 'process_article') as mock_article:
                mock_article_result = Mock()
                mock_article_result.success = True
                mock_article_result.data = {'language': 'en', 'filtered': False}
                mock_article.return_value = mock_article_result
                
                # Create URL item
                from wikipedia_crawler.models.data_models import URLItem
                url_item = URLItem(
                    url="https://en.wikipedia.org/wiki/Test_Article",
                    url_type=URLType.ARTICLE,
                    priority=2,
                    depth=1
                )
                
                # Process the URL
                crawler._process_url(url_item)
                
                # Verify calls
                mock_process_page.assert_called_once()
                mock_article.assert_called_once()
    
    def test_context_manager(self):
        """Test using crawler as context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            ) as crawler:
                assert crawler is not None
                assert not crawler._running
            
            # Should be properly cleaned up
            assert not crawler._running
    
    def test_state_management(self):
        """Test state saving and loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Singapore",
                output_dir=temp_dir
            )
            
            # Mock component state methods
            with patch.object(crawler.url_queue, 'save_state') as mock_queue_save, \
                 patch.object(crawler.deduplication, 'save_state') as mock_dedup_save, \
                 patch.object(crawler.progress_tracker, 'save_state') as mock_progress_save, \
                 patch.object(crawler.url_queue, 'load_state') as mock_queue_load, \
                 patch.object(crawler.deduplication, 'load_state') as mock_dedup_load, \
                 patch.object(crawler.progress_tracker, 'load_state') as mock_progress_load:
                
                # Configure return values
                mock_queue_load.return_value = True
                mock_dedup_load.return_value = True
                mock_progress_load.return_value = True
                
                # Test state loading
                crawler._load_state()
                
                mock_queue_load.assert_called_once()
                mock_dedup_load.assert_called_once()
                mock_progress_load.assert_called_once()
                
                # Test state saving
                crawler._save_state()
                
                mock_queue_save.assert_called_once()
                mock_dedup_save.assert_called_once()
                mock_progress_save.assert_called_once()