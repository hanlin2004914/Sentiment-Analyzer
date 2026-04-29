import { MarketSearchWorkspace } from "@/components/MarketSearchWorkspace";

export default function MarketsPage() {
  return (
    <div className="space-y-5">
      <section className="max-w-3xl space-y-3">
        <h1 className="text-3xl font-semibold tracking-normal">
          Market Search
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          Enter a Polymarket URL, market slug, or keyword. Resolved metadata is
          loaded from Polymarket through the app&apos;s server-side API routes.
        </p>
      </section>
      <MarketSearchWorkspace />
    </div>
  );
}
