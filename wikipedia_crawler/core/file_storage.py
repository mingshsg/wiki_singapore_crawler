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
    Supports configurable folder organization by category or other criteria.
    """
    
    def __init__(self, output_dir: Path, folder_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the file storage system.
        
        Args:
            output_dir: Base directory for storing crawled content
            folder_config: Configuration for folder organization
                - organize_by: 'category', 'date', 'type', or 'flat' (default)
                - category_folder_name: Name for category-based folder (default: extracted from URL)
                - create_subfolders: Whether to create subfolders for different content types
        """
        self.output_dir = Path(output_dir)
        self.folder_config = folder_config or {}
        self.logger = get_logger(__name__)
        self._lock = threading.Lock()  # For thread-safe operations
        self._existing_files: Set[str] = set()
        
        # Parse folder configuration
        self.organize_by = self.folder_config.get('organize_by', 'flat')
        self.category_folder_name = self.folder_config.get('category_folder_name', None)
        self.create_subfolders = self.folder_config.get('create_subfolders', False)
        
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
            
            # Determine target directory
            target_dir = self._get_target_directory('category', data)
            
            # Ensure unique filename
            with self._lock:
                unique_filename = create_unique_filename(filename, self._existing_files)
                self._existing_files.add(unique_filename)
            
            # Save file atomically
            file_path = target_dir / unique_filename
            self._save_json_atomic(file_path, data.to_dict())
            
            self.logger.info(f"Saved category: {data.title} -> {file_path}")
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
            
            # Determine target directory
            target_dir = self._get_target_directory('article', data)
            
            # Ensure unique filename
            with self._lock:
                unique_filename = create_unique_filename(filename, self._existing_files)
                self._existing_files.add(unique_filename)
            
            # Save file atomically
            file_path = target_dir / unique_filename
            self._save_json_atomic(file_path, data.to_dict())
            
            self.logger.info(f"Saved article: {data.title} -> {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save article {data.title}: {e}")
            raise IOError(f"Cannot save article data: {e}") from e
    
    def save_json(self, filename: str, data: Dict[str, Any], content_type: str = 'general') -> str:
        """
        Save arbitrary JSON data to a file.
        
        Args:
            filename: Desired filename (will be sanitized)
            data: Dictionary to save as JSON
            content_type: Type of content for folder organization
            
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
            
            # Determine target directory
            target_dir = self._get_target_directory(content_type, None)
            
            # Ensure unique filename
            with self._lock:
                unique_filename = create_unique_filename(safe_filename, self._existing_files)
                self._existing_files.add(unique_filename)
            
            # Save file atomically
            file_path = target_dir / unique_filename
            self._save_json_atomic(file_path, data)
            
            self.logger.debug(f"Saved JSON data -> {file_path}")
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
                # Recursively find all JSON files
                for file_path in self.output_dir.rglob('*.json'):
                    if file_path.is_file():
                        # Store relative path from output_dir for uniqueness checking
                        relative_path = file_path.relative_to(self.output_dir)
                        self._existing_files.add(str(relative_path))
                
                self.logger.debug(f"Loaded {len(self._existing_files)} existing files")
            else:
                self.logger.debug("Output directory does not exist yet")
                
        except Exception as e:
            self.logger.warning(f"Could not load existing files: {e}")
            # Continue with empty set - not a fatal error
    
    def _get_target_directory(self, content_type: str, data: Optional[Any] = None) -> Path:
        """
        Determine the target directory for saving files based on configuration.
        
        Args:
            content_type: Type of content ('category', 'article', 'general')
            data: Optional data object for extracting metadata
            
        Returns:
            Path to target directory
        """
        base_dir = self.output_dir
        
        if self.organize_by == 'flat':
            return base_dir
        
        elif self.organize_by == 'category':
            # Use configured category folder name or extract from data
            if self.category_folder_name:
                folder_name = self.category_folder_name
            else:
                # Try to extract category name from URL or use default
                folder_name = "Category_Singapore"  # Default fallback
            
            target_dir = base_dir / folder_name
            
            # Create subfolders by content type if configured
            if self.create_subfolders:
                if content_type == 'category':
                    target_dir = target_dir / 'categories'
                elif content_type == 'article':
                    target_dir = target_dir / 'articles'
                elif content_type == 'general':
                    target_dir = target_dir / 'general'
        
        elif self.organize_by == 'date':
            # Organize by current date
            today = datetime.now().strftime('%Y-%m-%d')
            target_dir = base_dir / today
            
            if self.create_subfolders:
                target_dir = target_dir / content_type
        
        elif self.organize_by == 'type':
            # Organize by content type only
            if content_type == 'category':
                target_dir = base_dir / 'categories'
            elif content_type == 'article':
                target_dir = base_dir / 'articles'
            else:
                target_dir = base_dir / 'general'
        
        else:
            # Default to flat structure
            target_dir = base_dir
        
        # Ensure directory exists
        self.ensure_directory_exists(target_dir)
        return target_dir
    
    def get_category_folder_name(self, start_url: str) -> str:
        """
        Extract category folder name from start URL.
        
        Args:
            start_url: Starting URL for crawling
            
        Returns:
            Folder name based on category
        """
        try:
            if 'Category:' in start_url:
                # Extract category name from URL
                category_part = start_url.split('Category:')[-1]
                # Clean up the category name for folder use
                folder_name = f"Category_{category_part.replace('%20', '_').replace(' ', '_')}"
                return folder_name
            else:
                return "General_Crawl"
        except Exception:
            return "Category_Unknown"