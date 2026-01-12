# Requirements Document

## Introduction

A web crawler system that systematically downloads and organizes Wikipedia pages related to Singapore, starting from the main Singapore category page and recursively processing subcategories and individual articles.

## Glossary

- **Crawler**: The main system that orchestrates the crawling process
- **Category_Page**: A Wikipedia page that contains subcategories and/or individual article links
- **Article_Page**: A Wikipedia page containing actual content about a specific topic
- **Deduplication_System**: Component that tracks processed URLs to prevent duplicate downloads
- **Progress_Tracker**: Component that maintains state of crawling progress for resumability
- **Language_Filter**: Component that determines if content is in English or Chinese languages
- **Content_Processor**: Component that converts HTML content to clean text or markdown format

## Requirements

### Requirement 1: Category Page Processing

**User Story:** As a researcher, I want to process Wikipedia category pages, so that I can systematically discover all Singapore-related content.

#### Acceptance Criteria

1. WHEN the Crawler processes a category page, THE System SHALL extract all subcategory links from the "Subcategories" section
2. WHEN the Crawler processes a category page, THE System SHALL extract all article links from the "Pages in category" section
3. WHEN a category page is processed, THE System SHALL save the page metadata as JSON including URL, subcategories list, and pages list
4. THE System SHALL save category metadata to the wiki folder with filename format "category_<sanitized_title>.json"

### Requirement 2: Article Content Extraction

**User Story:** As a researcher, I want to extract article content from Wikipedia pages, so that I can analyze the textual information about Singapore topics.

#### Acceptance Criteria

1. WHEN the Crawler visits an article page, THE System SHALL extract the main article content excluding talk pages
2. WHEN article content is extracted, THE Content_Processor SHALL convert HTML content to clean text or markdown format
3. THE Content_Processor SHALL remove all HTML tags, formatting, and image references from the content
4. WHEN article content is processed, THE Language_Filter SHALL determine if the content is in English or Chinese
5. IF the content is not in English or Chinese, THEN THE System SHALL skip processing and mark as filtered
6. WHEN article content is in English or Chinese, THE System SHALL save it as JSON with the original page title as filename
7. THE System SHALL sanitize filenames to remove invalid characters for filesystem compatibility
8. THE System SHALL save article files to the wiki folder with filename format "<sanitized_title>.json"

### Requirement 3: Recursive Crawling

**User Story:** As a researcher, I want the system to recursively process subcategories, so that I can discover all nested Singapore-related content.

#### Acceptance Criteria

1. WHEN a subcategory link is discovered, THE Crawler SHALL add it to the processing queue
2. WHEN processing subcategories, THE Crawler SHALL repeat the category processing steps recursively
3. THE Crawler SHALL continue processing until all discovered categories and articles are processed
4. WHEN all pages are processed, THE Crawler SHALL indicate completion status

### Requirement 4: Deduplication System

**User Story:** As a system operator, I want to prevent duplicate downloads, so that the crawler is efficient and doesn't waste resources.

#### Acceptance Criteria

1. WHEN the Crawler encounters a URL, THE Deduplication_System SHALL check if it has been previously processed
2. IF a URL has been processed, THEN THE System SHALL skip downloading and processing
3. THE Deduplication_System SHALL maintain a persistent record of processed URLs
4. WHEN the system restarts, THE Deduplication_System SHALL load the existing processed URLs list

### Requirement 5: Progress Tracking and Resumability

**User Story:** As a system operator, I want the crawler to resume from where it left off, so that interruptions don't require starting over.

#### Acceptance Criteria

1. THE Progress_Tracker SHALL maintain a persistent record of crawling state including pending URLs and completion status
2. WHEN the system starts, THE Progress_Tracker SHALL load existing state if available
3. WHEN the system restarts, THE Crawler SHALL resume processing from the saved state
4. THE Progress_Tracker SHALL update state after each successful page processing

### Requirement 6: File Organization

**User Story:** As a researcher, I want organized file storage, so that I can easily locate and analyze the downloaded content.

#### Acceptance Criteria

1. THE System SHALL create a "wiki" folder in the current directory if it doesn't exist
2. THE System SHALL save all JSON files to the wiki folder
3. WHEN saving files, THE System SHALL ensure filenames are filesystem-safe
4. THE System SHALL organize files with clear naming conventions distinguishing categories from articles

### Requirement 7: Starting Point Configuration

**User Story:** As a system operator, I want to configure the starting URL, so that the crawler begins from the correct Wikipedia category.

#### Acceptance Criteria

1. THE Crawler SHALL start processing from the URL "https://en.wikipedia.org/wiki/Category:Singapore"
2. THE System SHALL treat this initial URL as a category page for processing
3. WHEN starting fresh, THE Crawler SHALL add the starting URL to the processing queue
4. THE System SHALL validate that the starting URL is accessible before beginning crawling

### Requirement 8: Language Filtering

**User Story:** As a researcher, I want to filter content by language, so that I only collect English and Chinese Wikipedia articles.

#### Acceptance Criteria

1. WHEN processing any Wikipedia page, THE Language_Filter SHALL detect the page language
2. THE System SHALL only process pages that are in English or Chinese languages
3. WHEN a page is in an unsupported language, THE System SHALL log it as filtered and skip processing
4. THE Language_Filter SHALL use Wikipedia's language indicators or content analysis to determine language
5. THE System SHALL maintain statistics of filtered pages by language for reporting

### Requirement 9: Content Format Processing

**User Story:** As a researcher, I want clean, readable content without HTML formatting, so that I can easily analyze the textual information.

#### Acceptance Criteria

1. THE Content_Processor SHALL strip all HTML tags from Wikipedia article content
2. THE Content_Processor SHALL remove image references, captions, and media elements
3. THE Content_Processor SHALL preserve text structure using markdown formatting when possible
4. THE Content_Processor SHALL convert HTML formatting (bold, italic, headers) to equivalent markdown syntax
5. THE Content_Processor SHALL maintain paragraph breaks and list structures in the output
6. THE System SHALL save processed content as clean text or markdown in the JSON output

**User Story:** As a researcher, I want to filter content by language, so that I only collect English and Chinese Wikipedia articles.

#### Acceptance Criteria

1. WHEN processing any Wikipedia page, THE Language_Filter SHALL detect the page language
2. THE System SHALL only process pages that are in English or Chinese languages
3. WHEN a page is in an unsupported language, THE System SHALL log it as filtered and skip processing
4. THE Language_Filter SHALL use Wikipedia's language indicators or content analysis to determine language
5. THE System SHALL maintain statistics of filtered pages by language for reporting

**User Story:** As a system operator, I want to configure the starting URL, so that the crawler begins from the correct Wikipedia category.

#### Acceptance Criteria

1. THE Crawler SHALL start processing from the URL "https://en.wikipedia.org/wiki/Category:Singapore"
2. THE System SHALL treat this initial URL as a category page for processing
3. WHEN starting fresh, THE Crawler SHALL add the starting URL to the processing queue
4. THE System SHALL validate that the starting URL is accessible before beginning crawling

### Requirement 10: Network Connectivity Detection and User Interaction

**User Story:** As a system operator, I want the crawler to detect network connectivity issues and provide user options, so that I can decide whether to continue or skip problematic URLs during network outages.

#### Acceptance Criteria

1. WHEN all retry attempts fail for a URL, THE System SHALL test network connectivity by attempting to reach "https://www.google.com"
2. IF the connectivity test to Google fails, THEN THE System SHALL halt processing and present user options
3. THE System SHALL display a user prompt with two options: "Continue" or "Skip"
4. WHEN the user selects "Continue", THE System SHALL retry the failed URL with the same retry logic (3 attempts with exponential backoff)
5. WHEN the user selects "Skip", THE System SHALL mark the URL as skipped and proceed to the next URL in the queue
6. IF the user selects "Continue" and retries fail again, THE System SHALL repeat the connectivity test and user prompt
7. THE System SHALL maintain statistics of skipped URLs due to connectivity issues
8. THE System SHALL log all connectivity test results and user decisions for audit purposes
9. WHEN connectivity to Google succeeds but the original URL still fails, THE System SHALL treat it as a permanent failure and skip without user prompt

### Requirement 11: Failed URL Retry System

**User Story:** As a system operator, I want to retry previously failed URLs from completed crawling operations, so that I can recover from temporary failures and improve overall success rates.

#### Acceptance Criteria

1. THE System SHALL provide a dedicated retry script that can identify failed URLs from progress state files
2. WHEN loading failed URLs, THE System SHALL parse both JSON and text-based progress state formats for robustness
3. THE Retry System SHALL reuse existing crawler infrastructure (PageProcessor, ArticleHandler, FileStorage) for consistency
4. WHEN retrying a failed URL, THE System SHALL apply the same error handling and circuit breaker logic as the main crawler
5. THE System SHALL provide interactive user experience with real-time progress reporting during retry operations
6. WHEN retry operations complete, THE System SHALL generate comprehensive reports showing success/failure statistics
7. THE System SHALL save successfully retried content as JSON files in the same format as the main crawler
8. THE System SHALL distinguish between temporary failures (retryable) and permanent failures (404, 403, 410, 451)
9. THE System SHALL maintain detailed statistics including retry attempts, successes, failures, and processing errors
10. THE System SHALL provide user confirmation before starting retry operations
11. WHEN content processing fails due to insufficient content, THE System SHALL log the specific error for investigation

### Requirement 12: Smart Error Handling and Circuit Breaker Protection

**User Story:** As a system operator, I want intelligent error handling that distinguishes between temporary and permanent failures, so that the crawler efficiently handles various error conditions without wasting resources.

#### Acceptance Criteria

1. THE System SHALL implement exponential backoff retry logic with jitter for temporary failures
2. WHEN encountering HTTP 404, 403, 410, or 451 errors, THE System SHALL immediately mark URLs as permanent failures without retrying
3. WHEN encountering 5xx server errors, timeouts, or connection errors, THE System SHALL retry with exponential backoff (maximum 3 attempts)
4. THE System SHALL implement circuit breaker protection to prevent infinite retry loops
5. WHEN circuit breaker activates after 3 retry cycles, THE System SHALL test network connectivity and prompt user for action
6. THE System SHALL track detailed error statistics by category (permanent failures, temporary failures, circuit breaker activations)
7. THE System SHALL use jitter in retry delays to prevent thundering herd problems
8. THE System SHALL log all error conditions with appropriate severity levels for debugging and monitoring
9. THE System SHALL provide comprehensive error reporting in crawling summaries and retry reports