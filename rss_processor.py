import feedparser
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional
import nltk
from bs4 import BeautifulSoup
import requests
from dateutil import parser

from config import (
    RSS_FEEDS,
    DEFAULT_START_DATE,
    DEFAULT_END_DATE,
    PROCESSED_ARTICLES_DIR,
    RAW_ARTICLES_DIR,
    MIN_ARTICLE_LENGTH,
    MAX_ARTICLES_PER_FEED,
    ANALYSIS_CONFIG
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RSSProcessor:
    def __init__(self):
        self.feeds = RSS_FEEDS
        # Set date range to yesterday
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=1)
        
        logger.info(f"Initializing RSS Processor with {len(self.feeds)} feeds")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
        
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            logger.info("NLTK data already downloaded")
        except LookupError:
            logger.info("Downloading required NLTK data...")
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            nltk.download('maxent_ne_chunker')
            nltk.download('words')
            logger.info("NLTK data downloaded successfully")

    def is_article_from_yesterday(self, article: Dict) -> bool:
        """Check if an article was published yesterday."""
        try:
            # Try to get the published date from various possible fields
            pub_date = article.get('published', article.get('pubDate', article.get('updated')))
            if not pub_date:
                logger.warning(f"No publication date found for article: {article.get('title', 'Unknown title')}")
                return False

            # Parse the date string
            article_date = parser.parse(pub_date)
            
            # Convert to datetime if it's a date object
            if not isinstance(article_date, datetime):
                article_date = datetime.combine(article_date, datetime.min.time())
            
            # Check if the article is from yesterday
            is_yesterday = (
                article_date.date() == self.start_date.date() and
                self.start_date.date() <= article_date.date() <= self.end_date.date()
            )
            
            if is_yesterday:
                logger.info(f"Found yesterday's article: {article.get('title', 'Unknown title')} from {article_date}")
            else:
                logger.debug(f"Article not from yesterday: {article.get('title', 'Unknown title')} from {article_date}")
            
            return is_yesterday
        except Exception as e:
            logger.error(f"Error parsing date for article: {str(e)}")
            return False

    def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse an RSS feed."""
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            if feed.bozo:  # Feed parsing error
                logger.error(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                return None
            logger.info(f"Successfully fetched feed with {len(feed.entries)} entries")
            return feed
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
            return None

    def extract_article_content(self, article: Dict) -> str:
        """Extract the main content from an article."""
        try:
            # First try to get content from the article link
            link = article.get('link')
            if not link:
                logger.warning(f"No link found for article: {article.get('title', 'Unknown title')}")
                return ""

            logger.info(f"Fetching full article content from: {link}")
            response = requests.get(link, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }, timeout=15)  # Increased timeout
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find the main article content using various selectors
            content = None
            
            # Common content selectors for news websites
            selectors = [
                # Article content selectors
                ('article', {'class_': 'article-content'}),
                ('article', {'class_': 'content'}),
                ('article', {'class_': 'post-content'}),
                ('article', {'class_': 'entry-content'}),
                ('article', {'class_': 'article-body'}),
                ('article', {'class_': 'story-content'}),
                
                # Div content selectors
                ('div', {'class_': 'article-content'}),
                ('div', {'class_': 'content'}),
                ('div', {'class_': 'post-content'}),
                ('div', {'class_': 'entry-content'}),
                ('div', {'class_': 'article-body'}),
                ('div', {'class_': 'story-content'}),
                ('div', {'class_': 'article-text'}),
                ('div', {'class_': 'article-main'}),
                ('div', {'class_': 'main-content'}),
                
                # Specific RTVDrenthe selectors
                ('div', {'class_': 'layout-components-group article-content', 'data-v-28650198': ''}),
                ('div', {'class_': 'layout-components-group article-content'}),
                
                # Generic content containers
                ('main', {}),
                ('article', {}),
                ('div', {'id': 'content'}),
                ('div', {'id': 'article-content'}),
                ('div', {'id': 'main-content'})
            ]
            
            # Try each selector
            for tag, attrs in selectors:
                content = soup.find(tag, attrs)
                if content:
                    logger.info(f"Found content using selector: {tag} with {attrs}")
                    break

            if content:
                # Remove unwanted elements
                for element in content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript', 'form', 'button', 'input', 'select', 'textarea']):
                    element.decompose()
                
                # Remove common non-content elements
                for class_name in ['advertisement', 'social-share', 'related-articles', 'news-category-list', 'comments', 'sidebar']:
                    for element in content.find_all(class_=lambda x: x and class_name in x.lower()):
                        element.decompose()
                
                # Get all text elements
                text_elements = []
                for element in content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div']):
                    text = element.get_text(strip=True)
                    if text and len(text) > 10:  # Only include substantial text elements
                        text_elements.append(text)
                
                # Join all text elements with proper spacing
                text_content = ' '.join(text_elements)
                
                if text_content and len(text_content.split()) > 50:  # Ensure we have substantial content
                    logger.info(f"Successfully extracted content from {link} ({len(text_content.split())} words)")
                    return text_content
                else:
                    logger.warning(f"Found content container but insufficient text content in {link}")

            # If we couldn't find any content, log the HTML structure for debugging
            logger.warning(f"Could not find main content in article: {link}")
            logger.debug(f"Page structure: {soup.prettify()[:1000]}")  # Log first 1000 chars of HTML

            # Only fall back to RSS content if we absolutely couldn't get content from the link
            if 'content' in article:
                return article.content[0].value
            elif 'summary' in article:
                return article.summary
            elif 'description' in article:
                return article.description

            return ""

        except requests.RequestException as e:
            logger.error(f"Error fetching article content: {str(e)}")
            # Only fall back to RSS content on error
            if 'content' in article:
                return article.content[0].value
            elif 'summary' in article:
                return article.summary
            elif 'description' in article:
                return article.description
            return ""
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            return ""

    def clean_content(self, content: str) -> str:
        """Clean HTML and normalize content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            cleaned = soup.get_text(separator=' ', strip=True)
            logger.debug(f"Cleaned content length: {len(cleaned)} characters")
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning content: {str(e)}")
            return content

    def analyze_content(self, content: str) -> Dict:
        """Analyze article content based on configuration."""
        analysis = {}
        
        if not content or len(content.split()) < MIN_ARTICLE_LENGTH:
            logger.warning(f"Content too short for analysis: {len(content.split())} words")
            return analysis

        try:
            # Basic text analysis
            sentences = nltk.sent_tokenize(content)
            words = nltk.word_tokenize(content)
            
            analysis['basic_stats'] = {
                'word_count': len(words),
                'sentence_count': len(sentences),
                'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0
            }
            logger.debug(f"Basic analysis completed: {analysis['basic_stats']}")

            # Add more analysis based on ANALYSIS_CONFIG
            if ANALYSIS_CONFIG['extract_keywords']:
                # Implement keyword extraction
                pass

            if ANALYSIS_CONFIG['summarize_content']:
                # Implement content summarization
                pass

            if ANALYSIS_CONFIG['extract_entities']:
                # Implement named entity recognition
                pass

            if ANALYSIS_CONFIG['sentiment_analysis']:
                # Implement sentiment analysis
                pass

            return analysis
        except Exception as e:
            logger.error(f"Error in content analysis: {str(e)}")
            return analysis

    def process_article(self, article: Dict, feed_url: str) -> Optional[Dict]:
        """Process a single article."""
        try:
            logger.info(f"Processing article: {article.get('title', 'Unknown title')}")
            
            # Extract and clean content
            content = self.extract_article_content(article)
            cleaned_content = self.clean_content(content)
            
            if not cleaned_content:
                logger.warning("No content to process")
                return None

            # Analyze content
            analysis = self.analyze_content(cleaned_content)

            # Create article data structure
            article_data = {
                'title': article.get('title', ''),
                'link': article.get('link', ''),
                'published': article.get('published', ''),
                'feed_url': feed_url,
                'content': cleaned_content,
                'analysis': analysis,
                'metadata': {
                    'processed_date': datetime.now().isoformat(),
                    'word_count': len(cleaned_content.split()),
                    'sentence_count': len(nltk.sent_tokenize(cleaned_content)),
                    'unique_words': len(set(cleaned_content.lower().split())),
                    'language': 'en',  # Could be enhanced with language detection
                    'difficulty_level': 'medium'  # Could be calculated based on content
                }
            }

            logger.info(f"Successfully processed article: {article_data['title']}")
            return article_data
        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            return None

    def save_article(self, article_data: Dict):
        """Save processed article to storage."""
        try:
            # Create filename for the combined articles file
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"articles_{date_str}.json"
            filepath = PROCESSED_ARTICLES_DIR / filename
            
            # Load existing articles if file exists
            existing_articles = []
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        existing_articles = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Error reading existing articles file: {filepath}")
                        existing_articles = []
            
            # Add new article to the list
            existing_articles.append(article_data)
            
            # Save all articles back to the file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_articles, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved article to combined file: {filename}")
        except Exception as e:
            logger.error(f"Error saving article: {str(e)}")

    def cleanup_old_files(self):
        """Clean up old individual article files if they exist."""
        try:
            # Get all JSON files in the processed articles directory
            json_files = list(PROCESSED_ARTICLES_DIR.glob('*.json'))
            
            # Skip the combined articles file
            date_str = datetime.now().strftime('%Y%m%d')
            combined_file = PROCESSED_ARTICLES_DIR / f"articles_{date_str}.json"
            
            # Delete individual article files
            for file in json_files:
                if file != combined_file:
                    try:
                        file.unlink()
                        logger.info(f"Deleted old individual file: {file.name}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def process_feeds(self):
        """Process all configured RSS feeds."""
        logger.info("Starting feed processing")
        total_articles_processed = 0
        
        for feed_url in self.feeds:
            logger.info(f"Processing feed: {feed_url}")
            feed = self.fetch_feed(feed_url)
            
            if not feed:
                continue

            articles_processed = 0
            for entry in feed.entries:
                if articles_processed >= MAX_ARTICLES_PER_FEED:
                    logger.info(f"Reached maximum articles limit for feed: {feed_url}")
                    break

                # Only process articles from yesterday
                if not self.is_article_from_yesterday(entry):
                    continue

                article_data = self.process_article(entry, feed_url)
                if article_data:
                    self.save_article(article_data)
                    articles_processed += 1
                    total_articles_processed += 1

            logger.info(f"Processed {articles_processed} articles from {feed_url}")
        
        # Clean up old individual files
        self.cleanup_old_files()
        
        logger.info(f"Total articles processed: {total_articles_processed}")

def main():
    processor = RSSProcessor()
    processor.process_feeds()

if __name__ == "__main__":
    main() 