"""Filename sanitization utilities for the Wikipedia crawler."""

import re
import unicodedata
from pathlib import Path
from typing import Set


# Characters that are invalid in filenames on various operating systems
INVALID_CHARS = set('<>:"/\\|?*')

# Reserved names on Windows
RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

# Control characters (ASCII 0-31)
CONTROL_CHARS = set(chr(i) for i in range(32))


def sanitize_filename(filename: str, max_length: int = 200, replacement_char: str = '_') -> str:
    """
    Sanitize a filename to be safe for all major filesystems.
    
    Args:
        filename: The original filename to sanitize
        max_length: Maximum length for the filename (default: 200)
        replacement_char: Character to use for replacing invalid characters
    
    Returns:
        A sanitized filename that is safe for filesystem use
    
    Raises:
        ValueError: If the filename cannot be sanitized (e.g., empty after sanitization)
    """
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")
    
    # Start with the original filename
    sanitized = filename.strip()
    
    # Normalize Unicode characters (decompose and recompose)
    sanitized = unicodedata.normalize('NFKC', sanitized)
    
    # Remove or replace invalid characters
    sanitized = _remove_invalid_characters(sanitized, replacement_char)
    
    # Handle reserved names
    sanitized = _handle_reserved_names(sanitized, replacement_char)
    
    # Remove leading/trailing dots and spaces (problematic on Windows)
    sanitized = sanitized.strip('. ')
    
    # Ensure the filename is not empty after sanitization
    if not sanitized:
        raise ValueError("Filename becomes empty after sanitization")
    
    # Truncate if too long, but preserve file extension if present
    sanitized = _truncate_filename(sanitized, max_length)
    
    # Final validation
    if not _is_valid_filename(sanitized):
        raise ValueError(f"Unable to create valid filename from: {filename}")
    
    return sanitized


def _remove_invalid_characters(filename: str, replacement_char: str) -> str:
    """Remove or replace invalid characters from filename."""
    result = []
    
    for char in filename:
        if char in INVALID_CHARS or char in CONTROL_CHARS:
            # Replace invalid characters
            result.append(replacement_char)
        elif ord(char) > 127:
            # Handle non-ASCII characters - keep them but ensure they're safe
            # Most modern filesystems handle Unicode well
            result.append(char)
        else:
            result.append(char)
    
    # Collapse multiple replacement characters into single ones
    sanitized = ''.join(result)
    while replacement_char + replacement_char in sanitized:
        sanitized = sanitized.replace(replacement_char + replacement_char, replacement_char)
    
    return sanitized


def _handle_reserved_names(filename: str, replacement_char: str) -> str:
    """Handle Windows reserved names."""
    # Split filename and extension
    name_parts = filename.rsplit('.', 1)
    name = name_parts[0]
    extension = name_parts[1] if len(name_parts) > 1 else ''
    
    # Check if the name (without extension) is reserved
    if name.upper() in RESERVED_NAMES:
        name = name + replacement_char + 'file'
    
    # Reconstruct filename
    if extension:
        return f"{name}.{extension}"
    else:
        return name


def _truncate_filename(filename: str, max_length: int) -> str:
    """Truncate filename while preserving extension if possible."""
    if len(filename) <= max_length:
        return filename
    
    # Try to preserve file extension
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        name, extension = name_parts
        # Reserve space for extension and dot
        available_length = max_length - len(extension) - 1
        if available_length > 0:
            return f"{name[:available_length]}.{extension}"
    
    # If no extension or can't preserve it, just truncate
    return filename[:max_length]


def _is_valid_filename(filename: str) -> bool:
    """Validate that a filename is safe for filesystem use."""
    if not filename or not filename.strip():
        return False
    
    # Check for invalid characters
    if any(char in INVALID_CHARS or char in CONTROL_CHARS for char in filename):
        return False
    
    # Check for reserved names (Windows)
    name = filename.split('.')[0].upper()
    if name in RESERVED_NAMES:
        return False
    
    # Check for problematic leading/trailing characters
    if filename.startswith('.') or filename.endswith('.') or filename.endswith(' '):
        return False
    
    return True


def sanitize_wikipedia_title(title: str, page_type: str = 'article') -> str:
    """
    Sanitize a Wikipedia page title for use as a filename.
    
    Args:
        title: Wikipedia page title
        page_type: Type of page ('article' or 'category')
    
    Returns:
        Sanitized filename with appropriate prefix
    """
    if not title:
        raise ValueError("Title cannot be empty")
    
    # Remove Wikipedia namespace prefixes if present
    if title.startswith('Category:'):
        clean_title = title[9:]  # Remove 'Category:' prefix
        page_type = 'category'
    else:
        clean_title = title
    
    # Replace underscores with spaces for better readability
    clean_title = clean_title.replace('_', ' ')
    
    # Sanitize the title
    sanitized_title = sanitize_filename(clean_title)
    
    # Add appropriate prefix based on page type
    if page_type == 'category':
        return f"category_{sanitized_title}.json"
    else:
        return f"{sanitized_title}.json"


def create_unique_filename(base_filename: str, existing_files: Set[str]) -> str:
    """
    Create a unique filename by appending a number if the base filename already exists.
    
    Args:
        base_filename: The desired filename
        existing_files: Set of existing filenames to check against
    
    Returns:
        A unique filename
    """
    if base_filename not in existing_files:
        return base_filename
    
    # Split name and extension
    name_parts = base_filename.rsplit('.', 1)
    if len(name_parts) == 2:
        name, extension = name_parts
        template = f"{name}_{{}}.{extension}"
    else:
        template = f"{base_filename}_{{}}"
    
    # Find a unique number
    counter = 1
    while True:
        candidate = template.format(counter)
        if candidate not in existing_files:
            return candidate
        counter += 1
        
        # Safety check to prevent infinite loops
        if counter > 10000:
            raise ValueError("Unable to create unique filename after 10000 attempts")