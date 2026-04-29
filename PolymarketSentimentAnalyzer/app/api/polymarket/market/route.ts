import { NextResponse } from "next/server";
import {
  extractPolymarketSlug,
  getPolymarketMarketBySlug,
  getPolymarketMarketByUrl
} from "@/lib/polymarket";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const input = searchParams.get("input") ?? searchParams.get("slug") ?? "";

  if (!input.trim()) {
    return NextResponse.json(
      { error: "Missing Polymarket URL or slug." },
      { status: 400 }
    );
  }

  try {
    const market = input.includes("polymarket.com/")
      ? await getPolymarketMarketByUrl(input)
      : await getPolymarketMarketBySlug(extractPolymarketSlug(input));

    return NextResponse.json({ market });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Unable to load Polymarket market."
      },
      { status: 502 }
    );
  }
}
