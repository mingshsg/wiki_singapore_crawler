#!/usr/bin/env python3
"""Demonstrate network connectivity detection and user interaction capabilities with circuit breaker."""

import tempfile
import time
from unittest.mock import Mock, patch
from wikipedia_crawler.core.page_processor import PageProcessor
from wikipedia_crawler.utils.logging_config import setup_logging
import requests

def demo_connectivity_handling():
    """Demonstrate how the crawler handles network connectivity issues with circuit breaker."""
    setup_logging("INFO")
    
    print("=== Network Connectivity Detection Demo with Circuit Breaker ===")
    print()
    
    # Create page processor
    processor = PageProcessor(
        delay_between_requests=0.1,  # Fast for demo
        max_retries=2,  # Fewer retries for faster demo
        timeout=5
    )
    
    # Mock different scenarios
    def mock_get_with_connectivity_issues(url, **kwargs):
        """Mock HTTP requests with connectivity issues."""
        print(f"Mock request to: {url}")
        
        if "google.com" in url:
            # Simulate Google connectivity test failure
            raise requests.exceptions.ConnectionError("Network unreachable")
        else:
            # Simulate original URL failure
            raise requests.exceptions.ConnectionError("Connection failed")
    
    def mock_get_with_google_success(url, **kwargs):
        """Mock HTTP requests where Google works but target URL fails."""
        print(f"Mock request to: {url}")
        
        if "google.com" in url:
            # Google connectivity test succeeds
            response = Mock()
            response.status_code = 200
            return response
        else:
            # Original URL still fails
            raise requests.exceptions.ConnectionError("Connection failed")
    
    def mock_user_input_continue_always(prompt):
        """Mock user input that always chooses 'continue' to test circuit breaker."""
        print(f"[MOCK USER INPUT] {prompt}")
        print("[MOCK USER] Choosing 'continue' (testing circuit breaker)")
        return "continue"
    
    def mock_user_input_skip(prompt):
        """Mock user input that chooses 'skip'."""
        print(f"[MOCK USER INPUT] {prompt}")
        print("[MOCK USER] Choosing 'skip'")
        return "skip"
    
    def mock_user_input_mixed(prompt):
        """Mock user input that chooses 'continue' twice then 'skip'."""
        if not hasattr(mock_user_input_mixed, 'call_count'):
            mock_user_input_mixed.call_count = 0
        mock_user_input_mixed.call_count += 1
        
        print(f"[MOCK USER INPUT] {prompt}")
        if mock_user_input_mixed.call_count <= 2:
            print(f"[MOCK USER] Choosing 'continue' (attempt {mock_user_input_mixed.call_count})")
            return "continue"
        else:
            print("[MOCK USER] Choosing 'skip'")
            return "skip"
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Network connectivity issue - user chooses skip immediately",
            "mock_get": mock_get_with_connectivity_issues,
            "mock_input": mock_user_input_skip,
            "expected_behavior": "Should prompt user once and skip URL"
        },
        {
            "name": "Network connectivity issue - circuit breaker activation",
            "mock_get": mock_get_with_connectivity_issues,
            "mock_input": mock_user_input_continue_always,
            "expected_behavior": "Should hit circuit breaker after 3 retry cycles and auto-skip"
        },
        {
            "name": "Network connectivity issue - user retries then skips",
            "mock_get": mock_get_with_connectivity_issues,
            "mock_input": mock_user_input_mixed,
            "expected_behavior": "Should retry twice then skip on third prompt"
        },
        {
            "name": "Google works but target URL fails",
            "mock_get": mock_get_with_google_success,
            "mock_input": None,  # Should not prompt user
            "expected_behavior": "Should treat as permanent failure without user prompt"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f"Scenario {i}: {scenario['name']}")
        print(f"Expected: {scenario['expected_behavior']}")
        print(f"{'='*80}")
        
        # Reset stats for each test
        processor.reset_stats()
        
        # Reset mock function call counter if it exists
        if hasattr(mock_user_input_mixed, 'call_count'):
            mock_user_input_mixed.call_count = 0
        
        test_url = f"https://en.wikipedia.org/wiki/Test_Page_{i}"
        
        with patch.object(processor.session, 'get', side_effect=scenario['mock_get']):
            if scenario['mock_input']:
                with patch('builtins.input', side_effect=scenario['mock_input']):
                    start_time = time.time()
                    result = processor.process_page(test_url)
                    end_time = time.time()
            else:
                start_time = time.time()
                result = processor.process_page(test_url)
                end_time = time.time()
        
        # Show results
        print(f"\nResult: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        if not result.success:
            print(f"Error: {result.error_message}")
        
        stats = processor.get_stats()
        print(f"\nStatistics:")
        print(f"  Requests made: {stats['requests_made']}")
        print(f"  Connectivity tests: {stats.get('connectivity_tests', 0)}")
        print(f"  Connectivity failures: {stats.get('connectivity_failures', 0)}")
        print(f"  Skipped URLs: {stats.get('skipped_urls', 0)}")
        print(f"  User retries: {stats.get('user_retries', 0)}")
        print(f"  Circuit breaker activations: {stats.get('circuit_breaker_activations', 0)}")
        print(f"  User decisions: {stats.get('user_decisions', {})}")
        print(f"  Time taken: {end_time - start_time:.2f}s")
        
        # Explain what happened
        if stats.get('circuit_breaker_activations', 0) > 0:
            print(f"\n🛑 Circuit breaker activated - prevented infinite loop!")
        elif stats.get('connectivity_tests', 0) > 0:
            if stats.get('connectivity_failures', 0) > 0:
                print(f"\n✅ Connectivity test performed and failed - user interaction triggered")
            else:
                print(f"\n✅ Connectivity test performed and succeeded - no user interaction needed")
        else:
            print(f"\n✅ No connectivity test needed (permanent failure detected)")
    
    print(f"\n{'='*80}")
    print("Network Connectivity Detection Demo with Circuit Breaker Complete!")
    print(f"{'='*80}")
    print("\nKey behaviors demonstrated:")
    print("1. ✅ When all retries fail AND Google is unreachable → Prompt user")
    print("2. ✅ User can choose 'continue' to retry with full retry logic")
    print("3. ✅ User can choose 'skip' to move to next URL")
    print("4. ✅ If retries fail again → Repeat connectivity test and user prompt")
    print("5. ✅ Circuit breaker prevents infinite loops after 3 retry cycles")
    print("6. ✅ When Google is reachable but target URL fails → Treat as permanent failure")
    print("7. ✅ Comprehensive statistics tracking including circuit breaker activations")
    
    # Clean up
    processor.close()

if __name__ == "__main__":
    demo_connectivity_handling()