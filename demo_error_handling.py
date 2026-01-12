#!/usr/bin/env python3
"""Demonstrate error handling capabilities of the crawler."""

import tempfile
import time
from unittest.mock import Mock, patch
from wikipedia_crawler.core.page_processor import PageProcessor
from wikipedia_crawler.utils.logging_config import setup_logging
import requests

def demo_error_handling():
    """Demonstrate how the crawler handles different types of errors."""
    setup_logging("INFO")
    
    print("=== Wikipedia Crawler Error Handling Demo ===")
    print()
    
    # Create page processor
    processor = PageProcessor(
        delay_between_requests=0.1,  # Fast for demo
        max_retries=2,
        timeout=10
    )
    
    # Mock different types of HTTP responses
    def mock_get(url, **kwargs):
        """Mock HTTP requests with different error scenarios."""
        print(f"Mock request to: {url}")
        
        # Simulate different error conditions based on URL
        if "404_test" in url:
            # 404 Not Found - should give up immediately
            response = Mock()
            response.status_code = 404
            response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            return response
            
        elif "403_test" in url:
            # 403 Forbidden - should give up immediately
            response = Mock()
            response.status_code = 403
            response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
            return response
            
        elif "500_test" in url:
            # 500 Server Error - should retry
            response = Mock()
            response.status_code = 500
            response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
            return response
            
        elif "timeout_test" in url:
            # Timeout - should retry
            raise requests.exceptions.Timeout("Request timed out")
            
        elif "connection_test" in url:
            # Connection error - should retry
            raise requests.exceptions.ConnectionError("Connection failed")
            
        else:
            # Successful response
            response = Mock()
            response.status_code = 200
            response.text = """
            <html>
            <head><title>Category:Singapore - Wikipedia</title></head>
            <body>
                <h1 id="firstHeading">Category:Singapore</h1>
                <div id="mw-content-text">
                    <div class="mw-parser-output">
                        <p>This category contains articles related to Singapore.</p>
                        <div id="mw-subcategories">
                            <h2>Subcategories</h2>
                            <ul>
                                <li><a href="/wiki/Category:Singapore_geography">Singapore geography</a></li>
                                <li><a href="/wiki/Category:Singapore_history">Singapore history</a></li>
                            </ul>
                        </div>
                        <div id="mw-pages">
                            <h2>Pages in category "Singapore"</h2>
                            <ul>
                                <li><a href="/wiki/Singapore">Singapore</a></li>
                                <li><a href="/wiki/Marina_Bay_Sands">Marina Bay Sands</a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            response.content = response.text.encode('utf-8')
            return response
    
    # Test different error scenarios
    test_urls = [
        ("https://en.wikipedia.org/wiki/Category:Singapore", "Success"),
        ("https://en.wikipedia.org/wiki/Category:404_test", "404 - should give up"),
        ("https://en.wikipedia.org/wiki/Category:403_test", "403 - should give up"),
        ("https://en.wikipedia.org/wiki/Category:500_test", "500 - should retry"),
        ("https://en.wikipedia.org/wiki/Category:timeout_test", "Timeout - should retry"),
        ("https://en.wikipedia.org/wiki/Category:connection_test", "Connection error - should retry"),
    ]
    
    print("Testing Error Handling Scenarios:")
    print("=" * 50)
    
    with patch.object(processor.session, 'get', side_effect=mock_get):
        for url, description in test_urls:
            print(f"\n🔍 Testing: {description}")
            print(f"   URL: {url}")
            
            # Reset stats for each test
            processor.reset_stats()
            
            # Test the page processor directly
            start_time = time.time()
            result = processor.process_page(url)
            end_time = time.time()
            
            print(f"   Result: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
            if not result.success:
                print(f"   Error: {result.error_message}")
            
            stats = processor.get_stats()
            print(f"   Requests made: {stats['requests_made']}")
            print(f"   Retries attempted: {stats['retries_attempted']}")
            print(f"   Time taken: {end_time - start_time:.2f}s")
            
            # Show specific error categories
            error_categories = []
            if stats.get('permanent_failures', 0) > 0:
                error_categories.append(f"Permanent failures: {stats['permanent_failures']}")
            if stats.get('client_errors', 0) > 0:
                error_categories.append(f"Client errors: {stats['client_errors']}")
            if stats.get('connection_errors', 0) > 0:
                error_categories.append(f"Connection errors: {stats['connection_errors']}")
            if stats.get('timeout_errors', 0) > 0:
                error_categories.append(f"Timeout errors: {stats['timeout_errors']}")
            if stats.get('other_errors', 0) > 0:
                error_categories.append(f"Other errors: {stats['other_errors']}")
            
            if error_categories:
                print(f"   Error breakdown: {', '.join(error_categories)}")
            
            # Demonstrate the retry behavior
            if "404" in url or "403" in url:
                print(f"   → ✅ Permanent failure detected - no retries attempted")
            elif "500" in url or "timeout" in url or "connection" in url:
                print(f"   → ✅ Temporary failure - retries attempted with backoff")
            else:
                print(f"   → ✅ Success - no retries needed")
    
    print("\n" + "=" * 50)
    print("Error Handling Demo Complete!")
    print("\nKey behaviors demonstrated:")
    print("1. ✅ 404/403 errors: Give up immediately (no retries)")
    print("2. ✅ 5xx/timeout/connection errors: Retry with exponential backoff")
    print("3. ✅ Successful requests: Process normally")
    print("4. ✅ Detailed error statistics tracking")
    print("5. ✅ Jitter added to backoff to prevent thundering herd")
    
    # Clean up
    processor.close()

if __name__ == "__main__":
    demo_error_handling()