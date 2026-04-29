import { NextResponse } from "next/server";
import { searchPolymarketMarkets } from "@/lib/polymarket";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q") ?? "";

  if (!query.trim()) {
    return NextResponse.json({ markets: [] });
  }

  try {
    const markets = await searchPolymarketMarkets(query);
    return NextResponse.json({ markets });
  } catch (error) {
    return NextResponse.json(
      {
        markets: [],
        error:
          error instanceof Error
            ? error.message
            : "Unable to search Polymarket markets."
      },
      { status: 502 }
    );
  }
}
