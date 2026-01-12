"""Article page handler for processing Wikipedia article pages."""

from typing import Optional
from bs4 import BeautifulSoup

from wikipedia_crawler.models.data_models import ArticleData, ProcessResult
from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.processors.content_processor import ContentProcessor
from wikipedia_crawler.processors.language_filter import LanguageFilter
from wikipedia_crawler.utils.logging_config import get_logger


class ArticlePageHandler:
    """
    Handler for processing Wikipedia article pages.
    
    Features:
    - Extracts main article content from Wikipedia pages
    - Integrates with ContentProcessor for HTML-to-markdown conversion
    - Integrates with LanguageFilter for language detection and filtering
    - Saves processed articles as JSON files
    - Handles various Wikipedia article layouts and structures
    """
    
    def __init__(self, 
                 file_storage: FileStorage,
                 content_processor: Optional[ContentProcessor] = None,
                 language_filter: Optional[LanguageFilter] = None):
        """
        Initialize the article page handler.
        
        Args:
            file_storage: FileStorage instance for saving data
            content_processor: ContentProcessor instance (creates new if None)
            language_filter: LanguageFilter instance (creates new if None)
        """
        self.file_storage = file_storage
        self.content_processor = content_processor or ContentProcessor()
        self.language_filter = language_filter or LanguageFilter()
        self.logger = get_logger(__name__)
        
        # Statistics
        self._stats = {
            'articles_processed': 0,
            'articles_saved': 0,
            'articles_filtered': 0,
            'processing_errors': 0,
            'languages_detected': {}
        }
        
        self.logger.info("ArticlePageHandler initialized")
    
    def process_article(self, url: str, content: str) -> ProcessResult:
        """
        Process a Wikipedia article page.
        
        Args:
            url: URL of the article page
            content: HTML content of the page
            
        Returns:
            ProcessResult with processing status and metadata
        """
        try:
            self.logger.info(f"Processing article page: {url}")
            
            # Parse HTML content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract page title
            title = self._extract_title(soup, url)
            
            # Extract main article content
            article_html = self._extract_article_content(soup)
            
            if not article_html or not article_html.strip():
                self.logger.warning(f"No content extracted from article: {url}")
                return ProcessResult(
                    success=False,
                    url=url,
                    error_message="No article content found"
                )
            
            # Process content to markdown
            try:
                processed_content = self.content_processor.process_content(article_html)
            except Exception as e:
                self.logger.error(f"Content processing failed for {url}: {e}")
                return ProcessResult(
                    success=False,
                    url=url,
                    error_message=f"Content processing failed: {e}"
                )
            
            # Check if processed content is substantial
            if not processed_content or len(processed_content.strip()) < 20:
                self.logger.warning(f"Insufficient content after processing: {url}")
                return ProcessResult(
                    success=False,
                    url=url,
                    error_message="Insufficient content after processing"
                )
            
            # Filter by language
            should_process, detected_language = self.language_filter.filter_content(
                processed_content, url
            )
            
            # Update statistics
            self._stats['articles_processed'] += 1
            self._stats['languages_detected'][detected_language] = \
                self._stats['languages_detected'].get(detected_language, 0) + 1
            
            if not should_process:
                self._stats['articles_filtered'] += 1
                self.logger.info(f"Article filtered due to language: {detected_language} - {url}")
                return ProcessResult(
                    success=True,
                    url=url,
                    page_type="article",
                    data={
                        'title': title,
                        'language': detected_language,
                        'filtered': True,
                        'reason': f'Unsupported language: {detected_language}'
                    }
                )
            
            # Create article data
            article_data = ArticleData(
                url=url,
                title=title,
                content=processed_content,
                language=detected_language
            )
            
            # Save article
            try:
                self._save_article(article_data)
                self._stats['articles_saved'] += 1
            except Exception as e:
                self.logger.error(f"Failed to save article {title}: {e}")
                return ProcessResult(
                    success=False,
                    url=url,
                    error_message=f"Failed to save article: {e}"
                )
            
            self.logger.info(f"Successfully processed article: {title} ({detected_language})")
            
            return ProcessResult(
                success=True,
                url=url,
                page_type="article",
                data={
                    'title': title,
                    'language': detected_language,
                    'content_length': len(processed_content),
                    'filtered': False
                }
            )
            
        except Exception as e:
            self._stats['processing_errors'] += 1
            self.logger.error(f"Error processing article page {url}: {e}")
            return ProcessResult(
                success=False,
                url=url,
                error_message=str(e)
            )
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """
        Extract the article title from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page (fallback for title)
            
        Returns:
            Article title
        """
        # Method 1: Look for the main heading
        title_element = soup.find('h1', {'id': 'firstHeading'})
        if title_element:
            title = title_element.get_text().strip()
            return title
        
        # Method 2: Look for title in head
        title_element = soup.find('title')
        if title_element:
            title = title_element.get_text().strip()
            # Remove " - Wikipedia" suffix if present
            if title.endswith(' - Wikipedia'):
                title = title[:-12].strip()
            return title
        
        # Method 3: Extract from URL
        if '/wiki/' in url:
            title = url.split('/wiki/')[-1]
            # URL decode and clean up
            title = title.replace('_', ' ')
            return title
        
        # Fallback
        return "Unknown Article"
    
    def _extract_article_content(self, soup: BeautifulSoup) -> str:
        """
        Extract the main article content from the Wikipedia page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            HTML content of the main article
        """
        # Method 1: Look for the main content div
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if content_div:
            # Look for the parser output within the content
            parser_output = content_div.find('div', class_='mw-parser-output')
            if parser_output:
                return str(parser_output)
            return str(content_div)
        
        # Method 2: Look for parser output directly
        parser_output = soup.find('div', class_='mw-parser-output')
        if parser_output:
            return str(parser_output)
        
        # Method 3: Look for body content
        body_content = soup.find('div', {'id': 'bodyContent'})
        if body_content:
            return str(body_content)
        
        # Method 4: Look for content by class patterns
        content_candidates = [
            soup.find('div', class_=lambda x: x and 'content' in x.lower()),
            soup.find('main'),
            soup.find('article'),
        ]
        
        for candidate in content_candidates:
            if candidate and self._is_substantial_content(candidate):
                return str(candidate)
        
        # Fallback: return body or entire soup
        body = soup.find('body')
        if body:
            return str(body)
        
        return str(soup)
    
    def _is_substantial_content(self, element) -> bool:
        """
        Check if an element contains substantial article content.
        
        Args:
            element: BeautifulSoup element to check
            
        Returns:
            True if element contains substantial content, False otherwise
        """
        if not element:
            return False
        
        # Get text content
        text = element.get_text().strip()
        
        # Check for minimum length
        if len(text) < 100:
            return False
        
        # Check for paragraph content (articles should have paragraphs)
        paragraphs = element.find_all('p')
        substantial_paragraphs = [p for p in paragraphs if len(p.get_text().strip()) > 20]
        
        if len(substantial_paragraphs) < 1:
            return False
        
        # Check for typical article structure elements
        has_headings = bool(element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
        has_links = bool(element.find_all('a', href=True))
        
        # Should have either headings or links (typical of Wikipedia articles)
        return has_headings or has_links
    
    def _save_article(self, article_data: ArticleData) -> None:
        """
        Save article data to a JSON file.
        
        Args:
            article_data: ArticleData instance to save
        """
        try:
            # Use the FileStorage save_article method
            saved_path = self.file_storage.save_article(article_data)
            self.logger.debug(f"Saved article: {saved_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving article {article_data.title}: {e}")
            raise
    
    def get_stats(self) -> dict:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self._stats = {
            'articles_processed': 0,
            'articles_saved': 0,
            'articles_filtered': 0,
            'processing_errors': 0,
            'languages_detected': {}
        }
        self.logger.info("Article handler statistics reset")
    
    def get_content_processor_stats(self) -> dict:
        """Get statistics from the content processor."""
        if hasattr(self.content_processor, 'get_stats'):
            return self.content_processor.get_stats()
        return {}
    
    def get_language_filter_stats(self) -> dict:
        """Get statistics from the language filter."""
        return self.language_filter.get_language_stats()