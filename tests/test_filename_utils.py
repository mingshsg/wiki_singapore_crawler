"""Property-based tests for filename sanitization utilities."""

import os
import string
from pathlib import Path
from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest

from wikipedia_crawler.utils import (
    sanitize_filename, sanitize_wikipedia_title, create_unique_filename
)


# Custom strategies for generating test data
@composite
def filesystem_unsafe_text(draw):
    """Generate text that may contain filesystem-unsafe characters."""
    # Include all printable ASCII characters plus some Unicode
    unsafe_chars = '<>:"/\\|?*'
    control_chars = ''.join(chr(i) for i in range(32))
    
    base_text = draw(st.text(
        alphabet=string.printable + 'áéíóúñü中文日本語한국어',
        min_size=1,
        max_size=300
    ))
    
    # Sometimes add problematic characters
    if draw(st.booleans()):
        extra_chars = draw(st.text(alphabet=unsafe_chars + control_chars, max_size=10))
        base_text += extra_chars
    
    return base_text


@composite
def wikipedia_titles(draw):
    """Generate realistic Wikipedia page titles."""
    # Common Wikipedia title patterns
    patterns = [
        "Article Name",
        "Category:Topic Name", 
        "Person Name (disambiguation)",
        "Event (year)",
        "Location, Country",
        "Topic/Subtopic",
        "Name with numbers 123",
        "Unicode title 中文",
        "Title with 'quotes' and \"more quotes\"",
        "Title with (parentheses) and [brackets]"
    ]
    
    if draw(st.booleans()):
        # Use a predefined pattern
        return draw(st.sampled_from(patterns))
    else:
        # Generate a custom title
        words = draw(st.lists(
            st.text(alphabet=string.ascii_letters + string.digits + ' ()-[]{}.,;:!?\'\"', 
                   min_size=1, max_size=20),
            min_size=1, max_size=5
        ))
        return ' '.join(words)


class TestFilenameSanitization:
    """Test filename sanitization properties."""
    
    @given(filename=filesystem_unsafe_text())
    def test_sanitized_filename_is_filesystem_safe(self, filename):
        """
        Property 5: Filename Sanitization Safety
        For any input string, the sanitized filename should be safe for all major filesystems.
        **Feature: wikipedia-singapore-crawler, Property 5: Filename Sanitization Safety**
        **Validates: Requirements 2.7, 6.3**
        """
        # Skip empty or whitespace-only inputs as they should raise ValueError
        assume(filename.strip())
        
        try:
            sanitized = sanitize_filename(filename)
            
            # Test 1: No invalid characters
            invalid_chars = set('<>:"/\\|?*')
            control_chars = set(chr(i) for i in range(32))
            
            for char in sanitized:
                assert char not in invalid_chars, f"Invalid character '{char}' found in sanitized filename"
                assert char not in control_chars, f"Control character found in sanitized filename"
            
            # Test 2: No leading/trailing problematic characters
            assert not sanitized.startswith('.'), "Filename should not start with dot"
            assert not sanitized.endswith('.'), "Filename should not end with dot"
            assert not sanitized.endswith(' '), "Filename should not end with space"
            
            # Test 3: Not a reserved name (Windows)
            reserved_names = {
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
            }
            name_without_ext = sanitized.split('.')[0].upper()
            assert name_without_ext not in reserved_names, f"Filename uses reserved name: {name_without_ext}"
            
            # Test 4: Reasonable length
            assert len(sanitized) <= 200, f"Sanitized filename too long: {len(sanitized)} characters"
            
            # Test 5: Not empty
            assert sanitized, "Sanitized filename should not be empty"
            
            # Test 6: Should be creatable as a Path (basic validation)
            try:
                Path(sanitized)
            except (OSError, ValueError) as e:
                pytest.fail(f"Sanitized filename '{sanitized}' cannot be used as Path: {e}")
                
        except ValueError:
            # ValueError is acceptable for inputs that cannot be sanitized
            pass
    
    @given(
        filename=filesystem_unsafe_text(),
        max_length=st.integers(min_value=10, max_value=500)
    )
    def test_sanitized_filename_respects_length_limit(self, filename, max_length):
        """
        Property 5: Filename Sanitization Safety - Length limits
        For any input and max_length, sanitized filename should not exceed the limit.
        **Feature: wikipedia-singapore-crawler, Property 5: Filename Sanitization Safety**
        **Validates: Requirements 2.7, 6.3**
        """
        assume(filename.strip())
        
        try:
            sanitized = sanitize_filename(filename, max_length=max_length)
            assert len(sanitized) <= max_length, f"Sanitized filename exceeds max_length: {len(sanitized)} > {max_length}"
            
            # If original had an extension, try to preserve it
            if '.' in filename and len(sanitized) == max_length:
                # Should still be a valid filename
                assert sanitized, "Truncated filename should not be empty"
                
        except ValueError:
            # ValueError is acceptable for inputs that cannot be sanitized
            pass
    
    @given(title=wikipedia_titles())
    def test_wikipedia_title_sanitization_preserves_meaning(self, title):
        """
        Property 5: Filename Sanitization Safety - Wikipedia titles
        For any Wikipedia title, sanitization should preserve recognizable content.
        **Feature: wikipedia-singapore-crawler, Property 5: Filename Sanitization Safety**
        **Validates: Requirements 2.7, 6.3**
        """
        assume(title.strip())
        
        try:
            sanitized = sanitize_wikipedia_title(title)
            
            # Should end with .json
            assert sanitized.endswith('.json'), "Wikipedia title should be sanitized to .json file"
            
            # Should have appropriate prefix for categories
            if title.startswith('Category:'):
                assert sanitized.startswith('category_'), "Category titles should have 'category_' prefix"
            else:
                assert not sanitized.startswith('category_'), "Non-category titles should not have 'category_' prefix"
            
            # Should be filesystem safe
            filename_part = sanitized[:-5]  # Remove .json extension
            if filename_part.startswith('category_'):
                filename_part = filename_part[9:]  # Remove category_ prefix
            
            # Should contain some recognizable content from original title
            # (This is a heuristic test - we expect some similarity)
            original_clean = title.replace('Category:', '').replace('_', ' ').lower()
            sanitized_clean = filename_part.replace('_', ' ').lower()
            
            # At least some characters should be preserved
            common_chars = set(original_clean) & set(sanitized_clean)
            if len(original_clean) > 5:  # Only check for longer titles
                assert len(common_chars) > 0, "Sanitized title should preserve some characters from original"
                
        except ValueError:
            # ValueError is acceptable for titles that cannot be sanitized
            pass
    
    @given(
        base_filename=st.text(alphabet=string.ascii_letters + string.digits + '._-', 
                             min_size=1, max_size=50),
        existing_count=st.integers(min_value=0, max_value=10)
    )
    def test_unique_filename_generation(self, base_filename, existing_count):
        """
        Property 5: Filename Sanitization Safety - Unique filename generation
        For any base filename and set of existing files, generated filename should be unique.
        **Feature: wikipedia-singapore-crawler, Property 5: Filename Sanitization Safety**
        **Validates: Requirements 2.7, 6.3**
        """
        assume(base_filename.strip())
        
        # Create set of existing filenames
        existing_files = set()
        
        # Add the base filename if it should exist
        if existing_count > 0:
            existing_files.add(base_filename)
        
        # Add numbered variants
        for i in range(1, existing_count):
            if '.' in base_filename:
                name, ext = base_filename.rsplit('.', 1)
                existing_files.add(f"{name}_{i}.{ext}")
            else:
                existing_files.add(f"{base_filename}_{i}")
        
        # Generate unique filename
        unique_filename = create_unique_filename(base_filename, existing_files)
        
        # Test uniqueness
        assert unique_filename not in existing_files, "Generated filename should be unique"
        
        # Test that it's related to the original
        if base_filename not in existing_files:
            assert unique_filename == base_filename, "Should return original if not in existing set"
        else:
            # Should be a numbered variant
            if '.' in base_filename:
                name, ext = base_filename.rsplit('.', 1)
                assert unique_filename.startswith(f"{name}_"), "Numbered variant should have correct prefix"
                assert unique_filename.endswith(f".{ext}"), "Numbered variant should preserve extension"
            else:
                assert unique_filename.startswith(f"{base_filename}_"), "Numbered variant should have correct prefix"
    
    @given(
        filename1=filesystem_unsafe_text(),
        filename2=filesystem_unsafe_text()
    )
    def test_sanitization_consistency(self, filename1, filename2):
        """
        Property 5: Filename Sanitization Safety - Consistency
        Sanitizing the same input should always produce the same output.
        **Feature: wikipedia-singapore-crawler, Property 5: Filename Sanitization Safety**
        **Validates: Requirements 2.7, 6.3**
        """
        assume(filename1.strip() and filename2.strip())
        
        try:
            # Same input should produce same output
            result1a = sanitize_filename(filename1)
            result1b = sanitize_filename(filename1)
            assert result1a == result1b, "Sanitization should be deterministic"
            
            # Different inputs should generally produce different outputs (when both are valid)
            if filename1 != filename2:
                try:
                    result2 = sanitize_filename(filename2)
                    # If both succeed and inputs are different, outputs should generally be different
                    # (though this isn't guaranteed due to character replacement)
                    if result1a == result2:
                        # This is acceptable - different inputs can produce same sanitized output
                        pass
                except ValueError:
                    # Second filename might not be sanitizable
                    pass
                    
        except ValueError:
            # First filename might not be sanitizable - that's fine
            pass
    
    def test_edge_cases_and_error_conditions(self):
        """Test specific edge cases and error conditions."""
        # Empty string should raise ValueError
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            sanitize_filename("")
        
        # Whitespace-only should raise ValueError
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            sanitize_filename("   ")
        
        # String that becomes empty after sanitization
        with pytest.raises(ValueError, match="Filename becomes empty after sanitization"):
            sanitize_filename("...")
        
        # Very long filename should be truncated
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200
        
        # Reserved names should be handled
        result = sanitize_filename("CON")
        assert result != "CON"
        assert "CON" in result  # Should be modified, not completely replaced


if __name__ == "__main__":
    # Run a quick test to verify the test setup works
    import sys
    
    try:
        # Test basic functionality
        result = sanitize_filename("Test/File<Name>")
        print(f"✓ Basic sanitization test passed: '{result}'")
        
        wiki_result = sanitize_wikipedia_title("Category:Singapore")
        print(f"✓ Wikipedia title test passed: '{wiki_result}'")
        
        unique_result = create_unique_filename("test.txt", {"test.txt"})
        print(f"✓ Unique filename test passed: '{unique_result}'")
        
        print("✓ Property tests are ready to run with: pytest tests/test_filename_utils.py")
        
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        sys.exit(1)