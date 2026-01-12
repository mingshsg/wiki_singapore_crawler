"""Core components for the Wikipedia crawler."""

from .file_storage import FileStorage
from .url_queue import URLQueueManager
from .deduplication import DeduplicationSystem
from .page_processor import PageProcessor, PageType

__all__ = ['FileStorage', 'URLQueueManager', 'DeduplicationSystem', 'PageProcessor', 'PageType']