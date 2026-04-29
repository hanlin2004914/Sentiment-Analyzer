import Link from "next/link";
import { ArrowRight, FileJson, LineChart, Newspaper } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MethodologyCard } from "@/components/MethodologyCard";

const featureCards = [
  {
    title: "Polymarket market resolution",
    description:
      "Search by keyword, URL, or slug and load market metadata from Polymarket server-side routes.",
    icon: LineChart
  },
  {
    title: "Real news evidence",
    description:
      "Use NewsAPI when configured, GDELT, and RSS fallback sources to retrieve articles with real URLs.",
    icon: Newspaper
  },
  {
    title: "Benchmark export",
    description:
      "Turn market context, evidence, sentiment labels, and explanation into benchmark JSON.",
    icon: FileJson
  }
];

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="max-w-5xl space-y-5">
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">Polymarket only</Badge>
          <Badge variant="amber">Research dashboard</Badge>
          <Badge variant="outline">No trading functionality</Badge>
        </div>
        <div className="space-y-4">
          <h1 className="text-3xl font-semibold tracking-normal sm:text-5xl">
            Polymarket Sentiment vs Price Movement Dashboard
          </h1>
          <p className="max-w-3xl text-base leading-7 text-muted-foreground">
            A research/demo website for studying whether external news evidence
            aligns with Polymarket YES price movement, then exporting the result
            as a benchmark-ready sentiment question.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/dashboard">
              Open dashboard
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/markets">Search markets</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {featureCards.map((feature) => {
          const Icon = feature.icon;
          return (
            <Card key={feature.title}>
              <CardHeader>
                <div className="mb-3 flex size-10 items-center justify-center rounded-md bg-sky-50 text-sky-700">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <CardTitle>{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-muted-foreground">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <MethodologyCard />
    </div>
  );
}
