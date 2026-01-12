"""Language detection and filtering for Wikipedia content."""

import re
import logging
from typing import Dict, Set, Optional, Tuple
from collections import defaultdict
from urllib.parse import urlparse

try:
    from langdetect import detect, detect_langs, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

from wikipedia_crawler.utils.logging_config import get_logger


class LanguageFilter:
    """
    Detects and filters content based on language.
    
    Supports English and Chinese language detection using multiple methods
    including URL analysis, content analysis, and the langdetect library.
    """
    
    def __init__(self, supported_languages: Optional[Set[str]] = None):
        """
        Initialize the language filter.
        
        Args:
            supported_languages: Set of supported language codes (default: en, zh-cn, zh)
        """
        self.logger = get_logger(__name__)
        
        # Default supported languages
        if supported_languages is None:
            supported_languages = {'en', 'zh-cn', 'zh'}
        
        self.supported_languages = supported_languages
        self.language_stats = defaultdict(int)
        
        # Initialize langdetect if available
        if LANGDETECT_AVAILABLE:
            # Set seed for consistent results
            DetectorFactory.seed = 0
            self.logger.debug("Language detection library initialized")
        else:
            self.logger.warning("langdetect library not available, using fallback methods")
        
        # Language detection patterns
        self.language_patterns = {
            'zh': re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2b820-\u2ceaf\uf900-\ufaff\u3300-\u33ff\ufe30-\ufe4f\uf900-\ufaff\u2f800-\u2fa1f]+'),
            'en': re.compile(r'[a-zA-Z]+')
        }
        
        # Wikipedia domain to language mapping
        self.domain_language_map = {
            'en.wikipedia.org': 'en',
            'zh.wikipedia.org': 'zh',
            'zh-cn.wikipedia.org': 'zh-cn',
            'zh-tw.wikipedia.org': 'zh-tw'
        }
    
    def detect_language(self, content: str, url: str = "") -> str:
        """
        Detect the language of the given content.
        
        Args:
            content: Text content to analyze
            url: Optional URL for additional context
            
        Returns:
            Detected language code (e.g., 'en', 'zh', 'unknown')
        """
        if not content or not content.strip():
            return 'unknown'
        
        try:
            # Method 1: URL-based detection (most reliable for Wikipedia)
            url_language = self._detect_language_from_url(url)
            if url_language and url_language != 'unknown':
                self.logger.debug(f"Language detected from URL: {url_language}")
                return url_language
            
            # Method 2: Content-based detection using langdetect
            if LANGDETECT_AVAILABLE:
                langdetect_result = self._detect_language_with_langdetect(content)
                if langdetect_result and langdetect_result != 'unknown':
                    self.logger.debug(f"Language detected with langdetect: {langdetect_result}")
                    return langdetect_result
            
            # Method 3: Pattern-based detection (fallback)
            pattern_result = self._detect_language_with_patterns(content)
            self.logger.debug(f"Language detected with patterns: {pattern_result}")
            return pattern_result
            
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            return 'unknown'
    
    def is_supported_language(self, language: str) -> bool:
        """
        Check if a language is supported.
        
        Args:
            language: Language code to check
            
        Returns:
            True if language is supported, False otherwise
        """
        # Normalize language code
        normalized = self._normalize_language_code(language)
        return normalized in self.supported_languages
    
    def filter_content(self, content: str, url: str = "") -> Tuple[bool, str]:
        """
        Filter content based on language support.
        
        Args:
            content: Content to filter
            url: Optional URL for context
            
        Returns:
            Tuple of (should_process, detected_language)
        """
        detected_language = self.detect_language(content, url)
        
        # Update statistics
        self.language_stats[detected_language] += 1
        
        # Check if language is supported
        should_process = self.is_supported_language(detected_language)
        
        # Special case: if language is unknown but URL is from a supported Wikipedia domain,
        # we should still process it (likely short content or detection failure)
        if not should_process and detected_language == 'unknown' and url:
            url_language = self._detect_language_from_url(url)
            if self.is_supported_language(url_language):
                should_process = True
                # Update detected language to the URL-based detection for consistency
                detected_language = url_language
                self.logger.debug(f"Content accepted based on supported Wikipedia domain: {url_language}")
        
        if should_process:
            self.logger.debug(f"Content accepted: language {detected_language}")
        else:
            self.logger.debug(f"Content filtered: unsupported language {detected_language}")
        
        return should_process, detected_language
    
    def get_language_stats(self) -> Dict[str, int]:
        """
        Get statistics of detected languages.
        
        Returns:
            Dictionary mapping language codes to counts
        """
        return dict(self.language_stats)
    
    def reset_stats(self) -> None:
        """Reset language statistics."""
        self.language_stats.clear()
    
    def _detect_language_from_url(self, url: str) -> str:
        """Detect language from Wikipedia URL domain."""
        if not url:
            return 'unknown'
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            return self.domain_language_map.get(domain, 'unknown')
            
        except Exception as e:
            self.logger.debug(f"URL parsing failed: {e}")
            return 'unknown'
    
    def _detect_language_with_langdetect(self, content: str) -> str:
        """Detect language using the langdetect library."""
        if not LANGDETECT_AVAILABLE:
            return 'unknown'
        
        try:
            # Clean content for better detection
            cleaned_content = self._clean_content_for_detection(content)
            
            if len(cleaned_content) < 10:
                return 'unknown'
            
            # Detect language
            detected = detect(cleaned_content)
            
            # Map langdetect codes to our codes
            language_mapping = {
                'en': 'en',
                'zh-cn': 'zh-cn',
                'zh': 'zh',
                'zh-tw': 'zh'
            }
            
            return language_mapping.get(detected, detected)
            
        except LangDetectException as e:
            self.logger.debug(f"Language detection failed: {e}")
            return 'unknown'
        except Exception as e:
            self.logger.debug(f"Unexpected error in language detection: {e}")
            return 'unknown'
    
    def _detect_language_with_patterns(self, content: str) -> str:
        """Detect language using character patterns (fallback method)."""
        # Clean content
        cleaned_content = self._clean_content_for_detection(content)
        
        if len(cleaned_content) < 10:
            return 'unknown'
        
        # Count characters for each language
        language_scores = {}
        
        for lang_code, pattern in self.language_patterns.items():
            matches = pattern.findall(cleaned_content)
            total_chars = sum(len(match) for match in matches)
            language_scores[lang_code] = total_chars
        
        # Determine dominant language
        total_chars = sum(language_scores.values())
        if total_chars == 0:
            return 'unknown'
        
        # Calculate percentages
        percentages = {lang: count / total_chars for lang, count in language_scores.items()}
        
        # Chinese characters are a strong indicator
        if percentages.get('zh', 0) > 0.1:  # 10% Chinese characters
            return 'zh'
        
        # English characters (but could be many languages)
        if percentages.get('en', 0) > 0.8:  # 80% Latin characters
            return 'en'
        
        return 'unknown'
    
    def _clean_content_for_detection(self, content: str) -> str:
        """Clean content for better language detection."""
        # Remove URLs
        content = re.sub(r'https?://[^\s]+', '', content)
        
        # Remove email addresses
        content = re.sub(r'\S+@\S+', '', content)
        
        # Remove numbers and special characters for better detection
        content = re.sub(r'[0-9\[\](){}.,;:!?"\'-]+', ' ', content)
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    def _normalize_language_code(self, language: str) -> str:
        """Normalize language code for consistent comparison."""
        if not language:
            return 'unknown'
        
        language = language.lower().strip()
        
        # Handle common variations
        normalization_map = {
            'chinese': 'zh',
            'mandarin': 'zh',
            'english': 'en',
            'zh-hans': 'zh-cn',
            'zh-hant': 'zh-tw',
            'zh-sg': 'zh-cn',
            'zh-my': 'zh-cn'
        }
        
        return normalization_map.get(language, language)
    
    def get_detection_confidence(self, content: str, url: str = "") -> Dict[str, float]:
        """
        Get confidence scores for language detection methods.
        
        Args:
            content: Content to analyze
            url: Optional URL for context
            
        Returns:
            Dictionary with confidence scores for each method
        """
        confidence_scores = {
            'url_based': 0.0,
            'langdetect': 0.0,
            'pattern_based': 0.0
        }
        
        # URL-based confidence
        url_lang = self._detect_language_from_url(url)
        if url_lang != 'unknown':
            confidence_scores['url_based'] = 0.9  # High confidence for Wikipedia URLs
        
        # Langdetect confidence
        if LANGDETECT_AVAILABLE and content:
            try:
                cleaned_content = self._clean_content_for_detection(content)
                if len(cleaned_content) >= 10:
                    lang_probs = detect_langs(cleaned_content)
                    if lang_probs:
                        confidence_scores['langdetect'] = lang_probs[0].prob
            except:
                pass
        
        # Pattern-based confidence
        if content:
            cleaned_content = self._clean_content_for_detection(content)
            if len(cleaned_content) >= 10:
                # Simple heuristic based on character patterns
                zh_chars = len(self.language_patterns['zh'].findall(cleaned_content))
                en_chars = len(self.language_patterns['en'].findall(cleaned_content))
                total_chars = zh_chars + en_chars
                
                if total_chars > 0:
                    if zh_chars / total_chars > 0.1:
                        confidence_scores['pattern_based'] = min(0.8, zh_chars / total_chars)
                    elif en_chars / total_chars > 0.8:
                        confidence_scores['pattern_based'] = min(0.7, en_chars / total_chars)
        
        return confidence_scores