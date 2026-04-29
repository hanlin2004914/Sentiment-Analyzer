# Polymarket Sentiment vs Price Movement Dashboard

A research/demo website for comparing Polymarket YES price movement with external news evidence. The dashboard resolves Polymarket markets, retrieves price movement, searches public news sources, classifies each evidence item relative to the YES outcome, annotates the chart, and exports benchmark-ready JSON.

This project does not include trading, order placement, buy/sell controls, wallet connection, or financial advice functionality.

## Why Polymarket Only

The app is intentionally scoped to Polymarket so the benchmark workflow has one market schema, one platform vocabulary, and one consistent YES/NO outcome model. This keeps the research dataset cleaner than mixing Polymarket and other prediction market platforms.

## Tech Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- shadcn/ui-style local components
- Recharts
- Server-side API routes for Polymarket and news retrieval
- Vercel-friendly runtime

## Run Locally

```bash
npm install
npm run dev
```

Then open `http://localhost:3000`.

Optional environment variables:

```bash
NEWS_API_KEY=
NEXT_PUBLIC_APP_URL=
```

`NEWS_API_KEY` is optional. Without it, the app falls back to GDELT and Google News RSS.

## Pages

- `/` home page
- `/dashboard` Polymarket dashboard
- `/markets` market search
- `/evidence` evidence explorer
- `/benchmark` benchmark export
- `/methodology` methodology

## Polymarket Data

Polymarket utilities live in `lib/polymarket.ts`.

Implemented helpers:

- `searchPolymarketMarkets(query)`
- `getPolymarketMarketBySlug(slug)`
- `getPolymarketMarketByUrl(url)`
- `getPolymarketPriceHistory(marketId)`
- `normalizePolymarketMarket(rawMarket)`

Server routes:

- `app/api/polymarket/search/route.ts`
- `app/api/polymarket/market/route.ts`
- `app/api/polymarket/price-history/route.ts`

The app attempts to load CLOB price history for the YES token. If unavailable, it creates a clearly labeled `derived-demo` series from real current price and reported change fields. That fallback is not presented as real historical data.

## Real News Evidence

News utilities live in `lib/news.ts`.

The evidence pipeline tries:

1. NewsAPI, when `NEWS_API_KEY` is configured
2. GDELT DOC API
3. Google News RSS

Items must have valid real URLs to appear as original-source links. If all live retrieval fails, the app creates a clearly labeled non-clickable fallback item so the benchmark flow remains demonstrable.

## Sentiment Classification

Rule-based sentiment logic lives in `lib/sentiment.ts`.

`classifyEvidenceForYes(...)` answers:

> Does this news make the YES outcome more likely, less likely, or not clearly affected?

It returns:

- `sentimentForYes`
- `confidence`
- `reason`

The code includes TODOs for a future LLM or classifier-based scorer.

## Benchmark Export

Benchmark generation lives in `lib/explanation.ts`.

The exported object includes:

- market question and resolution rules
- YES and NO outcomes
- evidence titles, sources, URLs, sentiment labels, and confidence
- answer label
- difficulty
- explanation

Difficulty is heuristic:

- Easy: one strong evidence item clearly points in one direction
- Medium: multiple evidence items mostly agree
- Hard: mixed, weak, conflicting, or unclear evidence/price reaction

## Adding More Evidence Sources

Add a new fetcher in `lib/news.ts`, normalize results into `EvidenceItem`, and include it in `searchNewsEvidence`. Preserve the rule that clickable links must be real, valid external URLs.

## Limitations

- News search relevance is keyword-based.
- Sentiment classification is rule-based and approximate.
- Public news APIs may rate limit or omit relevant articles.
- CLOB historical data can be unavailable for some markets; fallback series are labeled.
- Price movement and news timing correlation does not imply causation.

## Disclaimer

This is a research/demo dashboard for dataset construction and analysis. It is not a trading app and does not provide financial advice.
