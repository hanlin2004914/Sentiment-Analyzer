import type {
  MarketCategory,
  PolymarketMarket,
  PolymarketSearchResult,
  PricePoint,
  PriceSeriesSource
} from "@/lib/types";

const GAMMA_API = "https://gamma-api.polymarket.com";
const CLOB_API = "https://clob.polymarket.com";

function parseJsonArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value !== "string") return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

function toNumber(value: unknown, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function optionalNumber(value: unknown) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : undefined;
}

function normalizeCategory(value: unknown): MarketCategory {
  const label = String(value ?? "").toLowerCase();
  if (label.includes("politic") || label.includes("election")) return "Political";
  if (label.includes("crypto") || label.includes("bitcoin")) return "Crypto";
  if (label.includes("sport") || label.includes("nba") || label.includes("nfl")) {
    return "Sports";
  }
  if (label.includes("finance") || label.includes("econom")) return "Finance";
  if (label.includes("tech") || label.includes("ai")) return "Tech";
  return "Other";
}

export function extractPolymarketSlug(input: string) {
  const trimmed = input.trim();
  if (!trimmed) return "";

  try {
    const url = new URL(trimmed);
    const parts = url.pathname.split("/").filter(Boolean);
    return parts[parts.length - 1] ?? "";
  } catch {
    return (
      trimmed
        .replace(/^https?:\/\/(www\.)?polymarket\.com\//, "")
        .split("?")[0]
        .split("/")
        .filter(Boolean)
        .pop() ?? trimmed
    );
  }
}

export function normalizePolymarketMarket(rawMarket: Record<string, unknown>) {
  const outcomes = parseJsonArray(rawMarket.outcomes);
  const outcomePrices = parseJsonArray(rawMarket.outcomePrices).map((value) =>
    toNumber(value)
  );
  const clobTokenIds = parseJsonArray(rawMarket.clobTokenIds);
  const yesIndex = Math.max(
    0,
    outcomes.findIndex((outcome) => outcome.toLowerCase() === "yes")
  );
  const noIndex = Math.max(
    0,
    outcomes.findIndex((outcome) => outcome.toLowerCase() === "no")
  );
  const fallbackPrice =
    optionalNumber(rawMarket.lastTradePrice) ??
    optionalNumber(rawMarket.bestAsk) ??
    optionalNumber(rawMarket.bestBid) ??
    0;
  const currentYesPrice = outcomePrices[yesIndex] ?? fallbackPrice;
  const slug = String(rawMarket.slug ?? "");
  const question = String(rawMarket.question ?? rawMarket.title ?? slug);

  const market: PolymarketMarket = {
    id: String(rawMarket.id ?? rawMarket.conditionId ?? slug),
    slug,
    question,
    category: normalizeCategory(rawMarket.category ?? rawMarket.question),
    outcomes: outcomes.length > 0 ? outcomes : ["Yes", "No"],
    yesOutcome: outcomes[yesIndex] ?? "Yes",
    noOutcome: outcomes[noIndex] ?? "No",
    resolutionRules: String(
      rawMarket.description ??
        rawMarket.resolutionSource ??
        "Resolution rules were not provided by the market metadata response."
    ),
    description:
      typeof rawMarket.description === "string" ? rawMarket.description : undefined,
    currentYesPrice,
    volume: toNumber(rawMarket.volumeNum ?? rawMarket.volume),
    liquidity: toNumber(rawMarket.liquidityNum ?? rawMarket.liquidity),
    startDate: String(rawMarket.startDate ?? rawMarket.startDateIso ?? ""),
    endDate: String(rawMarket.endDate ?? rawMarket.endDateIso ?? ""),
    clobTokenIds,
    yesTokenId: clobTokenIds[yesIndex],
    active: Boolean(rawMarket.active),
    closed: Boolean(rawMarket.closed),
    url: `https://polymarket.com/event/${slug}`,
    oneDayPriceChange: optionalNumber(rawMarket.oneDayPriceChange),
    oneWeekPriceChange: optionalNumber(rawMarket.oneWeekPriceChange),
    oneMonthPriceChange: optionalNumber(rawMarket.oneMonthPriceChange)
  };

  return market;
}

function toSearchResult(market: PolymarketMarket): PolymarketSearchResult {
  return {
    id: market.id,
    slug: market.slug,
    question: market.question,
    category: market.category,
    currentYesPrice: market.currentYesPrice,
    volume: market.volume,
    liquidity: market.liquidity,
    endDate: market.endDate,
    active: market.active,
    closed: market.closed
  };
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: { accept: "application/json" },
    next: { revalidate: 60 }
  });

  if (!response.ok) {
    throw new Error(`Polymarket request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function searchPolymarketMarkets(query: string) {
  const input = query.trim();
  if (!input) return [];

  if (input.includes("polymarket.com/") || /^[a-z0-9-]+$/i.test(input)) {
    try {
      const market = await getPolymarketMarketBySlug(extractPolymarketSlug(input));
      return [toSearchResult(market)];
    } catch {
      // Continue to keyword search for non-slug inputs such as "bitcoin".
    }
  }

  const url = new URL(`${GAMMA_API}/public-search`);
  url.searchParams.set("q", input);
  url.searchParams.set("limit_per_type", "8");
  url.searchParams.set("search_profiles", "false");
  url.searchParams.set("keep_closed_markets", "0");

  const data = await fetchJson<{
    events?: Array<{ markets?: Array<Record<string, unknown>> }>;
  }>(url.toString());
  const seen = new Set<string>();

  return (
    data.events
      ?.flatMap((event) => event.markets ?? [])
      .map(normalizePolymarketMarket)
      .filter((market) => {
        if (!market.slug || seen.has(market.slug)) return false;
        seen.add(market.slug);
        return true;
      })
      .sort((a, b) => {
        if (a.closed !== b.closed) return a.closed ? 1 : -1;
        return b.volume - a.volume;
      })
      .slice(0, 12)
      .map(toSearchResult) ?? []
  );
}

export async function getPolymarketMarketBySlug(slug: string) {
  const cleanSlug = extractPolymarketSlug(slug);
  const data = await fetchJson<Record<string, unknown>>(
    `${GAMMA_API}/markets/slug/${encodeURIComponent(cleanSlug)}`
  );
  return normalizePolymarketMarket(data);
}

export async function getPolymarketMarketByUrl(url: string) {
  return getPolymarketMarketBySlug(extractPolymarketSlug(url));
}

function derivedPriceSeries(market: PolymarketMarket): {
  source: PriceSeriesSource;
  points: PricePoint[];
} {
  const now = Date.now();
  const current = market.currentYesPrice || 0.5;
  const monthStart = Math.max(
    0.01,
    Math.min(0.99, current - (market.oneMonthPriceChange ?? 0))
  );
  const weekStart = Math.max(
    0.01,
    Math.min(0.99, current - (market.oneWeekPriceChange ?? 0))
  );
  const dayStart = Math.max(
    0.01,
    Math.min(0.99, current - (market.oneDayPriceChange ?? 0))
  );

  return {
    source: "derived-demo",
    points: [
      {
        timestamp: new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString(),
        yesPrice: monthStart,
        source: "derived-demo"
      },
      {
        timestamp: new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString(),
        yesPrice: weekStart,
        source: "derived-demo"
      },
      {
        timestamp: new Date(now - 24 * 60 * 60 * 1000).toISOString(),
        yesPrice: dayStart,
        source: "derived-demo"
      },
      {
        timestamp: new Date(now).toISOString(),
        yesPrice: current,
        source: "derived-demo"
      }
    ]
  };
}

export async function getPolymarketPriceHistory(
  marketId: string,
  options?: {
    yesTokenId?: string;
    market?: PolymarketMarket;
    interval?: "1d" | "1w" | "1m" | "max" | "all";
  }
) {
  const tokenId = options?.yesTokenId ?? marketId;

  if (tokenId) {
    const url = new URL(`${CLOB_API}/prices-history`);
    url.searchParams.set("market", tokenId);
    url.searchParams.set("interval", options?.interval ?? "1m");
    url.searchParams.set("fidelity", "60");

    try {
      const data = await fetchJson<{ history?: Array<{ t: number; p: number }> }>(
        url.toString()
      );
      const points =
        data.history
          ?.map((point) => ({
            timestamp: new Date(point.t * 1000).toISOString(),
            yesPrice: Math.max(0, Math.min(1, Number(point.p))),
            source: "clob-history" as const
          }))
          .filter((point) => Number.isFinite(point.yesPrice)) ?? [];

      if (points.length > 1) {
        return { source: "clob-history" as const, points };
      }
    } catch {
      // TODO: Add retry/backoff and richer CLOB error telemetry for production.
    }
  }

  // TODO: Replace this fallback with persisted historical snapshots when CLOB
  // history is unavailable for a token. The returned series is derived from
  // real current/change fields and must remain labeled as demo-derived.
  return derivedPriceSeries(
    options?.market ?? {
      id: marketId,
      slug: marketId,
      question: marketId,
      category: "Other",
      outcomes: ["Yes", "No"],
      yesOutcome: "Yes",
      noOutcome: "No",
      resolutionRules: "",
      currentYesPrice: 0.5,
      volume: 0,
      liquidity: 0,
      clobTokenIds: [],
      active: false,
      closed: false,
      url: ""
    }
  );
}
