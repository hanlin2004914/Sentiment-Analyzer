"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BenchmarkExportPanel } from "@/components/BenchmarkExportPanel";
import { EvidenceDetailDrawer } from "@/components/EvidenceDetailDrawer";
import { ExplanationCard } from "@/components/ExplanationCard";
import { MarketContextBundlePanel } from "@/components/MarketContextBundlePanel";
import { MarketOverviewCard } from "@/components/MarketOverviewCard";
import { NewsEvidenceTimeline } from "@/components/NewsEvidenceTimeline";
import { PolymarketSearchInput } from "@/components/PolymarketSearchInput";
import { PriceMovementChart } from "@/components/PriceMovementChart";
import {
  generateMarketExplanation,
  summarizeEvidenceSentiment
} from "@/lib/explanation";
import type {
  EvidenceItem,
  MarketContextBundle,
  PolymarketMarket,
  PricePoint,
  PriceSeriesSource,
  TimeWindow
} from "@/lib/types";
import { filterPriceSeriesByWindow, getTimeWindowHours } from "@/lib/utils";

const defaultMarketSlug = "will-bitcoin-hit-150k-by-june-30-2026";

async function fetchJson<T>(url: string, init?: RequestInit) {
  const response = await fetch(url, init);
  const data = (await response.json()) as T & { error?: string };
  if (!response.ok) throw new Error(data.error ?? "Request failed.");
  return data;
}

function filterEvidenceByWindow(
  evidenceItems: EvidenceItem[],
  priceSeries: PricePoint[],
  timeWindow: TimeWindow
) {
  if (timeWindow === "All" || priceSeries.length === 0) return evidenceItems;
  const lastTimestamp = new Date(priceSeries[priceSeries.length - 1].timestamp);
  const cutoff =
    lastTimestamp.getTime() - getTimeWindowHours(timeWindow) * 60 * 60 * 1000;
  return evidenceItems.filter(
    (item) => new Date(item.timestamp).getTime() >= cutoff
  );
}

function newsStartDate() {
  return new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
}

export function PolymarketDashboardWorkspace({
  initialMarketInput = defaultMarketSlug,
  focus = "full"
}: {
  initialMarketInput?: string;
  focus?: "full" | "evidence" | "benchmark";
}) {
  const [market, setMarket] = useState<PolymarketMarket | null>(null);
  const [priceSeries, setPriceSeries] = useState<PricePoint[]>([]);
  const [priceSeriesSource, setPriceSeriesSource] =
    useState<PriceSeriesSource>("derived-demo");
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);
  const [selectedTimeWindow, setSelectedTimeWindow] =
    useState<TimeWindow>("7D");
  const [selectedEvidence, setSelectedEvidence] =
    useState<EvidenceItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("Ready to load a Polymarket market.");
  const [error, setError] = useState<string | null>(null);

  async function loadMarket(input: string) {
    setLoading(true);
    setError(null);
    setStatus("Resolving Polymarket market...");

    try {
      const marketResponse = await fetchJson<{ market: PolymarketMarket }>(
        `/api/polymarket/market?input=${encodeURIComponent(input)}`
      );
      const resolvedMarket = marketResponse.market;
      setMarket(resolvedMarket);
      setStatus("Fetching price history and news evidence...");

      const [historyResponse, newsResponse] = await Promise.all([
        fetchJson<{ source: PriceSeriesSource; points: PricePoint[] }>(
          `/api/polymarket/price-history?slug=${encodeURIComponent(
            resolvedMarket.slug
          )}&tokenId=${encodeURIComponent(resolvedMarket.yesTokenId ?? "")}`
        ),
        fetchJson<{ evidenceItems: EvidenceItem[] }>("/api/news/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            marketQuestion: resolvedMarket.question,
            category: resolvedMarket.category,
            startDate: newsStartDate(),
            endDate: new Date().toISOString(),
            yesOutcome: resolvedMarket.yesOutcome,
            noOutcome: resolvedMarket.noOutcome
          })
        })
      ]);

      setPriceSeries(historyResponse.points);
      setPriceSeriesSource(historyResponse.source);
      setEvidenceItems(newsResponse.evidenceItems);
      setStatus(
        historyResponse.source === "clob-history"
          ? "Loaded Polymarket metadata, CLOB price history, and retrieved news evidence."
          : "Loaded Polymarket metadata and news evidence. Price series is demo-derived from real current/change fields."
      );
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load dashboard data."
      );
      setStatus("Loading failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadMarket(initialMarketInput);
    // Run only for the initial route query/default.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMarketInput]);

  const filteredPriceSeries = useMemo(
    () => filterPriceSeriesByWindow(priceSeries, selectedTimeWindow),
    [priceSeries, selectedTimeWindow]
  );
  const filteredEvidence = useMemo(
    () =>
      filterEvidenceByWindow(evidenceItems, priceSeries, selectedTimeWindow),
    [evidenceItems, priceSeries, selectedTimeWindow]
  );
  const explanation = useMemo(
    () =>
      market
        ? generateMarketExplanation({
            market,
            priceSeries: filteredPriceSeries,
            evidenceItems: filteredEvidence
          })
        : "Load a market to generate an explanation.",
    [market, filteredPriceSeries, filteredEvidence]
  );
  const detectedSentiment = useMemo(
    () => summarizeEvidenceSentiment(filteredEvidence),
    [filteredEvidence]
  );

  const contextBundle: MarketContextBundle | null = useMemo(() => {
    if (!market) return null;
    return {
      platform: "Polymarket",
      market,
      priceSeries: filteredPriceSeries,
      priceSeriesSource,
      evidenceItems: filteredEvidence,
      selectedTimeWindow,
      detectedSentimentSummary: detectedSentiment,
      explanation
    };
  }, [
    market,
    filteredPriceSeries,
    priceSeriesSource,
    filteredEvidence,
    selectedTimeWindow,
    detectedSentiment,
    explanation
  ]);

  return (
    <div className="space-y-5">
      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">Polymarket only</Badge>
          <Badge variant="outline">Research demo</Badge>
          {priceSeriesSource === "derived-demo" ? (
            <Badge variant="amber">derived price fallback</Badge>
          ) : (
            <Badge variant="positive">CLOB price history</Badge>
          )}
        </div>
        <div className="max-w-4xl">
          <h1 className="text-2xl font-semibold tracking-normal sm:text-3xl">
            Polymarket Sentiment vs Price Movement Dashboard
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Search a Polymarket market, retrieve public news evidence, classify
            sentiment toward YES, and export benchmark-ready research objects.
            No trading, wallet connection, order placement, or financial advice
            functionality is included.
          </p>
        </div>
      </section>

      <PolymarketSearchInput onMarketSelect={loadMarket} />

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-3 text-sm shadow-research">
        <div className="flex items-center gap-2 text-muted-foreground">
          {error ? (
            <AlertCircle className="size-4 text-destructive" aria-hidden="true" />
          ) : (
            <RefreshCw
              className={loading ? "size-4 animate-spin" : "size-4"}
              aria-hidden="true"
            />
          )}
          <span>{error ?? status}</span>
        </div>
        {market ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => loadMarket(market.slug)}
            disabled={loading}
          >
            Refresh data
          </Button>
        ) : null}
      </div>

      {market && contextBundle ? (
        <>
          {focus !== "benchmark" ? (
            <>
              <MarketOverviewCard market={market} priceSeries={priceSeries} />

              <section className="grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]">
                <PriceMovementChart
                  priceSeries={filteredPriceSeries}
                  evidenceItems={filteredEvidence}
                  priceSeriesSource={priceSeriesSource}
                  selectedTimeWindow={selectedTimeWindow}
                  onTimeWindowChange={setSelectedTimeWindow}
                />
                <NewsEvidenceTimeline
                  evidenceItems={filteredEvidence}
                  priceSeries={filteredPriceSeries}
                  onSelectEvidence={setSelectedEvidence}
                />
              </section>

              <ExplanationCard
                explanation={explanation}
                detectedSentiment={detectedSentiment}
              />
            </>
          ) : null}

          {focus !== "evidence" ? (
            <section className="grid gap-5 xl:grid-cols-2">
              <MarketContextBundlePanel contextBundle={contextBundle} />
              <BenchmarkExportPanel contextBundle={contextBundle} />
            </section>
          ) : null}
        </>
      ) : (
        <div className="rounded-lg border border-dashed bg-white p-8 text-center text-sm text-muted-foreground">
          Search for a Polymarket market to start the research workflow.
        </div>
      )}

      <EvidenceDetailDrawer
        evidence={selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
      />
    </div>
  );
}
