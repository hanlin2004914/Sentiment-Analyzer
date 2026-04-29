"use client";

import { FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentBadge } from "@/components/SentimentBadge";
import { findPriceMovementAfterEvidence } from "@/lib/explanation";
import type { EvidenceItem, PricePoint } from "@/lib/types";
import { formatDateTime, formatSignedProbability } from "@/lib/utils";

export function NewsEvidenceTimeline({
  evidenceItems,
  priceSeries,
  onSelectEvidence
}: {
  evidenceItems: EvidenceItem[];
  priceSeries: PricePoint[];
  onSelectEvidence: (item: EvidenceItem) => void;
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>News Evidence Timeline</CardTitle>
        <p className="text-sm text-muted-foreground">
          Clicking an item opens details in this app. Original sources are only
          opened from the drawer.
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {evidenceItems.length === 0 ? (
            <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
              No evidence items appear inside this selected time window.
            </p>
          ) : null}
          {evidenceItems.map((item, index) => {
            const reaction = findPriceMovementAfterEvidence(item, priceSeries, 36);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectEvidence(item)}
                className="relative block w-full rounded-md border bg-white p-3 text-left transition-colors hover:bg-muted"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    {index + 1}. {formatDateTime(item.publishedAt)}
                  </span>
                  <SentimentBadge sentiment={item.sentimentForYes} />
                  {item.isFallback ? (
                    <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
                      fallback
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 flex items-start gap-2 text-sm font-semibold leading-5">
                  <FileText
                    className="mt-0.5 size-4 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                  {item.title}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.source} | confidence {(item.confidence * 100).toFixed(0)}%
                </p>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-700">
                  {item.summary}
                </p>
                <p className="mt-2 rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                  Following move: {formatSignedProbability(reaction.change)}
                </p>
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
