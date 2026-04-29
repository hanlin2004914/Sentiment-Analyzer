"use client";

import { useMemo, useState } from "react";
import { Check, Clipboard, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { exportBenchmarkExample } from "@/lib/explanation";
import type { MarketContextBundle } from "@/lib/types";

function downloadJson(filename: string, json: string) {
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function BenchmarkExportPanel({
  contextBundle
}: {
  contextBundle: MarketContextBundle;
}) {
  const [copied, setCopied] = useState(false);
  const benchmarkJson = useMemo(
    () => JSON.stringify(exportBenchmarkExample(contextBundle), null, 2),
    [contextBundle]
  );

  async function copyBenchmark() {
    await navigator.clipboard.writeText(benchmarkJson);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Benchmark Export</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Labeled question format for Polymarket sentiment benchmark sets.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={copyBenchmark}>
            {copied ? <Check /> : <Clipboard />}
            {copied ? "Copied" : "Copy"}
          </Button>
          <Button
            type="button"
            onClick={() =>
              downloadJson(
                `${contextBundle.market.slug || "polymarket-benchmark"}-benchmark.json`,
                benchmarkJson
              )
            }
          >
            <Download />
            Download
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <pre className="max-h-[420px] overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {benchmarkJson}
        </pre>
      </CardContent>
    </Card>
  );
}
