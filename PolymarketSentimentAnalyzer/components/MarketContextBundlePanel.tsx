"use client";

import { useMemo, useState } from "react";
import { Check, Clipboard, Download, FileJson } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { exportBenchmarkExample } from "@/lib/explanation";
import type { MarketContextBundle } from "@/lib/types";
import { calculatePriceChange, filterPriceSeriesByWindow } from "@/lib/utils";

function serializeContext(contextBundle: MarketContextBundle) {
  return {
    platform: "Polymarket",
    market_id: contextBundle.market.id,
    market_slug: contextBundle.market.slug,
    market_question: contextBundle.market.question,
    yes_outcome: contextBundle.market.yesOutcome,
    no_outcome: contextBundle.market.noOutcome,
    resolution_rules: contextBundle.market.resolutionRules,
    current_yes_price: contextBundle.market.currentYesPrice,
    price_change_24h: calculatePriceChange(
      filterPriceSeriesByWindow(contextBundle.priceSeries, "1D")
    ).change,
    volume: contextBundle.market.volume,
    liquidity: contextBundle.market.liquidity,
    selected_time_window: contextBundle.selectedTimeWindow,
    price_series_source: contextBundle.priceSeriesSource,
    price_series: contextBundle.priceSeries,
    evidence_items: contextBundle.evidenceItems.map((item) => ({
      id: item.id,
      timestamp: item.timestamp,
      source: item.source,
      title: item.title,
      url: item.url,
      summary: item.summary,
      matched_keywords: item.matchedKeywords,
      sentiment_for_yes: item.sentimentForYes,
      confidence: item.confidence,
      reason: item.reason,
      data_source: item.dataSource,
      is_fallback: Boolean(item.isFallback)
    })),
    detected_sentiment_summary: contextBundle.detectedSentimentSummary,
    explanation: contextBundle.explanation
  };
}

function downloadJson(filename: string, json: string) {
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function MarketContextBundlePanel({
  contextBundle
}: {
  contextBundle: MarketContextBundle;
}) {
  const [copied, setCopied] = useState<"context" | "benchmark" | null>(null);
  const contextJson = useMemo(
    () => JSON.stringify(serializeContext(contextBundle), null, 2),
    [contextBundle]
  );
  const benchmarkJson = useMemo(
    () => JSON.stringify(exportBenchmarkExample(contextBundle), null, 2),
    [contextBundle]
  );

  async function copy(value: string, kind: "context" | "benchmark") {
    await navigator.clipboard.writeText(value);
    setCopied(kind);
    window.setTimeout(() => setCopied(null), 1400);
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Market Context Bundle</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Structured JSON for benchmark construction and downstream analysis.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={() => copy(contextJson, "context")}>
            {copied === "context" ? <Check /> : <Clipboard />}
            {copied === "context" ? "Copied" : "Copy JSON"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              downloadJson(
                `${contextBundle.market.slug || "polymarket-context"}.json`,
                contextJson
              )
            }
          >
            <Download />
            Download JSON
          </Button>
          <Button
            type="button"
            onClick={() => copy(benchmarkJson, "benchmark")}
          >
            {copied === "benchmark" ? <Check /> : <FileJson />}
            {copied === "benchmark" ? "Copied" : "Export Benchmark"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <pre className="max-h-[420px] overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {contextJson}
        </pre>
      </CardContent>
    </Card>
  );
}
