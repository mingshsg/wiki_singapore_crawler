#!/usr/bin/env python3
"""
Detailed investigation script for the failed URL: History_of_the_Jews_in_Singapore

This script provides comprehensive analysis of why the URL fails content processing,
including raw HTML analysis, content extraction debugging, and comparison with successful pages.
"""

import sys
import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor
from wikipedia_crawler.processors.article_handler import ArticlePageHandler
from wikipedia_crawler.processors.language_filter import LanguageFilter
from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.utils.logging_config import get_logger


class FailedURLInvestigator:
    """
    Comprehensive investigator for failed URL processing.
    
    Provides detailed analysis of content extraction failures including:
    - Raw HTML analysis
    - Step-by-step content processing debugging
    - Comparison with successful pages
    - Enhanced extraction attempts
    """
    
    def __init__(self):
        """Initialize the investigator."""
        self.logger = get_logger(__name__)
        self.content_processor = ContentProcessor()
        self.language_filter = LanguageFilter()
        self.file_storage = FileStorage("wiki_data")
        
        self.failed_url = "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
        
        # For comparison, use a successful Singapore-related article
        self.successful_url = "https://en.wikipedia.org/wiki/Singapore"
        
    def investigate_failed_url(self) -> Dict[str, Any]:
        """
        Perform comprehensive investigation of the failed URL.
        
        Returns:
            Dictionary with detailed investigation results
        """
        print("🔍 DETAILED INVESTIGATION: History_of_the_Jews_in_Singapore")
        print("=" * 80)
        
        investigation_results = {
            'url': self.failed_url,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'steps': {}
        }
        
        # Step 1: Fetch raw HTML
        print("\n📥 STEP 1: Fetching raw HTML content...")
        html_result = self._fetch_html(self.failed_url)
        investigation_results['steps']['html_fetch'] = html_result
        
        if not html_result['success']:
            print(f"❌ Failed to fetch HTML: {html_result['error']}")
            return investigation_results
        
        print(f"✅ HTML fetched successfully ({len(html_result['content'])} characters)")
        
        # Step 2: Parse HTML structure
        print("\n🏗️  STEP 2: Analyzing HTML structure...")
        structure_result = self._analyze_html_structure(html_result['content'])
        investigation_results['steps']['html_structure'] = structure_result
        
        # Step 3: Extract title
        print("\n📝 STEP 3: Extracting page title...")
        title_result = self._extract_title_debug(html_result['content'])
        investigation_results['steps']['title_extraction'] = title_result
        print(f"📝 Title: {title_result['title']}")
        
        # Step 4: Content extraction debugging
        print("\n📄 STEP 4: Debugging content extraction...")
        content_result = self._debug_content_extraction(html_result['content'])
        investigation_results['steps']['content_extraction'] = content_result
        
        # Step 5: Content processing debugging
        print("\n⚙️  STEP 5: Debugging content processing...")
        processing_result = self._debug_content_processing(content_result['raw_content'])
        investigation_results['steps']['content_processing'] = processing_result
        
        # Step 6: Language detection
        print("\n🌐 STEP 6: Testing language detection...")
        language_result = self._debug_language_detection(processing_result['processed_content'])
        investigation_results['steps']['language_detection'] = language_result
        
        # Step 7: Compare with successful page
        print("\n🔄 STEP 7: Comparing with successful page...")
        comparison_result = self._compare_with_successful_page()
        investigation_results['steps']['comparison'] = comparison_result
        
        # Step 8: Enhanced extraction attempts
        print("\n🚀 STEP 8: Attempting enhanced extraction methods...")
        enhanced_result = self._attempt_enhanced_extraction(html_result['content'])
        investigation_results['steps']['enhanced_extraction'] = enhanced_result
        
        return investigation_results
    
    def _fetch_html(self, url: str) -> Dict[str, Any]:
        """Fetch raw HTML content with detailed logging."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; WikipediaCrawler/1.0; Educational Research)'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return {
                'success': True,
                'content': response.text,
                'status_code': response.status_code,
                'content_length': len(response.text),
                'content_type': response.headers.get('content-type', 'unknown')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _analyze_html_structure(self, html_content: str) -> Dict[str, Any]:
        """Analyze the HTML structure of the page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check for key Wikipedia elements
        structure_info = {
            'has_mw_content_text': bool(soup.find('div', {'id': 'mw-content-text'})),
            'has_mw_parser_output': bool(soup.find('div', class_='mw-parser-output')),
            'has_body_content': bool(soup.find('div', {'id': 'bodyContent'})),
            'has_first_heading': bool(soup.find('h1', {'id': 'firstHeading'})),
            'paragraph_count': len(soup.find_all('p')),
            'heading_count': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            'link_count': len(soup.find_all('a', href=True)),
            'total_text_length': len(soup.get_text())
        }
        
        # Get sample paragraphs
        paragraphs = soup.find_all('p')
        structure_info['sample_paragraphs'] = []
        for i, p in enumerate(paragraphs[:5]):  # First 5 paragraphs
            text = p.get_text().strip()
            if text:
                structure_info['sample_paragraphs'].append({
                    'index': i,
                    'length': len(text),
                    'preview': text[:100] + '...' if len(text) > 100 else text
                })
        
        print(f"📊 Structure Analysis:")
        print(f"   - Main content div: {'✅' if structure_info['has_mw_content_text'] else '❌'}")
        print(f"   - Parser output div: {'✅' if structure_info['has_mw_parser_output'] else '❌'}")
        print(f"   - Body content div: {'✅' if structure_info['has_body_content'] else '❌'}")
        print(f"   - First heading: {'✅' if structure_info['has_first_heading'] else '❌'}")
        print(f"   - Paragraphs: {structure_info['paragraph_count']}")
        print(f"   - Headings: {structure_info['heading_count']}")
        print(f"   - Links: {structure_info['link_count']}")
        print(f"   - Total text length: {structure_info['total_text_length']}")
        
        return structure_info
    
    def _extract_title_debug(self, html_content: str) -> Dict[str, Any]:
        """Debug title extraction process."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        title_info = {
            'methods_tried': [],
            'title': None
        }
        
        # Method 1: firstHeading
        first_heading = soup.find('h1', {'id': 'firstHeading'})
        if first_heading:
            title = first_heading.get_text().strip()
            title_info['methods_tried'].append({
                'method': 'firstHeading',
                'success': True,
                'title': title
            })
            if not title_info['title']:
                title_info['title'] = title
        else:
            title_info['methods_tried'].append({
                'method': 'firstHeading',
                'success': False,
                'title': None
            })
        
        # Method 2: HTML title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            if title.endswith(' - Wikipedia'):
                title = title[:-12].strip()
            title_info['methods_tried'].append({
                'method': 'title_tag',
                'success': True,
                'title': title
            })
            if not title_info['title']:
                title_info['title'] = title
        else:
            title_info['methods_tried'].append({
                'method': 'title_tag',
                'success': False,
                'title': None
            })
        
        # Method 3: URL extraction
        url_title = self.failed_url.split('/wiki/')[-1].replace('_', ' ')
        title_info['methods_tried'].append({
            'method': 'url_extraction',
            'success': True,
            'title': url_title
        })
        if not title_info['title']:
            title_info['title'] = url_title
        
        return title_info
    
    def _debug_content_extraction(self, html_content: str) -> Dict[str, Any]:
        """Debug the content extraction process step by step."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        extraction_info = {
            'methods_tried': [],
            'raw_content': None,
            'content_length': 0
        }
        
        # Method 1: mw-content-text
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if content_div:
            parser_output = content_div.find('div', class_='mw-parser-output')
            if parser_output:
                content = str(parser_output)
                extraction_info['methods_tried'].append({
                    'method': 'mw-content-text -> mw-parser-output',
                    'success': True,
                    'content_length': len(content),
                    'text_length': len(parser_output.get_text().strip())
                })
                if not extraction_info['raw_content']:
                    extraction_info['raw_content'] = content
                    extraction_info['content_length'] = len(content)
            else:
                content = str(content_div)
                extraction_info['methods_tried'].append({
                    'method': 'mw-content-text (direct)',
                    'success': True,
                    'content_length': len(content),
                    'text_length': len(content_div.get_text().strip())
                })
                if not extraction_info['raw_content']:
                    extraction_info['raw_content'] = content
                    extraction_info['content_length'] = len(content)
        else:
            extraction_info['methods_tried'].append({
                'method': 'mw-content-text',
                'success': False,
                'content_length': 0,
                'text_length': 0
            })
        
        # Method 2: mw-parser-output directly
        parser_output = soup.find('div', class_='mw-parser-output')
        if parser_output:
            content = str(parser_output)
            extraction_info['methods_tried'].append({
                'method': 'mw-parser-output (direct)',
                'success': True,
                'content_length': len(content),
                'text_length': len(parser_output.get_text().strip())
            })
            if not extraction_info['raw_content']:
                extraction_info['raw_content'] = content
                extraction_info['content_length'] = len(content)
        else:
            extraction_info['methods_tried'].append({
                'method': 'mw-parser-output (direct)',
                'success': False,
                'content_length': 0,
                'text_length': 0
            })
        
        # Method 3: bodyContent
        body_content = soup.find('div', {'id': 'bodyContent'})
        if body_content:
            content = str(body_content)
            extraction_info['methods_tried'].append({
                'method': 'bodyContent',
                'success': True,
                'content_length': len(content),
                'text_length': len(body_content.get_text().strip())
            })
            if not extraction_info['raw_content']:
                extraction_info['raw_content'] = content
                extraction_info['content_length'] = len(content)
        else:
            extraction_info['methods_tried'].append({
                'method': 'bodyContent',
                'success': False,
                'content_length': 0,
                'text_length': 0
            })
        
        print(f"📄 Content Extraction Results:")
        for method in extraction_info['methods_tried']:
            status = "✅" if method['success'] else "❌"
            print(f"   {status} {method['method']}: {method['content_length']} chars, {method['text_length']} text chars")
        
        return extraction_info
    
    def _debug_content_processing(self, raw_content: str) -> Dict[str, Any]:
        """Debug the content processing step by step."""
        if not raw_content:
            return {
                'success': False,
                'error': 'No raw content to process',
                'processed_content': None
            }
        
        processing_info = {
            'success': False,
            'processed_content': None,
            'processing_steps': [],
            'error': None
        }
        
        try:
            # Step 1: Parse HTML
            soup = BeautifulSoup(raw_content, 'html.parser')
            processing_info['processing_steps'].append({
                'step': 'html_parsing',
                'success': True,
                'details': f'Parsed HTML with {len(soup.find_all())} elements'
            })
            
            # Step 2: Remove unwanted elements
            original_elements = len(soup.find_all())
            self.content_processor._remove_unwanted_elements(soup)
            remaining_elements = len(soup.find_all())
            processing_info['processing_steps'].append({
                'step': 'remove_unwanted_elements',
                'success': True,
                'details': f'Removed {original_elements - remaining_elements} elements, {remaining_elements} remaining'
            })
            
            # Step 3: Clean attributes
            self.content_processor._clean_attributes(soup)
            processing_info['processing_steps'].append({
                'step': 'clean_attributes',
                'success': True,
                'details': 'Cleaned element attributes'
            })
            
            # Step 4: Extract main content
            main_content = self.content_processor._extract_main_content(soup)
            text_length = len(main_content.get_text().strip()) if main_content else 0
            processing_info['processing_steps'].append({
                'step': 'extract_main_content',
                'success': True,
                'details': f'Extracted main content with {text_length} text characters'
            })
            
            # Step 5: Convert to markdown
            markdown_content = self.content_processor._convert_to_markdown(main_content)
            processing_info['processing_steps'].append({
                'step': 'convert_to_markdown',
                'success': True,
                'details': f'Converted to markdown: {len(markdown_content)} characters'
            })
            
            # Step 6: Apply cleanup patterns
            cleaned_content = self.content_processor._apply_cleanup_patterns(markdown_content)
            processing_info['processing_steps'].append({
                'step': 'apply_cleanup_patterns',
                'success': True,
                'details': f'Applied cleanup: {len(cleaned_content)} characters'
            })
            
            # Step 7: Final formatting
            final_content = self.content_processor._final_formatting(cleaned_content)
            processing_info['processing_steps'].append({
                'step': 'final_formatting',
                'success': True,
                'details': f'Final formatting: {len(final_content)} characters'
            })
            
            processing_info['success'] = True
            processing_info['processed_content'] = final_content
            
            print(f"⚙️  Content Processing Steps:")
            for step in processing_info['processing_steps']:
                print(f"   ✅ {step['step']}: {step['details']}")
            
            # Check if content meets minimum threshold
            content_length = len(final_content.strip())
            print(f"📏 Final content length: {content_length} characters")
            print(f"📏 Minimum threshold: 20 characters")
            print(f"📏 Meets threshold: {'✅ YES' if content_length >= 20 else '❌ NO'}")
            
            if content_length < 20:
                print(f"❌ FAILURE REASON: Content length ({content_length}) is below minimum threshold (20)")
                print(f"📝 Actual content preview: '{final_content[:100]}...'")
            
        except Exception as e:
            processing_info['error'] = str(e)
            processing_info['processing_steps'].append({
                'step': 'error',
                'success': False,
                'details': f'Processing failed: {e}'
            })
            print(f"❌ Content processing failed: {e}")
        
        return processing_info
    
    def _debug_language_detection(self, processed_content: str) -> Dict[str, Any]:
        """Debug language detection process."""
        if not processed_content:
            return {
                'success': False,
                'error': 'No processed content for language detection'
            }
        
        try:
            should_process, detected_language = self.language_filter.filter_content(
                processed_content, self.failed_url
            )
            
            language_info = {
                'success': True,
                'detected_language': detected_language,
                'should_process': should_process,
                'content_length': len(processed_content)
            }
            
            print(f"🌐 Language Detection:")
            print(f"   - Detected language: {detected_language}")
            print(f"   - Should process: {'✅ YES' if should_process else '❌ NO'}")
            
            return language_info
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _compare_with_successful_page(self) -> Dict[str, Any]:
        """Compare the failed page with a successful one."""
        print(f"🔄 Fetching successful page for comparison: {self.successful_url}")
        
        successful_html = self._fetch_html(self.successful_url)
        if not successful_html['success']:
            return {
                'success': False,
                'error': f"Failed to fetch successful page: {successful_html['error']}"
            }
        
        # Analyze both pages
        failed_structure = self._analyze_html_structure_simple(self._fetch_html(self.failed_url)['content'])
        successful_structure = self._analyze_html_structure_simple(successful_html['content'])
        
        comparison = {
            'success': True,
            'failed_page': failed_structure,
            'successful_page': successful_structure,
            'differences': {}
        }
        
        # Compare key metrics
        for key in failed_structure:
            if key in successful_structure:
                comparison['differences'][key] = {
                    'failed': failed_structure[key],
                    'successful': successful_structure[key],
                    'ratio': failed_structure[key] / successful_structure[key] if successful_structure[key] > 0 else 0
                }
        
        print(f"🔄 Comparison Results:")
        print(f"   Failed page paragraphs: {failed_structure['paragraph_count']}")
        print(f"   Successful page paragraphs: {successful_structure['paragraph_count']}")
        print(f"   Failed page text length: {failed_structure['total_text_length']}")
        print(f"   Successful page text length: {successful_structure['total_text_length']}")
        
        return comparison
    
    def _analyze_html_structure_simple(self, html_content: str) -> Dict[str, Any]:
        """Simple HTML structure analysis for comparison."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        return {
            'paragraph_count': len(soup.find_all('p')),
            'heading_count': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            'link_count': len(soup.find_all('a', href=True)),
            'total_text_length': len(soup.get_text())
        }
    
    def _attempt_enhanced_extraction(self, html_content: str) -> Dict[str, Any]:
        """Attempt enhanced extraction methods for minimal content pages."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        enhanced_methods = []
        
        # Method 1: Extract only lead section
        lead_paragraphs = []
        parser_output = soup.find('div', class_='mw-parser-output')
        if parser_output:
            # Get paragraphs before the first heading
            for element in parser_output.children:
                if element.name == 'p':
                    text = element.get_text().strip()
                    if text and len(text) > 10:  # Only substantial paragraphs
                        lead_paragraphs.append(text)
                elif element.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                    break  # Stop at first heading
        
        lead_content = '\n\n'.join(lead_paragraphs)
        enhanced_methods.append({
            'method': 'lead_section_only',
            'content_length': len(lead_content),
            'paragraph_count': len(lead_paragraphs),
            'content_preview': lead_content[:200] + '...' if len(lead_content) > 200 else lead_content
        })
        
        # Method 2: Extract all paragraphs with minimal filtering
        all_paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 5:  # Very minimal threshold
                all_paragraphs.append(text)
        
        all_content = '\n\n'.join(all_paragraphs)
        enhanced_methods.append({
            'method': 'all_paragraphs_minimal_filter',
            'content_length': len(all_content),
            'paragraph_count': len(all_paragraphs),
            'content_preview': all_content[:200] + '...' if len(all_content) > 200 else all_content
        })
        
        # Method 3: Raw text extraction
        raw_text = soup.get_text()
        # Clean up the raw text
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)
        
        enhanced_methods.append({
            'method': 'raw_text_extraction',
            'content_length': len(cleaned_text),
            'line_count': len(lines),
            'content_preview': cleaned_text[:200] + '...' if len(cleaned_text) > 200 else cleaned_text
        })
        
        print(f"🚀 Enhanced Extraction Methods:")
        for method in enhanced_methods:
            print(f"   - {method['method']}: {method['content_length']} chars")
            if method['content_length'] >= 20:
                print(f"     ✅ Would meet minimum threshold!")
                print(f"     📝 Preview: {method['content_preview']}")
            else:
                print(f"     ❌ Still below minimum threshold")
        
        return {
            'success': True,
            'methods': enhanced_methods
        }
    
    def generate_investigation_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive investigation report."""
        report_lines = []
        report_lines.append("# FAILED URL INVESTIGATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"URL: {results['url']}")
        report_lines.append(f"Investigation Date: {results['timestamp']}")
        report_lines.append("")
        
        # Summary
        report_lines.append("## EXECUTIVE SUMMARY")
        report_lines.append("")
        
        processing_step = results['steps'].get('content_processing', {})
        if processing_step.get('success'):
            final_length = len(processing_step.get('processed_content', '').strip())
            if final_length < 20:
                report_lines.append(f"❌ **ROOT CAUSE**: Content length ({final_length} chars) below minimum threshold (20 chars)")
                report_lines.append("")
                report_lines.append("The page is successfully fetched and processed, but the final content")
                report_lines.append("after Wikipedia-specific cleaning and markdown conversion is too short")
                report_lines.append("to meet the minimum content requirements.")
            else:
                report_lines.append("✅ Content processing succeeded - investigating other failure points...")
        else:
            report_lines.append("❌ **ROOT CAUSE**: Content processing failed")
            report_lines.append(f"Error: {processing_step.get('error', 'Unknown error')}")
        
        report_lines.append("")
        
        # Detailed steps
        for step_name, step_data in results['steps'].items():
            report_lines.append(f"## {step_name.upper().replace('_', ' ')}")
            report_lines.append("")
            
            if step_name == 'html_structure':
                report_lines.append(f"- Paragraphs found: {step_data['paragraph_count']}")
                report_lines.append(f"- Headings found: {step_data['heading_count']}")
                report_lines.append(f"- Total text length: {step_data['total_text_length']}")
                report_lines.append(f"- Main content div present: {'Yes' if step_data['has_mw_content_text'] else 'No'}")
                
            elif step_name == 'content_processing':
                if step_data.get('success'):
                    final_content = step_data.get('processed_content', '')
                    report_lines.append(f"- Processing: ✅ SUCCESS")
                    report_lines.append(f"- Final content length: {len(final_content.strip())} characters")
                    report_lines.append(f"- Meets minimum threshold (20 chars): {'Yes' if len(final_content.strip()) >= 20 else 'No'}")
                    if len(final_content.strip()) < 100:
                        report_lines.append(f"- Content preview: '{final_content.strip()}'")
                else:
                    report_lines.append(f"- Processing: ❌ FAILED")
                    report_lines.append(f"- Error: {step_data.get('error', 'Unknown')}")
            
            elif step_name == 'enhanced_extraction':
                report_lines.append("Enhanced extraction methods attempted:")
                for method in step_data.get('methods', []):
                    status = "✅" if method['content_length'] >= 20 else "❌"
                    report_lines.append(f"- {method['method']}: {status} {method['content_length']} chars")
            
            report_lines.append("")
        
        # Recommendations
        report_lines.append("## RECOMMENDATIONS")
        report_lines.append("")
        
        processing_step = results['steps'].get('content_processing', {})
        if processing_step.get('success'):
            final_length = len(processing_step.get('processed_content', '').strip())
            if final_length < 20:
                report_lines.append("1. **Lower minimum content threshold**: Consider reducing the 20-character minimum")
                report_lines.append("   for stub articles or pages with minimal content.")
                report_lines.append("")
                report_lines.append("2. **Enhanced extraction**: Implement alternative extraction methods")
                report_lines.append("   for pages that don't follow standard Wikipedia structure.")
                report_lines.append("")
                report_lines.append("3. **Manual review**: This page may legitimately have minimal content")
                report_lines.append("   and could be classified as a stub or redirect page.")
        
        return "\n".join(report_lines)


def main():
    """Main investigation function."""
    print("🔍 FAILED URL DETAILED INVESTIGATION")
    print("=" * 50)
    print("This script will perform a comprehensive analysis of why")
    print("'History_of_the_Jews_in_Singapore' fails content processing.")
    print()
    
    investigator = FailedURLInvestigator()
    
    try:
        # Perform investigation
        results = investigator.investigate_failed_url()
        
        # Generate report
        report = investigator.generate_investigation_report(results)
        
        # Save report
        report_file = Path("FAILED_URL_INVESTIGATION_REPORT.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 Detailed investigation report saved to: {report_file}")
        
        # Show summary
        processing_step = results['steps'].get('content_processing', {})
        if processing_step.get('success'):
            final_length = len(processing_step.get('processed_content', '').strip())
            if final_length < 20:
                print(f"\n🎯 ROOT CAUSE IDENTIFIED:")
                print(f"   Content length ({final_length} chars) is below minimum threshold (20 chars)")
                print(f"   The page processes successfully but has insufficient content.")
            else:
                print(f"\n❓ Content processing succeeded - need further investigation")
        else:
            print(f"\n❌ Content processing failed: {processing_step.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"\n❌ Investigation failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())