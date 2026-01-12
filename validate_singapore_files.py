#!/usr/bin/env python3
"""
Validation script for Singapore Wikipedia files.
Checks file integrity, content quality, and provides statistics.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime
import re


class SingaporeFileValidator:
    """Validates Singapore Wikipedia crawl files."""
    
    def __init__(self, data_directory: str = "wiki_data/Category_Singapore"):
        """
        Initialize the validator.
        
        Args:
            data_directory: Path to the Singapore data directory
        """
        self.data_dir = Path(data_directory)
        self.validation_results = {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'articles': 0,
            'categories': 0,
            'errors': [],
            'warnings': [],
            'content_stats': {},
            'language_distribution': {},
            'file_size_stats': {},
            'validation_time': None
        }
        
    def validate_all_files(self) -> Dict[str, Any]:
        """
        Validate all files in the Singapore directory.
        
        Returns:
            Validation results dictionary
        """
        start_time = datetime.now()
        print(f"🔍 Starting validation of Singapore files in: {self.data_dir}")
        print("=" * 60)
        
        if not self.data_dir.exists():
            error_msg = f"Directory does not exist: {self.data_dir}"
            self.validation_results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return self.validation_results
        
        # Find all JSON files
        json_files = list(self.data_dir.rglob('*.json'))
        self.validation_results['total_files'] = len(json_files)
        
        print(f"📁 Found {len(json_files)} JSON files to validate")
        
        # Validate each file
        for file_path in json_files:
            try:
                self._validate_single_file(file_path)
            except Exception as e:
                error_msg = f"Failed to validate {file_path.name}: {e}"
                self.validation_results['errors'].append(error_msg)
                self.validation_results['invalid_files'] += 1
        
        # Calculate statistics
        self._calculate_statistics()
        
        # Record validation time
        end_time = datetime.now()
        self.validation_results['validation_time'] = (end_time - start_time).total_seconds()
        
        # Print summary
        self._print_validation_summary()
        
        return self.validation_results
    
    def _validate_single_file(self, file_path: Path) -> None:
        """
        Validate a single JSON file.
        
        Args:
            file_path: Path to the JSON file
        """
        try:
            # Read and parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic structure validation
            if not isinstance(data, dict):
                raise ValueError("File does not contain a JSON object")
            
            # Check for required metadata
            if '_metadata' not in data:
                self.validation_results['warnings'].append(f"Missing metadata in {file_path.name}")
            
            # Determine file type and validate accordingly
            file_type = data.get('type', 'unknown')
            
            if file_type == 'article':
                self._validate_article_file(file_path, data)
                self.validation_results['articles'] += 1
            elif file_type == 'category':
                self._validate_category_file(file_path, data)
                self.validation_results['categories'] += 1
            else:
                # Try to infer type from filename
                if file_path.name.startswith('category_'):
                    self._validate_category_file(file_path, data)
                    self.validation_results['categories'] += 1
                else:
                    self._validate_article_file(file_path, data)
                    self.validation_results['articles'] += 1
            
            self.validation_results['valid_files'] += 1
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {file_path.name}: {e}"
            self.validation_results['errors'].append(error_msg)
            self.validation_results['invalid_files'] += 1
        except Exception as e:
            error_msg = f"Validation error in {file_path.name}: {e}"
            self.validation_results['errors'].append(error_msg)
            self.validation_results['invalid_files'] += 1
    
    def _validate_article_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Validate an article file.
        
        Args:
            file_path: Path to the file
            data: Parsed JSON data
        """
        required_fields = ['url', 'title', 'content', 'language']
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate URL
        url = data['url']
        if not url.startswith('https://en.wikipedia.org/wiki/'):
            self.validation_results['warnings'].append(f"Unusual URL in {file_path.name}: {url}")
        
        # Validate content
        content = data['content']
        if not isinstance(content, str):
            raise ValueError("Content must be a string")
        
        if len(content.strip()) < 100:
            self.validation_results['warnings'].append(f"Very short content in {file_path.name}: {len(content)} chars")
        
        # Check for Singapore relevance
        if not self._is_singapore_related(data['title'], content):
            self.validation_results['warnings'].append(f"Possibly non-Singapore content: {file_path.name}")
        
        # Track language
        language = data.get('language', 'unknown')
        self.validation_results['language_distribution'][language] = \
            self.validation_results['language_distribution'].get(language, 0) + 1
        
        # Track content length
        content_length = len(content)
        if 'content_lengths' not in self.validation_results['content_stats']:
            self.validation_results['content_stats']['content_lengths'] = []
        self.validation_results['content_stats']['content_lengths'].append(content_length)
    
    def _validate_category_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Validate a category file.
        
        Args:
            file_path: Path to the file
            data: Parsed JSON data
        """
        required_fields = ['url', 'title']
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate URL
        url = data['url']
        if 'Category:' not in url:
            self.validation_results['warnings'].append(f"Category URL doesn't contain 'Category:': {file_path.name}")
        
        # Check for subcategories and articles lists
        if 'subcategories' in data and not isinstance(data['subcategories'], list):
            raise ValueError("Subcategories must be a list")
        
        if 'articles' in data and not isinstance(data['articles'], list):
            raise ValueError("Articles must be a list")
    
    def _is_singapore_related(self, title: str, content: str) -> bool:
        """
        Check if content is Singapore-related.
        
        Args:
            title: Article title
            content: Article content
            
        Returns:
            True if Singapore-related, False otherwise
        """
        singapore_keywords = [
            'singapore', 'singaporean', 'spore', 'sg',
            'marina bay', 'changi', 'orchard road', 'sentosa',
            'merlion', 'raffles', 'lee kuan yew', 'pap',
            'hdb', 'mrt', 'cpf', 'nus', 'ntu', 'smu'
        ]
        
        text_to_check = (title + ' ' + content).lower()
        
        # Check for Singapore keywords
        for keyword in singapore_keywords:
            if keyword in text_to_check:
                return True
        
        return False
    
    def _calculate_statistics(self) -> None:
        """Calculate additional statistics from validation results."""
        # File size statistics
        if self.data_dir.exists():
            file_sizes = []
            for file_path in self.data_dir.rglob('*.json'):
                try:
                    size = file_path.stat().st_size
                    file_sizes.append(size)
                except Exception:
                    continue
            
            if file_sizes:
                self.validation_results['file_size_stats'] = {
                    'total_size_bytes': sum(file_sizes),
                    'average_size_bytes': sum(file_sizes) / len(file_sizes),
                    'min_size_bytes': min(file_sizes),
                    'max_size_bytes': max(file_sizes),
                    'total_size_mb': sum(file_sizes) / (1024 * 1024)
                }
        
        # Content statistics
        if 'content_lengths' in self.validation_results['content_stats']:
            lengths = self.validation_results['content_stats']['content_lengths']
            if lengths:
                self.validation_results['content_stats']['average_content_length'] = sum(lengths) / len(lengths)
                self.validation_results['content_stats']['min_content_length'] = min(lengths)
                self.validation_results['content_stats']['max_content_length'] = max(lengths)
                self.validation_results['content_stats']['total_content_chars'] = sum(lengths)
    
    def _print_validation_summary(self) -> None:
        """Print a summary of validation results."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        # File counts
        print(f"📁 Total files: {self.validation_results['total_files']}")
        print(f"✅ Valid files: {self.validation_results['valid_files']}")
        print(f"❌ Invalid files: {self.validation_results['invalid_files']}")
        print(f"📄 Articles: {self.validation_results['articles']}")
        print(f"📂 Categories: {self.validation_results['categories']}")
        
        # Success rate
        if self.validation_results['total_files'] > 0:
            success_rate = (self.validation_results['valid_files'] / self.validation_results['total_files']) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
        
        # Language distribution
        if self.validation_results['language_distribution']:
            print(f"\n🌐 Language distribution:")
            for lang, count in self.validation_results['language_distribution'].items():
                print(f"   {lang}: {count} files")
        
        # File size stats
        if self.validation_results['file_size_stats']:
            stats = self.validation_results['file_size_stats']
            print(f"\n💾 File size statistics:")
            print(f"   Total size: {stats['total_size_mb']:.2f} MB")
            print(f"   Average file size: {stats['average_size_bytes']:.0f} bytes")
            print(f"   Size range: {stats['min_size_bytes']} - {stats['max_size_bytes']} bytes")
        
        # Content stats
        if 'average_content_length' in self.validation_results['content_stats']:
            stats = self.validation_results['content_stats']
            print(f"\n📝 Content statistics:")
            print(f"   Average content length: {stats['average_content_length']:.0f} characters")
            print(f"   Content range: {stats['min_content_length']} - {stats['max_content_length']} characters")
            print(f"   Total content: {stats['total_content_chars']:,} characters")
        
        # Errors and warnings
        if self.validation_results['errors']:
            print(f"\n❌ Errors ({len(self.validation_results['errors'])}):")
            for error in self.validation_results['errors'][:5]:  # Show first 5
                print(f"   • {error}")
            if len(self.validation_results['errors']) > 5:
                print(f"   ... and {len(self.validation_results['errors']) - 5} more")
        
        if self.validation_results['warnings']:
            print(f"\n⚠️  Warnings ({len(self.validation_results['warnings'])}):")
            for warning in self.validation_results['warnings'][:5]:  # Show first 5
                print(f"   • {warning}")
            if len(self.validation_results['warnings']) > 5:
                print(f"   ... and {len(self.validation_results['warnings']) - 5} more")
        
        print(f"\n⏱️  Validation completed in {self.validation_results['validation_time']:.2f} seconds")
    
    def check_specific_files(self, file_patterns: List[str]) -> Dict[str, Any]:
        """
        Check specific files by pattern.
        
        Args:
            file_patterns: List of file patterns to check
            
        Returns:
            Results for specific files
        """
        results = {}
        
        for pattern in file_patterns:
            matching_files = list(self.data_dir.glob(pattern))
            results[pattern] = {
                'found': len(matching_files),
                'files': [f.name for f in matching_files]
            }
        
        return results
    
    def validate_singapore_specific_content(self) -> Dict[str, Any]:
        """
        Validate Singapore-specific content quality.
        
        Returns:
            Singapore-specific validation results
        """
        singapore_results = {
            'singapore_articles': 0,
            'non_singapore_articles': 0,
            'key_singapore_topics': [],
            'missing_key_topics': []
        }
        
        # Key Singapore topics that should be present
        expected_topics = [
            'Singapore',
            'History of Singapore',
            'Geography of Singapore',
            'Economy of Singapore',
            'Culture of Singapore',
            'Government of Singapore',
            'Marina Bay Sands',
            'Changi Airport',
            'Merlion',
            'Lee Kuan Yew'
        ]
        
        found_topics = set()
        
        # Check all article files
        for file_path in self.data_dir.rglob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get('type') == 'article' or not file_path.name.startswith('category_'):
                    title = data.get('title', '')
                    content = data.get('content', '')
                    
                    if self._is_singapore_related(title, content):
                        singapore_results['singapore_articles'] += 1
                        
                        # Check for key topics
                        for topic in expected_topics:
                            if topic.lower() in title.lower():
                                found_topics.add(topic)
                    else:
                        singapore_results['non_singapore_articles'] += 1
            
            except Exception:
                continue
        
        singapore_results['key_singapore_topics'] = list(found_topics)
        singapore_results['missing_key_topics'] = [t for t in expected_topics if t not in found_topics]
        
        return singapore_results


def main():
    """Main validation function."""
    # Check command line arguments
    data_dir = "wiki_data/Category_Singapore"
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    
    # Create validator and run validation
    validator = SingaporeFileValidator(data_dir)
    results = validator.validate_all_files()
    
    # Check Singapore-specific content
    print("\n" + "=" * 60)
    print("🇸🇬 SINGAPORE-SPECIFIC VALIDATION")
    print("=" * 60)
    
    singapore_results = validator.validate_singapore_specific_content()
    print(f"🏙️  Singapore-related articles: {singapore_results['singapore_articles']}")
    print(f"🌍 Non-Singapore articles: {singapore_results['non_singapore_articles']}")
    
    if singapore_results['key_singapore_topics']:
        print(f"\n✅ Found key Singapore topics:")
        for topic in singapore_results['key_singapore_topics']:
            print(f"   • {topic}")
    
    if singapore_results['missing_key_topics']:
        print(f"\n❌ Missing key Singapore topics:")
        for topic in singapore_results['missing_key_topics']:
            print(f"   • {topic}")
    
    # Check for specific important files
    important_patterns = [
        "Singapore.json",
        "*History of Singapore*.json",
        "*Marina Bay*.json",
        "*Changi*.json",
        "*Merlion*.json"
    ]
    
    print(f"\n🔍 Checking for important Singapore files:")
    specific_results = validator.check_specific_files(important_patterns)
    for pattern, result in specific_results.items():
        if result['found'] > 0:
            print(f"   ✅ {pattern}: {result['found']} files found")
        else:
            print(f"   ❌ {pattern}: No files found")
    
    # Return appropriate exit code
    if results['invalid_files'] > 0:
        print(f"\n⚠️  Validation completed with {results['invalid_files']} invalid files")
        sys.exit(1)
    else:
        print(f"\n✅ All {results['valid_files']} files validated successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()