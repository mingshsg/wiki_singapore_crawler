"""Property tests for recursive processing completeness."""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List, Set

from wikipedia_crawler.core.wikipedia_crawler import WikipediaCrawler
from wikipedia_crawler.models.data_models import URLItem, URLType, ProcessResult


# Test data generators
@st.composite
def wikipedia_url_tree(draw):
    """Generate a tree structure of Wikipedia URLs for testing."""
    # Generate root category
    root_category = "https://en.wikipedia.org/wiki/Category:Singapore"
    
    # Generate subcategories (depth 1)
    num_subcategories = draw(st.integers(min_value=0, max_value=5))
    subcategories = []
    for i in range(num_subcategories):
        subcategories.append(f"https://en.wikipedia.org/wiki/Category:Singapore_Subcategory_{i}")
    
    # Generate articles for root category
    num_root_articles = draw(st.integers(min_value=0, max_value=10))
    root_articles = []
    for i in range(num_root_articles):
        root_articles.append(f"https://en.wikipedia.org/wiki/Singapore_Article_{i}")
    
    # Generate articles for each subcategory
    subcategory_articles = {}
    for i, subcat in enumerate(subcategories):
        num_articles = draw(st.integers(min_value=0, max_value=8))
        articles = []
        for j in range(num_articles):
            articles.append(f"https://en.wikipedia.org/wiki/Singapore_Subcategory_{i}_Article_{j}")
        subcategory_articles[subcat] = articles
    
    return {
        'root': root_category,
        'subcategories': subcategories,
        'root_articles': root_articles,
        'subcategory_articles': subcategory_articles
    }


class TestRecursiveProcessingCompleteness:
    """
    Property tests for recursive processing completeness.
    
    **Feature: wikipedia-singapore-crawler, Property 8: Recursive Processing Completeness**
    
    For any Wikipedia category tree structure, the crawler should process all reachable 
    categories and articles exactly once, with proper completion detection when no more 
    URLs remain.
    """
    
    @given(url_tree=wikipedia_url_tree())
    @settings(max_examples=10, deadline=15000)  # Reduced examples for faster testing
    def test_recursive_processing_completeness(self, url_tree):
        """
        Property test: All reachable URLs in a category tree are processed exactly once.
        
        This test validates that:
        1. All URLs in the tree structure are discovered and processed
        2. No URL is processed more than once (deduplication works)
        3. Processing completes when no more URLs remain
        4. The correct number of categories and articles are processed
        """
        assume(len(url_tree['subcategories']) > 0 or len(url_tree['root_articles']) > 0)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create crawler with max_depth=2 to process subcategories
            crawler = WikipediaCrawler(
                start_url=url_tree['root'],
                output_dir=temp_dir,
                max_depth=2,
                delay_between_requests=0.01  # Fast for testing
            )
            
            # Calculate expected totals
            expected_categories = 1 + len(url_tree['subcategories'])  # root + subcategories
            expected_articles = len(url_tree['root_articles']) + sum(
                len(articles) for articles in url_tree['subcategory_articles'].values()
            )
            expected_total = expected_categories + expected_articles
            
            # Track processed URLs
            processed_urls = set()
            
            def mock_process_page(url):
                """Mock page processing that returns appropriate content based on URL."""
                processed_urls.add(url)
                
                result = Mock()
                result.success = True
                result.url = url
                
                if '/Category:' in url:
                    result.page_type = "category"
                    result.content = self._generate_category_html(url, url_tree)
                else:
                    result.page_type = "article"
                    result.content = self._generate_article_html(url)
                
                return result
            
            # Mock category handler to return discovered URLs
            def mock_process_category(url, content, depth):
                """Mock category processing that returns the expected subcategories and articles."""
                result = Mock()
                result.success = True
                result.url = url
                result.discovered_urls = []
                
                if url == url_tree['root']:
                    # Always add root articles
                    result.discovered_urls.extend(url_tree['root_articles'])
                    
                    # Only add subcategories if depth < max_depth (simulating real logic)
                    if depth < crawler.category_handler.max_depth:
                        result.discovered_urls.extend(url_tree['subcategories'])
                        
                elif url in url_tree['subcategories']:
                    # Always add subcategory articles
                    result.discovered_urls.extend(url_tree['subcategory_articles'].get(url, []))
                
                return result
            
            # Mock article handler to simulate successful processing
            def mock_process_article(url, content):
                """Mock article processing that always succeeds."""
                result = Mock()
                result.success = True
                result.url = url
                result.data = {'language': 'en', 'filtered': False}
                return result
            
            # Apply mocks
            with patch.object(crawler.page_processor, 'process_page', side_effect=mock_process_page), \
                 patch.object(crawler.category_handler, 'process_category', side_effect=mock_process_category), \
                 patch.object(crawler.article_handler, 'process_article', side_effect=mock_process_article):
                
                # Start crawling
                crawler.start_crawling()
                
                # Wait for the crawler to actually start processing
                max_wait_time = 20  # seconds
                start_time = time.time()
                
                # First wait for crawler to start running
                while time.time() - start_time < 5:
                    if crawler._crawl_thread and crawler._crawl_thread.is_alive():
                        break
                    time.sleep(0.1)
                
                # Then wait for completion
                while time.time() - start_time < max_wait_time:
                    status = crawler.get_status()
                    # Check if crawler thread is done and no pending URLs
                    if (not crawler._crawl_thread or not crawler._crawl_thread.is_alive()) and status.pending_urls == 0:
                        break
                    time.sleep(0.1)
                
                # Stop crawler
                crawler.stop_crawling()
                
                # Get final status
                final_status = crawler.get_status()
                
                # Verify completeness properties
                
                # Property 1: All expected URLs were processed
                all_expected_urls = {url_tree['root']}
                all_expected_urls.update(url_tree['subcategories'])
                all_expected_urls.update(url_tree['root_articles'])
                for articles in url_tree['subcategory_articles'].values():
                    all_expected_urls.update(articles)
                
                # The crawler should have processed all expected URLs
                assert final_status.total_processed == expected_total, \
                    f"Expected {expected_total} total processed, got {final_status.total_processed}"
                
                # Property 2: Correct categorization of processed items
                assert final_status.categories_processed == expected_categories, \
                    f"Expected {expected_categories} categories, got {final_status.categories_processed}"
                
                assert final_status.articles_processed == expected_articles, \
                    f"Expected {expected_articles} articles, got {final_status.articles_processed}"
                
                # Property 3: No pending URLs remain
                assert final_status.pending_urls == 0, \
                    f"Expected 0 pending URLs, got {final_status.pending_urls}"
                
                # Property 4: All URLs are marked as processed in deduplication system
                for url in all_expected_urls:
                    assert crawler.deduplication.is_processed(url), \
                        f"URL not marked as processed in deduplication: {url}"
    
    def _generate_category_html(self, url: str, url_tree: Dict) -> str:
        """Generate mock HTML content for a category page."""
        if url == url_tree['root']:
            title = "Category:Singapore"
        else:
            # Extract category name from URL
            title = url.split('/')[-1].replace('_', ' ')
        
        return f"""
        <html>
        <head><title>{title} - Wikipedia</title></head>
        <body>
            <h1 id="firstHeading">{title}</h1>
            <div id="mw-content-text">
                <div class="mw-parser-output">
                    <p>This is a category page for {title}.</p>
                    <div id="mw-subcategories">
                        <h2>Subcategories</h2>
                    </div>
                    <div id="mw-pages">
                        <h2>Pages in category</h2>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_article_html(self, url: str) -> str:
        """Generate mock HTML content for an article page."""
        title = url.split('/')[-1].replace('_', ' ')
        
        return f"""
        <html>
        <head><title>{title} - Wikipedia</title></head>
        <body>
            <h1 id="firstHeading">{title}</h1>
            <div id="mw-content-text">
                <div class="mw-parser-output">
                    <p>This is an article about {title}.</p>
                    <p>It contains substantial content about Singapore-related topics.</p>
                    <p>The article has multiple paragraphs with meaningful information.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def test_empty_category_handling(self):
        """Test that empty categories are handled correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Empty_Category",
                output_dir=temp_dir,
                max_depth=2,
                delay_between_requests=0.01
            )
            
            def mock_process_page(url):
                result = Mock()
                result.success = True
                result.url = url
                result.page_type = "category"
                result.content = self._generate_category_html(url, {'root': url})
                return result
            
            def mock_process_category(url, content, depth):
                result = Mock()
                result.success = True
                result.url = url
                result.discovered_urls = []  # Empty category
                return result
            
            with patch.object(crawler.page_processor, 'process_page', side_effect=mock_process_page), \
                 patch.object(crawler.category_handler, 'process_category', side_effect=mock_process_category):
                
                crawler.start_crawling()
                
                # Wait for the crawler to actually start processing
                max_wait_time = 15
                start_time = time.time()
                
                # First wait for crawler to start running
                while time.time() - start_time < 5:
                    if crawler._crawl_thread and crawler._crawl_thread.is_alive():
                        break
                    time.sleep(0.1)
                
                # Then wait for completion
                while time.time() - start_time < max_wait_time:
                    status = crawler.get_status()
                    # Check if crawler thread is done and no pending URLs
                    if (not crawler._crawl_thread or not crawler._crawl_thread.is_alive()) and status.pending_urls == 0:
                        break
                    time.sleep(0.1)
                
                crawler.stop_crawling()
                
                # Verify empty category was processed
                final_status = crawler.get_status()
                assert final_status.categories_processed == 1, \
                    f"Expected 1 category processed, got {final_status.categories_processed}"
                assert final_status.articles_processed == 0, \
                    f"Expected 0 articles processed, got {final_status.articles_processed}"
                assert final_status.total_processed == 1, \
                    f"Expected 1 total processed, got {final_status.total_processed}"
                assert final_status.pending_urls == 0, \
                    f"Expected 0 pending URLs, got {final_status.pending_urls}"
    
    def test_depth_limiting_completeness(self):
        """Test that depth limiting works correctly and processing completes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a deep category tree but limit depth to 0 (only root category)
            crawler = WikipediaCrawler(
                start_url="https://en.wikipedia.org/wiki/Category:Root",
                output_dir=temp_dir,
                max_depth=0,  # Only process root category (depth 0)
                delay_between_requests=0.01
            )
            
            processed_urls = set()
            
            def mock_process_page(url):
                processed_urls.add(url)
                result = Mock()
                result.success = True
                result.url = url
                
                if '/Category:' in url:
                    result.page_type = "category"
                    result.content = self._generate_category_html(url, {'root': url})
                else:
                    result.page_type = "article"
                    result.content = self._generate_article_html(url)
                
                return result
            
            def mock_process_category(url, content, depth):
                result = Mock()
                result.success = True
                result.url = url
                
                # Simulate the real depth limiting logic from CategoryPageHandler
                discovered_urls = []
                
                if depth == 0:  # Root category
                    # Always add articles
                    discovered_urls.extend([
                        "https://en.wikipedia.org/wiki/Root_Article_1",
                        "https://en.wikipedia.org/wiki/Root_Article_2"
                    ])
                    
                    # Only add subcategories if depth < max_depth (simulating real logic)
                    if depth < crawler.category_handler.max_depth:
                        discovered_urls.append("https://en.wikipedia.org/wiki/Category:Deep_Subcategory")
                
                result.discovered_urls = discovered_urls
                return result
            
            def mock_process_article(url, content):
                result = Mock()
                result.success = True
                result.url = url
                result.data = {'language': 'en', 'filtered': False}
                return result
            
            with patch.object(crawler.page_processor, 'process_page', side_effect=mock_process_page), \
                 patch.object(crawler.category_handler, 'process_category', side_effect=mock_process_category), \
                 patch.object(crawler.article_handler, 'process_article', side_effect=mock_process_article):
                
                crawler.start_crawling()
                
                # Wait for the crawler to actually start processing
                max_wait_time = 15
                start_time = time.time()
                
                # First wait for crawler to start running
                while time.time() - start_time < 5:
                    if crawler._crawl_thread and crawler._crawl_thread.is_alive():
                        break
                    time.sleep(0.1)
                
                # Then wait for completion
                while time.time() - start_time < max_wait_time:
                    status = crawler.get_status()
                    # Check if crawler thread is done and no pending URLs
                    if (not crawler._crawl_thread or not crawler._crawl_thread.is_alive()) and status.pending_urls == 0:
                        break
                    time.sleep(0.1)
                
                crawler.stop_crawling()
                
                # Verify depth limiting worked
                final_status = crawler.get_status()
                
                # Should process: 1 root category + 2 articles = 3 total
                # Should NOT process: deep subcategory (due to depth limit of 0)
                assert final_status.categories_processed == 1, \
                    f"Expected 1 category processed, got {final_status.categories_processed}"
                assert final_status.articles_processed == 2, \
                    f"Expected 2 articles processed, got {final_status.articles_processed}"
                assert final_status.total_processed == 3, \
                    f"Expected 3 total processed, got {final_status.total_processed}"
                assert final_status.pending_urls == 0, \
                    f"Expected 0 pending URLs, got {final_status.pending_urls}"
                
                # Verify the deep subcategory was not processed
                assert "https://en.wikipedia.org/wiki/Category:Deep_Subcategory" not in processed_urls, \
                    "Deep subcategory should not have been processed due to depth limit"
                assert "https://en.wikipedia.org/wiki/Root_Article_1" in processed_urls, \
                    "Root article 1 should have been processed"
                assert "https://en.wikipedia.org/wiki/Root_Article_2" in processed_urls, \
                    "Root article 2 should have been processed"