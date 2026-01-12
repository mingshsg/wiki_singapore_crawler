"""Configuration management for the Wikipedia crawler."""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class CrawlerConfig:
    """Configuration settings for the Wikipedia crawler."""
    
    # URLs and paths
    start_url: str = "https://en.wikipedia.org/wiki/Category:Singapore"
    output_dir: Path = Path("./wiki")
    
    # Request settings
    request_delay: float = 1.0  # Delay between requests in seconds
    request_timeout: int = 30   # Request timeout in seconds
    max_retries: int = 3        # Maximum number of retries for failed requests
    
    # Crawling behavior
    max_depth: int = 5              # Maximum depth for subcategory crawling
    
    # Language filtering
    supported_languages: list = None  # Will default to ['en', 'zh-cn', 'zh']
    
    # File settings
    max_filename_length: int = 200
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "crawler.log"
    
    def __post_init__(self):
        """Post-initialization setup."""
        if self.supported_languages is None:
            self.supported_languages = ['en', 'zh-cn', 'zh']
        
        # Ensure output_dir is a Path object
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'CrawlerConfig':
        """Load configuration from a JSON file."""
        if not config_path:
            return cls()
        
        config_file = Path(config_path)
        if not config_file.exists():
            logging.warning(f"Configuration file {config_path} not found, using defaults")
            return cls()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Convert output_dir string to Path if present
            if 'output_dir' in config_data:
                config_data['output_dir'] = Path(config_data['output_dir'])
            
            return cls(**config_data)
        
        except (json.JSONDecodeError, TypeError) as e:
            logging.error(f"Error loading configuration from {config_path}: {e}")
            logging.info("Using default configuration")
            return cls()
    
    def save(self, config_path: str) -> None:
        """Save configuration to a JSON file."""
        config_data = asdict(self)
        
        # Convert Path to string for JSON serialization
        config_data['output_dir'] = str(config_data['output_dir'])
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        if not self.start_url.startswith('https://'):
            logging.error("Start URL must use HTTPS")
            return False
        
        if self.request_delay < 0:
            logging.error("Request delay must be non-negative")
            return False
        
        if self.request_timeout <= 0:
            logging.error("Request timeout must be positive")
            return False
        
        if self.max_retries < 0:
            logging.error("Max retries must be non-negative")
            return False
        
        if self.max_depth < 1:
            logging.error("Max depth must be at least 1")
            return False
        
        return True