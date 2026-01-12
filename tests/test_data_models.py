"""Property-based tests for data model serialization."""

import json
from datetime import datetime
from hypothesis import given, strategies as st
from hypothesis.strategies import composite
import pytest

from wikipedia_crawler.models import (
    URLItem, CategoryData, ArticleData, ProcessResult, CrawlStatus, URLType, ProcessStatus
)


# Custom strategies for generating test data
@composite
def wikipedia_urls(draw):
    """Generate valid Wikipedia URLs."""
    domains = ['en.wikipedia.org', 'zh.wikipedia.org']
    domain = draw(st.sampled_from(domains))
    
    # Generate path components
    path_chars = st.characters(
        whitelist_categories=['Lu', 'Ll', 'Nd'],
        whitelist_characters='_-()[]{}.,;:!?'
    )
    path_component = draw(st.text(path_chars, min_size=1, max_size=50))
    
    return f"https://{domain}/wiki/{path_component}"


@composite
def category_urls(draw):
    """Generate valid Wikipedia category URLs."""
    base_url = draw(wikipedia_urls())
    if '/wiki/' in base_url:
        base_url = base_url.replace('/wiki/', '/wiki/Category:')
    return base_url


@composite
def safe_text(draw):
    """Generate text that's safe for JSON serialization."""
    return draw(st.text(
        alphabet=st.characters(
            whitelist_categories=['Lu', 'Ll', 'Nd', 'Zs'],
            whitelist_characters='.,;:!?()-[]{}"\''
        ),
        min_size=1,
        max_size=200
    ))


@composite
def url_lists(draw):
    """Generate lists of Wikipedia URLs."""
    return draw(st.lists(wikipedia_urls(), min_size=0, max_size=10))


class TestDataModelSerialization:
    """Test data model serialization properties."""
    
    @given(
        url=wikipedia_urls(),
        title=safe_text(),
        subcategories=url_lists(),
        articles=url_lists()
    )
    def test_category_data_serialization_round_trip(self, url, title, subcategories, articles):
        """
        Property 4: File Storage Integrity - CategoryData serialization
        For any CategoryData instance, serializing to dict and back should preserve all data.
        **Feature: wikipedia-singapore-crawler, Property 4: File Storage Integrity**
        **Validates: Requirements 1.3, 2.6**
        """
        # Create original CategoryData
        original = CategoryData(
            url=url,
            title=title,
            subcategories=subcategories,
            articles=articles,
            processed_at=datetime.now()
        )
        
        # Serialize to dict and back
        data_dict = original.to_dict()
        restored = CategoryData.from_dict(data_dict)
        
        # Verify all fields are preserved
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.subcategories == original.subcategories
        assert restored.articles == original.articles
        # Allow small datetime differences due to serialization
        assert abs((restored.processed_at - original.processed_at).total_seconds()) < 1
        
        # Verify JSON serialization works
        json_str = original.to_json()
        parsed_json = json.loads(json_str)
        assert parsed_json['type'] == 'category'
        assert parsed_json['url'] == url
        assert parsed_json['title'] == title
    
    @given(
        url=wikipedia_urls(),
        title=safe_text(),
        content=safe_text(),
        language=st.sampled_from(['en', 'zh-cn', 'zh', 'fr', 'de', 'es'])
    )
    def test_article_data_serialization_round_trip(self, url, title, content, language):
        """
        Property 4: File Storage Integrity - ArticleData serialization
        For any ArticleData instance, serializing to dict and back should preserve all data.
        **Feature: wikipedia-singapore-crawler, Property 4: File Storage Integrity**
        **Validates: Requirements 1.3, 2.6**
        """
        # Create original ArticleData
        original = ArticleData(
            url=url,
            title=title,
            content=content,
            language=language,
            processed_at=datetime.now()
        )
        
        # Serialize to dict and back
        data_dict = original.to_dict()
        restored = ArticleData.from_dict(data_dict)
        
        # Verify all fields are preserved
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.content == original.content
        assert restored.language == original.language
        # Allow small datetime differences due to serialization
        assert abs((restored.processed_at - original.processed_at).total_seconds()) < 1
        
        # Verify JSON serialization works
        json_str = original.to_json()
        parsed_json = json.loads(json_str)
        assert parsed_json['type'] == 'article'
        assert parsed_json['url'] == url
        assert parsed_json['title'] == title
        assert parsed_json['language'] == language
    
    @given(
        is_running=st.booleans(),
        total_processed=st.integers(min_value=0, max_value=10000),
        pending_urls=st.integers(min_value=0, max_value=1000),
        categories_processed=st.integers(min_value=0, max_value=1000),
        articles_processed=st.integers(min_value=0, max_value=1000),
        filtered_count=st.integers(min_value=0, max_value=1000),
        error_count=st.integers(min_value=0, max_value=100)
    )
    def test_crawl_status_serialization_and_metrics(
        self, is_running, total_processed, pending_urls, 
        categories_processed, articles_processed, filtered_count, error_count
    ):
        """
        Property 4: File Storage Integrity - CrawlStatus serialization and metrics
        For any CrawlStatus instance, serialization should preserve data and metrics should be consistent.
        **Feature: wikipedia-singapore-crawler, Property 4: File Storage Integrity**
        **Validates: Requirements 1.3, 2.6**
        """
        # Ensure total_processed is consistent with individual counts
        actual_total = categories_processed + articles_processed + filtered_count + error_count
        if actual_total > 0:
            total_processed = actual_total
        
        # Create CrawlStatus
        status = CrawlStatus(
            is_running=is_running,
            total_processed=total_processed,
            pending_urls=pending_urls,
            categories_processed=categories_processed,
            articles_processed=articles_processed,
            filtered_count=filtered_count,
            error_count=error_count
        )
        
        # Test serialization
        status_dict = status.to_dict()
        
        # Verify all fields are present and correct
        assert status_dict['is_running'] == is_running
        assert status_dict['total_processed'] == total_processed
        assert status_dict['pending_urls'] == pending_urls
        assert status_dict['categories_processed'] == categories_processed
        assert status_dict['articles_processed'] == articles_processed
        assert status_dict['filtered_count'] == filtered_count
        assert status_dict['error_count'] == error_count
        
        # Test metrics consistency
        success_rate = status.get_success_rate()
        if total_processed == 0:
            assert success_rate == 0.0
        else:
            expected_success = (categories_processed + articles_processed) / total_processed
            assert abs(success_rate - expected_success) < 0.001
        
        # Test processing summary
        summary = status.get_processing_summary()
        assert isinstance(summary, str)
        
        # Handle special case where status shows "Not started"
        if not is_running and total_processed == 0:
            assert summary == "Not started"
        else:
            assert str(total_processed) in summary
            assert str(categories_processed) in summary
            assert str(articles_processed) in summary
    
    @given(
        success=st.booleans(),
        url=wikipedia_urls(),
        page_type=st.one_of(st.none(), st.sampled_from(['category', 'article', 'unknown'])),
        error_message=st.one_of(st.none(), safe_text()),
        discovered_urls=st.one_of(st.none(), url_lists())
    )
    def test_process_result_validation_and_consistency(
        self, success, url, page_type, error_message, discovered_urls
    ):
        """
        Property 4: File Storage Integrity - ProcessResult validation
        For any ProcessResult, the success flag should be consistent with error_message.
        **Feature: wikipedia-singapore-crawler, Property 4: File Storage Integrity**
        **Validates: Requirements 1.3, 2.6**
        """
        # Ensure validation rules are met
        if not success and not error_message:
            error_message = "Test error message"  # Required for failed results
        
        # Create ProcessResult
        result = ProcessResult(
            success=success,
            url=url,
            page_type=page_type,
            error_message=error_message,
            discovered_urls=discovered_urls
        )
        
        # Verify fields are set correctly
        assert result.success == success
        assert result.url == url
        assert result.page_type == page_type
        assert result.error_message == error_message
        assert result.discovered_urls == discovered_urls
        
        # Test logical consistency: failed results should have error messages
        if not success:
            assert result.error_message is not None, "Failed results must have error_message"
    
    @given(
        url=wikipedia_urls(),
        url_type=st.sampled_from([URLType.CATEGORY, URLType.ARTICLE]),
        priority=st.integers(min_value=0, max_value=100),
        depth=st.integers(min_value=0, max_value=10)
    )
    def test_url_item_validation_and_properties(self, url, url_type, priority, depth):
        """
        Property 4: File Storage Integrity - URLItem validation
        For any valid URLItem, all validation rules should be satisfied.
        **Feature: wikipedia-singapore-crawler, Property 4: File Storage Integrity**
        **Validates: Requirements 1.3, 2.6**
        """
        # Create URLItem
        url_item = URLItem(
            url=url,
            url_type=url_type,
            priority=priority,
            depth=depth
        )
        
        # Verify fields are set correctly
        assert url_item.url == url
        assert url_item.url_type == url_type
        assert url_item.priority == priority
        assert url_item.depth == depth
        assert isinstance(url_item.discovered_at, datetime)
        
        # Verify URL validation rules
        assert url_item.url.startswith('https://')
        assert 'wikipedia.org' in url_item.url
    
    def test_invalid_url_item_creation(self):
        """Test that invalid URLs are properly rejected."""
        # Test non-HTTPS URL
        with pytest.raises(ValueError, match="URL must use HTTPS protocol"):
            URLItem("http://en.wikipedia.org/wiki/Test", URLType.ARTICLE)
        
        # Test non-Wikipedia URL
        with pytest.raises(ValueError, match="URL must be from Wikipedia"):
            URLItem("https://example.com/test", URLType.ARTICLE)
    
    def test_invalid_process_result_creation(self):
        """Test that invalid ProcessResult types are rejected."""
        # Test invalid page_type
        with pytest.raises(ValueError, match="page_type must be one of"):
            ProcessResult(True, "https://en.wikipedia.org/wiki/Test", page_type="invalid_type")
        
        # Test failed result without error_message
        with pytest.raises(ValueError, match="error_message is required when success is False"):
            ProcessResult(False, "https://en.wikipedia.org/wiki/Test")


if __name__ == "__main__":
    # Run a quick test to verify the test setup works
    import sys
    
    try:
        # Test basic functionality
        category = CategoryData(
            url="https://en.wikipedia.org/wiki/Category:Singapore",
            title="Singapore",
            subcategories=["Category:Singapore_history"],
            articles=["Singapore"]
        )
        
        # Test serialization
        data_dict = category.to_dict()
        restored = CategoryData.from_dict(data_dict)
        
        print("✓ Basic serialization test passed")
        print("✓ Property tests are ready to run with: pytest tests/test_data_models.py")
        
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        sys.exit(1)