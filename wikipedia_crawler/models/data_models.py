"""Core data models for the Wikipedia crawler."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import json


class URLType(Enum):
    """Type of Wikipedia URL."""
    CATEGORY = "category"
    ARTICLE = "article"


class ProcessStatus(Enum):
    """Status of page processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FILTERED = "filtered"
    ERROR = "error"


@dataclass
class URLItem:
    """Represents a URL to be processed with metadata."""
    url: str
    url_type: URLType
    priority: int = 0
    depth: int = 0  # Depth level for subcategory crawling
    discovered_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate URL item after initialization."""
        if not self.url.startswith('https://'):
            raise ValueError("URL must use HTTPS protocol")
        if not 'wikipedia.org' in self.url:
            raise ValueError("URL must be from Wikipedia")


@dataclass
class CategoryData:
    """Data structure for Wikipedia category pages."""
    url: str
    title: str
    subcategories: List[str] = field(default_factory=list)
    articles: List[str] = field(default_factory=list)
    processed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'title': self.title,
            'subcategories': self.subcategories,
            'articles': self.articles,
            'processed_at': self.processed_at.isoformat(),
            'type': 'category'
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryData':
        """Create instance from dictionary."""
        # Parse datetime if it's a string
        processed_at = data.get('processed_at')
        if isinstance(processed_at, str):
            processed_at = datetime.fromisoformat(processed_at)
        elif processed_at is None:
            processed_at = datetime.now()
        
        return cls(
            url=data['url'],
            title=data['title'],
            subcategories=data.get('subcategories', []),
            articles=data.get('articles', []),
            processed_at=processed_at
        )


@dataclass
class ArticleData:
    """Data structure for Wikipedia article pages."""
    url: str
    title: str
    content: str  # Markdown formatted content
    language: str
    processed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'title': self.title,
            'content': self.content,
            'language': self.language,
            'processed_at': self.processed_at.isoformat(),
            'type': 'article'
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleData':
        """Create instance from dictionary."""
        # Parse datetime if it's a string
        processed_at = data.get('processed_at')
        if isinstance(processed_at, str):
            processed_at = datetime.fromisoformat(processed_at)
        elif processed_at is None:
            processed_at = datetime.now()
        
        return cls(
            url=data['url'],
            title=data['title'],
            content=data['content'],
            language=data['language'],
            processed_at=processed_at
        )


@dataclass
class ProcessResult:
    """Result of processing a Wikipedia page."""
    success: bool
    url: str
    error_message: Optional[str] = None
    content: Optional[str] = None
    page_type: Optional[str] = None  # "category", "article", "unknown"
    status_code: Optional[int] = None
    content_length: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    discovered_urls: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate process result after initialization."""
        if self.page_type is not None:
            valid_types = {"category", "article", "unknown"}
            if self.page_type not in valid_types:
                raise ValueError(f"page_type must be one of {valid_types}")
        
        if not self.success and not self.error_message:
            raise ValueError("error_message is required when success is False")


@dataclass
class CrawlStatus:
    """Current status of the crawling process."""
    is_running: bool
    total_processed: int = 0
    pending_urls: int = 0
    categories_processed: int = 0
    articles_processed: int = 0
    filtered_count: int = 0
    error_count: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'is_running': self.is_running,
            'total_processed': self.total_processed,
            'pending_urls': self.pending_urls,
            'categories_processed': self.categories_processed,
            'articles_processed': self.articles_processed,
            'filtered_count': self.filtered_count,
            'error_count': self.error_count,
            'start_time': self.start_time.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()
    
    def get_success_rate(self) -> float:
        """Calculate the success rate of processing."""
        if self.total_processed == 0:
            return 0.0
        successful = self.categories_processed + self.articles_processed
        return successful / self.total_processed
    
    def get_processing_summary(self) -> str:
        """Get a human-readable summary of processing status."""
        if not self.is_running and self.total_processed == 0:
            return "Not started"
        
        summary_parts = [
            f"Processed: {self.total_processed}",
            f"Categories: {self.categories_processed}",
            f"Articles: {self.articles_processed}",
            f"Filtered: {self.filtered_count}",
            f"Errors: {self.error_count}",
            f"Pending: {self.pending_urls}"
        ]
        
        if self.total_processed > 0:
            success_rate = self.get_success_rate() * 100
            summary_parts.append(f"Success: {success_rate:.1f}%")
        
        return " | ".join(summary_parts)


@dataclass
class ProgressReport:
    """Detailed progress report for the crawling process."""
    status: CrawlStatus
    recent_urls: List[str] = field(default_factory=list)
    language_stats: Dict[str, int] = field(default_factory=dict)
    error_summary: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'status': self.status.to_dict(),
            'recent_urls': self.recent_urls,
            'language_stats': self.language_stats,
            'error_summary': self.error_summary
        }