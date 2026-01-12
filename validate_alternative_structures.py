#!/usr/bin/env python3
"""
Final validation that both old and new Wikipedia document structures work as alternatives.
"""

import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.processors.content_processor import ContentProcessor


def create_test_html_structures():
    """Create test HTML with both old and new structures."""
    
    # Sample content for testing
    sample_content = """
    <div class="mw-parser-output">
        <h1>Test Article</h1>
        <p>This is a test article with substantial content to verify that both document structures work correctly.</p>
        <h2>Section 1</h2>
        <p>Content for section 1 with <a href="/wiki/Link">links</a> and formatting.</p>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
        <h2>Section 2</h2>
        <p>More content to ensure we have enough text for validation.</p>
    </div>
    """
    
    # Structure 1: New Wikipedia structure (mw-content-container)
    new_structure = f"""
    <html>
    <body>
        <div class="mw-content-container">
            <div id="mw-content-text">
                {sample_content}
            </div>
        </div>
    </body>
    </html>
    """
    
    # Structure 2: Traditional Wikipedia structure (direct mw-content-text)
    old_structure = f"""
    <html>
    <body>
        <div id="mw-content-text">
            {sample_content}
        </div>
    </body>
    </html>
    """
    
    # Structure 3: Minimal structure (direct mw-parser-output)
    minimal_structure = f"""
    <html>
    <body>
        {sample_content}
    </body>
    </html>
    """
    
    return new_structure, old_structure, minimal_structure


def validate_alternative_structures():
    """Validate that all document structures work as alternatives."""
    
    print("🔄 Validating Alternative Document Structures")
    print("=" * 60)
    
    # Create test structures
    new_html, old_html, minimal_html = create_test_html_structures()
    
    # Initialize content processor
    processor = ContentProcessor()
    
    test_cases = [
        ("New Structure (mw-content-container)", new_html),
        ("Traditional Structure (mw-content-text)", old_html),
        ("Minimal Structure (mw-parser-output)", minimal_html)
    ]
    
    results = []
    
    for name, html in test_cases:
        print(f"\n📋 Testing: {name}")
        print("-" * 40)
        
        try:
            # Process the content
            processed = processor.process_content(html)
            
            # Validate results
            success = True
            issues = []
            
            # Check content length
            if len(processed) < 100:
                success = False
                issues.append(f"Content too short: {len(processed)} chars")
            
            # Check for title
            if "Test Article" not in processed:
                success = False
                issues.append("Missing title")
            
            # Check for sections
            if "Section 1" not in processed or "Section 2" not in processed:
                success = False
                issues.append("Missing sections")
            
            # Check for links
            if "[links]" not in processed and "links" not in processed:
                success = False
                issues.append("Missing links")
            
            # Report results
            if success:
                print(f"✅ SUCCESS: {len(processed)} characters processed")
                print(f"📄 Content preview: {processed[:150]}...")
            else:
                print(f"❌ FAILED: {', '.join(issues)}")
                print(f"📄 Content: {processed[:200]}...")
            
            results.append((name, success, len(processed), issues))
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((name, False, 0, [str(e)]))
    
    # Summary
    print(f"\n📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    successful_tests = sum(1 for _, success, _, _ in results if success)
    total_tests = len(results)
    
    print(f"✅ Successful tests: {successful_tests}/{total_tests}")
    
    for name, success, length, issues in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}: {length} chars")
        if issues:
            for issue in issues:
                print(f"    - {issue}")
    
    # Overall result
    if successful_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! Both document structures work as alternatives.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Alternative structures may not be working correctly.")
        return False


def test_extraction_priority():
    """Test that the newer structure is preferred when both are present."""
    
    print(f"\n🔍 Testing Extraction Priority")
    print("=" * 40)
    
    # Create HTML with both structures present
    html_with_both = """
    <html>
    <body>
        <div class="mw-content-container">
            <div id="mw-content-text">
                <div class="mw-parser-output">
                    <h1>Newer Structure Content</h1>
                    <p>This content should be preferred because it's in the newer mw-content-container structure.</p>
                </div>
            </div>
        </div>
        <div id="mw-content-text">
            <div class="mw-parser-output">
                <h1>Older Structure Content</h1>
                <p>This content should NOT be used when newer structure is available.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    processor = ContentProcessor()
    
    try:
        processed = processor.process_content(html_with_both)
        
        if "Newer Structure Content" in processed and "Older Structure Content" not in processed:
            print("✅ Newer structure correctly preferred")
            return True
        elif "Older Structure Content" in processed:
            print("❌ Older structure was used instead of newer")
            return False
        else:
            print("❌ Neither structure was properly extracted")
            return False
            
    except Exception as e:
        print(f"❌ Error testing priority: {e}")
        return False


if __name__ == "__main__":
    # Run validation tests
    structures_valid = validate_alternative_structures()
    priority_correct = test_extraction_priority()
    
    print(f"\n🏁 FINAL RESULT")
    print("=" * 30)
    
    if structures_valid and priority_correct:
        print("✅ All validations passed!")
        print("✅ Both document structures work as alternatives")
        print("✅ Newer structure is correctly prioritized")
    else:
        print("❌ Some validations failed")
        if not structures_valid:
            print("❌ Alternative structures not working correctly")
        if not priority_correct:
            print("❌ Structure priority not working correctly")