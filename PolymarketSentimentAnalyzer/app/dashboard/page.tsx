import { PolymarketDashboardWorkspace } from "@/components/PolymarketDashboardWorkspace";

type DashboardPageProps = {
  searchParams?: Promise<{
    market?: string;
  }>;
};

export default async function DashboardPage({
  searchParams
}: DashboardPageProps) {
  const params = await (searchParams ??
    Promise.resolve<{ market?: string }>({}));

  return <PolymarketDashboardWorkspace initialMarketInput={params.market} />;
}
