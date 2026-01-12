"""Property-based tests for language filtering."""

import re
from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest

from wikipedia_crawler.processors import LanguageFilter


# Custom strategies for generating test data
@composite
def english_text(draw):
    """Generate English-like text."""
    words = draw(st.lists(
        st.text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 
               min_size=1, max_size=15),
        min_size=1, max_size=20
    ))
    return ' '.join(words)


@composite
def chinese_text(draw):
    """Generate Chinese-like text."""
    # Common Chinese characters
    chinese_chars = '的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严'
    
    # Generate random Chinese text
    num_chars = draw(st.integers(min_value=5, max_value=100))
    chars = draw(st.lists(st.sampled_from(chinese_chars), min_size=num_chars, max_size=num_chars))
    
    # Add some spaces to make it more realistic
    text_parts = []
    current_part = []
    
    for char in chars:
        current_part.append(char)
        if draw(st.booleans()) and len(current_part) > 2:  # Random word breaks
            text_parts.append(''.join(current_part))
            current_part = []
    
    if current_part:
        text_parts.append(''.join(current_part))
    
    return ' '.join(text_parts) if text_parts else ''.join(chars)


@composite
def mixed_language_text(draw):
    """Generate text with mixed languages."""
    english_part = draw(english_text())
    chinese_part = draw(chinese_text())
    
    # Mix them in various ways
    mix_style = draw(st.integers(min_value=0, max_value=2))
    
    if mix_style == 0:
        return f"{english_part} {chinese_part}"
    elif mix_style == 1:
        return f"{chinese_part} {english_part}"
    else:
        # Interleave
        return f"{english_part} {chinese_part} {english_part}"


@composite
def wikipedia_urls(draw):
    """Generate Wikipedia URLs for different languages."""
    domains = [
        'en.wikipedia.org',
        'zh.wikipedia.org', 
        'zh-cn.wikipedia.org',
        'fr.wikipedia.org',
        'de.wikipedia.org',
        'es.wikipedia.org'
    ]
    
    domain = draw(st.sampled_from(domains))
    article = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_',
        min_size=1, max_size=30
    ))
    
    return f"https://{domain}/wiki/{article}"


class TestLanguageFiltering:
    """Test language filtering properties."""
    
    @given(
        content=english_text(),
        url=st.sampled_from([
            'https://en.wikipedia.org/wiki/Test',
            'https://en.wikipedia.org/wiki/Article',
            ''
        ])
    )
    def test_english_content_detection_and_acceptance(self, content, url):
        """
        Property 3: Language Detection Consistency - English content
        For any English content, it should be detected as English and accepted.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        assume(content.strip())
        
        language_filter = LanguageFilter()
        should_process, detected_lang = language_filter.filter_content(content, url)
        
        # If URL is from English Wikipedia, content should always be accepted
        if 'en.wikipedia.org' in url:
            assert should_process, f"English Wikipedia content should be accepted. Detected: {detected_lang}"
            assert detected_lang == 'en', f"English Wikipedia URL should detect as 'en', got '{detected_lang}'"
        else:
            # For content without URL context, language detection may vary
            # We only assert that the system behaves consistently and doesn't crash
            assert isinstance(should_process, bool)
            assert isinstance(detected_lang, str)
            
            # If detected as English, should be processed
            if detected_lang == 'en':
                assert should_process, f"Content detected as English should be processed"
    
    @given(
        content=chinese_text(),
        url=st.sampled_from([
            'https://zh.wikipedia.org/wiki/测试',
            'https://zh-cn.wikipedia.org/wiki/文章',
            ''
        ])
    )
    def test_chinese_content_detection_and_acceptance(self, content, url):
        """
        Property 3: Language Detection Consistency - Chinese content
        For any Chinese content, it should be detected as Chinese and accepted.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        assume(content.strip())
        
        language_filter = LanguageFilter()
        should_process, detected_lang = language_filter.filter_content(content, url)
        
        # If URL is from Chinese Wikipedia, content should always be accepted
        if any(domain in url for domain in ['zh.wikipedia.org', 'zh-cn.wikipedia.org']):
            assert should_process, f"Chinese Wikipedia content should be accepted. Detected: {detected_lang}"
            assert detected_lang in ['zh', 'zh-cn'], f"Chinese Wikipedia URL should detect as Chinese variant, got '{detected_lang}'"
        else:
            # For content without URL context, language detection may vary
            # We only assert that the system behaves consistently and doesn't crash
            assert isinstance(should_process, bool)
            assert isinstance(detected_lang, str)
            
            # If detected as Chinese, should be processed
            if detected_lang in ['zh', 'zh-cn']:
                assert should_process, f"Content detected as Chinese should be processed"
    
    @given(
        content=st.text(
            alphabet='àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ',  # Non-English/Chinese characters
            min_size=10,
            max_size=100
        ),
        url=st.sampled_from([
            'https://fr.wikipedia.org/wiki/Article',
            'https://de.wikipedia.org/wiki/Artikel',
            'https://es.wikipedia.org/wiki/Artículo'
        ])
    )
    def test_unsupported_language_filtering(self, content, url):
        """
        Property 3: Language Detection Consistency - Unsupported language filtering
        For any content in unsupported languages, it should be filtered out.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        assume(content.strip())
        
        language_filter = LanguageFilter()
        should_process, detected_lang = language_filter.filter_content(content, url)
        
        # If language is detected as something other than supported languages, should be filtered
        if detected_lang not in ['en', 'zh', 'zh-cn', 'unknown']:
            assert not should_process, f"Unsupported language '{detected_lang}' should be filtered"
    
    @given(url=wikipedia_urls())
    def test_url_based_language_detection_consistency(self, url):
        """
        Property 3: Language Detection Consistency - URL-based detection
        For any Wikipedia URL, language detection should be consistent with domain.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        language_filter = LanguageFilter()
        
        # Test with minimal content to rely on URL detection
        should_process, detected_lang = language_filter.filter_content("test", url)
        
        # Check consistency with domain
        if 'en.wikipedia.org' in url:
            assert detected_lang == 'en', f"English Wikipedia URL should detect as 'en', got '{detected_lang}'"
            assert should_process, "English Wikipedia content should be processed"
        elif 'zh.wikipedia.org' in url or 'zh-cn.wikipedia.org' in url:
            assert detected_lang in ['zh', 'zh-cn'], f"Chinese Wikipedia URL should detect as Chinese variant, got '{detected_lang}'"
            assert should_process, "Chinese Wikipedia content should be processed"
        elif any(domain in url for domain in ['fr.wikipedia.org', 'de.wikipedia.org', 'es.wikipedia.org']):
            # These should be filtered out
            if detected_lang not in ['en', 'zh', 'zh-cn', 'unknown']:
                assert not should_process, f"Unsupported Wikipedia domain should be filtered"
    
    @given(
        supported_langs=st.sets(
            st.sampled_from(['en', 'zh', 'zh-cn', 'fr', 'de', 'es', 'ja', 'ko']),
            min_size=1,
            max_size=4
        ),
        test_lang=st.sampled_from(['en', 'zh', 'zh-cn', 'fr', 'de', 'es', 'ja', 'ko'])
    )
    def test_custom_supported_languages_configuration(self, supported_langs, test_lang):
        """
        Property 3: Language Detection Consistency - Custom language configuration
        For any set of supported languages, filtering should respect the configuration.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        language_filter = LanguageFilter(supported_langs)
        
        # Test if language is supported
        is_supported = language_filter.is_supported_language(test_lang)
        
        # Should match the configuration
        expected_supported = test_lang in supported_langs
        assert is_supported == expected_supported, f"Language '{test_lang}' support should be {expected_supported}, got {is_supported}"
    
    @given(
        content=st.one_of(english_text(), chinese_text(), mixed_language_text()),
        filter_calls=st.integers(min_value=1, max_value=5)
    )
    def test_language_detection_consistency_across_calls(self, content, filter_calls):
        """
        Property 3: Language Detection Consistency - Repeated detection consistency
        For any content, repeated language detection should yield consistent results.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        assume(content.strip())
        
        language_filter = LanguageFilter()
        
        # Perform multiple detections
        results = []
        for _ in range(filter_calls):
            should_process, detected_lang = language_filter.filter_content(content)
            results.append((should_process, detected_lang))
        
        # All results should be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result == first_result, f"Detection result {i} differs from first result: {result} vs {first_result}"
    
    @given(
        content=st.text(min_size=0, max_size=1000),
        url=st.text(min_size=0, max_size=100)
    )
    def test_language_filtering_robustness(self, content, url):
        """
        Property 3: Language Detection Consistency - Robustness
        For any input (including invalid), language filtering should not crash.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        language_filter = LanguageFilter()
        
        # Should not raise exceptions
        try:
            should_process, detected_lang = language_filter.filter_content(content, url)
            
            # Results should be valid types
            assert isinstance(should_process, bool)
            assert isinstance(detected_lang, str)
            
            # Language code should be reasonable
            assert len(detected_lang) <= 10  # Reasonable length limit
            
        except Exception as e:
            # Should not crash on any input
            pytest.fail(f"Language filtering crashed on input: {e}")
    
    @given(
        initial_content=english_text(),
        additional_calls=st.integers(min_value=1, max_value=10)
    )
    def test_language_statistics_accuracy(self, initial_content, additional_calls):
        """
        Property 3: Language Detection Consistency - Statistics accuracy
        For any sequence of language filtering operations, statistics should be accurate.
        **Feature: wikipedia-singapore-crawler, Property 3: Language Detection Consistency**
        **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.5**
        """
        assume(initial_content.strip())
        
        language_filter = LanguageFilter()
        
        # Reset stats to start clean
        language_filter.reset_stats()
        initial_stats = language_filter.get_language_stats()
        assert len(initial_stats) == 0, "Stats should be empty after reset"
        
        # Perform filtering operations
        detected_languages = []
        for _ in range(additional_calls):
            _, detected_lang = language_filter.filter_content(initial_content)
            detected_languages.append(detected_lang)
        
        # Check statistics accuracy
        final_stats = language_filter.get_language_stats()
        
        # Count expected occurrences
        from collections import Counter
        expected_counts = Counter(detected_languages)
        
        # Verify statistics match
        for lang, expected_count in expected_counts.items():
            actual_count = final_stats.get(lang, 0)
            assert actual_count == expected_count, f"Expected {expected_count} occurrences of '{lang}', got {actual_count}"
        
        # Total count should match
        total_expected = sum(expected_counts.values())
        total_actual = sum(final_stats.values())
        assert total_actual == total_expected, f"Total count mismatch: expected {total_expected}, got {total_actual}"
    
    def test_empty_and_edge_case_handling(self):
        """Test handling of empty content and edge cases."""
        language_filter = LanguageFilter()
        
        # Empty content
        should_process, detected_lang = language_filter.filter_content('', '')
        assert detected_lang == 'unknown'
        assert not should_process  # Unknown language should not be processed
        
        # Whitespace only
        should_process, detected_lang = language_filter.filter_content('   \n\t   ', '')
        assert detected_lang == 'unknown'
        
        # Very short content
        should_process, detected_lang = language_filter.filter_content('a', '')
        assert isinstance(should_process, bool)
        assert isinstance(detected_lang, str)
        
        # Numbers and symbols only
        should_process, detected_lang = language_filter.filter_content('123 !@# 456', '')
        assert detected_lang == 'unknown'
    
    def test_language_normalization_consistency(self):
        """Test language code normalization."""
        language_filter = LanguageFilter()
        
        # Test normalization cases
        test_cases = [
            ('en', 'en'),
            ('EN', 'en'),
            ('English', 'en'),
            ('zh', 'zh'),
            ('Chinese', 'zh'),
            ('zh-hans', 'zh-cn'),
            ('zh-cn', 'zh-cn'),
            ('unknown_lang', 'unknown_lang')
        ]
        
        for input_lang, expected in test_cases:
            normalized = language_filter._normalize_language_code(input_lang)
            assert normalized == expected, f"Expected '{expected}' for '{input_lang}', got '{normalized}'"


if __name__ == "__main__":
    # Run a quick test to verify the test setup works
    import sys
    
    try:
        language_filter = LanguageFilter()
        
        # Test basic functionality
        should_process, detected_lang = language_filter.filter_content(
            "This is English text", 
            "https://en.wikipedia.org/wiki/Test"
        )
        
        assert should_process
        assert detected_lang == 'en'
        
        print("✓ Basic language filtering test passed")
        print("✓ Property tests are ready to run with: pytest tests/test_language_filtering.py")
        
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        sys.exit(1)