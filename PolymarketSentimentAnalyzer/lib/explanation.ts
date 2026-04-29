import type {
  BenchmarkExample,
  EvidenceItem,
  MarketContextBundle,
  PolymarketMarket,
  PricePoint,
  SentimentForYes
} from "@/lib/types";
import { calculatePriceChange, formatProbability } from "@/lib/utils";

export function findPriceMovementAfterEvidence(
  evidenceItem: EvidenceItem,
  priceSeries: PricePoint[],
  timeWindowHours = 24
) {
  const eventTime = new Date(evidenceItem.timestamp).getTime();
  const windowEnd = eventTime + timeWindowHours * 60 * 60 * 1000;
  const startPoint =
    [...priceSeries]
      .reverse()
      .find((point) => new Date(point.timestamp).getTime() <= eventTime) ??
    priceSeries[0];
  const endPoint =
    priceSeries
      .filter((point) => {
        const timestamp = new Date(point.timestamp).getTime();
        return timestamp > eventTime && timestamp <= windowEnd;
      })
      .at(-1) ??
    priceSeries.find((point) => new Date(point.timestamp).getTime() > eventTime) ??
    startPoint;

  return {
    startPoint,
    endPoint,
    change: (endPoint?.yesPrice ?? 0) - (startPoint?.yesPrice ?? 0)
  };
}

export function generateMarketExplanation({
  market,
  priceSeries,
  evidenceItems
}: {
  market: PolymarketMarket;
  priceSeries: PricePoint[];
  evidenceItems: EvidenceItem[];
}) {
  if (priceSeries.length < 2) {
    return "There is not enough price history to connect evidence with market movement.";
  }

  const usableEvidence = evidenceItems.filter((item) => !item.isFallback);
  const reactions = usableEvidence.map((item) => ({
    item,
    movement: findPriceMovementAfterEvidence(item, priceSeries, 36)
  }));
  const threshold = 0.015;

  const positiveUp = reactions.find(
    ({ item, movement }) =>
      item.sentimentForYes === "positive" && movement.change > threshold
  );
  if (positiveUp) {
    return `The YES price increased after positive evidence appeared. It moved from ${formatProbability(
      positiveUp.movement.startPoint.yesPrice
    )} to ${formatProbability(
      positiveUp.movement.endPoint.yesPrice
    )} near "${positiveUp.item.title}", suggesting traders interpreted the news as favorable to "${market.yesOutcome}".`;
  }

  const negativeDown = reactions.find(
    ({ item, movement }) =>
      item.sentimentForYes === "negative" && movement.change < -threshold
  );
  if (negativeDown) {
    return `The YES price decreased after negative evidence appeared. It moved from ${formatProbability(
      negativeDown.movement.startPoint.yesPrice
    )} to ${formatProbability(
      negativeDown.movement.endPoint.yesPrice
    )} near "${negativeDown.item.title}", suggesting the market reacted against the YES outcome.`;
  }

  const flat = reactions.find(
    ({ movement }) => Math.abs(movement.change) <= threshold
  );
  if (flat) {
    return "The evidence was directionally relevant, but the market showed limited price reaction during this window.";
  }

  const totalMove = calculatePriceChange(priceSeries);
  if (Math.abs(totalMove.change) > threshold) {
    return "The market moved without a clear matching news catalyst in the retrieved evidence. The move may reflect liquidity, speculation, private information, or news not captured by the current evidence pipeline.";
  }

  return "Retrieved evidence did not show a strong directional relationship with YES price movement in the selected window.";
}

export function summarizeEvidenceSentiment(
  evidenceItems: EvidenceItem[]
): SentimentForYes {
  const realItems = evidenceItems.filter((item) => !item.isFallback);
  const items = realItems.length > 0 ? realItems : evidenceItems;
  const totals = items.reduce(
    (acc, item) => {
      acc[item.sentimentForYes] += item.confidence;
      return acc;
    },
    { positive: 0, negative: 0, neutral: 0 } satisfies Record<
      SentimentForYes,
      number
    >
  );

  if (Math.abs(totals.positive - totals.negative) < 0.3) return "neutral";
  return totals.positive > totals.negative ? "positive" : "negative";
}

export function exportBenchmarkExample(
  contextBundle: MarketContextBundle
): BenchmarkExample {
  const answer = summarizeEvidenceSentiment(contextBundle.evidenceItems);
  const realEvidence = contextBundle.evidenceItems.filter((item) => !item.isFallback);
  const directionalItems = realEvidence.filter(
    (item) => item.sentimentForYes !== "neutral" && item.confidence >= 0.7
  );
  const directions = new Set(realEvidence.map((item) => item.sentimentForYes));
  const difficulty =
    directionalItems.length === 1 && directions.size <= 2
      ? "easy"
      : directions.size <= 2 && directionalItems.length > 1
        ? "medium"
        : "hard";

  return {
    type: "Prediction Market Sentiment",
    platform: "Polymarket",
    category: contextBundle.market.category,
    market_question: contextBundle.market.question,
    yes_outcome: contextBundle.market.yesOutcome,
    no_outcome: contextBundle.market.noOutcome,
    resolution_rules: contextBundle.market.resolutionRules,
    evidence: contextBundle.evidenceItems.map((item) => ({
      timestamp: item.timestamp,
      source: item.source,
      title: item.title,
      url: item.url,
      sentiment_for_yes: item.sentimentForYes,
      confidence: item.confidence
    })),
    question:
      "Based on the evidence, is the sentiment positive, negative, or neutral for the YES outcome of this Polymarket market?",
    answer,
    difficulty,
    explanation: contextBundle.explanation
  };
}
