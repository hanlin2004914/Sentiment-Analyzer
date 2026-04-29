import { Badge } from "@/components/ui/badge";
import type { SentimentForYes } from "@/lib/types";

const labelBySentiment: Record<SentimentForYes, string> = {
  positive: "Positive for YES",
  negative: "Negative for YES",
  neutral: "Neutral"
};

export function SentimentBadge({
  sentiment
}: {
  sentiment: SentimentForYes;
}) {
  return <Badge variant={sentiment}>{labelBySentiment[sentiment]}</Badge>;
}
