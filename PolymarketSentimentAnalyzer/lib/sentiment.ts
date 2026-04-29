import type {
  EvidenceClassification,
  EvidenceItem,
  SentimentForYes
} from "@/lib/types";

const bullishTerms = [
  "lead",
  "leads",
  "leading",
  "wins",
  "win",
  "approval",
  "approved",
  "passes",
  "pass",
  "surges",
  "rises",
  "rally",
  "gains",
  "record high",
  "all-time high",
  "breaks above",
  "could hit",
  "will hit",
  "targets",
  "target",
  "forecast",
  "bullish",
  "endorsement",
  "support",
  "beats",
  "strong",
  "accumulation",
  "inflows"
];

const bearishTerms = [
  "falls",
  "drops",
  "declines",
  "scandal",
  "investigation",
  "rejects",
  "rejected",
  "delay",
  "delayed",
  "misses",
  "lawsuit",
  "injury",
  "injured",
  "risk",
  "weak",
  "outflows",
  "below",
  "selloff",
  "loss"
];

function scoreTerms(text: string, terms: string[]) {
  return terms.reduce(
    (score, term) => score + (text.includes(term) ? 1 : 0),
    0
  );
}

function detectYesPolarity(marketQuestion: string) {
  const text = marketQuestion.toLowerCase();
  if (
    /\b(dip|drop|fall|below|under|lose|fail|miss|resign|down)\b/.test(text)
  ) {
    return "bearish_yes";
  }
  if (
    /\b(win|lead|pass|approve|hit|reach|above|over|rise|increase|up)\b/.test(
      text
    )
  ) {
    return "bullish_yes";
  }
  return "direction_unknown";
}

export function classifyEvidenceForYes({
  marketQuestion,
  yesOutcome,
  noOutcome,
  evidenceTitle,
  evidenceSummary
}: {
  marketQuestion: string;
  yesOutcome: string;
  noOutcome: string;
  evidenceTitle: string;
  evidenceSummary?: string;
}): EvidenceClassification {
  const text = `${evidenceTitle} ${evidenceSummary ?? ""}`.toLowerCase();
  const bullishScore = scoreTerms(text, bullishTerms);
  const bearishScore = scoreTerms(text, bearishTerms);
  const polarity = detectYesPolarity(marketQuestion);
  const directionalScore =
    polarity === "bearish_yes"
      ? bearishScore - bullishScore
      : bullishScore - bearishScore;

  if (Math.abs(directionalScore) === 0) {
    return {
      sentimentForYes: "neutral",
      confidence: 0.45,
      reason: `The article contains no clear directional signal for ${yesOutcome} versus ${noOutcome}.`
    };
  }

  const sentimentForYes: SentimentForYes =
    directionalScore > 0 ? "positive" : "negative";
  const confidence = Math.min(0.9, 0.55 + Math.abs(directionalScore) * 0.12);
  const directionText =
    sentimentForYes === "positive"
      ? "makes the YES outcome look more likely"
      : "makes the YES outcome look less likely";

  return {
    sentimentForYes,
    confidence,
    reason: `Rule-based keyword evidence ${directionText} for a market where YES means "${yesOutcome}".`
  };
}

export function summarizeDetectedSentiment(
  evidenceItems: EvidenceItem[]
): SentimentForYes {
  const totals = evidenceItems.reduce(
    (acc, item) => {
      acc[item.sentimentForYes] += item.confidence;
      return acc;
    },
    { positive: 0, negative: 0, neutral: 0 } satisfies Record<
      SentimentForYes,
      number
    >
  );

  if (Math.abs(totals.positive - totals.negative) < 0.25) return "neutral";
  return totals.positive > totals.negative ? "positive" : "negative";
}

// TODO: Replace the rule-based scorer with an LLM/classifier ensemble that
// explicitly reasons over the market question and outcome semantics.
