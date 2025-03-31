import feedparser
import json
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional
import nltk
from bs4 import BeautifulSoup
import requests

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
        self.start_date = DEFAULT_START_DATE
        self.end_date = DEFAULT_END_DATE
        
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            nltk.download('maxent_ne_chunker')
            nltk.download('words')

    def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse an RSS feed."""
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo:  # Feed parsing error
                logger.error(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                return None
            return feed
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
            return None

    def extract_article_content(self, article: Dict) -> str:
        """Extract the main content from an article."""
        if 'content' in article:
            return article.content[0].value
        elif 'summary' in article:
            return article.summary
        elif 'description' in article:
            return article.description
        return ""

    def clean_content(self, content: str) -> str:
        """Clean HTML and normalize content."""
        soup = BeautifulSoup(content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def analyze_content(self, content: str) -> Dict:
        """Analyze article content based on configuration."""
        analysis = {}
        
        if not content or len(content.split()) < MIN_ARTICLE_LENGTH:
            return analysis

        # Basic text analysis
        sentences = nltk.sent_tokenize(content)
        words = nltk.word_tokenize(content)
        
        analysis['basic_stats'] = {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0
        }

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

    def process_article(self, article: Dict, feed_url: str) -> Optional[Dict]:
        """Process a single article."""
        try:
            # Extract and clean content
            content = self.extract_article_content(article)
            cleaned_content = self.clean_content(content)

            # Analyze content
            analysis = self.analyze_content(cleaned_content)

            # Create article data structure
            article_data = {
                'title': article.get('title', ''),
                'link': article.get('link', ''),
                'published': article.get('published', ''),
                'feed_url': feed_url,
                'content': cleaned_content,
                'analysis': analysis
            }

            return article_data
        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            return None

    def save_article(self, article_data: Dict):
        """Save processed article to storage."""
        try:
            # Create filename from title and date
            safe_title = "".join(c for c in article_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_title}_{date_str}.json"
            
            # Save to processed articles directory
            filepath = PROCESSED_ARTICLES_DIR / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved article: {filename}")
        except Exception as e:
            logger.error(f"Error saving article: {str(e)}")

    def process_feeds(self):
        """Process all configured RSS feeds."""
        for feed_url in self.feeds:
            logger.info(f"Processing feed: {feed_url}")
            feed = self.fetch_feed(feed_url)
            
            if not feed:
                continue

            articles_processed = 0
            for entry in feed.entries:
                if articles_processed >= MAX_ARTICLES_PER_FEED:
                    break

                article_data = self.process_article(entry, feed_url)
                if article_data:
                    self.save_article(article_data)
                    articles_processed += 1

            logger.info(f"Processed {articles_processed} articles from {feed_url}")

def main():
    processor = RSSProcessor()
    processor.process_feeds()

if __name__ == "__main__":
    main() 