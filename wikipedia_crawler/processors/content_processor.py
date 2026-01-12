"""Content processing for converting HTML to clean markdown."""

import re
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup, Comment, NavigableString
from markdownify import markdownify as md

from wikipedia_crawler.utils.logging_config import get_logger


class ContentProcessor:
    """
    Processes HTML content and converts it to clean markdown format.
    
    Handles Wikipedia-specific content cleaning including removal of
    navigation elements, infoboxes, references, and media elements.
    """
    
    def __init__(self):
        """Initialize the content processor."""
        self.logger = get_logger(__name__)
        
        # Elements to remove completely
        self.remove_elements = {
            'script', 'style', 'noscript', 'meta', 'link', 'head',
            'nav', 'header', 'footer', 'aside',
            # Wikipedia-specific elements
            'table.infobox', 'div.navbox', 'div.hatnote', 'div.dablink',
            'div.ambox', 'div.mbox-small', 'div.sistersitebox',
            'div.reflist', 'ol.references', 'div.refbegin',
            # Navigation and editing elements
            'span.mw-editsection', 'div.printfooter', 'div.catlinks',
            'div#toc', 'div.toc', 'div.toccolours',
            # Media and file elements
            'div.thumb', 'div.thumbinner', 'div.thumbcaption',
            'div.gallery', 'div.gallerybox', 'div.gallerytext'
        }
        
        # Attributes to remove from all elements
        self.remove_attributes = {
            'class', 'id', 'style', 'onclick', 'onload', 'onmouseover',
            'data-*', 'aria-*', 'role', 'tabindex'
        }
        
        # Wikipedia-specific patterns to clean
        self.cleanup_patterns = [
            # Remove citation markers like [1], [2], [citation needed]
            (r'\[\d+\]', ''),
            (r'\[citation needed\]', ''),
            (r'\[clarification needed\]', ''),
            (r'\[when\?\]', ''),
            (r'\[who\?\]', ''),
            (r'\[where\?\]', ''),
            # Remove edit links
            (r'\[edit\]', ''),
            # Clean up multiple whitespace
            (r'\s+', ' '),
            # Remove empty lines with just whitespace
            (r'\n\s*\n\s*\n', '\n\n'),
        ]
    
    def process_content(self, html_content: str) -> str:
        """
        Process HTML content and convert to clean markdown.
        
        Args:
            html_content: Raw HTML content to process
            
        Returns:
            Clean markdown formatted content
            
        Raises:
            ValueError: If content cannot be processed
        """
        if not html_content or not html_content.strip():
            return ""
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Clean up attributes
            self._clean_attributes(soup)
            
            # Extract main content
            main_content = self._extract_main_content(soup)
            
            # Convert to markdown
            markdown_content = self._convert_to_markdown(main_content)
            
            # Apply cleanup patterns
            cleaned_content = self._apply_cleanup_patterns(markdown_content)
            
            # Final formatting
            final_content = self._final_formatting(cleaned_content)
            
            self.logger.debug(f"Processed content: {len(html_content)} -> {len(final_content)} characters")
            return final_content
            
        except Exception as e:
            self.logger.error(f"Failed to process content: {e}")
            raise ValueError(f"Content processing failed: {e}") from e
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        """Remove unwanted HTML elements from the soup."""
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove elements by tag and class
        for selector in self.remove_elements:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove specific Wikipedia elements
        self._remove_wikipedia_specific_elements(soup)
    
    def _remove_wikipedia_specific_elements(self, soup: BeautifulSoup) -> None:
        """Remove Wikipedia-specific elements that clutter content."""
        # Remove infoboxes
        for infobox in soup.find_all('table', class_=lambda x: x and 'infobox' in x):
            infobox.decompose()
        
        # Remove navigation boxes
        for navbox in soup.find_all('div', class_=lambda x: x and 'navbox' in x):
            navbox.decompose()
        
        # Remove reference sections
        for ref_section in soup.find_all(['div', 'section'], class_=lambda x: x and 'reflist' in x):
            ref_section.decompose()
        
        # Remove "See also" and similar sections (often not useful for content)
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if heading.get_text().strip().lower() in ['see also', 'references', 'external links', 'further reading']:
                # Remove the heading and everything until the next heading of same or higher level
                current = heading
                while current and current.next_sibling:
                    next_elem = current.next_sibling
                    if (next_elem.name in ['h1', 'h2', 'h3', 'h4'] and 
                        int(next_elem.name[1:]) <= int(heading.name[1:])):
                        break
                    if hasattr(next_elem, 'decompose'):
                        next_elem.decompose()
                    else:
                        current = next_elem
                heading.decompose()
        
        # Remove image and media elements
        for img in soup.find_all(['img', 'figure', 'audio', 'video']):
            img.decompose()
        
        # Remove file links (File:, Image:, Media:)
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if any(prefix in href.lower() for prefix in ['/wiki/file:', '/wiki/image:', '/wiki/media:']):
                link.decompose()
    
    def _clean_attributes(self, soup: BeautifulSoup) -> None:
        """Remove unwanted attributes from HTML elements."""
        for element in soup.find_all():
            # Keep only essential attributes
            attrs_to_keep = {}
            
            # Keep href for links
            if element.name == 'a' and element.get('href'):
                href = element.get('href')
                # Only keep Wikipedia article links
                if href.startswith('/wiki/') and ':' not in href:
                    attrs_to_keep['href'] = href
            
            # Keep src for images (though we'll remove most images)
            elif element.name == 'img' and element.get('alt'):
                attrs_to_keep['alt'] = element.get('alt')
            
            # Replace all attributes with cleaned set
            element.attrs = attrs_to_keep
    
    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract the main content area from Wikipedia page."""
        # Try to find the main content div
        main_content = soup.find('div', {'id': 'mw-content-text'})
        if not main_content:
            main_content = soup.find('div', class_='mw-parser-output')
        if not main_content:
            main_content = soup.find('div', {'id': 'bodyContent'})
        if not main_content:
            # Fallback to the entire body or soup
            main_content = soup.find('body') or soup
        
        return main_content
    
    def _convert_to_markdown(self, soup: BeautifulSoup) -> str:
        """Convert cleaned HTML to markdown."""
        # Configure markdownify options
        markdown_options = {
            'heading_style': 'ATX',  # Use # for headings
            'bullets': '-',          # Use - for bullet points
            'convert': ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 
                       'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
                       'blockquote', 'code', 'pre', 'a'],
            'escape_asterisks': False,
            'escape_underscores': False
        }
        
        # Convert to markdown
        html_str = str(soup)
        markdown = md(html_str, **markdown_options)
        
        return markdown
    
    def _apply_cleanup_patterns(self, content: str) -> str:
        """Apply regex cleanup patterns to the content."""
        for pattern, replacement in self.cleanup_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.IGNORECASE)
        
        return content
    
    def _final_formatting(self, content: str) -> str:
        """Apply final formatting and cleanup."""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace
            line = line.strip()
            
            # Skip empty lines that are just whitespace
            if not line:
                # Only add empty line if the last line wasn't empty
                if cleaned_lines and cleaned_lines[-1]:
                    cleaned_lines.append('')
                continue
            
            # Clean up markdown formatting issues
            line = self._fix_markdown_formatting(line)
            
            cleaned_lines.append(line)
        
        # Join lines and ensure proper spacing
        result = '\n'.join(cleaned_lines)
        
        # Remove excessive newlines (more than 2 consecutive)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # Ensure content ends with single newline
        result = result.rstrip() + '\n' if result.strip() else ''
        
        return result
    
    def _fix_markdown_formatting(self, line: str) -> str:
        """Fix common markdown formatting issues."""
        # Fix spacing around headers
        if line.startswith('#'):
            # Ensure space after #
            line = re.sub(r'^(#+)([^\s])', r'\1 \2', line)
        
        # Fix list formatting
        if re.match(r'^[\-\*\+]\s*[^\s]', line):
            # Ensure space after list marker
            line = re.sub(r'^([\-\*\+])([^\s])', r'\1 \2', line)
        
        # Fix numbered list formatting
        if re.match(r'^\d+\.\s*[^\s]', line):
            # Ensure space after number
            line = re.sub(r'^(\d+\.)([^\s])', r'\1 \2', line)
        
        # Clean up excessive spaces
        line = re.sub(r'\s+', ' ', line)
        
        return line
    
    def get_content_stats(self, original_html: str, processed_markdown: str) -> Dict[str, Any]:
        """
        Get statistics about the content processing.
        
        Args:
            original_html: Original HTML content
            processed_markdown: Processed markdown content
            
        Returns:
            Dictionary with processing statistics
        """
        return {
            'original_size': len(original_html),
            'processed_size': len(processed_markdown),
            'compression_ratio': len(processed_markdown) / len(original_html) if original_html else 0,
            'original_lines': original_html.count('\n') + 1 if original_html else 0,
            'processed_lines': processed_markdown.count('\n') + 1 if processed_markdown else 0,
            'has_headers': bool(re.search(r'^#+\s', processed_markdown, re.MULTILINE)),
            'has_lists': bool(re.search(r'^[\-\*\+\d+\.]\s', processed_markdown, re.MULTILINE)),
            'has_links': bool(re.search(r'\[.*\]\(.*\)', processed_markdown))
        }