"use client";

import { FormEvent, useState } from "react";
import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { PolymarketSearchResult } from "@/lib/types";
import { formatProbability, formatVolume } from "@/lib/utils";

const starterQueries = ["bitcoin", "election", "fed rates", "nba"];

export function PolymarketSearchInput({
  onMarketSelect,
  compact = false
}: {
  onMarketSelect: (slugOrUrl: string) => void;
  compact?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PolymarketSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(
    "Paste a Polymarket URL/slug or search by keyword."
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      setMessage("Enter a Polymarket market URL, slug, or keyword.");
      return;
    }

    setLoading(true);
    setMessage("Searching Polymarket...");

    try {
      const response = await fetch(
        `/api/polymarket/search?q=${encodeURIComponent(trimmed)}`
      );
      const data = (await response.json()) as {
        markets?: PolymarketSearchResult[];
        error?: string;
      };
      if (!response.ok) throw new Error(data.error ?? "Search failed.");
      setResults(data.markets ?? []);
      if ((data.markets ?? []).length === 1) {
        onMarketSelect(data.markets![0].slug);
      }
      setMessage(
        (data.markets ?? []).length > 0
          ? "Select a market below or search again."
          : "No Polymarket markets were returned for that query."
      );
    } catch (error) {
      setResults([]);
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to search Polymarket right now."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border bg-card p-4 shadow-research">
      <form onSubmit={handleSubmit} className="grid gap-3">
        <label className="text-sm font-medium" htmlFor="polymarket-query">
          Polymarket market input
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="polymarket-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="will-bitcoin-hit-150k-by-june-30-2026"
              className="pl-9"
            />
          </div>
          <Button type="submit" disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {starterQueries.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setQuery(item);
                setResults([]);
              }}
              className="rounded-md border px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              {item}
            </button>
          ))}
        </div>
        <p className="text-sm text-muted-foreground">{message}</p>
      </form>

      {results.length > 0 && !compact ? (
        <div className="mt-4 grid gap-2">
          {results.map((market) => (
            <button
              key={market.slug}
              type="button"
              onClick={() => onMarketSelect(market.slug)}
              className="rounded-md border p-3 text-left transition-colors hover:bg-muted"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">Polymarket</Badge>
                <Badge variant="amber">{market.category}</Badge>
                {market.closed ? (
                  <Badge variant="neutral">Closed</Badge>
                ) : (
                  <Badge variant="positive">Active</Badge>
                )}
              </div>
              <p className="mt-2 text-sm font-semibold">{market.question}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                YES {formatProbability(market.currentYesPrice)} | Volume{" "}
                {formatVolume(market.volume)} | Liquidity{" "}
                {formatVolume(market.liquidity)}
              </p>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
