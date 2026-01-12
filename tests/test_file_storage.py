"""Unit tests for file storage operations."""

import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

from wikipedia_crawler.core import FileStorage
from wikipedia_crawler.models import CategoryData, ArticleData


class TestFileStorage:
    """Test file storage operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileStorage(Path(self.temp_dir))
        
        # Sample data for testing
        self.sample_category = CategoryData(
            url="https://en.wikipedia.org/wiki/Category:Singapore",
            title="Singapore",
            subcategories=["Category:Singapore_history", "Category:Singapore_culture"],
            articles=["Singapore", "History_of_Singapore", "Culture_of_Singapore"]
        )
        
        self.sample_article = ArticleData(
            url="https://en.wikipedia.org/wiki/Singapore",
            title="Singapore",
            content="# Singapore\n\nSingapore is a city-state in Southeast Asia...",
            language="en"
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_directory_creation(self):
        """Test that output directory is created properly."""
        # Directory should exist after FileStorage initialization
        assert Path(self.temp_dir).exists()
        assert Path(self.temp_dir).is_dir()
    
    def test_save_category_basic(self):
        """Test basic category saving functionality."""
        # Save category
        file_path = self.storage.save_category(self.sample_category)
        
        # Verify file was created
        assert Path(file_path).exists()
        assert Path(file_path).name == "category_Singapore.json"
        
        # Verify file content
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['type'] == 'category'
        assert data['title'] == 'Singapore'
        assert data['url'] == self.sample_category.url
        assert data['subcategories'] == self.sample_category.subcategories
        assert data['articles'] == self.sample_category.articles
        assert '_metadata' in data
        assert 'saved_at' in data['_metadata']
    
    def test_save_article_basic(self):
        """Test basic article saving functionality."""
        # Save article
        file_path = self.storage.save_article(self.sample_article)
        
        # Verify file was created
        assert Path(file_path).exists()
        assert Path(file_path).name == "Singapore.json"
        
        # Verify file content
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['type'] == 'article'
        assert data['title'] == 'Singapore'
        assert data['url'] == self.sample_article.url
        assert data['content'] == self.sample_article.content
        assert data['language'] == self.sample_article.language
        assert '_metadata' in data
    
    def test_filename_sanitization(self):
        """Test that problematic filenames are properly sanitized."""
        problematic_category = CategoryData(
            url="https://en.wikipedia.org/wiki/Category:Test",
            title="File/with\\invalid:chars<>|?*",
            subcategories=[],
            articles=[]
        )
        
        file_path = self.storage.save_category(problematic_category)
        filename = Path(file_path).name
        
        # Should not contain invalid characters
        invalid_chars = set('<>:"/\\|?*')
        for char in filename:
            assert char not in invalid_chars
        
        # Should still be recognizable
        assert filename.startswith('category_')
        assert filename.endswith('.json')
    
    def test_duplicate_filename_handling(self):
        """Test handling of duplicate filenames."""
        # Save first category
        file_path1 = self.storage.save_category(self.sample_category)
        
        # Save another category with same title
        duplicate_category = CategoryData(
            url="https://en.wikipedia.org/wiki/Category:Singapore_duplicate",
            title="Singapore",  # Same title
            subcategories=[],
            articles=[]
        )
        
        file_path2 = self.storage.save_category(duplicate_category)
        
        # Should have different filenames
        assert file_path1 != file_path2
        assert Path(file_path1).name == "category_Singapore.json"
        assert Path(file_path2).name == "category_Singapore_1.json"
        
        # Both files should exist
        assert Path(file_path1).exists()
        assert Path(file_path2).exists()
    
    def test_file_exists_checking(self):
        """Test file existence checking functionality."""
        # Initially no files should exist
        assert not self.storage.file_exists("nonexistent.json")
        
        # Save a file
        file_path = self.storage.save_category(self.sample_category)
        filename = Path(file_path).name
        
        # Now it should exist
        assert self.storage.file_exists(filename)
        assert not self.storage.file_exists("still_nonexistent.json")
    
    def test_get_existing_files(self):
        """Test getting list of existing files."""
        # Initially should be empty
        existing = self.storage.get_existing_files()
        assert len(existing) == 0
        
        # Save some files
        self.storage.save_category(self.sample_category)
        self.storage.save_article(self.sample_article)
        
        # Should now have 2 files
        existing = self.storage.get_existing_files()
        assert len(existing) == 2
        assert "category_Singapore.json" in existing
        assert "Singapore.json" in existing
    
    def test_storage_statistics(self):
        """Test storage statistics functionality."""
        # Initial stats
        stats = self.storage.get_storage_stats()
        assert stats['total_files'] == 0
        assert stats['category_files'] == 0
        assert stats['article_files'] == 0
        assert stats['total_size_bytes'] == 0
        
        # Save files and check stats
        self.storage.save_category(self.sample_category)
        self.storage.save_article(self.sample_article)
        
        stats = self.storage.get_storage_stats()
        assert stats['total_files'] == 2
        assert stats['category_files'] == 1
        assert stats['article_files'] == 1
        assert stats['total_size_bytes'] > 0
        assert 'output_directory' in stats
    
    def test_ensure_directory_exists(self):
        """Test directory creation functionality."""
        nested_path = Path(self.temp_dir) / "nested" / "deep" / "directory"
        
        # Should not exist initially
        assert not nested_path.exists()
        
        # Create it
        self.storage.ensure_directory_exists(nested_path)
        
        # Should exist now
        assert nested_path.exists()
        assert nested_path.is_dir()
    
    def test_save_json_generic(self):
        """Test generic JSON saving functionality."""
        test_data = {
            "test_key": "test_value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"inner": "value"}
        }
        
        file_path = self.storage.save_json("test_file", test_data)
        
        # Verify file was created
        assert Path(file_path).exists()
        assert Path(file_path).name == "test_file.json"
        
        # Verify content
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # Should contain original data plus metadata
        assert saved_data['test_key'] == test_data['test_key']
        assert saved_data['number'] == test_data['number']
        assert saved_data['list'] == test_data['list']
        assert saved_data['nested'] == test_data['nested']
        assert '_metadata' in saved_data
    
    def test_cleanup_temp_files(self):
        """Test temporary file cleanup."""
        # Create some temporary files
        temp_file1 = Path(self.temp_dir) / "test1.tmp"
        temp_file2 = Path(self.temp_dir) / "test2.tmp"
        regular_file = Path(self.temp_dir) / "regular.json"
        
        temp_file1.write_text("temp content 1")
        temp_file2.write_text("temp content 2")
        regular_file.write_text("regular content")
        
        # All should exist
        assert temp_file1.exists()
        assert temp_file2.exists()
        assert regular_file.exists()
        
        # Cleanup temp files
        removed_count = self.storage.cleanup_temp_files()
        
        # Temp files should be removed, regular file should remain
        assert not temp_file1.exists()
        assert not temp_file2.exists()
        assert regular_file.exists()
        assert removed_count == 2
    
    def test_thread_safety(self):
        """Test thread safety of file operations."""
        results = []
        errors = []
        
        def save_category_worker(worker_id):
            try:
                category = CategoryData(
                    url=f"https://en.wikipedia.org/wiki/Category:Test_{worker_id}",
                    title=f"Test Category {worker_id}",
                    subcategories=[],
                    articles=[]
                )
                file_path = self.storage.save_category(category)
                results.append(file_path)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=save_category_worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert len(set(results)) == 10  # All paths should be unique
    
    def test_error_handling_permission_denied(self):
        """Test error handling when file permissions are denied."""
        # This test is platform-specific and may not work on all systems
        if Path(self.temp_dir).stat().st_mode & 0o200:  # Check if writable
            # Make directory read-only
            Path(self.temp_dir).chmod(0o444)
            
            try:
                # Should raise IOError
                with pytest.raises(IOError):
                    self.storage.save_category(self.sample_category)
            finally:
                # Restore permissions for cleanup
                Path(self.temp_dir).chmod(0o755)
    
    def test_error_handling_invalid_json(self):
        """Test error handling with data that cannot be serialized to JSON."""
        # Create data with non-serializable content
        invalid_data = {
            "valid_key": "valid_value",
            "invalid_key": set([1, 2, 3])  # Sets are not JSON serializable
        }
        
        with pytest.raises(IOError):
            self.storage.save_json("invalid_data", invalid_data)
    
    def test_atomic_file_operations(self):
        """Test that file operations are atomic."""
        # Mock a failure during file writing to test atomic behavior
        original_replace = Path.replace
        
        def failing_replace(self, target):
            if str(target).endswith('test_atomic.json'):
                raise OSError("Simulated failure")
            return original_replace(self, target)
        
        with patch.object(Path, 'replace', failing_replace):
            with pytest.raises(IOError):
                self.storage.save_json("test_atomic", {"test": "data"})
        
        # File should not exist after failed atomic operation
        target_file = Path(self.temp_dir) / "test_atomic.json"
        assert not target_file.exists()
    
    def test_unicode_content_handling(self):
        """Test handling of Unicode content in filenames and data."""
        unicode_category = CategoryData(
            url="https://zh.wikipedia.org/wiki/Category:新加坡",
            title="新加坡 (Singapore in Chinese)",
            subcategories=["Category:新加坡历史"],
            articles=["新加坡", "新加坡历史"]
        )
        
        file_path = self.storage.save_category(unicode_category)
        
        # File should be created successfully
        assert Path(file_path).exists()
        
        # Content should be preserved
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['title'] == unicode_category.title
        assert data['subcategories'] == unicode_category.subcategories
        assert data['articles'] == unicode_category.articles


if __name__ == "__main__":
    # Run a quick test to verify the test setup works
    import sys
    
    try:
        # Test basic functionality
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStorage(Path(temp_dir))
            
            category = CategoryData(
                url="https://en.wikipedia.org/wiki/Category:Test",
                title="Test Category",
                subcategories=[],
                articles=[]
            )
            
            file_path = storage.save_category(category)
            assert Path(file_path).exists()
            
        print("✓ Basic file storage test passed")
        print("✓ Unit tests are ready to run with: pytest tests/test_file_storage.py")
        
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        sys.exit(1)