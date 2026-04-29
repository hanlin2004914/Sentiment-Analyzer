"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarketOverviewCard } from "@/components/MarketOverviewCard";
import { PolymarketSearchInput } from "@/components/PolymarketSearchInput";
import type { PolymarketMarket, PricePoint } from "@/lib/types";

async function fetchMarket(input: string) {
  const response = await fetch(
    `/api/polymarket/market?input=${encodeURIComponent(input)}`
  );
  const data = (await response.json()) as {
    market?: PolymarketMarket;
    error?: string;
  };
  if (!response.ok || !data.market) {
    throw new Error(data.error ?? "Unable to resolve Polymarket market.");
  }
  return data.market;
}

export function MarketSearchWorkspace() {
  const [market, setMarket] = useState<PolymarketMarket | null>(null);
  const [message, setMessage] = useState("No market selected yet.");
  const placeholderSeries: PricePoint[] = market
    ? [
        {
          timestamp: new Date().toISOString(),
          yesPrice: market.currentYesPrice
        }
      ]
    : [];

  async function handleSelect(input: string) {
    setMessage("Resolving market metadata from Polymarket...");
    try {
      const resolved = await fetchMarket(input);
      setMarket(resolved);
      setMessage("Market resolved. Open it in the dashboard to fetch news and price history.");
    } catch (error) {
      setMarket(null);
      setMessage(
        error instanceof Error ? error.message : "Unable to resolve market."
      );
    }
  }

  return (
    <div className="space-y-5">
      <PolymarketSearchInput onMarketSelect={handleSelect} />
      <Card>
        <CardHeader>
          <CardTitle>Resolved Market</CardTitle>
          <p className="text-sm text-muted-foreground">{message}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {market ? (
            <>
              <MarketOverviewCard market={market} priceSeries={placeholderSeries} />
              <Button asChild>
                <Link href={`/dashboard?market=${market.slug}`}>
                  Open in dashboard
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
            </>
          ) : (
            <p className="rounded-md border border-dashed p-5 text-sm text-muted-foreground">
              Search by keyword, slug, or URL to preview Polymarket metadata.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
