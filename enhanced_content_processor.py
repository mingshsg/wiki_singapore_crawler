#!/usr/bin/env python3
"""
Enhanced Content Processor for handling edge cases like minimal content pages.

This processor extends the original ContentProcessor with fallback methods
for pages where the standard Wikipedia content extraction fails.
"""

import sys
import re
from pathlib import Path
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor
from wikipedia_crawler.utils.logging_config import get_logger


class EnhancedContentProcessor(ContentProcessor):
    """
    Enhanced content processor with fallback methods for edge cases.
    
    Features:
    - All original ContentProcessor functionality
    - Fallback extraction methods for minimal content pages
    - Configurable minimum content thresholds
    - Detailed logging of extraction attempts
    """
    
    def __init__(self, min_content_threshold: int = 20):
        """
        Initialize the enhanced content processor.
        
        Args:
            min_content_threshold: Minimum characters required for valid content
        """
        super().__init__()
        self.min_content_threshold = min_content_threshold
        self.logger = get_logger(__name__)
        
        # Statistics for enhanced processing
        self._enhanced_stats = {
            'primary_method_successes': 0,
            'fallback_method_successes': 0,
            'total_failures': 0,
            'methods_used': {}
        }
    
    def process_content(self, html_content: str) -> str:
        """
        Process HTML content with enhanced fallback methods.
        
        Args:
            html_content: Raw HTML content to process
            
        Returns:
            Clean markdown formatted content
            
        Raises:
            ValueError: If content cannot be processed by any method
        """
        if not html_content or not html_content.strip():
            return ""
        
        try:
            # Try the original processing method first
            processed_content = super().process_content(html_content)
            
            # Check if the primary method produced sufficient content
            if len(processed_content.strip()) >= self.min_content_threshold:
                self._enhanced_stats['primary_method_successes'] += 1
                self._enhanced_stats['methods_used']['primary'] = \
                    self._enhanced_stats['methods_used'].get('primary', 0) + 1
                self.logger.debug(f"Primary method succeeded: {len(processed_content)} characters")
                return processed_content
            
            # Primary method failed, try enhanced extraction methods
            self.logger.info(f"Primary method produced insufficient content ({len(processed_content.strip())} chars), trying fallback methods")
            
            enhanced_content = self._try_enhanced_extraction(html_content)
            
            if enhanced_content and len(enhanced_content.strip()) >= self.min_content_threshold:
                self._enhanced_stats['fallback_method_successes'] += 1
                self.logger.info(f"Enhanced extraction succeeded: {len(enhanced_content)} characters")
                return enhanced_content
            
            # All methods failed
            self._enhanced_stats['total_failures'] += 1
            self.logger.warning(f"All extraction methods failed for content")
            raise ValueError(f"Insufficient content after all processing attempts: {len(enhanced_content.strip()) if enhanced_content else 0} characters")
            
        except Exception as e:
            self._enhanced_stats['total_failures'] += 1
            self.logger.error(f"Enhanced content processing failed: {e}")
            raise ValueError(f"Enhanced content processing failed: {e}") from e
    
    def _try_enhanced_extraction(self, html_content: str) -> Optional[str]:
        """
        Try enhanced extraction methods for minimal content pages.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Processed content or None if all methods fail
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Extract all paragraphs with minimal filtering
        method1_content = self._extract_all_paragraphs_minimal(soup)
        if method1_content and len(method1_content.strip()) >= self.min_content_threshold:
            self._enhanced_stats['methods_used']['all_paragraphs_minimal'] = \
                self._enhanced_stats['methods_used'].get('all_paragraphs_minimal', 0) + 1
            self.logger.debug("Enhanced method 1 (all paragraphs minimal) succeeded")
            return method1_content
        
        # Method 2: Extract lead section only
        method2_content = self._extract_lead_section_only(soup)
        if method2_content and len(method2_content.strip()) >= self.min_content_threshold:
            self._enhanced_stats['methods_used']['lead_section_only'] = \
                self._enhanced_stats['methods_used'].get('lead_section_only', 0) + 1
            self.logger.debug("Enhanced method 2 (lead section only) succeeded")
            return method2_content
        
        # Method 3: Conservative element removal
        method3_content = self._extract_with_conservative_removal(soup)
        if method3_content and len(method3_content.strip()) >= self.min_content_threshold:
            self._enhanced_stats['methods_used']['conservative_removal'] = \
                self._enhanced_stats['methods_used'].get('conservative_removal', 0) + 1
            self.logger.debug("Enhanced method 3 (conservative removal) succeeded")
            return method3_content
        
        # Method 4: Raw text extraction as last resort
        method4_content = self._extract_raw_text_cleaned(soup)
        if method4_content and len(method4_content.strip()) >= self.min_content_threshold:
            self._enhanced_stats['methods_used']['raw_text_cleaned'] = \
                self._enhanced_stats['methods_used'].get('raw_text_cleaned', 0) + 1
            self.logger.debug("Enhanced method 4 (raw text cleaned) succeeded")
            return method4_content
        
        self.logger.warning("All enhanced extraction methods failed")
        return None
    
    def _extract_all_paragraphs_minimal(self, soup: BeautifulSoup) -> str:
        """
        Extract all paragraphs with minimal filtering.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Processed content from all paragraphs
        """
        # Find the main content area
        main_content = self._extract_main_content(soup)
        
        # Extract all paragraphs with very minimal filtering
        paragraphs = []
        for p in main_content.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 5:  # Very minimal threshold
                paragraphs.append(text)
        
        if not paragraphs:
            return ""
        
        # Join paragraphs and apply basic cleanup
        content = '\n\n'.join(paragraphs)
        
        # Apply minimal cleanup patterns
        content = self._apply_minimal_cleanup(content)
        
        return content
    
    def _extract_lead_section_only(self, soup: BeautifulSoup) -> str:
        """
        Extract only the lead section (content before first heading).
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Processed lead section content
        """
        main_content = self._extract_main_content(soup)
        
        lead_paragraphs = []
        
        # Get paragraphs before the first heading
        for element in main_content.children:
            if hasattr(element, 'name'):
                if element.name == 'p':
                    text = element.get_text().strip()
                    if text and len(text) > 10:  # Only substantial paragraphs
                        lead_paragraphs.append(text)
                elif element.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                    break  # Stop at first heading
        
        if not lead_paragraphs:
            return ""
        
        content = '\n\n'.join(lead_paragraphs)
        content = self._apply_minimal_cleanup(content)
        
        return content
    
    def _extract_with_conservative_removal(self, soup: BeautifulSoup) -> str:
        """
        Extract content with conservative element removal.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Processed content with conservative cleaning
        """
        # Make a copy to avoid modifying the original
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        # Remove only the most problematic elements
        conservative_remove_elements = {
            'script', 'style', 'noscript', 'meta', 'link', 'head',
            'nav', 'header', 'footer',
            # Only remove obvious navigation/editing elements
            'span.mw-editsection', 'div.printfooter',
            'div#toc', 'div.toc'
        }
        
        # Remove elements conservatively
        for selector in conservative_remove_elements:
            for element in soup_copy.select(selector):
                element.decompose()
        
        # Extract main content
        main_content = self._extract_main_content(soup_copy)
        
        # Convert to markdown with minimal processing
        markdown_content = self._convert_to_markdown(main_content)
        
        # Apply minimal cleanup
        cleaned_content = self._apply_minimal_cleanup(markdown_content)
        
        return cleaned_content
    
    def _extract_raw_text_cleaned(self, soup: BeautifulSoup) -> str:
        """
        Extract raw text with basic cleaning as last resort.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Cleaned raw text content
        """
        main_content = self._extract_main_content(soup)
        
        # Get raw text
        raw_text = main_content.get_text()
        
        # Clean up the raw text
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        # Filter out navigation and metadata lines
        content_lines = []
        for line in lines:
            # Skip very short lines (likely navigation)
            if len(line) < 10:
                continue
            
            # Skip lines that look like navigation or metadata
            if any(skip_phrase in line.lower() for skip_phrase in [
                'jump to content', 'main menu', 'navigation', 'search',
                'create account', 'log in', 'talk', 'contributions',
                'edit', 'view history', 'what links here', 'related changes',
                'special pages', 'permanent link', 'page information',
                'cite this page', 'download as pdf', 'printable version'
            ]):
                continue
            
            content_lines.append(line)
        
        if not content_lines:
            return ""
        
        # Join lines and apply minimal cleanup
        content = '\n\n'.join(content_lines)
        content = self._apply_minimal_cleanup(content)
        
        return content
    
    def _apply_minimal_cleanup(self, content: str) -> str:
        """
        Apply minimal cleanup patterns that preserve content.
        
        Args:
            content: Content to clean
            
        Returns:
            Minimally cleaned content
        """
        # Only apply the most essential cleanup patterns
        minimal_patterns = [
            # Remove citation markers like [1], [2]
            (r'\[\d+\]', ''),
            # Remove edit links
            (r'\[edit\]', ''),
            # Clean up multiple whitespace
            (r'\s+', ' '),
            # Remove excessive newlines
            (r'\n\s*\n\s*\n', '\n\n'),
        ]
        
        for pattern, replacement in minimal_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.IGNORECASE)
        
        return content.strip()
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """
        Get enhanced processing statistics.
        
        Returns:
            Dictionary with enhanced processing statistics
        """
        return self._enhanced_stats.copy()
    
    def reset_enhanced_stats(self) -> None:
        """Reset enhanced processing statistics."""
        self._enhanced_stats = {
            'primary_method_successes': 0,
            'fallback_method_successes': 0,
            'total_failures': 0,
            'methods_used': {}
        }


def test_enhanced_processor():
    """Test the enhanced processor on the failed URL."""
    import requests
    
    print("🧪 TESTING ENHANCED CONTENT PROCESSOR")
    print("=" * 50)
    
    # Initialize enhanced processor
    processor = EnhancedContentProcessor(min_content_threshold=20)
    
    # Test URL
    test_url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
    
    try:
        # Fetch content
        print(f"📥 Fetching content from: {test_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
        }
        response = requests.get(test_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Fetched {len(response.text)} characters")
        
        # Process with enhanced processor
        print(f"\n⚙️  Processing with enhanced content processor...")
        processed_content = processor.process_content(response.text)
        
        print(f"✅ Processing succeeded!")
        print(f"📏 Final content length: {len(processed_content)} characters")
        print(f"📝 Full processed content:")
        print(f"'{processed_content}'")
        
        # Show statistics
        stats = processor.get_enhanced_stats()
        print(f"\n📊 Enhanced Processing Statistics:")
        print(f"   Primary method successes: {stats['primary_method_successes']}")
        print(f"   Fallback method successes: {stats['fallback_method_successes']}")
        print(f"   Total failures: {stats['total_failures']}")
        print(f"   Methods used: {stats['methods_used']}")
        
        # Test with lower threshold to see fallback methods
        print(f"\n🔄 Testing with higher threshold (500 chars) to trigger fallback methods...")
        processor_high_threshold = EnhancedContentProcessor(min_content_threshold=500)
        
        try:
            processed_content_fallback = processor_high_threshold.process_content(response.text)
            print(f"✅ Fallback processing succeeded!")
            print(f"📏 Fallback content length: {len(processed_content_fallback)} characters")
            print(f"📝 Fallback content preview (first 300 chars):")
            print(f"   {processed_content_fallback[:300]}...")
            
            fallback_stats = processor_high_threshold.get_enhanced_stats()
            print(f"\n📊 Fallback Processing Statistics:")
            print(f"   Primary method successes: {fallback_stats['primary_method_successes']}")
            print(f"   Fallback method successes: {fallback_stats['fallback_method_successes']}")
            print(f"   Methods used: {fallback_stats['methods_used']}")
            
        except Exception as e:
            print(f"❌ Fallback test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    import re
    success = test_enhanced_processor()
    sys.exit(0 if success else 1)