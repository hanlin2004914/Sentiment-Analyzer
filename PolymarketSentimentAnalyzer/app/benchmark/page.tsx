import { PolymarketDashboardWorkspace } from "@/components/PolymarketDashboardWorkspace";

export default function BenchmarkPage() {
  return (
    <div className="space-y-5">
      <section className="max-w-3xl space-y-3">
        <h1 className="text-3xl font-semibold tracking-normal">
          Benchmark Export
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          Export the selected Polymarket context as labeled benchmark JSON for
          sentiment evaluation datasets.
        </p>
      </section>
      <PolymarketDashboardWorkspace focus="benchmark" />
    </div>
  );
}
