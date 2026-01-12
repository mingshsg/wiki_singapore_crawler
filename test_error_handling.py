#!/usr/bin/env python3
"""Test the error handling behavior of the page processor."""

import unittest
from unittest.mock import Mock, patch
import requests
from wikipedia_crawler.core.page_processor import PageProcessor
from wikipedia_crawler.utils.logging_config import setup_logging

class TestErrorHandling(unittest.TestCase):
    """Test error handling in the page processor."""
    
    def setUp(self):
        """Set up test fixtures."""
        setup_logging("WARNING")  # Reduce log noise during tests
        self.processor = PageProcessor(
            delay_between_requests=0.01,  # Very fast for tests
            max_retries=2,
            timeout=5
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.processor.close()
    
    def test_404_gives_up_immediately(self):
        """Test that 404 errors don't retry."""
        def mock_404_response(*args, **kwargs):
            response = Mock()
            response.status_code = 404
            return response
        
        with patch.object(self.processor.session, 'get', side_effect=mock_404_response):
            result = self.processor.process_page("https://example.com/404_test")
            
            # Should fail without retries
            self.assertFalse(result.success)
            
            stats = self.processor.get_stats()
            self.assertEqual(stats['requests_made'], 1)  # Only one request
            self.assertEqual(stats['retries_attempted'], 0)  # No retries
            self.assertEqual(stats['permanent_failures'], 1)  # Marked as permanent failure
    
    def test_403_gives_up_immediately(self):
        """Test that 403 errors don't retry."""
        def mock_403_response(*args, **kwargs):
            response = Mock()
            response.status_code = 403
            return response
        
        with patch.object(self.processor.session, 'get', side_effect=mock_403_response):
            result = self.processor.process_page("https://example.com/403_test")
            
            # Should fail without retries
            self.assertFalse(result.success)
            
            stats = self.processor.get_stats()
            self.assertEqual(stats['requests_made'], 1)  # Only one request
            self.assertEqual(stats['retries_attempted'], 0)  # No retries
            self.assertEqual(stats['permanent_failures'], 1)  # Marked as permanent failure
    
    def test_500_retries_with_backoff(self):
        """Test that 500 errors retry with exponential backoff."""
        def mock_500_response(*args, **kwargs):
            response = Mock()
            response.status_code = 500
            return response
        
        with patch.object(self.processor.session, 'get', side_effect=mock_500_response):
            result = self.processor.process_page("https://example.com/500_test")
            
            # Should fail after retries
            self.assertFalse(result.success)
            
            stats = self.processor.get_stats()
            self.assertEqual(stats['requests_made'], 3)  # 1 initial + 2 retries
            self.assertEqual(stats['retries_attempted'], 2)  # 2 retries
            self.assertEqual(stats['total_failures'], 1)  # Marked as total failure
    
    def test_timeout_retries(self):
        """Test that timeout errors retry."""
        def mock_timeout(*args, **kwargs):
            raise requests.exceptions.Timeout("Request timed out")
        
        with patch.object(self.processor.session, 'get', side_effect=mock_timeout):
            result = self.processor.process_page("https://example.com/timeout_test")
            
            # Should fail after retries
            self.assertFalse(result.success)
            
            stats = self.processor.get_stats()
            self.assertEqual(stats['retries_attempted'], 2)  # 2 retries
            self.assertEqual(stats['timeout_errors'], 3)  # 1 initial + 2 retries
    
    def test_connection_error_retries(self):
        """Test that connection errors retry."""
        def mock_connection_error(*args, **kwargs):
            raise requests.exceptions.ConnectionError("Connection failed")
        
        with patch.object(self.processor.session, 'get', side_effect=mock_connection_error):
            result = self.processor.process_page("https://example.com/connection_test")
            
            # Should fail after retries
            self.assertFalse(result.success)
            
            stats = self.processor.get_stats()
            self.assertEqual(stats['retries_attempted'], 2)  # 2 retries
            self.assertEqual(stats['connection_errors'], 3)  # 1 initial + 2 retries
    
    def test_success_no_retries(self):
        """Test that successful requests don't retry."""
        def mock_success_response(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            response.text = "<html><body><h1>Test Page</h1></body></html>"
            response.headers = {'content-type': 'text/html'}
            return response
        
        with patch.object(self.processor.session, 'get', side_effect=mock_success_response):
            result = self.processor.process_page("https://example.com/success_test")
            
            # Should succeed
            self.assertTrue(result.success)
            
            stats = self.processor.get_stats()
            self.assertEqual(stats['requests_made'], 1)  # Only one request
            self.assertEqual(stats['retries_attempted'], 0)  # No retries
            self.assertEqual(stats['successful_requests'], 1)  # Marked as successful

if __name__ == "__main__":
    print("Testing Error Handling Behavior")
    print("=" * 40)
    
    # Run the tests
    unittest.main(verbosity=2)