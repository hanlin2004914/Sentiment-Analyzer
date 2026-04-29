import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MethodologyCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Research Methodology</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm leading-7 text-muted-foreground">
        <p>
          The dashboard resolves a Polymarket market, retrieves YES probability
          movement, searches public news sources, and classifies each evidence
          item relative to the market&apos;s YES outcome.
        </p>
        <p>
          If CLOB price history is unavailable, the chart is explicitly labeled
          as a derived demo series created from real current price and reported
          change fields. It is not presented as real historical data.
        </p>
        <p>
          Sentiment classification is rule-based for the MVP. It answers whether
          the article makes YES more likely, less likely, or not clearly affected.
        </p>
      </CardContent>
    </Card>
  );
}
