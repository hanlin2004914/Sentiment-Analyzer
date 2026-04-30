import feedparser
import requests
from bs4 import BeautifulSoup
import re
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}

# RSS feeds for financial news
RSS_SOURCES = [
    {
        "name": "Yahoo Finance - Top Stories",
        "url": "https://finance.yahoo.com/news/rssindex",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "Yahoo Finance - Markets",
        "url": "https://finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "Reuters Markets",
        "url": "https://feeds.reuters.com/reuters/companyNews",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "MarketWatch Top Stories",
        "url": "http://feeds.marketwatch.com/marketwatch/topstories/",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "MarketWatch Markets",
        "url": "http://feeds.marketwatch.com/marketwatch/marketpulse/",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "Seeking Alpha Market News",
        "url": "https://seekingalpha.com/market_currents.xml",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "CNBC Finance",
        "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "CNBC World Economy",
        "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "type": "news",
        "entity_type": "country",
    },
    {
        "name": "Financial Times",
        "url": "https://www.ft.com/rss/home",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "Bloomberg Markets",
        "url": "https://feeds.bloomberg.com/markets/news.rss",
        "type": "news",
        "entity_type": "equity",
    },
    {
        "name": "Investopedia News",
        "url": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=rss_headline",
        "type": "news",
        "entity_type": "equity",
    },
]


def fetch_rss_feed(source):
    """Fetch articles from an RSS feed."""
    articles = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:20]:  # max 20 per feed
            title = entry.get("title", "").strip()
            url = entry.get("link", "")
            published = entry.get("published", entry.get("updated", ""))
            summary = entry.get("summary", entry.get("description", ""))

            # Clean HTML from summary
            if summary:
                soup = BeautifulSoup(summary, "html.parser")
                content = soup.get_text(separator=" ").strip()
            else:
                content = ""

            if title and url:
                articles.append({
                    "title": title,
                    "content": content,
                    "source": source["name"],
                    "url": url,
                    "published_at": published,
                    "article_type": source["type"],
                    "entity_type": source["entity_type"],
                    "entity": "",
                })
    except Exception as e:
        print(f"Error fetching {source['name']}: {e}")
    return articles


def fetch_article_content(url):
    """Try to fetch full article content from URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script/style
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try common article selectors
        selectors = [
            "article",
            '[class*="article-body"]',
            '[class*="story-body"]',
            '[class*="post-content"]',
            '[class*="entry-content"]',
            "main",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator=" ").strip()
                text = re.sub(r'\s+', ' ', text)
                if len(text) > 200:
                    return text

        # Fallback: all paragraphs
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs)
        return re.sub(r'\s+', ' ', text).strip()
    except Exception as e:
        print(f"Error fetching article content from {url}: {e}")
        return ""


def fetch_all_feeds():
    """Fetch articles from all configured RSS feeds."""
    all_articles = []
    for source in RSS_SOURCES:
        print(f"Fetching: {source['name']}")
        articles = fetch_rss_feed(source)
        all_articles.extend(articles)
        time.sleep(0.5)  # polite delay
    return all_articles


def chunk_text(text, target_tokens=75, min_tokens=50, max_tokens=100):
    """
    Split text into chunks of approximately target_tokens tokens.
    Uses whitespace tokenization as a simple approximation.
    """
    # Simple word-based tokenization approximation
    words = text.split()
    chunks = []
    current_chunk = []
    current_count = 0

    for word in words:
        # Approximate token count: words + subword splits for long words
        token_estimate = max(1, len(word) // 4 + 1) if len(word) > 8 else 1
        current_chunk.append(word)
        current_count += token_estimate

        if current_count >= target_tokens:
            chunk_text_str = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text_str,
                "token_count": current_count,
            })
            current_chunk = []
            current_count = 0

    # Add remaining
    if current_chunk and current_count >= min_tokens:
        chunks.append({
            "text": " ".join(current_chunk),
            "token_count": current_count,
        })
    elif current_chunk and chunks:
        # Append to last chunk if too short
        chunks[-1]["text"] += " " + " ".join(current_chunk)
        chunks[-1]["token_count"] += current_count

    return chunks
