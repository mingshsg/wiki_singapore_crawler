"""File storage system for the Wikipedia crawler."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Set, Optional, Dict, Any
import threading
from datetime import datetime

from wikipedia_crawler.models import CategoryData, ArticleData
from wikipedia_crawler.utils import sanitize_wikipedia_title, create_unique_filename
from wikipedia_crawler.utils.logging_config import get_logger


class FileStorage:
    """
    Handles all file I/O operations for the Wikipedia crawler.
    
    Provides atomic file operations, directory management, and organized storage
    for both category and article data with proper filename sanitization.
    """
    
    def __init__(self, output_dir: Path):
        """
        Initialize the file storage system.
        
        Args:
            output_dir: Base directory for storing crawled content
        """
        self.output_dir = Path(output_dir)
        self.logger = get_logger(__name__)
        self._lock = threading.Lock()  # For thread-safe operations
        self._existing_files: Set[str] = set()
        
        # Ensure output directory exists
        self.ensure_directory_exists(self.output_dir)
        
        # Load existing files for conflict detection
        self._load_existing_files()
    
    def save_category(self, data: CategoryData) -> str:
        """
        Save category data as JSON file.
        
        Args:
            data: CategoryData instance to save
            
        Returns:
            Path to the saved file
            
        Raises:
            IOError: If file cannot be saved
        """
        try:
            # Generate filename
            filename = sanitize_wikipedia_title(data.title, page_type='category')
            
            # Ensure unique filename
            with self._lock:
                unique_filename = create_unique_filename(filename, self._existing_files)
                self._existing_files.add(unique_filename)
            
            # Save file atomically
            file_path = self.output_dir / unique_filename
            self._save_json_atomic(file_path, data.to_dict())
            
            self.logger.info(f"Saved category: {data.title} -> {unique_filename}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save category {data.title}: {e}")
            raise IOError(f"Cannot save category data: {e}") from e
    
    def save_article(self, data: ArticleData) -> str:
        """
        Save article data as JSON file.
        
        Args:
            data: ArticleData instance to save
            
        Returns:
            Path to the saved file
            
        Raises:
            IOError: If file cannot be saved
        """
        try:
            # Generate filename
            filename = sanitize_wikipedia_title(data.title, page_type='article')
            
            # Ensure unique filename
            with self._lock:
                unique_filename = create_unique_filename(filename, self._existing_files)
                self._existing_files.add(unique_filename)
            
            # Save file atomically
            file_path = self.output_dir / unique_filename
            self._save_json_atomic(file_path, data.to_dict())
            
            self.logger.info(f"Saved article: {data.title} -> {unique_filename}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save article {data.title}: {e}")
            raise IOError(f"Cannot save article data: {e}") from e
    
    def save_json(self, filename: str, data: Dict[str, Any]) -> str:
        """
        Save arbitrary JSON data to a file.
        
        Args:
            filename: Desired filename (will be sanitized)
            data: Dictionary to save as JSON
            
        Returns:
            Path to the saved file
            
        Raises:
            IOError: If file cannot be saved
        """
        try:
            # Sanitize filename
            from wikipedia_crawler.utils.filename_utils import sanitize_filename
            safe_filename = sanitize_filename(filename)
            
            # Ensure .json extension
            if not safe_filename.endswith('.json'):
                safe_filename += '.json'
            
            # Ensure unique filename
            with self._lock:
                unique_filename = create_unique_filename(safe_filename, self._existing_files)
                self._existing_files.add(unique_filename)
            
            # Save file atomically
            file_path = self.output_dir / unique_filename
            self._save_json_atomic(file_path, data)
            
            self.logger.debug(f"Saved JSON data -> {unique_filename}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON file {filename}: {e}")
            raise IOError(f"Cannot save JSON data: {e}") from e
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in the output directory.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        with self._lock:
            return filename in self._existing_files
    
    def get_existing_files(self) -> Set[str]:
        """
        Get set of existing filenames.
        
        Returns:
            Set of existing filenames
        """
        with self._lock:
            return self._existing_files.copy()
    
    def ensure_directory_exists(self, path: Path) -> None:
        """
        Create directory if it doesn't exist.
        
        Args:
            path: Directory path to create
            
        Raises:
            IOError: If directory cannot be created
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {path}")
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            raise IOError(f"Cannot create directory: {e}") from e
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored files.
        
        Returns:
            Dictionary with storage statistics
        """
        with self._lock:
            total_files = len(self._existing_files)
            
            # Count by type
            category_files = sum(1 for f in self._existing_files if f.startswith('category_'))
            article_files = total_files - category_files
            
            # Calculate total size
            total_size = 0
            for filename in self._existing_files:
                file_path = self.output_dir / filename
                if file_path.exists():
                    total_size += file_path.stat().st_size
            
            return {
                'total_files': total_files,
                'category_files': category_files,
                'article_files': article_files,
                'total_size_bytes': total_size,
                'output_directory': str(self.output_dir)
            }
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up any temporary files in the output directory.
        
        Returns:
            Number of temporary files removed
        """
        temp_pattern = "*.tmp"
        removed_count = 0
        
        try:
            for temp_file in self.output_dir.glob(temp_pattern):
                try:
                    temp_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Removed temporary file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Could not remove temp file {temp_file}: {e}")
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} temporary files")
                
        except Exception as e:
            self.logger.error(f"Error during temp file cleanup: {e}")
        
        return removed_count
    
    def _save_json_atomic(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Save JSON data atomically using a temporary file.
        
        Args:
            file_path: Target file path
            data: Data to save as JSON
            
        Raises:
            IOError: If file cannot be saved
        """
        # Create temporary file in the same directory
        temp_dir = file_path.parent
        
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.tmp',
                dir=temp_dir,
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                
                # Add metadata
                data_with_metadata = data.copy()
                data_with_metadata['_metadata'] = {
                    'saved_at': datetime.now().isoformat(),
                    'crawler_version': '1.0.0',
                    'file_format_version': '1.0'
                }
                
                # Write JSON with proper formatting
                json.dump(
                    data_with_metadata,
                    temp_file,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True
                )
                temp_file.flush()
                temp_path = Path(temp_file.name)
            
            # Atomic move to final location
            temp_path.replace(file_path)
            
        except Exception as e:
            # Clean up temp file if it exists
            try:
                if 'temp_path' in locals():
                    temp_path.unlink(missing_ok=True)
            except:
                pass
            raise IOError(f"Failed to save file atomically: {e}") from e
    
    def _load_existing_files(self) -> None:
        """Load existing files from the output directory."""
        try:
            if self.output_dir.exists():
                for file_path in self.output_dir.iterdir():
                    if file_path.is_file() and file_path.suffix == '.json':
                        self._existing_files.add(file_path.name)
                
                self.logger.debug(f"Loaded {len(self._existing_files)} existing files")
            else:
                self.logger.debug("Output directory does not exist yet")
                
        except Exception as e:
            self.logger.warning(f"Could not load existing files: {e}")
            # Continue with empty set - not a fatal error