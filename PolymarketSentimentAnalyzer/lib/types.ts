export type MarketCategory =
  | "Political"
  | "Finance"
  | "Crypto"
  | "Sports"
  | "Tech"
  | "Other";

export type SentimentForYes = "positive" | "negative" | "neutral";

export type TimeWindow = "1D" | "7D" | "30D" | "All";

export type PriceSeriesSource = "clob-history" | "derived-demo";

export interface PolymarketMarket {
  id: string;
  slug: string;
  question: string;
  category: MarketCategory;
  outcomes: string[];
  yesOutcome: string;
  noOutcome: string;
  resolutionRules: string;
  description?: string;
  currentYesPrice: number;
  volume: number;
  liquidity: number;
  startDate?: string;
  endDate?: string;
  clobTokenIds: string[];
  yesTokenId?: string;
  active: boolean;
  closed: boolean;
  url: string;
  oneDayPriceChange?: number;
  oneWeekPriceChange?: number;
  oneMonthPriceChange?: number;
  raw?: unknown;
}

export interface PolymarketSearchResult {
  id: string;
  slug: string;
  question: string;
  category: MarketCategory;
  currentYesPrice: number;
  volume: number;
  liquidity: number;
  endDate?: string;
  active: boolean;
  closed: boolean;
}

export interface PricePoint {
  timestamp: string;
  yesPrice: number;
  volume?: number;
  source?: PriceSeriesSource;
}

export interface EvidenceItem {
  id: string;
  source: string;
  title: string;
  url?: string;
  publishedAt: string;
  timestamp: string;
  summary: string;
  matchedKeywords: string[];
  sentimentForYes: SentimentForYes;
  confidence: number;
  reason: string;
  dataSource: "newsapi" | "gdelt" | "rss" | "fallback-demo";
  isFallback?: boolean;
}

export interface MarketContextBundle {
  platform: "Polymarket";
  market: PolymarketMarket;
  priceSeries: PricePoint[];
  priceSeriesSource: PriceSeriesSource;
  evidenceItems: EvidenceItem[];
  selectedTimeWindow: TimeWindow;
  detectedSentimentSummary: SentimentForYes;
  explanation: string;
}

export interface BenchmarkExample {
  type: "Prediction Market Sentiment";
  category: MarketCategory;
  platform: "Polymarket";
  market_question: string;
  yes_outcome: string;
  no_outcome: string;
  resolution_rules: string;
  evidence: Array<{
    timestamp: string;
    source: string;
    title: string;
    url?: string;
    sentiment_for_yes: SentimentForYes;
    confidence: number;
  }>;
  question: string;
  answer: SentimentForYes;
  difficulty: "easy" | "medium" | "hard";
  explanation: string;
}

export interface EvidenceClassification {
  sentimentForYes: SentimentForYes;
  confidence: number;
  reason: string;
}

export interface NewsSearchInput {
  marketQuestion: string;
  category: MarketCategory;
  keywords?: string[];
  startDate?: string;
  endDate?: string;
  yesOutcome: string;
  noOutcome: string;
}
