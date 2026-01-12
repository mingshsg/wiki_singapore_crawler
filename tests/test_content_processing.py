"""Property-based tests for content processing."""

import re
from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest

from wikipedia_crawler.processors import ContentProcessor


# Custom strategies for generating test data
@composite
def html_content(draw):
    """Generate realistic HTML content for testing."""
    # Basic HTML elements
    elements = [
        '<p>{text}</p>',
        '<h1>{text}</h1>',
        '<h2>{text}</h2>',
        '<h3>{text}</h3>',
        '<strong>{text}</strong>',
        '<em>{text}</em>',
        '<a href="/wiki/{link}">{text}</a>',
        '<ul><li>{text}</li></ul>',
        '<ol><li>{text}</li></ol>',
        '<blockquote>{text}</blockquote>',
    ]
    
    # Generate text content
    text_content = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=['Lu', 'Ll', 'Nd', 'Zs'],
            whitelist_characters='.,;:!?()-[]{}"\''
        ),
        min_size=1,
        max_size=100
    ))
    
    # Generate link text
    link_text = draw(st.text(
        alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd']),
        min_size=1,
        max_size=20
    ))
    
    # Choose random elements and combine
    num_elements = draw(st.integers(min_value=1, max_value=5))
    html_parts = []
    
    for _ in range(num_elements):
        element = draw(st.sampled_from(elements))
        html_parts.append(element.format(text=text_content, link=link_text))
    
    return '\n'.join(html_parts)


@composite
def wikipedia_html(draw):
    """Generate Wikipedia-like HTML content."""
    # Wikipedia-specific elements to test removal
    unwanted_elements = [
        '<div class="hatnote">{text}</div>',
        '<table class="infobox"><tr><td>{text}</td></tr></table>',
        '<div class="navbox">{text}</div>',
        '<span class="mw-editsection">[edit]</span>',
        '<sup class="reference"><a href="#ref1">[1]</a></sup>',
        '<div class="reflist"><ol><li>{text}</li></ol></div>',
        '<div class="thumb"><div class="thumbinner">{text}</div></div>',
    ]
    
    # Good content elements
    content_elements = [
        '<p>{text}</p>',
        '<h2><span class="mw-headline">{text}</span></h2>',
        '<ul><li>{text}</li></ul>',
        '<blockquote>{text}</blockquote>',
    ]
    
    text_content = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=['Lu', 'Ll', 'Nd', 'Zs'],
            whitelist_characters='.,;:!?()-'
        ),
        min_size=5,
        max_size=50
    ))
    
    # Mix good and bad elements
    all_elements = unwanted_elements + content_elements
    num_elements = draw(st.integers(min_value=2, max_value=8))
    
    html_parts = ['<div class="mw-parser-output">']
    for _ in range(num_elements):
        element = draw(st.sampled_from(all_elements))
        html_parts.append(element.format(text=text_content))
    html_parts.append('</div>')
    
    return '\n'.join(html_parts)


class TestContentProcessing:
    """Test content processing properties."""
    
    @given(html_input=html_content())
    def test_content_processing_removes_html_tags(self, html_input):
        """
        Property 2: Content Processing Round Trip - HTML tag removal
        For any HTML input, processed output should contain no HTML tags.
        **Feature: wikipedia-singapore-crawler, Property 2: Content Processing Round Trip**
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        assume(html_input.strip())
        
        processor = ContentProcessor()
        result = processor.process_content(html_input)
        
        # Should not contain HTML tags
        html_tag_pattern = re.compile(r'<[^>]+>')
        html_tags = html_tag_pattern.findall(result)
        
        assert len(html_tags) == 0, f"Found HTML tags in processed content: {html_tags}"
    
    @given(html_input=wikipedia_html())
    def test_wikipedia_specific_element_removal(self, html_input):
        """
        Property 2: Content Processing Round Trip - Wikipedia element removal
        For any Wikipedia HTML, unwanted elements should be removed.
        **Feature: wikipedia-singapore-crawler, Property 2: Content Processing Round Trip**
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        assume(html_input.strip())
        
        processor = ContentProcessor()
        result = processor.process_content(html_input)
        
        # Should not contain Wikipedia-specific unwanted elements
        unwanted_patterns = [
            r'\[edit\]',           # Edit links
            r'\[\d+\]',            # Citation numbers
            r'infobox',            # Infobox remnants
            r'navbox',             # Navigation box remnants
            r'reflist',            # Reference list remnants
        ]
        
        for pattern in unwanted_patterns:
            matches = re.findall(pattern, result, re.IGNORECASE)
            assert len(matches) == 0, f"Found unwanted pattern '{pattern}' in result: {matches}"
    
    @given(html_input=html_content())
    def test_content_processing_preserves_text_structure(self, html_input):
        """
        Property 2: Content Processing Round Trip - Structure preservation
        For any HTML input, essential text structure should be preserved in markdown.
        **Feature: wikipedia-singapore-crawler, Property 2: Content Processing Round Trip**
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        assume(html_input.strip())
        
        processor = ContentProcessor()
        result = processor.process_content(html_input)
        
        # If input had headers, output should have markdown headers
        if '<h1>' in html_input or '<h2>' in html_input or '<h3>' in html_input:
            # Should have some form of header structure (# or text emphasis)
            has_headers = '#' in result or '**' in result or '*' in result
            assert has_headers, "Headers should be converted to some form of markdown emphasis"
        
        # If input had lists, output should preserve list-like structure
        if '<ul>' in html_input or '<ol>' in html_input:
            # Should have list markers, line breaks, or preserved content structure
            list_pattern = re.compile(r'[-*]|\d+\.|^\s*\w', re.MULTILINE)
            assert list_pattern.search(result), f"Lists should preserve some structural elements. Result: '{result}'"
        
        # If input had links, output should preserve link content or structure
        if '<a href=' in html_input:
            # Should have markdown links or at least preserve the link text/URL
            has_links = (re.search(r'\[.*?\]\(.*?\)', result) or 
                        '/wiki/' in result or 
                        'http' in result)
            assert has_links, "Links should preserve URL or link text content"
    
    @given(
        html_input=html_content(),
        repeat_count=st.integers(min_value=1, max_value=3)
    )
    def test_content_processing_consistency(self, html_input, repeat_count):
        """
        Property 2: Content Processing Round Trip - Processing consistency
        For any HTML input, processing multiple times should yield the same result.
        **Feature: wikipedia-singapore-crawler, Property 2: Content Processing Round Trip**
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        assume(html_input.strip())
        
        processor = ContentProcessor()
        
        # Process multiple times
        results = []
        for _ in range(repeat_count):
            result = processor.process_content(html_input)
            results.append(result)
        
        # All results should be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result == first_result, f"Processing result {i} differs from first result"
    
    @given(html_input=st.text(min_size=0, max_size=1000))
    def test_content_processing_handles_invalid_html(self, html_input):
        """
        Property 2: Content Processing Round Trip - Invalid HTML handling
        For any text input (including invalid HTML), processing should not crash.
        **Feature: wikipedia-singapore-crawler, Property 2: Content Processing Round Trip**
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        processor = ContentProcessor()
        
        # Should not raise exceptions
        try:
            result = processor.process_content(html_input)
            # Result should be a string
            assert isinstance(result, str)
        except ValueError:
            # ValueError is acceptable for truly invalid input
            pass
    
    @given(html_input=html_content())
    def test_content_processing_output_format(self, html_input):
        """
        Property 2: Content Processing Round Trip - Output format validation
        For any HTML input, output should be valid markdown format.
        **Feature: wikipedia-singapore-crawler, Property 2: Content Processing Round Trip**
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        assume(html_input.strip())
        
        processor = ContentProcessor()
        result = processor.process_content(html_input)
        
        if result.strip():  # Only test non-empty results
            # Should not have excessive whitespace
            assert not re.search(r'\n{4,}', result), "Should not have more than 3 consecutive newlines"
            
            # Should not have trailing whitespace on lines
            lines = result.split('\n')
            for line in lines:
                assert line == line.rstrip(), f"Line should not have trailing whitespace: '{line}'"
            
            # Should end with single newline if not empty
            if result:
                assert result.endswith('\n'), "Content should end with single newline"
                assert not result.endswith('\n\n'), "Content should not end with multiple newlines"
    
    @given(
        original_html=html_content(),
        processed_markdown=st.text(min_size=0, max_size=500)
    )
    def test_content_stats_calculation(self, original_html, processed_markdown):
        """
        Property 2: Content Processing Round Trip - Statistics accuracy
        For any content processing operation, statistics should be accurate.
        **Feature: wikipedia-singapore-crawler, Property 2: Content Processing Round Trip**
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        processor = ContentProcessor()
        stats = processor.get_content_stats(original_html, processed_markdown)
        
        # Verify statistics accuracy
        assert stats['original_size'] == len(original_html)
        assert stats['processed_size'] == len(processed_markdown)
        
        if original_html:
            expected_ratio = len(processed_markdown) / len(original_html)
            assert abs(stats['compression_ratio'] - expected_ratio) < 0.001
        else:
            assert stats['compression_ratio'] == 0
        
        assert stats['original_lines'] == (original_html.count('\n') + 1 if original_html else 0)
        assert stats['processed_lines'] == (processed_markdown.count('\n') + 1 if processed_markdown else 0)
        
        # Boolean flags should be boolean
        assert isinstance(stats['has_headers'], bool)
        assert isinstance(stats['has_lists'], bool)
        assert isinstance(stats['has_links'], bool)
    
    def test_empty_content_handling(self):
        """Test handling of empty and whitespace-only content."""
        processor = ContentProcessor()
        
        # Empty string
        result = processor.process_content('')
        assert result == ''
        
        # Whitespace only
        result = processor.process_content('   \n\t   ')
        assert result == ''
        
        # None input should be handled gracefully
        try:
            result = processor.process_content(None)
        except (ValueError, TypeError):
            # Either exception is acceptable for None input
            pass
    
    def test_real_wikipedia_content_processing(self):
        """Test with realistic Wikipedia content."""
        processor = ContentProcessor()
        
        # Sample Wikipedia article structure
        wikipedia_html = '''
        <div class="mw-parser-output">
            <div class="hatnote">For other uses, see Singapore (disambiguation).</div>
            <p><b>Singapore</b> is a <a href="/wiki/City-state">city-state</a> in Southeast Asia.</p>
            <table class="infobox">
                <tr><td>Capital</td><td>Singapore</td></tr>
            </table>
            <h2><span class="mw-headline">History</span><span class="mw-editsection">[edit]</span></h2>
            <p>Founded in 1819<sup class="reference"><a href="#cite_note-1">[1]</a></sup>.</p>
            <h2>References</h2>
            <div class="reflist">
                <ol class="references">
                    <li id="cite_note-1">Historical reference</li>
                </ol>
            </div>
        </div>
        '''
        
        result = processor.process_content(wikipedia_html)
        
        # Should contain main content
        assert 'Singapore' in result
        assert 'city-state' in result
        
        # Should not contain unwanted elements
        assert '[edit]' not in result
        assert 'infobox' not in result.lower()
        assert 'references' not in result.lower()
        assert '[1]' not in result
        
        # Should have proper markdown structure
        assert '**Singapore**' in result or '*Singapore*' in result  # Bold formatting
        assert '#' in result  # Headers converted


if __name__ == "__main__":
    # Run a quick test to verify the test setup works
    import sys
    
    try:
        processor = ContentProcessor()
        
        # Test basic functionality
        test_html = '<p><strong>Test</strong> content with <a href="/wiki/Link">link</a>.</p>'
        result = processor.process_content(test_html)
        
        assert 'Test' in result
        assert '<' not in result  # No HTML tags
        
        print("✓ Basic content processing test passed")
        print("✓ Property tests are ready to run with: pytest tests/test_content_processing.py")
        
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        sys.exit(1)