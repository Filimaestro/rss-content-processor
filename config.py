from datetime import datetime, timedelta
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RSS Feed Configuration
RSS_FEEDS = [
    # Add your RSS feed URLs here
    # Example: "https://example.com/feed.xml"
    "https://www.rtvdrenthe.nl/rss/index.xml"
]

# Date Configuration
DEFAULT_START_DATE = datetime.now() - timedelta(days=7)  # Last 7 days
DEFAULT_END_DATE = datetime.now()

# Storage Configuration
STORAGE_DIR = Path(os.getenv('STORAGE_DIR', 'storage'))
PROCESSED_ARTICLES_DIR = STORAGE_DIR / "processed_articles"
RAW_ARTICLES_DIR = STORAGE_DIR / "raw_articles"

# Content Analysis Configuration
MIN_ARTICLE_LENGTH = int(os.getenv('MIN_ARTICLE_LENGTH', '100'))  # Minimum number of words for analysis
MAX_ARTICLES_PER_FEED = int(os.getenv('MAX_ARTICLES_PER_FEED', '50'))  # Maximum number of articles to process per feed

# Create necessary directories
for directory in [STORAGE_DIR, PROCESSED_ARTICLES_DIR, RAW_ARTICLES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Analysis Parameters
ANALYSIS_CONFIG = {
    "extract_keywords": os.getenv('EXTRACT_KEYWORDS', 'True').lower() == 'true',
    "summarize_content": os.getenv('SUMMARIZE_CONTENT', 'True').lower() == 'true',
    "extract_entities": os.getenv('EXTRACT_ENTITIES', 'True').lower() == 'true',
    "sentiment_analysis": os.getenv('SENTIMENT_ANALYSIS', 'True').lower() == 'true'
} 