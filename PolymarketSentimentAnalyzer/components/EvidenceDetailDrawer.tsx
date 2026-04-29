"use client";

import { ExternalLink, X } from "lucide-react";
import { SentimentBadge } from "@/components/SentimentBadge";
import { Button } from "@/components/ui/button";
import type { EvidenceItem } from "@/lib/types";
import { formatDateTime, isValidExternalUrl } from "@/lib/utils";

export function EvidenceDetailDrawer({
  evidence,
  onClose
}: {
  evidence?: EvidenceItem | null;
  onClose: () => void;
}) {
  if (!evidence) return null;
  const canOpenSource = isValidExternalUrl(evidence.url);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/30">
      <button
        type="button"
        aria-label="Close evidence details"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
      />
      <aside className="relative h-full w-full max-w-xl overflow-y-auto bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Evidence detail
            </p>
            <h2 className="mt-2 text-xl font-semibold leading-7">
              {evidence.title}
            </h2>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose}>
            <X className="size-5" aria-hidden="true" />
            <span className="sr-only">Close</span>
          </Button>
        </div>

        <div className="space-y-4 text-sm leading-6">
          <div className="flex flex-wrap items-center gap-2">
            <SentimentBadge sentiment={evidence.sentimentForYes} />
            {evidence.isFallback ? (
              <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
                fallback demo
              </span>
            ) : null}
          </div>

          <dl className="grid gap-3 rounded-md border bg-muted/40 p-3">
            <div>
              <dt className="text-xs font-medium text-muted-foreground">Source</dt>
              <dd>{evidence.source}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted-foreground">
                Published
              </dt>
              <dd>{formatDateTime(evidence.publishedAt)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted-foreground">
                Confidence
              </dt>
              <dd>{(evidence.confidence * 100).toFixed(0)}%</dd>
            </div>
          </dl>

          <section>
            <h3 className="text-sm font-semibold">Matched keywords</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {evidence.matchedKeywords.length > 0 ? (
                evidence.matchedKeywords.map((keyword) => (
                  <span
                    key={keyword}
                    className="rounded-md border bg-white px-2 py-1 text-xs"
                  >
                    {keyword}
                  </span>
                ))
              ) : (
                <span className="text-muted-foreground">
                  No exact keyword match was returned.
                </span>
              )}
            </div>
          </section>

          <section>
            <h3 className="text-sm font-semibold">Summary</h3>
            <p className="mt-2 text-slate-700">{evidence.summary}</p>
          </section>

          <section>
            <h3 className="text-sm font-semibold">Sentiment reason</h3>
            <p className="mt-2 text-slate-700">{evidence.reason}</p>
          </section>

          <section>
            <h3 className="text-sm font-semibold">Original source URL</h3>
            <p className="mt-2 break-all text-muted-foreground">
              {canOpenSource ? evidence.url : "No valid real URL was available."}
            </p>
          </section>

          {canOpenSource ? (
            <Button asChild>
              <a href={evidence.url} target="_blank" rel="noreferrer">
                <ExternalLink className="size-4" aria-hidden="true" />
                Open Original Source
              </a>
            </Button>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
