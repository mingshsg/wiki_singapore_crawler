#!/usr/bin/env python3
"""Test the network connectivity detection and user interaction logic."""

import unittest
from unittest.mock import Mock, patch
import requests
from wikipedia_crawler.core.page_processor import PageProcessor
from wikipedia_crawler.utils.logging_config import setup_logging

class TestConnectivityHandling(unittest.TestCase):
    """Test network connectivity detection and user interaction."""
    
    def setUp(self):
        """Set up test fixtures."""
        setup_logging("WARNING")  # Reduce log noise during tests
        self.processor = PageProcessor(
            delay_between_requests=0.01,  # Very fast for tests
            max_retries=1,  # Minimal retries for faster tests
            timeout=5
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.processor.close()
    
    def test_connectivity_test_success(self):
        """Test that connectivity test to Google works correctly."""
        def mock_google_success(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            return response
        
        with patch.object(self.processor.session, 'get', side_effect=mock_google_success):
            result = self.processor._test_network_connectivity()
            
            self.assertTrue(result)
            stats = self.processor.get_stats()
            self.assertEqual(stats['connectivity_tests'], 1)
            self.assertEqual(stats['connectivity_successes'], 1)
            self.assertEqual(stats['connectivity_failures'], 0)
    
    def test_connectivity_test_failure(self):
        """Test that connectivity test failure is detected correctly."""
        def mock_google_failure(*args, **kwargs):
            raise requests.exceptions.ConnectionError("Network unreachable")
        
        with patch.object(self.processor.session, 'get', side_effect=mock_google_failure):
            result = self.processor._test_network_connectivity()
            
            self.assertFalse(result)
            stats = self.processor.get_stats()
            self.assertEqual(stats['connectivity_tests'], 1)
            self.assertEqual(stats['connectivity_successes'], 0)
            self.assertEqual(stats['connectivity_failures'], 1)
    
    def test_user_skip_choice(self):
        """Test that user choosing 'skip' is handled correctly."""
        def mock_failed_request(*args, **kwargs):
            if "google.com" in args[0]:
                raise requests.exceptions.ConnectionError("Network unreachable")
            else:
                raise requests.exceptions.ConnectionError("Connection failed")
        
        def mock_user_skip(prompt):
            return "skip"
        
        with patch.object(self.processor.session, 'get', side_effect=mock_failed_request):
            with patch('builtins.input', side_effect=mock_user_skip):
                result = self.processor.process_page("https://example.com/test")
                
                self.assertFalse(result.success)
                stats = self.processor.get_stats()
                self.assertEqual(stats['skipped_urls'], 1)
                self.assertEqual(stats['user_decisions']['skip'], 1)
                self.assertEqual(stats['connectivity_tests'], 1)
                self.assertEqual(stats['connectivity_failures'], 1)
    
    def test_user_continue_choice_success(self):
        """Test that user choosing 'continue' and succeeding works correctly."""
        call_count = {'count': 0}
        
        def mock_request_with_eventual_success(*args, **kwargs):
            call_count['count'] += 1
            
            if "google.com" in args[0]:
                # Google connectivity test fails initially
                raise requests.exceptions.ConnectionError("Network unreachable")
            else:
                # First attempts fail, but user retry succeeds
                if call_count['count'] <= 3:  # Initial attempts fail
                    raise requests.exceptions.ConnectionError("Connection failed")
                else:  # User retry succeeds
                    response = Mock()
                    response.status_code = 200
                    response.text = "<html><body>Test content</body></html>"
                    response.headers = {'content-type': 'text/html'}
                    return response
        
        def mock_user_continue(prompt):
            return "continue"
        
        with patch.object(self.processor.session, 'get', side_effect=mock_request_with_eventual_success):
            with patch('builtins.input', side_effect=mock_user_continue):
                result = self.processor.process_page("https://example.com/test")
                
                self.assertTrue(result.success)
                stats = self.processor.get_stats()
                self.assertEqual(stats['user_retries'], 1)
                self.assertEqual(stats['user_retry_successes'], 1)
                self.assertEqual(stats['user_decisions']['continue'], 1)
    
    def test_google_works_but_url_fails(self):
        """Test that when Google works but target URL fails, no user prompt occurs."""
        def mock_google_works_url_fails(*args, **kwargs):
            if "google.com" in args[0]:
                # Google connectivity test succeeds
                response = Mock()
                response.status_code = 200
                return response
            else:
                # Target URL fails
                raise requests.exceptions.ConnectionError("Connection failed")
        
        with patch.object(self.processor.session, 'get', side_effect=mock_google_works_url_fails):
            result = self.processor.process_page("https://example.com/test")
            
            self.assertFalse(result.success)
            stats = self.processor.get_stats()
            # Should not have any user interaction stats
            self.assertEqual(stats.get('skipped_urls', 0), 0)
            self.assertEqual(stats.get('user_retries', 0), 0)
            self.assertEqual(stats['connectivity_tests'], 1)
            self.assertEqual(stats['connectivity_successes'], 1)
    
    def test_circuit_breaker_activation(self):
        """Test that circuit breaker activates after maximum retry cycles."""
        def mock_failed_request(*args, **kwargs):
            if "google.com" in args[0]:
                raise requests.exceptions.ConnectionError("Network unreachable")
            else:
                raise requests.exceptions.ConnectionError("Connection failed")
        
        def mock_user_always_continue(prompt):
            return "continue"
        
        with patch.object(self.processor.session, 'get', side_effect=mock_failed_request):
            with patch('builtins.input', side_effect=mock_user_always_continue):
                result = self.processor.process_page("https://example.com/test")
                
                self.assertFalse(result.success)
                stats = self.processor.get_stats()
                # Circuit breaker should activate after 3 retry cycles
                self.assertEqual(stats['circuit_breaker_activations'], 1)
                self.assertEqual(stats['skipped_urls'], 1)
                self.assertEqual(stats['user_retries'], 3)  # Should have 3 user retry attempts
                self.assertEqual(stats['user_decisions']['continue'], 3)
    
    def test_circuit_breaker_warning_display(self):
        """Test that circuit breaker warning is displayed on final retry cycle."""
        call_count = {'count': 0}
        
        def mock_failed_request(*args, **kwargs):
            if "google.com" in args[0]:
                raise requests.exceptions.ConnectionError("Network unreachable")
            else:
                raise requests.exceptions.ConnectionError("Connection failed")
        
        def mock_user_continue_then_skip(prompt):
            call_count['count'] += 1
            if call_count['count'] <= 2:
                return "continue"
            else:
                return "skip"
        
        with patch.object(self.processor.session, 'get', side_effect=mock_failed_request):
            with patch('builtins.input', side_effect=mock_user_continue_then_skip):
                result = self.processor.process_page("https://example.com/test")
                
                self.assertFalse(result.success)
                stats = self.processor.get_stats()
                # Should not activate circuit breaker since user chose skip on 3rd cycle
                self.assertEqual(stats.get('circuit_breaker_activations', 0), 0)
                self.assertEqual(stats['skipped_urls'], 1)
                self.assertEqual(stats['user_retries'], 2)
                self.assertEqual(stats['user_decisions']['continue'], 2)
                self.assertEqual(stats['user_decisions']['skip'], 1)
    
    def test_connectivity_recovery_during_retry_cycle(self):
        """Test behavior when connectivity recovers during a retry cycle."""
        google_call_count = {'count': 0}
        
        def mock_connectivity_recovery(*args, **kwargs):
            url = args[0]
            
            if "google.com" in url:
                google_call_count['count'] += 1
                # First Google connectivity test fails, second succeeds
                if google_call_count['count'] == 1:
                    raise requests.exceptions.ConnectionError("Network unreachable")
                else:
                    response = Mock()
                    response.status_code = 200
                    return response
            else:
                # Target URL always fails
                raise requests.exceptions.ConnectionError("Connection failed")
        
        def mock_user_continue(prompt):
            return "continue"
        
        with patch.object(self.processor.session, 'get', side_effect=mock_connectivity_recovery):
            with patch('builtins.input', side_effect=mock_user_continue):
                result = self.processor.process_page("https://example.com/test")
                
                self.assertFalse(result.success)
                stats = self.processor.get_stats()
                # Should not activate circuit breaker since connectivity recovered
                self.assertEqual(stats.get('circuit_breaker_activations', 0), 0)
                # Should have 1 user retry attempt before connectivity recovered
                self.assertEqual(stats['user_retries'], 1)
                # Should have 2 connectivity tests: initial + after user retry
                self.assertEqual(stats['connectivity_tests'], 2)
                self.assertEqual(stats['connectivity_failures'], 1)
                self.assertEqual(stats['connectivity_successes'], 1)
    
    def test_permanent_failure_no_connectivity_test(self):
        """Test that permanent failures (404) don't trigger connectivity tests."""
        def mock_404_response(*args, **kwargs):
            response = Mock()
            response.status_code = 404
            return response
        
        with patch.object(self.processor.session, 'get', side_effect=mock_404_response):
            result = self.processor.process_page("https://example.com/test")
            
            self.assertFalse(result.success)
            stats = self.processor.get_stats()
            # Should not have any connectivity tests for permanent failures
            self.assertEqual(stats.get('connectivity_tests', 0), 0)
            self.assertEqual(stats['permanent_failures'], 1)

if __name__ == "__main__":
    print("Testing Network Connectivity Detection and User Interaction")
    print("=" * 60)
    
    # Run the tests
    unittest.main(verbosity=2)