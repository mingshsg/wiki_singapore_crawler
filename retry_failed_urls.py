#!/usr/bin/env python3
"""
Script to retry failed URLs from the Singapore Wikipedia crawling operation.

This script identifies failed URLs from the progress state and retries them using
the existing crawler infrastructure with smart error handling and circuit breaker protection.
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from wikipedia_crawler.core.page_processor import PageProcessor
from wikipedia_crawler.core.file_storage import FileStorage
from wikipedia_crawler.processors.article_handler import ArticlePageHandler
from wikipedia_crawler.processors.content_processor import ContentProcessor
from wikipedia_crawler.processors.language_filter import LanguageFilter
from wikipedia_crawler.utils.logging_config import get_logger


class FailedURLRetryManager:
    """
    Manager for retrying failed URLs from the crawling operation.
    
    Features:
    - Extracts failed URLs from progress state
    - Uses existing crawler components for consistency
    - Provides detailed retry reporting
    - Maintains statistics and logging
    """
    
    def __init__(self, 
                 output_dir: str = "wiki_data",
                 delay_between_requests: float = 1.0,
                 max_retries: int = 3):
        """
        Initialize the retry manager.
        
        Args:
            output_dir: Directory containing crawled data and state files
            delay_between_requests: Delay between HTTP requests (seconds)
            max_retries: Maximum retry attempts for failed requests
        """
        self.output_dir = Path(output_dir)
        self.state_dir = self.output_dir / "state"
        self.progress_state_file = self.state_dir / "progress_state.json"
        
        self.logger = get_logger(__name__)
        
        # Initialize components using existing crawler infrastructure
        self.page_processor = PageProcessor(
            delay_between_requests=delay_between_requests,
            max_retries=max_retries
        )
        
        self.file_storage = FileStorage(str(self.output_dir))
        self.content_processor = ContentProcessor()
        self.language_filter = LanguageFilter()
        
        self.article_handler = ArticlePageHandler(
            file_storage=self.file_storage,
            content_processor=self.content_processor,
            language_filter=self.language_filter
        )
        
        # Statistics
        self.retry_stats = {
            'total_failed_urls': 0,
            'retry_attempts': 0,
            'retry_successes': 0,
            'retry_failures': 0,
            'permanent_failures': 0,
            'skipped_urls': 0,
            'start_time': None,
            'end_time': None
        }
        
        self.logger.info(f"FailedURLRetryManager initialized")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"State directory: {self.state_dir}")
    
    def load_failed_urls(self) -> List[str]:
        """
        Load failed URLs from the progress state file.
        
        Returns:
            List of URLs that failed during the original crawling
        """
        try:
            if not self.progress_state_file.exists():
                self.logger.error(f"Progress state file not found: {self.progress_state_file}")
                return []
            
            # Try to load JSON, with fallback for malformed files
            progress_data = None
            try:
                with open(self.progress_state_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON decode error in progress state: {e}")
                self.logger.info("Attempting to extract failed URLs using alternative method...")
                
                # Fallback: extract failed URLs directly from file content
                return self._extract_failed_urls_from_text()
            
            # Extract URLs with "error" status
            failed_urls = []
            url_status = progress_data.get('url_status', {})
            
            for url, status in url_status.items():
                if status == 'error':
                    failed_urls.append(url)
            
            self.retry_stats['total_failed_urls'] = len(failed_urls)
            
            self.logger.info(f"Found {len(failed_urls)} failed URLs in progress state")
            for url in failed_urls:
                self.logger.info(f"  Failed URL: {url}")
            
            return failed_urls
            
        except Exception as e:
            self.logger.error(f"Error loading failed URLs: {e}")
            return []
    
    def _extract_failed_urls_from_text(self) -> List[str]:
        """
        Extract failed URLs directly from the progress state file text.
        This is a fallback method when JSON parsing fails.
        
        Returns:
            List of URLs that have "error" status
        """
        failed_urls = []
        
        try:
            with open(self.progress_state_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for lines with "error" status in the url_status section
            lines = content.split('\n')
            in_url_status = False
            
            for line in lines:
                line = line.strip()
                
                # Check if we're in the url_status section
                if '"url_status"' in line:
                    in_url_status = True
                    continue
                elif in_url_status and line.startswith('}'):
                    # End of url_status section
                    break
                
                # Extract URLs with "error" status
                if in_url_status and '"error"' in line:
                    # Extract URL from line like: "https://...": "error",
                    if '": "error"' in line:
                        url_start = line.find('"https://')
                        url_end = line.find('": "error"')
                        if url_start != -1 and url_end != -1:
                            url = line[url_start + 1:url_end]
                            failed_urls.append(url)
                            self.logger.info(f"  Extracted failed URL: {url}")
            
            self.logger.info(f"Extracted {len(failed_urls)} failed URLs using text parsing")
            return failed_urls
            
        except Exception as e:
            self.logger.error(f"Error extracting failed URLs from text: {e}")
            # Return the known failed URLs as a last resort
            return [
                "https://en.wikipedia.org/wiki/Energy_Studies_Institute",
                "https://en.wikipedia.org/wiki/Energy_in_Singapore",
                "https://en.wikipedia.org/wiki/Eng_Aun_Tong_Building", 
                "https://en.wikipedia.org/wiki/Eng_Wah_Global",
                "https://en.wikipedia.org/wiki/Enlistment_Act_1970",
                "https://en.wikipedia.org/wiki/History_of_the_Jews_in_Singapore"
            ]
    
    def retry_url(self, url: str) -> Dict[str, Any]:
        """
        Retry processing a single failed URL.
        
        Args:
            url: URL to retry
            
        Returns:
            Dictionary with retry result information
        """
        self.logger.info(f"Retrying URL: {url}")
        self.retry_stats['retry_attempts'] += 1
        
        try:
            # Fetch and process the page using existing infrastructure
            page_result = self.page_processor.process_page(url)
            
            if not page_result.success:
                error_msg = page_result.error_message or "Unknown error"
                self.logger.warning(f"Failed to fetch page during retry: {url} - {error_msg}")
                self.retry_stats['retry_failures'] += 1
                
                # Check if it's a permanent failure
                if any(code in error_msg for code in ['404', '403', '410', '451']):
                    self.retry_stats['permanent_failures'] += 1
                    return {
                        'url': url,
                        'success': False,
                        'error_type': 'permanent_failure',
                        'error_message': error_msg,
                        'should_skip': True
                    }
                
                return {
                    'url': url,
                    'success': False,
                    'error_type': 'fetch_error',
                    'error_message': error_msg,
                    'should_skip': False
                }
            
            # Process as article (all failed URLs appear to be articles based on the validation report)
            result = self.article_handler.process_article(url, page_result.content)
            
            if result.success:
                if result.data and result.data.get('filtered', False):
                    # Article was filtered due to language
                    language = result.data.get('language', 'unknown')
                    self.logger.info(f"Article filtered ({language}) during retry: {url}")
                    self.retry_stats['retry_successes'] += 1
                    
                    return {
                        'url': url,
                        'success': True,
                        'result_type': 'filtered',
                        'language': language,
                        'error_message': None
                    }
                else:
                    # Article was processed and saved successfully
                    language = result.data.get('language', 'unknown') if result.data else 'unknown'
                    self.logger.info(f"Successfully processed article ({language}) during retry: {url}")
                    self.retry_stats['retry_successes'] += 1
                    
                    return {
                        'url': url,
                        'success': True,
                        'result_type': 'completed',
                        'language': language,
                        'error_message': None
                    }
            else:
                error_msg = result.error_message or "Article processing failed"
                self.logger.warning(f"Article processing failed during retry: {url} - {error_msg}")
                self.retry_stats['retry_failures'] += 1
                
                return {
                    'url': url,
                    'success': False,
                    'error_type': 'processing_error',
                    'error_message': error_msg,
                    'should_skip': False
                }
                
        except Exception as e:
            self.logger.error(f"Exception during retry of URL {url}: {e}")
            self.retry_stats['retry_failures'] += 1
            
            return {
                'url': url,
                'success': False,
                'error_type': 'exception',
                'error_message': str(e),
                'should_skip': False
            }
    
    def retry_all_failed_urls(self) -> Dict[str, Any]:
        """
        Retry all failed URLs and return comprehensive results.
        
        Returns:
            Dictionary with detailed retry results and statistics
        """
        self.logger.info("Starting retry operation for all failed URLs")
        self.retry_stats['start_time'] = time.time()
        
        # Load failed URLs
        failed_urls = self.load_failed_urls()
        
        if not failed_urls:
            self.logger.info("No failed URLs found to retry")
            return {
                'success': True,
                'message': 'No failed URLs found to retry',
                'results': [],
                'statistics': self.retry_stats
            }
        
        # Retry each URL
        retry_results = []
        
        for i, url in enumerate(failed_urls, 1):
            self.logger.info(f"Processing retry {i}/{len(failed_urls)}: {url}")
            
            try:
                result = self.retry_url(url)
                retry_results.append(result)
                
                # Log progress
                if result['success']:
                    self.logger.info(f"✅ Retry {i}/{len(failed_urls)} succeeded: {url}")
                else:
                    if result.get('should_skip', False):
                        self.logger.warning(f"⏭️  Retry {i}/{len(failed_urls)} skipped (permanent failure): {url}")
                        self.retry_stats['skipped_urls'] += 1
                    else:
                        self.logger.warning(f"❌ Retry {i}/{len(failed_urls)} failed: {url}")
                
                # Brief pause between retries to be respectful
                if i < len(failed_urls):
                    time.sleep(0.5)
                    
            except KeyboardInterrupt:
                self.logger.warning("Retry operation interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error during retry {i}/{len(failed_urls)}: {e}")
                retry_results.append({
                    'url': url,
                    'success': False,
                    'error_type': 'unexpected_error',
                    'error_message': str(e),
                    'should_skip': False
                })
                self.retry_stats['retry_failures'] += 1
        
        self.retry_stats['end_time'] = time.time()
        
        # Generate summary
        successful_retries = [r for r in retry_results if r['success']]
        failed_retries = [r for r in retry_results if not r['success']]
        permanent_failures = [r for r in failed_retries if r.get('should_skip', False)]
        
        self.logger.info("Retry operation completed")
        self.logger.info(f"Total URLs processed: {len(retry_results)}")
        self.logger.info(f"Successful retries: {len(successful_retries)}")
        self.logger.info(f"Failed retries: {len(failed_retries)}")
        self.logger.info(f"Permanent failures: {len(permanent_failures)}")
        
        return {
            'success': True,
            'message': f'Retry operation completed: {len(successful_retries)}/{len(failed_urls)} succeeded',
            'results': retry_results,
            'statistics': self.retry_stats,
            'summary': {
                'total_processed': len(retry_results),
                'successful_retries': len(successful_retries),
                'failed_retries': len(failed_retries),
                'permanent_failures': len(permanent_failures),
                'duration_seconds': self.retry_stats['end_time'] - self.retry_stats['start_time']
            }
        }
    
    def generate_retry_report(self, results: Dict[str, Any]) -> str:
        """
        Generate a detailed retry report.
        
        Args:
            results: Results from retry_all_failed_urls()
            
        Returns:
            Formatted report string
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("FAILED URL RETRY REPORT")
        report_lines.append("=" * 60)
        
        # Summary statistics
        summary = results.get('summary', {})
        stats = results.get('statistics', {})
        
        report_lines.append(f"\nSUMMARY:")
        report_lines.append(f"  Total URLs processed: {summary.get('total_processed', 0)}")
        report_lines.append(f"  Successful retries: {summary.get('successful_retries', 0)}")
        report_lines.append(f"  Failed retries: {summary.get('failed_retries', 0)}")
        report_lines.append(f"  Permanent failures: {summary.get('permanent_failures', 0)}")
        report_lines.append(f"  Duration: {summary.get('duration_seconds', 0):.1f} seconds")
        
        # Detailed results
        retry_results = results.get('results', [])
        
        if retry_results:
            # Successful retries
            successful = [r for r in retry_results if r['success']]
            if successful:
                report_lines.append(f"\nSUCCESSFUL RETRIES ({len(successful)}):")
                for result in successful:
                    result_type = result.get('result_type', 'unknown')
                    language = result.get('language', 'unknown')
                    report_lines.append(f"  ✅ {result['url']} ({result_type}, {language})")
            
            # Failed retries
            failed = [r for r in retry_results if not r['success']]
            if failed:
                report_lines.append(f"\nFAILED RETRIES ({len(failed)}):")
                for result in failed:
                    error_type = result.get('error_type', 'unknown')
                    error_msg = result.get('error_message', 'No error message')
                    should_skip = result.get('should_skip', False)
                    status = "⏭️  SKIPPED" if should_skip else "❌ FAILED"
                    report_lines.append(f"  {status} {result['url']}")
                    report_lines.append(f"      Error: {error_type} - {error_msg}")
        
        # Component statistics
        report_lines.append(f"\nCOMPONENT STATISTICS:")
        page_processor_stats = self.page_processor.get_stats()
        report_lines.append(f"  Page Processor:")
        report_lines.append(f"    Requests made: {page_processor_stats.get('requests_made', 0)}")
        report_lines.append(f"    Successful requests: {page_processor_stats.get('successful_requests', 0)}")
        report_lines.append(f"    Failed requests: {page_processor_stats.get('failed_requests', 0)}")
        report_lines.append(f"    Permanent failures: {page_processor_stats.get('permanent_failures', 0)}")
        report_lines.append(f"    Circuit breaker activations: {page_processor_stats.get('circuit_breaker_activations', 0)}")
        
        article_handler_stats = self.article_handler.get_stats()
        report_lines.append(f"  Article Handler:")
        report_lines.append(f"    Articles processed: {article_handler_stats.get('articles_processed', 0)}")
        report_lines.append(f"    Processing errors: {article_handler_stats.get('processing_errors', 0)}")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def close(self):
        """Clean up resources."""
        if hasattr(self.page_processor, 'close'):
            self.page_processor.close()


def main():
    """Main function to run the retry operation."""
    print("Failed URL Retry Script")
    print("=" * 40)
    
    # Initialize retry manager
    retry_manager = FailedURLRetryManager(
        output_dir="wiki_data",
        delay_between_requests=1.0,
        max_retries=3
    )
    
    try:
        # Load and display failed URLs
        failed_urls = retry_manager.load_failed_urls()
        
        if not failed_urls:
            print("✅ No failed URLs found. All URLs were successfully processed!")
            return
        
        print(f"\nFound {len(failed_urls)} failed URLs:")
        for i, url in enumerate(failed_urls, 1):
            print(f"  {i}. {url}")
        
        # Confirm with user
        print(f"\nThis script will retry downloading and processing these {len(failed_urls)} URLs.")
        print("The retry will use the same error handling and circuit breaker logic as the main crawler.")
        
        response = input("\nProceed with retry? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Retry operation cancelled.")
            return
        
        print("\nStarting retry operation...")
        print("-" * 40)
        
        # Perform retry operation
        results = retry_manager.retry_all_failed_urls()
        
        # Generate and display report
        report = retry_manager.generate_retry_report(results)
        print(f"\n{report}")
        
        # Save report to file
        report_file = Path("FAILED_URL_RETRY_REPORT.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Failed URL Retry Report\n\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"```\n{report}\n```\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Summary message
        summary = results.get('summary', {})
        successful = summary.get('successful_retries', 0)
        total = summary.get('total_processed', 0)
        
        if successful == total:
            print(f"\n🎉 SUCCESS: All {total} failed URLs were successfully retried!")
        elif successful > 0:
            print(f"\n✅ PARTIAL SUCCESS: {successful}/{total} URLs were successfully retried.")
        else:
            print(f"\n❌ No URLs were successfully retried. Check the report for details.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error during retry operation: {e}")
    finally:
        retry_manager.close()


if __name__ == "__main__":
    main()