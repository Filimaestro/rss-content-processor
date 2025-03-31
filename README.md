# RSS Content Processor

A Python-based tool for processing RSS feeds, analyzing content, and storing processed articles for further use.

## Features

- RSS feed parsing and article extraction
- Date-based article filtering
- Content analysis and processing
- Structured storage of processed content

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your RSS feeds in `config.py`

## Usage

Run the main script:
```bash
python rss_processor.py
```

## Configuration

Edit `config.py` to:
- Add RSS feed URLs
- Configure date ranges
- Set storage preferences
- Adjust analysis parameters

## Project Structure

- `rss_processor.py`: Main script for RSS processing
- `config.py`: Configuration settings
- `utils/`: Utility functions for content processing
- `storage/`: Processed content storage 