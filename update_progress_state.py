#!/usr/bin/env python3
"""
Script to update progress state file to mark successfully retried URLs as completed.
"""

import json
import sys
from pathlib import Path

def update_progress_state():
    """Update the progress state to mark successful retries as completed."""
    
    # URLs that were successfully retried
    successful_retries = [
        "https://en.wikipedia.org/wiki/Energy_Studies_Institute",
        "https://en.wikipedia.org/wiki/Energy_in_Singapore", 
        "https://en.wikipedia.org/wiki/Eng_Aun_Tong_Building",
        "https://en.wikipedia.org/wiki/Eng_Wah_Global",
        "https://en.wikipedia.org/wiki/Enlistment_Act_1970"
    ]
    
    progress_file = Path("wiki_data/state/progress_state.json")
    
    if not progress_file.exists():
        print(f"❌ Progress state file not found: {progress_file}")
        return False
    
    try:
        # Read the current progress state
        with open(progress_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse as JSON
        try:
            progress_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON decode error: {e}")
            print("Attempting to fix the JSON and update...")
            
            # Fix the JSON by updating the URL statuses directly in the text
            updated_content = content
            for url in successful_retries:
                # Replace "error" with "completed" for successful URLs
                old_pattern = f'"{url}": "error"'
                new_pattern = f'"{url}": "completed"'
                updated_content = updated_content.replace(old_pattern, new_pattern)
            
            # Update error count from 6 to 1
            updated_content = updated_content.replace('"error_count": 6', '"error_count": 1')
            
            # Update error summary
            updated_content = updated_content.replace('"content_processing_error": 6', '"content_processing_error": 1')
            
            # Write the updated content back
            with open(progress_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print("✅ Progress state updated successfully (text-based method)")
            return True
        
        # If JSON parsing succeeded, update normally
        url_status = progress_data.get('url_status', {})
        
        # Update successful URLs to completed status
        updates_made = 0
        for url in successful_retries:
            if url in url_status and url_status[url] == 'error':
                url_status[url] = 'completed'
                updates_made += 1
                print(f"✅ Updated {url} from error to completed")
        
        # Update error counts
        if 'status' in progress_data:
            progress_data['status']['error_count'] = 1
        
        if 'error_summary' in progress_data:
            progress_data['error_summary']['content_processing_error'] = 1
        
        # Write back the updated JSON
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Progress state updated successfully ({updates_made} URLs updated)")
        return True
        
    except Exception as e:
        print(f"❌ Error updating progress state: {e}")
        return False

def main():
    """Main function."""
    print("Progress State Update Script")
    print("=" * 40)
    print("This script will mark the 5 successfully retried URLs as completed")
    print("in the progress state file.")
    print()
    
    success = update_progress_state()
    
    if success:
        print("\n🎉 Progress state updated successfully!")
        print("The 5 successfully retried URLs are now marked as completed.")
        print("Only 'History_of_the_Jews_in_Singapore' remains as failed.")
    else:
        print("\n❌ Failed to update progress state.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())