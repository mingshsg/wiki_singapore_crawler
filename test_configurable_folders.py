#!/usr/bin/env python3
"""
Test script for configurable folder organization.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.models.data_models import ArticleData, CategoryData
from datetime import datetime


def test_folder_configurations():
    """Test different folder configuration options."""
    
    print("🧪 Testing Configurable Folder Organization")
    print("=" * 50)
    
    # Test data
    test_article = ArticleData(
        url="https://en.wikipedia.org/wiki/Test_Article",
        title="Test Article",
        content="This is a test article about Singapore.",
        language="en"
    )
    
    test_category = CategoryData(
        url="https://en.wikipedia.org/wiki/Category:Test",
        title="Category:Test",
        subcategories=["Subcategory1"],
        articles=["Article1", "Article2"]
    )
    
    # Test configurations
    configurations = [
        {
            'name': 'Flat Structure',
            'config': {'organize_by': 'flat'},
            'output_dir': 'test_output/flat'
        },
        {
            'name': 'Category Organization',
            'config': {
                'organize_by': 'category',
                'category_folder_name': 'Category_Singapore',
                'create_subfolders': False
            },
            'output_dir': 'test_output/category'
        },
        {
            'name': 'Category with Subfolders',
            'config': {
                'organize_by': 'category',
                'category_folder_name': 'Category_Singapore',
                'create_subfolders': True
            },
            'output_dir': 'test_output/category_subfolders'
        },
        {
            'name': 'Type Organization',
            'config': {'organize_by': 'type'},
            'output_dir': 'test_output/type'
        },
        {
            'name': 'Date Organization',
            'config': {
                'organize_by': 'date',
                'create_subfolders': True
            },
            'output_dir': 'test_output/date'
        }
    ]
    
    # Test each configuration
    for config_test in configurations:
        print(f"\n📁 Testing: {config_test['name']}")
        print(f"   Config: {config_test['config']}")
        
        try:
            # Create file storage with configuration
            storage = FileStorage(
                output_dir=config_test['output_dir'],
                folder_config=config_test['config']
            )
            
            # Save test files
            article_path = storage.save_article(test_article)
            category_path = storage.save_category(test_category)
            
            print(f"   ✅ Article saved to: {article_path}")
            print(f"   ✅ Category saved to: {category_path}")
            
            # Verify files exist
            if Path(article_path).exists() and Path(category_path).exists():
                print(f"   ✅ Files verified successfully")
            else:
                print(f"   ❌ File verification failed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 Test Summary:")
    print(f"   All folder configurations tested")
    print(f"   Check test_output/ directory for results")


def test_singapore_folder_structure():
    """Test the specific Singapore folder structure."""
    
    print(f"\n🇸🇬 Testing Singapore Folder Structure")
    print("=" * 50)
    
    # Configuration matching the updated config.json
    singapore_config = {
        'organize_by': 'category',
        'category_folder_name': 'Category_Singapore',
        'create_subfolders': False
    }
    
    storage = FileStorage(
        output_dir='test_output/singapore_test',
        folder_config=singapore_config
    )
    
    # Test with Singapore-specific data
    singapore_article = ArticleData(
        url="https://en.wikipedia.org/wiki/Marina_Bay_Sands",
        title="Marina Bay Sands",
        content="Marina Bay Sands is an integrated resort in Singapore...",
        language="en"
    )
    
    singapore_category = CategoryData(
        url="https://en.wikipedia.org/wiki/Category:Singapore",
        title="Category:Singapore",
        subcategories=["Category:Singapore culture", "Category:Singapore history"],
        articles=["Singapore", "History of Singapore", "Marina Bay Sands"]
    )
    
    try:
        article_path = storage.save_article(singapore_article)
        category_path = storage.save_category(singapore_category)
        
        print(f"✅ Singapore article saved to: {article_path}")
        print(f"✅ Singapore category saved to: {category_path}")
        
        # Verify the folder structure
        expected_folder = Path('test_output/singapore_test/Category_Singapore')
        if expected_folder.exists():
            print(f"✅ Category_Singapore folder created successfully")
            
            # List contents
            contents = list(expected_folder.iterdir())
            print(f"📁 Folder contents ({len(contents)} files):")
            for item in contents[:5]:  # Show first 5
                print(f"   • {item.name}")
            if len(contents) > 5:
                print(f"   ... and {len(contents) - 5} more files")
        else:
            print(f"❌ Expected folder not found: {expected_folder}")
            
    except Exception as e:
        print(f"❌ Error testing Singapore structure: {e}")


def show_current_singapore_structure():
    """Show the current Singapore folder structure."""
    
    print(f"\n📂 Current Singapore Folder Structure")
    print("=" * 50)
    
    singapore_dir = Path("wiki_data/Category_Singapore")
    
    if singapore_dir.exists():
        print(f"✅ Found Singapore directory: {singapore_dir}")
        
        # Count files by type
        json_files = list(singapore_dir.rglob('*.json'))
        article_files = [f for f in json_files if not f.name.startswith('category_')]
        category_files = [f for f in json_files if f.name.startswith('category_')]
        
        print(f"📊 Directory statistics:")
        print(f"   Total JSON files: {len(json_files)}")
        print(f"   Article files: {len(article_files)}")
        print(f"   Category files: {len(category_files)}")
        
        # Show subdirectories
        subdirs = [d for d in singapore_dir.iterdir() if d.is_dir()]
        if subdirs:
            print(f"   Subdirectories: {len(subdirs)}")
            for subdir in subdirs:
                subdir_files = len(list(subdir.rglob('*.json')))
                print(f"     • {subdir.name}: {subdir_files} files")
        else:
            print(f"   No subdirectories (flat structure)")
        
        # Show sample files
        print(f"\n📄 Sample files:")
        for file_path in json_files[:5]:
            print(f"   • {file_path.name}")
        if len(json_files) > 5:
            print(f"   ... and {len(json_files) - 5} more")
            
    else:
        print(f"❌ Singapore directory not found: {singapore_dir}")


if __name__ == "__main__":
    # Show current structure
    show_current_singapore_structure()
    
    # Test folder configurations
    test_folder_configurations()
    
    # Test Singapore-specific structure
    test_singapore_folder_structure()
    
    print(f"\n✅ All tests completed!")
    print(f"📁 Check test_output/ directory for generated folder structures")