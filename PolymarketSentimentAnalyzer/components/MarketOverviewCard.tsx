import { CalendarClock, Droplets, Landmark, Vote } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PolymarketMarket, PricePoint } from "@/lib/types";
import {
  calculatePriceChange,
  filterPriceSeriesByWindow,
  formatDateTime,
  formatProbability,
  formatSignedProbability,
  formatVolume
} from "@/lib/utils";

export function MarketOverviewCard({
  market,
  priceSeries
}: {
  market: PolymarketMarket;
  priceSeries: PricePoint[];
}) {
  const change24h = calculatePriceChange(
    filterPriceSeriesByWindow(priceSeries, "1D")
  );

  const metrics = [
    {
      label: "Current YES price",
      value: formatProbability(market.currentYesPrice),
      helper: `Outcome: ${market.yesOutcome}`,
      icon: Vote
    },
    {
      label: "24h change",
      value: formatSignedProbability(change24h.change),
      helper: `${formatProbability(change24h.startPrice)} to ${formatProbability(
        change24h.endPrice
      )}`,
      icon: Landmark
    },
    {
      label: "Volume",
      value: formatVolume(market.volume),
      helper: "Reported by Polymarket",
      icon: Landmark
    },
    {
      label: "Liquidity",
      value: formatVolume(market.liquidity),
      helper: "Reported by Polymarket",
      icon: Droplets
    }
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">Polymarket</Badge>
          <Badge variant="amber">{market.category}</Badge>
          {market.closed ? (
            <Badge variant="neutral">Closed</Badge>
          ) : (
            <Badge variant="positive">Active</Badge>
          )}
        </div>
        <CardTitle className="pt-2 text-xl leading-7">
          {market.question}
        </CardTitle>
        <p className="text-sm leading-6 text-muted-foreground">
          {market.resolutionRules}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <div key={metric.label} className="rounded-md border bg-white p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    {metric.label}
                  </p>
                  <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                </div>
                <p className="mt-2 text-xl font-semibold">{metric.value}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {metric.helper}
                </p>
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1">
            <CalendarClock className="size-3.5" aria-hidden="true" />
            Ends {formatDateTime(market.endDate)}
          </span>
          <span className="rounded-md bg-muted px-2 py-1">
            Outcomes: {market.outcomes.join(" / ")}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
