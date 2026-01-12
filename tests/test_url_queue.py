"""Property-based tests for URL queue management."""

import tempfile
import os
from datetime import datetime
from pathlib import Path
from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest

from wikipedia_crawler.core.url_queue import URLQueueManager
from wikipedia_crawler.models.data_models import URLItem, URLType


# Custom strategies for generating test data
@composite
def wikipedia_url(draw):
    """Generate Wikipedia URLs."""
    domains = ['en.wikipedia.org', 'zh.wikipedia.org', 'zh-cn.wikipedia.org']
    domain = draw(st.sampled_from(domains))
    
    # Generate article/category name
    name = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-',
        min_size=1, max_size=50
    ))
    
    return f"https://{domain}/wiki/{name}"


@composite
def wikipedia_category_url(draw):
    """Generate Wikipedia category URLs."""
    domains = ['en.wikipedia.org', 'zh.wikipedia.org', 'zh-cn.wikipedia.org']
    domain = draw(st.sampled_from(domains))
    
    # Generate category name
    name = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-',
        min_size=1, max_size=50
    ))
    
    return f"https://{domain}/wiki/Category:{name}"


@composite
def url_with_type(draw):
    """Generate URL with corresponding URLType."""
    url_type = draw(st.sampled_from([URLType.CATEGORY, URLType.ARTICLE]))
    
    if url_type == URLType.CATEGORY:
        url = draw(wikipedia_category_url())
    else:
        url = draw(wikipedia_url())
    
    depth = draw(st.integers(min_value=0, max_value=10))
    
    return url, url_type, depth


class TestURLQueueManagement:
    """Test URL queue management properties."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_queue_state.json")
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @given(
        urls_and_types=st.lists(url_with_type(), min_size=1, max_size=20, unique_by=lambda x: x[0])
    )
    def test_queue_management_consistency(self, urls_and_types):
        """
        Property 6: Queue Management Consistency
        For any discovered Wikipedia URL, adding it to the processing queue and then 
        retrieving it should preserve the URL and its metadata, with proper deduplication 
        preventing duplicate entries.
        **Feature: wikipedia-singapore-crawler, Property 6: Queue Management Consistency**
        **Validates: Requirements 3.1, 4.1, 4.2**
        """
        queue_manager = URLQueueManager(self.state_file)
        
        # Add all URLs to queue
        added_urls = []
        for url, url_type, depth in urls_and_types:
            was_added = queue_manager.add_url(url, url_type, depth)
            if was_added:
                added_urls.append((url, url_type, depth))
        
        # All unique URLs should have been added
        assert len(added_urls) == len(urls_and_types), "All unique URLs should be added"
        
        # Retrieve URLs and verify they match what was added
        retrieved_urls = []
        while not queue_manager.is_empty():
            url_item = queue_manager.get_next_url()
            assert url_item is not None, "Should retrieve valid URLItem"
            retrieved_urls.append((url_item.url, url_item.url_type, url_item.depth))
        
        # Should retrieve same number of URLs
        assert len(retrieved_urls) == len(added_urls), "Should retrieve same number of URLs as added"
        
        # All added URLs should be retrievable (order may differ due to priority)
        added_set = set(added_urls)
        retrieved_set = set(retrieved_urls)
        assert retrieved_set == added_set, "Retrieved URLs should match added URLs"
    
    @given(
        url_data=url_with_type(),
        duplicate_attempts=st.integers(min_value=1, max_value=5)
    )
    def test_queue_deduplication_prevention(self, url_data, duplicate_attempts):
        """
        Property 6: Queue Management Consistency - Deduplication
        For any URL, attempting to add it multiple times should only result in 
        one entry in the queue.
        **Feature: wikipedia-singapore-crawler, Property 6: Queue Management Consistency**
        **Validates: Requirements 3.1, 4.1, 4.2**
        """
        queue_manager = URLQueueManager(self.state_file)
        url, url_type, depth = url_data
        
        # Attempt to add the same URL multiple times
        add_results = []
        for _ in range(duplicate_attempts):
            result = queue_manager.add_url(url, url_type, depth)
            add_results.append(result)
        
        # Only the first addition should succeed
        assert add_results[0] == True, "First addition should succeed"
        assert all(result == False for result in add_results[1:]), "Subsequent additions should fail"
        
        # Queue should contain exactly one item
        assert queue_manager.size() == 1, "Queue should contain exactly one item"
        
        # Should be able to retrieve the URL once
        url_item = queue_manager.get_next_url()
        assert url_item is not None, "Should retrieve the URL"
        assert url_item.url == url, "Retrieved URL should match added URL"
        
        # Queue should now be empty
        assert queue_manager.is_empty(), "Queue should be empty after retrieval"
        assert queue_manager.get_next_url() is None, "Should not retrieve any more URLs"
    
    @given(
        category_urls=st.lists(
            st.tuples(wikipedia_category_url(), st.just(URLType.CATEGORY), st.integers(0, 5)),
            min_size=1, max_size=10, unique_by=lambda x: x[0]
        ),
        article_urls=st.lists(
            st.tuples(wikipedia_url(), st.just(URLType.ARTICLE), st.integers(0, 5)),
            min_size=1, max_size=10, unique_by=lambda x: x[0]
        )
    )
    def test_queue_priority_ordering(self, category_urls, article_urls):
        """
        Property 6: Queue Management Consistency - Priority ordering
        For any mix of category and article URLs, categories should be processed 
        before articles due to priority ordering.
        **Feature: wikipedia-singapore-crawler, Property 6: Queue Management Consistency**
        **Validates: Requirements 3.1, 4.1, 4.2**
        """
        queue_manager = URLQueueManager(self.state_file)
        
        # Add articles first, then categories (reverse priority order)
        for url, url_type, depth in article_urls:
            queue_manager.add_url(url, url_type, depth)
        
        for url, url_type, depth in category_urls:
            queue_manager.add_url(url, url_type, depth)
        
        # Retrieve all URLs and check that categories come first
        retrieved_types = []
        while not queue_manager.is_empty():
            url_item = queue_manager.get_next_url()
            retrieved_types.append(url_item.url_type)
        
        # Find the last category and first article
        last_category_index = -1
        first_article_index = len(retrieved_types)
        
        for i, url_type in enumerate(retrieved_types):
            if url_type == URLType.CATEGORY:
                last_category_index = i
            elif url_type == URLType.ARTICLE and first_article_index == len(retrieved_types):
                first_article_index = i
        
        # All categories should come before all articles
        if last_category_index >= 0 and first_article_index < len(retrieved_types):
            assert last_category_index < first_article_index, "Categories should be processed before articles"
    
    @given(
        urls_and_types=st.lists(url_with_type(), min_size=1, max_size=15, unique_by=lambda x: x[0])
    )
    def test_queue_completion_tracking(self, urls_and_types):
        """
        Property 6: Queue Management Consistency - Completion tracking
        For any set of URLs, marking them as completed should prevent them from 
        being processed again and update statistics correctly.
        **Feature: wikipedia-singapore-crawler, Property 6: Queue Management Consistency**
        **Validates: Requirements 3.1, 4.1, 4.2**
        """
        queue_manager = URLQueueManager(self.state_file)
        
        # Add URLs to queue
        added_urls = []
        for url, url_type, depth in urls_and_types:
            if queue_manager.add_url(url, url_type, depth):
                added_urls.append(url)
        
        initial_stats = queue_manager.get_stats()
        
        # Process and mark URLs as completed
        completed_urls = []
        while not queue_manager.is_empty():
            url_item = queue_manager.get_next_url()
            queue_manager.mark_completed(url_item.url)
            completed_urls.append(url_item.url)
        
        # Check final statistics
        final_stats = queue_manager.get_stats()
        
        # All URLs should be marked as completed
        assert final_stats['urls_completed'] == len(added_urls), "All URLs should be marked as completed"
        assert final_stats['completed_urls'] == len(added_urls), "Completed count should match"
        
        # Attempting to add the same URLs again should fail (they're completed)
        for url, url_type, depth in urls_and_types:
            if url in completed_urls:
                was_added = queue_manager.add_url(url, url_type, depth)
                assert not was_added, f"Completed URL should not be added again: {url}"
    
    @given(
        urls_and_types=st.lists(url_with_type(), min_size=1, max_size=10, unique_by=lambda x: x[0])
    )
    def test_queue_statistics_accuracy(self, urls_and_types):
        """
        Property 6: Queue Management Consistency - Statistics accuracy
        For any sequence of queue operations, statistics should accurately reflect 
        the current state.
        **Feature: wikipedia-singapore-crawler, Property 6: Queue Management Consistency**
        **Validates: Requirements 3.1, 4.1, 4.2**
        """
        queue_manager = URLQueueManager(self.state_file)
        
        # Track expected statistics
        expected_categories = 0
        expected_articles = 0
        expected_added = 0
        
        # Add URLs and track expectations
        for url, url_type, depth in urls_and_types:
            was_added = queue_manager.add_url(url, url_type, depth)
            if was_added:
                expected_added += 1
                if url_type == URLType.CATEGORY:
                    expected_categories += 1
                else:
                    expected_articles += 1
        
        # Check statistics after adding
        stats = queue_manager.get_stats()
        assert stats['urls_added'] == expected_added, "Added count should be accurate"
        assert stats['categories_pending'] == expected_categories, "Category count should be accurate"
        assert stats['articles_pending'] == expected_articles, "Article count should be accurate"
        assert stats['queue_size'] == expected_added, "Queue size should match added count"
        
        # Process half the URLs
        processed_count = 0
        target_process = max(1, expected_added // 2)
        
        while not queue_manager.is_empty() and processed_count < target_process:
            url_item = queue_manager.get_next_url()
            queue_manager.mark_completed(url_item.url)
            processed_count += 1
            
            if url_item.url_type == URLType.CATEGORY:
                expected_categories -= 1
            else:
                expected_articles -= 1
        
        # Check statistics after partial processing
        stats = queue_manager.get_stats()
        assert stats['urls_completed'] == processed_count, "Completed count should be accurate"
        assert stats['categories_pending'] == expected_categories, "Remaining category count should be accurate"
        assert stats['articles_pending'] == expected_articles, "Remaining article count should be accurate"
        assert stats['queue_size'] == expected_added - processed_count, "Queue size should reflect processed URLs"
    
    @given(
        urls_and_types=st.lists(url_with_type(), min_size=1, max_size=8, unique_by=lambda x: x[0])
    )
    def test_queue_thread_safety_basic(self, urls_and_types):
        """
        Property 6: Queue Management Consistency - Thread safety
        For any set of URLs, concurrent operations should maintain consistency.
        **Feature: wikipedia-singapore-crawler, Property 6: Queue Management Consistency**
        **Validates: Requirements 3.1, 4.1, 4.2**
        """
        import threading
        import time
        
        queue_manager = URLQueueManager(self.state_file)
        results = {'added': [], 'retrieved': [], 'errors': []}
        
        def add_urls():
            try:
                for url, url_type, depth in urls_and_types:
                    result = queue_manager.add_url(url, url_type, depth)
                    results['added'].append((url, result))
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                results['errors'].append(f"Add error: {e}")
        
        def retrieve_urls():
            try:
                time.sleep(0.005)  # Let some URLs be added first
                while True:
                    url_item = queue_manager.get_next_url()
                    if url_item is None:
                        break
                    results['retrieved'].append(url_item.url)
                    time.sleep(0.001)
            except Exception as e:
                results['errors'].append(f"Retrieve error: {e}")
        
        # Run concurrent operations
        add_thread = threading.Thread(target=add_urls)
        retrieve_thread = threading.Thread(target=retrieve_urls)
        
        add_thread.start()
        retrieve_thread.start()
        
        add_thread.join(timeout=5.0)
        retrieve_thread.join(timeout=5.0)
        
        # Check for errors
        assert len(results['errors']) == 0, f"Thread safety errors: {results['errors']}"
        
        # Check that operations completed successfully
        successful_adds = sum(1 for _, success in results['added'] if success)
        assert len(results['retrieved']) <= successful_adds, "Should not retrieve more URLs than successfully added"
    
    def test_queue_empty_operations(self):
        """Test queue behavior when empty."""
        queue_manager = URLQueueManager(self.state_file)
        
        # Empty queue operations
        assert queue_manager.is_empty(), "New queue should be empty"
        assert queue_manager.size() == 0, "New queue should have size 0"
        assert queue_manager.get_next_url() is None, "Empty queue should return None"
        
        # Statistics should be zero
        stats = queue_manager.get_stats()
        assert stats['urls_added'] == 0, "No URLs should be added initially"
        assert stats['queue_size'] == 0, "Queue size should be 0"
    
    def test_queue_clear_functionality(self):
        """Test queue clearing functionality."""
        queue_manager = URLQueueManager(self.state_file)
        
        # Add some URLs
        queue_manager.add_url("https://en.wikipedia.org/wiki/Test", URLType.ARTICLE, 0)
        queue_manager.add_url("https://en.wikipedia.org/Category:Test", URLType.CATEGORY, 0)
        
        assert not queue_manager.is_empty(), "Queue should not be empty after adding URLs"
        
        # Clear the queue
        queue_manager.clear()
        
        # Queue should be empty
        assert queue_manager.is_empty(), "Queue should be empty after clearing"
        assert queue_manager.size() == 0, "Queue size should be 0 after clearing"
        
        # Statistics should be reset
        stats = queue_manager.get_stats()
        assert stats['urls_added'] == 0, "Statistics should be reset after clearing"


if __name__ == "__main__":
    # Run a quick test to verify the test setup works
    import sys
    
    try:
        # Test basic functionality
        temp_dir = tempfile.mkdtemp()
        state_file = os.path.join(temp_dir, "test_state.json")
        
        queue_manager = URLQueueManager(state_file)
        
        # Test basic operations
        assert queue_manager.add_url("https://en.wikipedia.org/wiki/Test", URLType.ARTICLE, 0)
        assert not queue_manager.is_empty()
        
        url_item = queue_manager.get_next_url()
        assert url_item is not None
        assert url_item.url == "https://en.wikipedia.org/wiki/Test"
        
        queue_manager.mark_completed(url_item.url)
        assert queue_manager.is_empty()
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        print("✓ Basic URL queue test passed")
        print("✓ Property tests are ready to run with: pytest tests/test_url_queue.py")
        
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        sys.exit(1)