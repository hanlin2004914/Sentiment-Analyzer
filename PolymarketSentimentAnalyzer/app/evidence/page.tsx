import { PolymarketDashboardWorkspace } from "@/components/PolymarketDashboardWorkspace";

export default function EvidenceExplorerPage() {
  return (
    <div className="space-y-5">
      <section className="max-w-3xl space-y-3">
        <h1 className="text-3xl font-semibold tracking-normal">
          Evidence Explorer
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          Review retrieved news evidence, sentiment labels, confidence scores,
          and classification reasons without leaving the app.
        </p>
      </section>
      <PolymarketDashboardWorkspace focus="evidence" />
    </div>
  );
}
