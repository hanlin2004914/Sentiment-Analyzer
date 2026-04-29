import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MethodologyCard } from "@/components/MethodologyCard";

const steps = [
  {
    title: "1. Resolve a Polymarket market",
    body: "The server routes call Polymarket Gamma endpoints to search markets and load metadata such as question, outcomes, volume, liquidity, end date, and rules."
  },
  {
    title: "2. Load YES probability movement",
    body: "The app requests CLOB price history for the YES token when available. If that fails, it labels the chart as a derived demo series based on real current price/change fields."
  },
  {
    title: "3. Retrieve news evidence",
    body: "The evidence route tries NewsAPI when NEWS_API_KEY is present, then GDELT, then Google News RSS. Items without valid real URLs are not shown as clickable sources."
  },
  {
    title: "4. Classify sentiment toward YES",
    body: "A rule-based classifier evaluates whether each article makes the YES outcome more likely, less likely, or not clearly affected."
  },
  {
    title: "5. Export benchmark examples",
    body: "The context bundle and benchmark panel serialize market metadata, price series, evidence, sentiment labels, difficulty, and explanation."
  }
];

export default function MethodologyPage() {
  return (
    <div className="space-y-6">
      <section className="max-w-4xl space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">Methodology</Badge>
          <Badge variant="outline">Research demo only</Badge>
        </div>
        <h1 className="text-3xl font-semibold tracking-normal">
          Transparent Research Methodology
        </h1>
        <p className="text-sm leading-7 text-muted-foreground">
          This dashboard is intended for research and benchmark dataset
          construction. It does not provide trading controls, wallet connection,
          order placement, or financial advice.
        </p>
      </section>

      <MethodologyCard />

      <section className="grid gap-4 md:grid-cols-2">
        {steps.map((step) => (
          <Card key={step.title}>
            <CardHeader>
              <CardTitle>{step.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-6 text-muted-foreground">
                {step.body}
              </p>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}
