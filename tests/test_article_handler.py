"""Unit tests for ArticlePageHandler."""

import pytest
from pathlib import Path
import tempfile
import shutil
import json
from unittest.mock import Mock, patch

from wikipedia_crawler.processors.article_handler import ArticlePageHandler
from wikipedia_crawler.processors.content_processor import ContentProcessor
from wikipedia_crawler.processors.language_filter import LanguageFilter
from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.models.data_models import ArticleData


class TestArticlePageHandler:
    """Test suite for ArticlePageHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_storage = FileStorage(self.temp_dir)
        self.content_processor = ContentProcessor()
        self.language_filter = LanguageFilter()
        self.handler = ArticlePageHandler(
            self.file_storage,
            self.content_processor,
            self.language_filter
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_process_article_success_english(self):
        """Test successful processing of an English Wikipedia article."""
        html_content = '''
        <html>
        <head><title>Singapore - Wikipedia</title></head>
        <body>
        <h1 id="firstHeading">Singapore</h1>
        <div id="mw-content-text">
        <div class="mw-parser-output">
        <p>Singapore is a sovereign city-state and island country in Southeast Asia.</p>
        <h2>History</h2>
        <p>Singapore was founded as a British trading colony in 1819.</p>
        <h2>Geography</h2>
        <p>Singapore consists of 63 islands, including the main island.</p>
        </div>
        </div>
        </body>
        </html>
        '''
        
        result = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Singapore",
            content=html_content
        )
        
        assert result.success
        assert result.page_type == "article"
        assert result.data['title'] == 'Singapore'
        assert result.data['language'] == 'en'
        assert not result.data['filtered']
        assert result.data['content_length'] > 0
        
        # Check that file was saved
        saved_files = list(self.temp_dir.glob("*.json"))
        assert len(saved_files) == 1
        
        # Verify file content
        with open(saved_files[0], 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data['title'] == 'Singapore'
        assert saved_data['type'] == 'article'
        assert saved_data['language'] == 'en'
        assert 'Singapore is a sovereign city-state' in saved_data['content']
    
    def test_process_article_success_chinese(self):
        """Test successful processing of a Chinese Wikipedia article."""
        html_content = '''
        <html>
        <head><title>新加坡 - 维基百科</title></head>
        <body>
        <h1 id="firstHeading">新加坡</h1>
        <div id="mw-content-text">
        <div class="mw-parser-output">
        <p>新加坡共和国是东南亚的一个岛国城邦。</p>
        <h2>历史</h2>
        <p>新加坡于1819年被英国建立为贸易殖民地。</p>
        </div>
        </div>
        </body>
        </html>
        '''
        
        result = self.handler.process_article(
            url="https://zh.wikipedia.org/wiki/新加坡",
            content=html_content
        )
        
        assert result.success
        assert result.page_type == "article"
        assert result.data['title'] == '新加坡'
        assert result.data['language'] == 'zh'
        assert not result.data['filtered']
    
    def test_process_article_filtered_language(self):
        """Test article filtering for unsupported language."""
        # Mock language filter to return unsupported language
        mock_language_filter = Mock()
        mock_language_filter.filter_content.return_value = (False, 'fr')
        
        handler = ArticlePageHandler(
            self.file_storage,
            self.content_processor,
            mock_language_filter
        )
        
        html_content = '''
        <html>
        <body>
        <h1 id="firstHeading">Paris</h1>
        <div id="mw-content-text">
        <p>Paris est la capitale de la France et une grande ville européenne.</p>
        <p>Elle est située sur la Seine et compte plusieurs millions d'habitants.</p>
        </div>
        </body>
        </html>
        '''
        
        result = handler.process_article(
            url="https://fr.wikipedia.org/wiki/Paris",
            content=html_content
        )
        
        assert result.success
        assert result.data['filtered']
        assert result.data['language'] == 'fr'
        assert 'Unsupported language' in result.data['reason']
        
        # No file should be saved for filtered content
        saved_files = list(self.temp_dir.glob("*.json"))
        assert len(saved_files) == 0
    
    def test_process_article_no_content(self):
        """Test handling of pages with no extractable content."""
        html_content = '''
        <html>
        <body>
        <h1 id="firstHeading">Empty Page</h1>
        <div id="mw-content-text">
        <!-- No actual content -->
        </div>
        </body>
        </html>
        '''
        
        result = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Empty_Page",
            content=html_content
        )
        
        assert not result.success
        assert "Insufficient content after processing" in result.error_message
    
    def test_process_article_malformed_html(self):
        """Test handling of malformed HTML content."""
        malformed_htmls = [
            "",  # Empty content
            "<html><body></body></html>",  # No content
            "<html><body><h1>Broken HTML",  # Unclosed tags
            "Not HTML at all",  # Plain text
        ]
        
        for html in malformed_htmls:
            result = self.handler.process_article(
                url="https://en.wikipedia.org/wiki/Test",
                content=html
            )
            
            # Should not crash, but may fail gracefully
            assert isinstance(result.success, bool)
            if not result.success:
                assert result.error_message is not None
    
    def test_title_extraction_methods(self):
        """Test various methods of title extraction."""
        # Test with firstHeading
        html1 = '''
        <html>
        <body>
        <h1 id="firstHeading">Title from H1</h1>
        <div id="mw-content-text">
        <p>This is substantial content for testing title extraction methods.</p>
        <p>It has multiple paragraphs to ensure it passes content validation.</p>
        </div>
        </body>
        </html>
        '''
        
        result1 = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Test1",
            content=html1
        )
        assert result1.success
        assert result1.data['title'] == 'Title from H1'
        
        # Test with title tag
        html2 = '''
        <html>
        <head><title>Title from Head - Wikipedia</title></head>
        <body>
        <div id="mw-content-text">
        <p>This is substantial content for testing title extraction from head tag.</p>
        <p>Multiple paragraphs ensure content validation passes successfully.</p>
        </div>
        </body>
        </html>
        '''
        
        result2 = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Test2",
            content=html2
        )
        assert result2.success
        assert result2.data['title'] == 'Title from Head'
        
        # Test with URL fallback
        html3 = '''
        <html>
        <body>
        <div id="mw-content-text">
        <p>This content has no title elements, so title should come from URL.</p>
        <p>Multiple paragraphs ensure the content passes validation checks.</p>
        </div>
        </body>
        </html>
        '''
        
        result3 = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/URL_Title_Test",
            content=html3
        )
        assert result3.success
        assert result3.data['title'] == 'URL Title Test'
    
    def test_content_extraction_methods(self):
        """Test various methods of content extraction."""
        # Test with mw-content-text and mw-parser-output
        html1 = '''
        <html>
        <body>
        <h1 id="firstHeading">Test</h1>
        <div id="mw-content-text">
        <div class="mw-parser-output">
        <p>Main content here with substantial text for testing extraction methods.</p>
        <p>Additional paragraph to ensure content validation passes.</p>
        </div>
        </div>
        </body>
        </html>
        '''
        
        result1 = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Test1",
            content=html1
        )
        assert result1.success
        
        # Test with just mw-parser-output
        html2 = '''
        <html>
        <body>
        <h1 id="firstHeading">Test</h1>
        <div class="mw-parser-output">
        <p>Parser output content with substantial text for testing.</p>
        <p>Multiple paragraphs ensure content validation succeeds.</p>
        </div>
        </body>
        </html>
        '''
        
        result2 = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Test2",
            content=html2
        )
        assert result2.success
        
        # Test with bodyContent fallback
        html3 = '''
        <html>
        <body>
        <h1 id="firstHeading">Test</h1>
        <div id="bodyContent">
        <p>Body content here with substantial text for testing extraction.</p>
        <p>Additional content to ensure validation passes successfully.</p>
        </div>
        </body>
        </html>
        '''
        
        result3 = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Test3",
            content=html3
        )
        assert result3.success
    
    def test_content_processor_integration(self):
        """Test integration with ContentProcessor."""
        html_content = '''
        <html>
        <body>
        <h1 id="firstHeading">Test Article</h1>
        <div id="mw-content-text">
        <div class="mw-parser-output">
        <p>This is a <strong>test</strong> article with <em>formatting</em>.</p>
        <table class="infobox">
        <tr><td>Should be removed</td></tr>
        </table>
        <h2>Section</h2>
        <p>More content here.</p>
        </div>
        </div>
        </body>
        </html>
        '''
        
        result = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Test_Article",
            content=html_content
        )
        
        assert result.success
        
        # Check that file was saved and content was processed
        saved_files = list(self.temp_dir.glob("*.json"))
        assert len(saved_files) == 1
        
        with open(saved_files[0], 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        content = saved_data['content']
        
        # Should contain processed markdown
        assert 'test' in content.lower()
        assert 'section' in content.lower()
        
        # Infobox should be removed by content processor
        assert 'Should be removed' not in content
    
    def test_language_filter_integration(self):
        """Test integration with LanguageFilter."""
        # Test with supported language
        html_en = '''
        <html>
        <body>
        <h1 id="firstHeading">English Article</h1>
        <div id="mw-content-text">
        <p>This is an English article about Singapore with substantial content.</p>
        <p>Singapore is a city-state in Southeast Asia with rich history and culture.</p>
        </div>
        </body>
        </html>
        '''
        
        result_en = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/English_Article",
            content=html_en
        )
        
        assert result_en.success
        assert not result_en.data['filtered']
        assert result_en.data['language'] == 'en'
        
        # Test with Chinese content
        html_zh = '''
        <html>
        <body>
        <h1 id="firstHeading">中文文章</h1>
        <div id="mw-content-text">
        <p>这是一篇关于新加坡的中文文章，包含丰富的内容和信息。</p>
        <p>新加坡是东南亚的城市国家，拥有悠久的历史和多元文化。</p>
        </div>
        </body>
        </html>
        '''
        
        result_zh = self.handler.process_article(
            url="https://zh.wikipedia.org/wiki/中文文章",
            content=html_zh
        )
        
        assert result_zh.success
        assert not result_zh.data['filtered']
        assert result_zh.data['language'] == 'zh'
    
    def test_statistics_tracking(self):
        """Test that processing statistics are tracked correctly."""
        initial_stats = self.handler.get_stats()
        
        # Process successful article
        html_success = '''
        <html>
        <body>
        <h1 id="firstHeading">Success Article</h1>
        <div id="mw-content-text">
        <p>This article will be processed successfully with substantial content.</p>
        <p>It contains multiple paragraphs to ensure proper validation and processing.</p>
        </div>
        </body>
        </html>
        '''
        
        result1 = self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Success_Article",
            content=html_success
        )
        assert result1.success
        
        # Process article that will be filtered
        mock_language_filter = Mock()
        mock_language_filter.filter_content.return_value = (False, 'fr')
        
        handler_with_mock = ArticlePageHandler(
            self.file_storage,
            self.content_processor,
            mock_language_filter
        )
        
        result2 = handler_with_mock.process_article(
            url="https://fr.wikipedia.org/wiki/French_Article",
            content=html_success.replace('Success Article', 'French Article')
        )
        assert result2.success and result2.data['filtered']
        
        # Check statistics
        final_stats = self.handler.get_stats()
        
        assert final_stats['articles_processed'] == initial_stats['articles_processed'] + 1
        assert final_stats['articles_saved'] == initial_stats['articles_saved'] + 1
        assert 'en' in final_stats['languages_detected']
    
    def test_error_handling_content_processor_failure(self):
        """Test error handling when ContentProcessor fails."""
        # Mock content processor to raise an exception
        mock_content_processor = Mock()
        mock_content_processor.process_content.side_effect = Exception("Processing failed")
        
        handler = ArticlePageHandler(
            self.file_storage,
            mock_content_processor,
            self.language_filter
        )
        
        html_content = '''
        <html>
        <body>
        <h1 id="firstHeading">Test</h1>
        <div id="mw-content-text"><p>Content</p></div>
        </body>
        </html>
        '''
        
        result = handler.process_article(
            url="https://en.wikipedia.org/wiki/Test",
            content=html_content
        )
        
        assert not result.success
        assert "Content processing failed" in result.error_message
    
    def test_error_handling_file_storage_failure(self):
        """Test error handling when FileStorage fails."""
        # Mock file storage to raise an exception
        mock_file_storage = Mock()
        mock_file_storage.save_article.side_effect = IOError("Disk full")
        
        handler = ArticlePageHandler(
            mock_file_storage,
            self.content_processor,
            self.language_filter
        )
        
        html_content = '''
        <html>
        <body>
        <h1 id="firstHeading">Test</h1>
        <div id="mw-content-text">
        <p>This is a test article with enough content for validation.</p>
        <p>Multiple paragraphs ensure the content passes all checks.</p>
        </div>
        </body>
        </html>
        '''
        
        result = handler.process_article(
            url="https://en.wikipedia.org/wiki/Test",
            content=html_content
        )
        
        assert not result.success
        assert "Failed to save article" in result.error_message
    
    def test_substantial_content_detection(self):
        """Test detection of substantial article content."""
        # Test with substantial content
        substantial_html = '''
        <div>
        <p>This is a substantial paragraph with enough content to be considered meaningful.</p>
        <p>Another paragraph with more content and information.</p>
        <h2>A heading</h2>
        <p>More content under the heading.</p>
        </div>
        '''
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(substantial_html, 'html.parser')
        div = soup.find('div')
        
        assert self.handler._is_substantial_content(div)
        
        # Test with minimal content
        minimal_html = '''
        <div>
        <p>Short.</p>
        </div>
        '''
        
        soup = BeautifulSoup(minimal_html, 'html.parser')
        div = soup.find('div')
        
        assert not self.handler._is_substantial_content(div)
        
        # Test with no content
        assert not self.handler._is_substantial_content(None)
    
    def test_get_processor_stats(self):
        """Test getting statistics from integrated processors."""
        # Test language filter stats
        lang_stats = self.handler.get_language_filter_stats()
        assert isinstance(lang_stats, dict)
        
        # Test content processor stats (may not have stats method)
        content_stats = self.handler.get_content_processor_stats()
        assert isinstance(content_stats, dict)
    
    def test_reset_stats(self):
        """Test resetting processing statistics."""
        # Process an article to generate some stats
        html_content = '''
        <html>
        <body>
        <h1 id="firstHeading">Test</h1>
        <div id="mw-content-text">
        <p>Test content for statistics with substantial text content.</p>
        <p>Multiple paragraphs ensure proper processing and validation.</p>
        </div>
        </body>
        </html>
        '''
        
        self.handler.process_article(
            url="https://en.wikipedia.org/wiki/Test",
            content=html_content
        )
        
        # Check that stats were updated
        stats_before = self.handler.get_stats()
        assert stats_before['articles_processed'] > 0
        
        # Reset stats
        self.handler.reset_stats()
        
        # Check that stats were reset
        stats_after = self.handler.get_stats()
        assert stats_after['articles_processed'] == 0
        assert stats_after['articles_saved'] == 0
        assert stats_after['languages_detected'] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])