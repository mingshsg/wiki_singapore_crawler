"""Category page handler for processing Wikipedia category pages."""

import re
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

from wikipedia_crawler.models.data_models import CategoryData, ProcessResult
from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.utils.logging_config import get_logger


class CategoryPageHandler:
    """
    Handler for processing Wikipedia category pages.
    
    Features:
    - Extracts subcategory and article links from category pages
    - Handles Wikipedia-specific category page structure
    - Saves category metadata as JSON files
    - Validates and normalizes Wikipedia URLs
    """
    
    def __init__(self, file_storage: FileStorage, max_depth: int = 5):
        """
        Initialize the category page handler.
        
        Args:
            file_storage: FileStorage instance for saving data
            max_depth: Maximum depth for subcategory crawling
        """
        self.file_storage = file_storage
        self.max_depth = max_depth
        self.logger = get_logger(__name__)
        
        # Statistics
        self._stats = {
            'categories_processed': 0,
            'subcategories_found': 0,
            'articles_found': 0,
            'invalid_urls_filtered': 0
        }
        
        self.logger.info(f"CategoryPageHandler initialized with max_depth={max_depth}")
    
    def process_category(self, url: str, content: str, depth: int = 0) -> ProcessResult:
        """
        Process a Wikipedia category page.
        
        Args:
            url: URL of the category page
            content: HTML content of the page
            depth: Current depth level
            
        Returns:
            ProcessResult with extracted links and metadata
        """
        try:
            self.logger.info(f"Processing category page: {url} (depth: {depth})")
            
            # Parse HTML content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract page title
            title = self._extract_title(soup, url)
            
            # Extract subcategories and articles
            subcategories = self._extract_subcategories(soup, url)
            articles = self._extract_articles(soup, url)
            
            # Filter and validate URLs
            subcategories = self._filter_valid_urls(subcategories)
            articles = self._filter_valid_urls(articles)
            
            # Update statistics
            self._stats['categories_processed'] += 1
            self._stats['subcategories_found'] += len(subcategories)
            self._stats['articles_found'] += len(articles)
            
            # Create category data
            category_data = CategoryData(
                url=url,
                title=title,
                subcategories=subcategories,
                articles=articles
            )
            
            # Save category metadata
            self._save_category_metadata(category_data)
            
            # Prepare discovered URLs for further processing
            discovered_urls = []
            
            # Add subcategories if we haven't reached max depth
            if depth < self.max_depth:
                discovered_urls.extend(subcategories)
                self.logger.debug(f"Added {len(subcategories)} subcategories for processing")
            else:
                self.logger.info(f"Max depth ({self.max_depth}) reached, skipping subcategories")
            
            # Always add articles
            discovered_urls.extend(articles)
            
            self.logger.info(f"Successfully processed category: {title} "
                           f"({len(subcategories)} subcategories, {len(articles)} articles)")
            
            return ProcessResult(
                success=True,
                url=url,
                page_type="category",
                discovered_urls=discovered_urls,
                data={
                    'title': title,
                    'subcategories_count': len(subcategories),
                    'articles_count': len(articles),
                    'depth': depth
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing category page {url}: {e}")
            return ProcessResult(
                success=False,
                url=url,
                error_message=str(e)
            )
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """
        Extract the category title from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page (fallback for title)
            
        Returns:
            Category title
        """
        # Method 1: Look for the main heading
        title_element = soup.find('h1', {'id': 'firstHeading'})
        if title_element:
            title = title_element.get_text().strip()
            # Remove "Category:" prefix if present
            if title.startswith('Category:'):
                title = title[9:].strip()
            return title
        
        # Method 2: Extract from URL
        if '/Category:' in url:
            title = url.split('/Category:')[-1]
            # URL decode and clean up
            title = title.replace('_', ' ')
            return title
        
        # Fallback
        return "Unknown Category"
    
    def _extract_subcategories(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract subcategory links from the category page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
            
        Returns:
            List of subcategory URLs
        """
        subcategories = set()
        
        # Method 1: Look for subcategories section
        subcategories_div = soup.find('div', {'id': 'mw-subcategories'})
        if subcategories_div:
            links = subcategories_div.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and '/Category:' in href:
                    full_url = self._resolve_url(href, base_url)
                    if full_url:
                        subcategories.add(full_url)
        
        # Method 2: Look for category tree widget
        category_tree = soup.find('div', class_='CategoryTreeTag')
        if category_tree:
            links = category_tree.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and '/Category:' in href:
                    full_url = self._resolve_url(href, base_url)
                    if full_url:
                        subcategories.add(full_url)
        
        # Method 3: Look for "Subcategories" heading and following content
        subcategories_heading = soup.find('h2', string=lambda text: 
                                         text and 'subcategories' in text.lower())
        if subcategories_heading:
            # Find the next div or ul after the heading
            next_element = subcategories_heading.find_next_sibling(['div', 'ul'])
            if next_element:
                links = next_element.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    if href and '/Category:' in href:
                        full_url = self._resolve_url(href, base_url)
                        if full_url:
                            subcategories.add(full_url)
        
        # Method 4: General search for category links in the main content
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if content_div:
            # Look for links that are clearly category links
            category_links = content_div.find_all('a', href=lambda href: 
                                                 href and '/Category:' in href)
            for link in category_links:
                href = link.get('href')
                # Additional validation: check if the link text suggests it's a subcategory
                link_text = link.get_text().strip().lower()
                if any(indicator in link_text for indicator in ['category', 'categories']):
                    full_url = self._resolve_url(href, base_url)
                    if full_url:
                        subcategories.add(full_url)
        
        result = list(subcategories)
        self.logger.debug(f"Extracted {len(result)} subcategories from {base_url}")
        return result
    
    def _extract_articles(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract article links from the category page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
            
        Returns:
            List of article URLs
        """
        articles = set()
        
        # Method 1: Look for pages section
        pages_div = soup.find('div', {'id': 'mw-pages'})
        if pages_div:
            links = pages_div.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and self._is_article_link(href):
                    full_url = self._resolve_url(href, base_url)
                    if full_url:
                        articles.add(full_url)
        
        # Method 2: Look for "Pages in category" heading and following content
        pages_heading = soup.find('h2', string=lambda text: 
                                 text and 'pages in category' in text.lower())
        if pages_heading:
            # Find the next div or ul after the heading
            next_element = pages_heading.find_next_sibling(['div', 'ul'])
            if next_element:
                links = next_element.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    if href and self._is_article_link(href):
                        full_url = self._resolve_url(href, base_url)
                        if full_url:
                            articles.add(full_url)
        
        # Method 3: Look for category members in lists
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if content_div:
            # Find lists that might contain article links
            lists = content_div.find_all(['ul', 'ol'])
            for list_element in lists:
                # Skip navigation lists
                if list_element.find_parent(['nav', 'div'], class_=lambda x: 
                                          x and any(nav in x.lower() for nav in ['nav', 'menu', 'toc'])):
                    continue
                
                links = list_element.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    if href and self._is_article_link(href):
                        full_url = self._resolve_url(href, base_url)
                        if full_url:
                            articles.add(full_url)
        
        # Method 4: Look for category gallery (media files)
        gallery_div = soup.find('div', {'id': 'mw-category-media'})
        if gallery_div:
            links = gallery_div.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and self._is_article_link(href):
                    full_url = self._resolve_url(href, base_url)
                    if full_url:
                        articles.add(full_url)
        
        result = list(articles)
        self.logger.debug(f"Extracted {len(result)} articles from {base_url}")
        return result
    
    def _is_article_link(self, href: str) -> bool:
        """
        Check if a link points to a Wikipedia article.
        
        Args:
            href: Link href attribute
            
        Returns:
            True if it's an article link, False otherwise
        """
        if not href:
            return False
        
        # Exclude category links
        if '/Category:' in href:
            return False
        
        # Exclude special pages
        special_prefixes = [
            '/Special:', '/Help:', '/Template:', '/User:', '/Talk:',
            '/File:', '/Media:', '/Wikipedia:', '/Portal:'
        ]
        
        if any(prefix in href for prefix in special_prefixes):
            return False
        
        # Exclude external links
        if href.startswith('http') and 'wikipedia.org' not in href:
            return False
        
        # Exclude anchors and fragments
        if href.startswith('#'):
            return False
        
        # Must be a wiki article path
        if href.startswith('/wiki/') or 'wikipedia.org/wiki/' in href:
            return True
        
        return False
    
    def _resolve_url(self, href: str, base_url: str) -> Optional[str]:
        """
        Resolve a relative URL to an absolute URL.
        
        Args:
            href: Link href (may be relative)
            base_url: Base URL for resolution
            
        Returns:
            Absolute URL or None if invalid
        """
        try:
            if href.startswith('http'):
                return href
            
            # Handle relative URLs
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                return f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            
            # Use urljoin for other relative URLs
            return urljoin(base_url, href)
            
        except Exception as e:
            self.logger.warning(f"Error resolving URL {href} with base {base_url}: {e}")
            return None
    
    def _filter_valid_urls(self, urls: List[str]) -> List[str]:
        """
        Filter and validate Wikipedia URLs.
        
        Args:
            urls: List of URLs to filter
            
        Returns:
            List of valid Wikipedia URLs
        """
        valid_urls = []
        
        for url in urls:
            if self._is_valid_wikipedia_url(url):
                valid_urls.append(url)
            else:
                self._stats['invalid_urls_filtered'] += 1
        
        return valid_urls
    
    def _is_valid_wikipedia_url(self, url: str) -> bool:
        """
        Check if a URL is a valid Wikipedia URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Must be HTTPS
            if parsed.scheme != 'https':
                return False
            
            # Must be Wikipedia domain
            if 'wikipedia.org' not in parsed.netloc:
                return False
            
            # Must have a path
            if not parsed.path or parsed.path == '/':
                return False
            
            # Must be a wiki page
            if not parsed.path.startswith('/wiki/'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _save_category_metadata(self, category_data: CategoryData) -> None:
        """
        Save category metadata to a JSON file.
        
        Args:
            category_data: CategoryData instance to save
        """
        try:
            # Use the FileStorage save_category method
            saved_path = self.file_storage.save_category(category_data)
            self.logger.debug(f"Saved category metadata: {saved_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving category metadata for {category_data.title}: {e}")
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
            'categories_processed': 0,
            'subcategories_found': 0,
            'articles_found': 0,
            'invalid_urls_filtered': 0
        }
        self.logger.info("Category handler statistics reset")