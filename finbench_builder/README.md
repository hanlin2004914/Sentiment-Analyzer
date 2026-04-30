# Financial Benchmark Builder

A web-based tool for building **financial sentiment benchmark datasets** with
real-time stock-price context and user-authored evaluation questions.

Designed around the five aspect-specific sentiment tasks from financial
NLP benchmarks:

| Task | Article Type | Entity Type |
|---|---|---|
| **Equity News Sentiment** | news | equity |
| **Equity Social Media Sentiment** | social | equity |
| **Equity Transcript Sentiment** | transcript | equity |
| **ES News Sentiment** | news | es |
| **Country News Sentiment** | news | country |

Each chunk is annotated as `positive` / `negative` / `neutral` and paired with
the stock-price movement around the article's publish date, so annotators see
how the market actually reacted.

---

## Features

### Data collection
- One-click fetch from **12 financial RSS sources** (Yahoo Finance, Reuters,
  Bloomberg, CNBC, Financial Times, MarketWatch, Seeking Alpha, Investopedia, …)
- Manual upload for earnings-call transcripts and other long-form text
- Automatic chunking to ~70–80 tokens (configurable)

### Annotation
- Single-chunk focused mode that auto-loads the next unlabeled chunk
- Task-specific guiding question shown for each chunk type
- **Keyboard shortcuts**: `1` Positive · `2` Negative · `3` Neutral · `U` Undo · `S` Skip
- Filter the queue by article type or entity type

### Stock-price context (Yahoo Finance)
- Inline mini-chart of the company's price around the publish date
- Before-price / after-price / % change — the same data brokers display
- Editable ticker per article; price data is cached in SQLite

### User-authored benchmark questions
- Write your own evaluation questions about each chunk
- Attach a categorical answer (Positive / Negative / Neutral) or a custom answer
- Multiple questions per chunk; questions become the export records

### Export
- JSONL or JSON
- Two modes: **questions** (recommended) or raw **chunks** with sentiment labels
- Each question record includes the chunk context, source metadata, and price movement

---

## Project structure

```
financial-benchmark/
├── backend/
│   ├── main.py            # Flask API server
│   ├── database.py        # SQLite schema + queries (articles / chunks / questions)
│   ├── scraper.py         # RSS fetching + text chunking
│   ├── prices.py          # Yahoo Finance price-movement fetcher
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .gitignore
├── start.bat              # Windows one-click launcher
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.9+

### Install and run

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Then open <http://localhost:5000> in your browser.

On Windows you can also double-click `start.bat`.

---

## Usage

1. **Dashboard** — click *Fetch News Feeds* to pull articles from all RSS sources.
2. **Upload** — paste earnings-call transcripts or other long text. They are
   automatically split into ~70–80 token chunks.
3. **Annotate** —
   - Press **1 / 2 / 3** (or click) to label the chunk's sentiment
   - View the company's stock movement in the side panel
   - Write benchmark questions about this chunk and pick an answer
   - **U** to undo, **S** to skip, *Next Chunk →* to advance
4. **Articles** — browse and re-label any chunk; trigger full-content fetch
   or re-chunking on a per-article basis.
5. **Export** — download the dataset as JSON or JSONL in either mode.

---

## Export schema

### Questions mode (recommended)
```json
{
  "question_id": 7,
  "question": "Will AAPL stock rise within 7 days based on this news?",
  "answer": "positive",
  "notes": null,
  "context": "...the chunk text...",
  "chunk_label": "positive",
  "title": "Article title",
  "source": "Yahoo Finance",
  "url": "https://...",
  "article_type": "news",
  "entity": "AAPL",
  "entity_type": "equity",
  "published_at": "...",
  "price_change_pct": 2.34,
  "price_before": 175.20,
  "price_after": 179.30
}
```

### Chunks mode
```json
{
  "chunk_id": 42,
  "text": "...",
  "label": "positive",
  "token_count": 74,
  "title": "...",
  "source": "...",
  "url": "...",
  "article_type": "news",
  "entity": "AAPL",
  "entity_type": "equity",
  "published_at": "..."
}
```

`label` / `answer` ∈ `{positive, negative, neutral}`
`article_type` ∈ `{news, transcript, social}`
`entity_type` ∈ `{equity, country, es}`

---

## Notes

- The local SQLite database (`backend/benchmark.db`) is git-ignored — it can
  contain full text scraped from third-party sites. Share the **exported**
  JSONL dataset rather than the database file.
- Stock-price data comes from Yahoo Finance's public chart API (the same data
  Robinhood and other brokers display). No API key or login required.
- Chunk-size targeting uses a simple word-based token approximation. For
  exact tokenizer-aware chunking, swap in `tiktoken` inside `scraper.py`.
