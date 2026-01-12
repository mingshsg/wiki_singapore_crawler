"""Property-based tests for CategoryPageHandler."""

import pytest
from hypothesis import given, strategies as st, assume, settings
from bs4 import BeautifulSoup
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch

from wikipedia_crawler.processors.category_handler import CategoryPageHandler
from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.models.data_models import CategoryData


# Test data generators
@st.composite
def wikipedia_category_html(draw):
    """Generate realistic Wikipedia category page HTML."""
    title = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=['Lu', 'Ll', 'Nd', 'Pc'], 
        whitelist_characters=' -_'
    )))
    
    # Ensure title is not empty after stripping and has meaningful content
    assume(len(title.strip()) > 0)
    assume(not all(c in '_-. ()[]' for c in title.strip()))
    
    # Generate subcategories
    num_subcategories = draw(st.integers(min_value=0, max_value=10))
    subcategories = []
    for _ in range(num_subcategories):
        subcat_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=['Lu', 'Ll', 'Nd', 'Pc'], 
            whitelist_characters=' -_'
        )))
        subcategories.append(subcat_name)
    
    # Generate articles
    num_articles = draw(st.integers(min_value=0, max_value=20))
    articles = []
    for _ in range(num_articles):
        article_name = draw(st.text(min_size=1, max_size=80, alphabet=st.characters(
            whitelist_categories=['Lu', 'Ll', 'Nd', 'Pc'], 
            whitelist_characters=' -_'
        )))
        articles.append(article_name)
    
    # Build HTML structure
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head><title>Category:' + title + ' - Wikipedia</title></head>',
        '<body>',
        '<h1 id="firstHeading">Category:' + title + '</h1>',
        '<div id="mw-content-text">',
    ]
    
    # Add subcategories section if any
    if subcategories:
        html_parts.extend([
            '<div id="mw-subcategories">',
            '<h2>Subcategories</h2>',
            '<div class="CategoryTreeTag">',
        ])
        for subcat in subcategories:
            html_parts.append(f'<a href="/wiki/Category:{subcat.replace(" ", "_")}">{subcat}</a>')
        html_parts.extend(['</div>', '</div>'])
    
    # Add articles section if any
    if articles:
        html_parts.extend([
            '<div id="mw-pages">',
            '<h2>Pages in category "' + title + '"</h2>',
        ])
        for article in articles:
            html_parts.append(f'<a href="/wiki/{article.replace(" ", "_")}">{article}</a>')
        html_parts.append('</div>')
    
    html_parts.extend(['</div>', '</body>', '</html>'])
    
    return {
        'html': '\n'.join(html_parts),
        'title': title,
        'expected_subcategories': [f"https://en.wikipedia.org/wiki/Category:{s.replace(' ', '_')}" 
                                 for s in subcategories],
        'expected_articles': [f"https://en.wikipedia.org/wiki/{a.replace(' ', '_')}" 
                            for a in articles]
    }


@st.composite
def wikipedia_urls(draw):
    """Generate valid Wikipedia URLs."""
    page_name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=['Lu', 'Ll', 'Nd', 'Pc'], 
        whitelist_characters=' -_'
    )))
    
    url_type = draw(st.sampled_from(['article', 'category']))
    
    if url_type == 'category':
        return f"https://en.wikipedia.org/wiki/Category:{page_name.replace(' ', '_')}"
    else:
        return f"https://en.wikipedia.org/wiki/{page_name.replace(' ', '_')}"


class TestCategoryPageHandler:
    """Test suite for CategoryPageHandler with property-based testing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_storage = FileStorage(self.temp_dir)
        self.handler = CategoryPageHandler(self.file_storage, max_depth=5)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @given(wikipedia_category_html())
    @settings(max_examples=50, deadline=5000)
    def test_property_category_link_extraction_completeness(self, category_data):
        """
        Feature: wikipedia-singapore-crawler, Property 1: Category Link Extraction Completeness
        
        For any Wikipedia category page HTML content, extracting subcategory and article 
        links should return all valid Wikipedia links from the respective sections without 
        duplicates or invalid URLs.
        """
        html_content = category_data['html']
        expected_subcategories = set(category_data['expected_subcategories'])
        expected_articles = set(category_data['expected_articles'])
        
        # Process the category page
        result = self.handler.process_category(
            url="https://en.wikipedia.org/wiki/Category:Test",
            content=html_content,
            depth=0
        )
        
        # Verify processing succeeded
        assert result.success, f"Processing failed: {result.error_message}"
        assert result.page_type == "category"
        
        # Extract discovered URLs by type
        discovered_urls = result.discovered_urls or []
        discovered_subcategories = set()
        discovered_articles = set()
        
        for url in discovered_urls:
            if '/Category:' in url:
                discovered_subcategories.add(url)
            else:
                discovered_articles.add(url)
        
        # Property 1a: All expected subcategories should be found
        missing_subcategories = expected_subcategories - discovered_subcategories
        assert len(missing_subcategories) == 0, f"Missing subcategories: {missing_subcategories}"
        
        # Property 1b: All expected articles should be found
        missing_articles = expected_articles - discovered_articles
        assert len(missing_articles) == 0, f"Missing articles: {missing_articles}"
        
        # Property 1c: No duplicates in discovered URLs
        assert len(discovered_urls) == len(set(discovered_urls)), "Duplicate URLs found"
        
        # Property 1d: All discovered URLs should be valid Wikipedia URLs
        for url in discovered_urls:
            assert url.startswith('https://'), f"Non-HTTPS URL: {url}"
            assert 'wikipedia.org' in url, f"Non-Wikipedia URL: {url}"
            assert '/wiki/' in url, f"Invalid wiki URL: {url}"
        
        # Property 1e: No invalid URLs should be included
        for url in discovered_urls:
            # Should not contain special pages
            invalid_patterns = ['/Special:', '/Help:', '/Template:', '/User:', '/Talk:']
            assert not any(pattern in url for pattern in invalid_patterns), \
                f"Invalid URL pattern found: {url}"
    
    @given(st.text(min_size=1, max_size=200, alphabet=st.characters(
        whitelist_categories=['Lu', 'Ll', 'Nd', 'Pc'], 
        whitelist_characters=' -_()[]'
    )))
    @settings(max_examples=30)
    def test_title_extraction_robustness(self, title_text):
        """Test that title extraction handles various title formats correctly."""
        assume(len(title_text.strip()) > 0)
        # Avoid titles that would result in empty filenames after sanitization
        assume(not all(c in '_-. ()[]' for c in title_text))
        
        # Create minimal HTML with title
        html = f'''
        <html>
        <head><title>Category:{title_text} - Wikipedia</title></head>
        <body>
        <h1 id="firstHeading">Category:{title_text}</h1>
        <div id="mw-content-text"></div>
        </body>
        </html>
        '''
        
        result = self.handler.process_category(
            url="https://en.wikipedia.org/wiki/Category:Test",
            content=html,
            depth=0
        )
        
        assert result.success
        assert result.data['title'] == title_text.strip()
    
    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=20)
    def test_depth_limiting_behavior(self, depth):
        """Test that depth limiting works correctly for subcategory processing."""
        # Create HTML with subcategories
        html = '''
        <html>
        <body>
        <h1 id="firstHeading">Category:Test</h1>
        <div id="mw-content-text">
        <div id="mw-subcategories">
        <a href="/wiki/Category:Subcategory1">Subcategory1</a>
        <a href="/wiki/Category:Subcategory2">Subcategory2</a>
        </div>
        <div id="mw-pages">
        <a href="/wiki/Article1">Article1</a>
        </div>
        </div>
        </body>
        </html>
        '''
        
        result = self.handler.process_category(
            url="https://en.wikipedia.org/wiki/Category:Test",
            content=html,
            depth=depth
        )
        
        assert result.success
        discovered_urls = result.discovered_urls or []
        
        # Count subcategories and articles
        subcategories = [url for url in discovered_urls if '/Category:' in url]
        articles = [url for url in discovered_urls if '/Category:' not in url]
        
        # Articles should always be included
        assert len(articles) == 1
        
        # Subcategories should only be included if depth < max_depth
        if depth < self.handler.max_depth:
            assert len(subcategories) == 2, f"Expected 2 subcategories at depth {depth}"
        else:
            assert len(subcategories) == 0, f"Expected 0 subcategories at depth {depth}"
    
    @given(wikipedia_urls())
    @settings(max_examples=30)
    def test_url_validation_consistency(self, url):
        """Test that URL validation is consistent and correct."""
        is_valid = self.handler._is_valid_wikipedia_url(url)
        
        # All generated URLs should be valid
        assert is_valid, f"Generated URL should be valid: {url}"
        
        # Test with invalid modifications
        invalid_variants = [
            url.replace('https://', 'http://'),  # Non-HTTPS
            url.replace('wikipedia.org', 'example.com'),  # Non-Wikipedia
            url + '#fragment',  # With fragment (should still be valid)
            url + '?param=value',  # With query params (should still be valid)
        ]
        
        # HTTP variant should be invalid
        assert not self.handler._is_valid_wikipedia_url(invalid_variants[0])
        # Non-Wikipedia should be invalid
        assert not self.handler._is_valid_wikipedia_url(invalid_variants[1])
    
    def test_malformed_html_handling(self):
        """Test handling of malformed or incomplete HTML."""
        malformed_htmls = [
            "",  # Empty content
            "<html><body></body></html>",  # No category content
            "<html><body><h1>No ID</h1></body></html>",  # Missing required elements
            "<html><body><div>Broken HTML",  # Unclosed tags
            "Not HTML at all",  # Plain text
        ]
        
        for html in malformed_htmls:
            result = self.handler.process_category(
                url="https://en.wikipedia.org/wiki/Category:Test",
                content=html,
                depth=0
            )
            
            # Should not crash, but may succeed with empty results
            assert isinstance(result.success, bool)
            if result.success:
                # If successful, should have valid structure
                assert isinstance(result.discovered_urls, list)
                assert isinstance(result.data, dict)
    
    def test_file_storage_integration(self):
        """Test integration with FileStorage for saving category data."""
        html = '''
        <html>
        <body>
        <h1 id="firstHeading">Category:Singapore</h1>
        <div id="mw-content-text">
        <div id="mw-subcategories">
        <a href="/wiki/Category:Singapore_culture">Singapore culture</a>
        </div>
        </div>
        </body>
        </html>
        '''
        
        result = self.handler.process_category(
            url="https://en.wikipedia.org/wiki/Category:Singapore",
            content=html,
            depth=0
        )
        
        assert result.success
        
        # Check that file was saved
        saved_files = list(self.temp_dir.glob("*.json"))
        assert len(saved_files) == 1
        
        # Verify file content
        import json
        with open(saved_files[0], 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data['title'] == 'Singapore'
        assert saved_data['type'] == 'category'
        assert len(saved_data['subcategories']) == 1
    
    def test_statistics_tracking(self):
        """Test that processing statistics are tracked correctly."""
        initial_stats = self.handler.get_stats()
        
        html = '''
        <html>
        <body>
        <h1 id="firstHeading">Category:Test</h1>
        <div id="mw-content-text">
        <div id="mw-subcategories">
        <a href="/wiki/Category:Sub1">Sub1</a>
        <a href="/wiki/Category:Sub2">Sub2</a>
        </div>
        <div id="mw-pages">
        <a href="/wiki/Article1">Article1</a>
        <a href="/wiki/Article2">Article2</a>
        <a href="/wiki/Article3">Article3</a>
        </div>
        </div>
        </body>
        </html>
        '''
        
        result = self.handler.process_category(
            url="https://en.wikipedia.org/wiki/Category:Test",
            content=html,
            depth=0
        )
        
        assert result.success
        
        final_stats = self.handler.get_stats()
        
        # Verify statistics were updated
        assert final_stats['categories_processed'] == initial_stats['categories_processed'] + 1
        assert final_stats['subcategories_found'] == initial_stats['subcategories_found'] + 2
        assert final_stats['articles_found'] == initial_stats['articles_found'] + 3
    
    def test_error_handling_and_recovery(self):
        """Test error handling when file storage fails."""
        # Mock file storage to raise an exception
        with patch.object(self.file_storage, 'save_category', side_effect=IOError("Disk full")):
            html = '''
            <html>
            <body>
            <h1 id="firstHeading">Category:Test</h1>
            <div id="mw-content-text"></div>
            </body>
            </html>
            '''
            
            result = self.handler.process_category(
                url="https://en.wikipedia.org/wiki/Category:Test",
                content=html,
                depth=0
            )
            
            # Should fail gracefully
            assert not result.success
            assert "Disk full" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])