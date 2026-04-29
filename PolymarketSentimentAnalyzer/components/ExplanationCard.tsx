import { Lightbulb } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentBadge } from "@/components/SentimentBadge";
import type { SentimentForYes } from "@/lib/types";

export function ExplanationCard({
  explanation,
  detectedSentiment
}: {
  explanation: string;
  detectedSentiment: SentimentForYes;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Sentiment vs Price Explanation</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Rule-based interpretation of retrieved evidence and following YES
            price movement.
          </p>
        </div>
        <Lightbulb className="size-5 text-amber-600" aria-hidden="true" />
      </CardHeader>
      <CardContent>
        <div className="mb-4">
          <SentimentBadge sentiment={detectedSentiment} />
        </div>
        <p className="text-sm leading-7 text-slate-700">{explanation}</p>
      </CardContent>
    </Card>
  );
}
