"""Property-based tests for state persistence and resumability."""

import tempfile
import os
from datetime import datetime
from pathlib import Path
from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest

from wikipedia_crawler.core.url_queue import URLQueueManager
from wikipedia_crawler.core.deduplication import DeduplicationSystem
from wikipedia_crawler.models.data_models import URLItem, URLType


# Custom strategies for generating test data
@composite
def wikipedia_url(draw):
    """Generate Wikipedia URLs."""
    domains = ['en.wikipedia.org', 'zh.wikipedia.org', 'zh-cn.wikipedia.org']
    domain = draw(st.sampled_from(domains))
    
    # Generate article name
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


class TestStatePersistence:
    """Test state persistence and resumability properties."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.queue_state_file = os.path.join(self.temp_dir, "test_queue_state.json")
        self.dedup_state_file = os.path.join(self.temp_dir, "test_dedup_state.json")
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @given(
        urls_and_types=st.lists(url_with_type(), min_size=1, max_size=15, unique_by=lambda x: x[0])
    )
    def test_queue_state_persistence_round_trip(self, urls_and_types):
        """
        Property 7: State Persistence Round Trip - Queue state
        For any queue state (including pending URLs and statistics), saving the state 
        and then loading it should restore the exact same system state.
        **Feature: wikipedia-singapore-crawler, Property 7: State Persistence Round Trip**
        **Validates: Requirements 4.3, 4.4, 5.1, 5.2, 5.3, 5.4**
        """
        # Create first queue manager and populate it
        queue_manager1 = URLQueueManager(self.queue_state_file)
        
        # Add URLs to queue
        added_urls = []
        for url, url_type, depth in urls_and_types:
            if queue_manager1.add_url(url, url_type, depth):
                added_urls.append((url, url_type, depth))
        
        # Process some URLs (but not all)
        processed_count = len(added_urls) // 2
        processed_urls = []
        
        for _ in range(processed_count):
            if not queue_manager1.is_empty():
                url_item = queue_manager1.get_next_url()
                queue_manager1.mark_completed(url_item.url)
                processed_urls.append(url_item.url)
        
        # Get state before saving
        original_stats = queue_manager1.get_stats()
        original_pending = queue_manager1.get_pending_urls()
        original_completed = queue_manager1.get_completed_urls()
        original_size = queue_manager1.size()
        
        # Save state
        queue_manager1.save_state()
        
        # Create new queue manager and load state
        queue_manager2 = URLQueueManager(self.queue_state_file)
        load_success = queue_manager2.load_state()
        
        assert load_success, "State should load successfully"
        
        # Compare restored state
        restored_stats = queue_manager2.get_stats()
        restored_pending = queue_manager2.get_pending_urls()
        restored_completed = queue_manager2.get_completed_urls()
        restored_size = queue_manager2.size()
        
        # Statistics should match
        assert restored_stats['urls_added'] == original_stats['urls_added'], "URLs added count should match"
        assert restored_stats['urls_completed'] == original_stats['urls_completed'], "URLs completed count should match"
        assert restored_stats['categories_pending'] == original_stats['categories_pending'], "Categories pending should match"
        assert restored_stats['articles_pending'] == original_stats['articles_pending'], "Articles pending should match"
        
        # Queue state should match
        assert restored_size == original_size, "Queue size should match"
        assert set(restored_pending) == set(original_pending), "Pending URLs should match"
        assert set(restored_completed) == set(original_completed), "Completed URLs should match"
        
        # Should be able to continue processing from where we left off
        remaining_urls = []
        while not queue_manager2.is_empty():
            url_item = queue_manager2.get_next_url()
            remaining_urls.append(url_item.url)
        
        # All remaining URLs should be from the original set minus processed ones
        expected_remaining = [url for url, _, _ in added_urls if url not in processed_urls]
        assert set(remaining_urls) == set(expected_remaining), "Remaining URLs should match expected"
    
    @given(
        urls=st.lists(
            st.one_of(wikipedia_url(), wikipedia_category_url()),
            min_size=1, max_size=20, unique=True
        )
    )
    def test_deduplication_state_persistence_round_trip(self, urls):
        """
        Property 7: State Persistence Round Trip - Deduplication state
        For any deduplication state (processed URLs and statistics), saving the state 
        and then loading it should restore the exact same system state.
        **Feature: wikipedia-singapore-crawler, Property 7: State Persistence Round Trip**
        **Validates: Requirements 4.3, 4.4, 5.1, 5.2, 5.3, 5.4**
        """
        # Create first deduplication system and populate it
        dedup_system1 = DeduplicationSystem(self.dedup_state_file)
        
        # Mark some URLs as processed
        processed_count = 0
        for url in urls:
            if dedup_system1.mark_processed(url):
                processed_count += 1
        
        # Get state before saving
        original_stats = dedup_system1.get_stats()
        original_processed = dedup_system1.get_processed_urls()
        original_count = dedup_system1.get_processed_count()
        
        # Save state
        dedup_system1.save_state()
        
        # Create new deduplication system and load state
        dedup_system2 = DeduplicationSystem(self.dedup_state_file)
        load_success = dedup_system2.load_state()
        
        assert load_success, "State should load successfully"
        
        # Compare restored state
        restored_stats = dedup_system2.get_stats()
        restored_processed = dedup_system2.get_processed_urls()
        restored_count = dedup_system2.get_processed_count()
        
        # Statistics should match
        assert restored_stats['urls_processed'] == original_stats['urls_processed'], "URLs processed count should match"
        assert restored_stats['duplicates_prevented'] == original_stats['duplicates_prevented'], "Duplicates prevented should match"
        
        # Processed URLs should match
        assert restored_count == original_count, "Processed count should match"
        assert set(restored_processed) == set(original_processed), "Processed URLs should match"
        
        # Deduplication behavior should be preserved
        for url in urls:
            assert dedup_system2.is_processed(url), f"URL should still be marked as processed: {url}"
            
            # Attempting to mark as processed again should return False
            was_new = dedup_system2.mark_processed(url)
            assert not was_new, f"URL should not be marked as new when already processed: {url}"
    
    @given(
        initial_urls=st.lists(url_with_type(), min_size=1, max_size=10, unique_by=lambda x: x[0]),
        additional_urls=st.lists(url_with_type(), min_size=1, max_size=10, unique_by=lambda x: x[0])
    )
    def test_combined_state_persistence_consistency(self, initial_urls, additional_urls):
        """
        Property 7: State Persistence Round Trip - Combined system consistency
        For any combined crawler state (queue + deduplication), the systems should 
        maintain consistency after save/load cycles.
        **Feature: wikipedia-singapore-crawler, Property 7: State Persistence Round Trip**
        **Validates: Requirements 4.3, 4.4, 5.1, 5.2, 5.3, 5.4**
        """
        # Ensure no overlap between initial and additional URLs
        initial_url_set = {url for url, _, _ in initial_urls}
        additional_urls = [(url, url_type, depth) for url, url_type, depth in additional_urls 
                          if url not in initial_url_set]
        assume(len(additional_urls) > 0)
        
        # Create initial systems
        queue_manager1 = URLQueueManager(self.queue_state_file)
        dedup_system1 = DeduplicationSystem(self.dedup_state_file)
        
        # Add initial URLs to queue
        for url, url_type, depth in initial_urls:
            queue_manager1.add_url(url, url_type, depth)
        
        # Process some URLs and mark them in deduplication system
        processed_urls = []
        process_count = len(initial_urls) // 2
        
        for _ in range(process_count):
            if not queue_manager1.is_empty():
                url_item = queue_manager1.get_next_url()
                queue_manager1.mark_completed(url_item.url)
                dedup_system1.mark_processed(url_item.url)
                processed_urls.append(url_item.url)
        
        # Save both states
        queue_manager1.save_state()
        dedup_system1.save_state()
        
        # Create new systems and load states
        queue_manager2 = URLQueueManager(self.queue_state_file)
        dedup_system2 = DeduplicationSystem(self.dedup_state_file)
        
        queue_loaded = queue_manager2.load_state()
        dedup_loaded = dedup_system2.load_state()
        
        assert queue_loaded and dedup_loaded, "Both states should load successfully"
        
        # Add additional URLs to test consistency
        for url, url_type, depth in additional_urls:
            # URL should not be in deduplication system yet
            assert not dedup_system2.is_processed(url), f"New URL should not be processed: {url}"
            
            # Should be able to add to queue
            was_added = queue_manager2.add_url(url, url_type, depth)
            assert was_added, f"New URL should be addable to queue: {url}"
        
        # Process additional URLs
        additional_processed = []
        while not queue_manager2.is_empty():
            url_item = queue_manager2.get_next_url()
            queue_manager2.mark_completed(url_item.url)
            dedup_system2.mark_processed(url_item.url)
            additional_processed.append(url_item.url)
        
        # Verify consistency
        all_processed = processed_urls + additional_processed
        
        # All processed URLs should be in deduplication system
        for url in all_processed:
            assert dedup_system2.is_processed(url), f"Processed URL should be in deduplication system: {url}"
        
        # Queue should be empty
        assert queue_manager2.is_empty(), "Queue should be empty after processing all URLs"
        
        # Statistics should be consistent
        queue_stats = queue_manager2.get_stats()
        dedup_stats = dedup_system2.get_stats()
        
        expected_total = len(initial_urls) + len(additional_urls)
        assert queue_stats['urls_completed'] == expected_total, "Queue completed count should match total URLs"
        assert dedup_stats['total_processed_urls'] == expected_total, "Deduplication processed count should match total URLs"
    
    @given(
        urls_and_types=st.lists(url_with_type(), min_size=1, max_size=8, unique_by=lambda x: x[0])
    )
    def test_state_persistence_with_interruption_simulation(self, urls_and_types):
        """
        Property 7: State Persistence Round Trip - Interruption recovery
        For any crawler state, simulating an interruption (save/load cycle) should 
        allow seamless continuation of processing.
        **Feature: wikipedia-singapore-crawler, Property 7: State Persistence Round Trip**
        **Validates: Requirements 4.3, 4.4, 5.1, 5.2, 5.3, 5.4**
        """
        # Phase 1: Initial processing
        queue_manager1 = URLQueueManager(self.queue_state_file)
        dedup_system1 = DeduplicationSystem(self.dedup_state_file)
        
        # Add all URLs
        for url, url_type, depth in urls_and_types:
            queue_manager1.add_url(url, url_type, depth)
        
        # Process about half the URLs
        phase1_processed = []
        target_process = max(1, len(urls_and_types) // 2)
        
        for _ in range(target_process):
            if not queue_manager1.is_empty():
                url_item = queue_manager1.get_next_url()
                queue_manager1.mark_completed(url_item.url)
                dedup_system1.mark_processed(url_item.url)
                phase1_processed.append(url_item.url)
        
        # Save state (simulating graceful shutdown)
        queue_manager1.save_state()
        dedup_system1.save_state()
        
        phase1_remaining = queue_manager1.size()
        
        # Phase 2: Recovery and continuation
        queue_manager2 = URLQueueManager(self.queue_state_file)
        dedup_system2 = DeduplicationSystem(self.dedup_state_file)
        
        # Load state (simulating restart)
        queue_loaded = queue_manager2.load_state()
        dedup_loaded = dedup_system2.load_state()
        
        assert queue_loaded and dedup_loaded, "State should load successfully after interruption"
        
        # Should have same remaining count
        assert queue_manager2.size() == phase1_remaining, "Queue size should match after recovery"
        
        # Previously processed URLs should still be marked as processed
        for url in phase1_processed:
            assert dedup_system2.is_processed(url), f"Previously processed URL should remain processed: {url}"
            
            # Should not be able to add to queue again
            original_url = next((u for u, _, _ in urls_and_types if u == url), None)
            if original_url:
                original_type = next(t for u, t, _ in urls_and_types if u == original_url)
                was_added = queue_manager2.add_url(url, original_type, 0)
                assert not was_added, f"Previously processed URL should not be re-addable: {url}"
        
        # Continue processing remaining URLs
        phase2_processed = []
        while not queue_manager2.is_empty():
            url_item = queue_manager2.get_next_url()
            queue_manager2.mark_completed(url_item.url)
            dedup_system2.mark_processed(url_item.url)
            phase2_processed.append(url_item.url)
        
        # Verify complete processing
        all_processed = set(phase1_processed + phase2_processed)
        all_original = {url for url, _, _ in urls_and_types}
        
        assert all_processed == all_original, "All original URLs should be processed across both phases"
        
        # Final statistics should be consistent
        final_queue_stats = queue_manager2.get_stats()
        final_dedup_stats = dedup_system2.get_stats()
        
        assert final_queue_stats['urls_completed'] == len(urls_and_types), "All URLs should be completed"
        assert final_dedup_stats['total_processed_urls'] == len(urls_and_types), "All URLs should be in deduplication system"
    
    def test_state_persistence_empty_systems(self):
        """Test state persistence with empty systems."""
        # Test empty queue
        queue_manager1 = URLQueueManager(self.queue_state_file)
        queue_manager1.save_state()
        
        queue_manager2 = URLQueueManager(self.queue_state_file)
        loaded = queue_manager2.load_state()
        
        assert loaded, "Empty queue state should load successfully"
        assert queue_manager2.is_empty(), "Loaded queue should be empty"
        assert queue_manager2.size() == 0, "Loaded queue should have size 0"
        
        # Test empty deduplication system
        dedup_system1 = DeduplicationSystem(self.dedup_state_file)
        dedup_system1.save_state()
        
        dedup_system2 = DeduplicationSystem(self.dedup_state_file)
        loaded = dedup_system2.load_state()
        
        assert loaded, "Empty deduplication state should load successfully"
        assert dedup_system2.get_processed_count() == 0, "Loaded deduplication system should have no processed URLs"
    
    def test_state_persistence_file_not_found(self):
        """Test behavior when state files don't exist."""
        nonexistent_queue_file = os.path.join(self.temp_dir, "nonexistent_queue.json")
        nonexistent_dedup_file = os.path.join(self.temp_dir, "nonexistent_dedup.json")
        
        # Queue manager should handle missing file gracefully
        queue_manager = URLQueueManager(nonexistent_queue_file)
        loaded = queue_manager.load_state()
        
        assert not loaded, "Loading nonexistent state should return False"
        assert queue_manager.is_empty(), "Queue should be empty when no state file exists"
        
        # Deduplication system should handle missing file gracefully
        dedup_system = DeduplicationSystem(nonexistent_dedup_file)
        loaded = dedup_system.load_state()
        
        assert not loaded, "Loading nonexistent state should return False"
        assert dedup_system.get_processed_count() == 0, "Deduplication system should be empty when no state file exists"
    
    def test_state_persistence_corrupted_file_handling(self):
        """Test handling of corrupted state files."""
        # Create corrupted queue state file
        with open(self.queue_state_file, 'w') as f:
            f.write("invalid json content {")
        
        queue_manager = URLQueueManager(self.queue_state_file)
        loaded = queue_manager.load_state()
        
        assert not loaded, "Loading corrupted state should return False"
        assert queue_manager.is_empty(), "Queue should be empty when state file is corrupted"
        
        # Create corrupted deduplication state file
        with open(self.dedup_state_file, 'w') as f:
            f.write("invalid json content {")
        
        dedup_system = DeduplicationSystem(self.dedup_state_file)
        loaded = dedup_system.load_state()
        
        assert not loaded, "Loading corrupted state should return False"
        assert dedup_system.get_processed_count() == 0, "Deduplication system should be empty when state file is corrupted"


if __name__ == "__main__":
    # Run a quick test to verify the test setup works
    import sys
    
    try:
        # Test basic functionality
        temp_dir = tempfile.mkdtemp()
        queue_state_file = os.path.join(temp_dir, "test_queue_state.json")
        dedup_state_file = os.path.join(temp_dir, "test_dedup_state.json")
        
        # Test queue persistence
        queue_manager1 = URLQueueManager(queue_state_file)
        queue_manager1.add_url("https://en.wikipedia.org/wiki/Test", URLType.ARTICLE, 0)
        queue_manager1.save_state()
        
        queue_manager2 = URLQueueManager(queue_state_file)
        loaded = queue_manager2.load_state()
        assert loaded
        assert not queue_manager2.is_empty()
        
        # Test deduplication persistence
        dedup_system1 = DeduplicationSystem(dedup_state_file)
        dedup_system1.mark_processed("https://en.wikipedia.org/wiki/Test")
        dedup_system1.save_state()
        
        dedup_system2 = DeduplicationSystem(dedup_state_file)
        loaded = dedup_system2.load_state()
        assert loaded
        assert dedup_system2.is_processed("https://en.wikipedia.org/wiki/Test")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        print("✓ Basic state persistence test passed")
        print("✓ Property tests are ready to run with: pytest tests/test_state_persistence.py")
        
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        sys.exit(1)