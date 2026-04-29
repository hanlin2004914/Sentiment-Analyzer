import { NextResponse } from "next/server";
import {
  getPolymarketMarketBySlug,
  getPolymarketPriceHistory
} from "@/lib/polymarket";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const slug = searchParams.get("slug") ?? "";
  const marketId = searchParams.get("marketId") ?? "";
  const tokenId = searchParams.get("tokenId") ?? "";
  const interval =
    (searchParams.get("interval") as "1d" | "1w" | "1m" | "max" | "all") ??
    "1m";

  if (!slug && !marketId && !tokenId) {
    return NextResponse.json(
      { error: "Missing market slug, market id, or YES token id." },
      { status: 400 }
    );
  }

  try {
    const market = slug ? await getPolymarketMarketBySlug(slug) : undefined;
    const history = await getPolymarketPriceHistory(marketId || tokenId, {
      yesTokenId: tokenId || market?.yesTokenId,
      market,
      interval
    });

    return NextResponse.json(history);
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Unable to load price history."
      },
      { status: 502 }
    );
  }
}
