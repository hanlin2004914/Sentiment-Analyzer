import { XMLParser } from "fast-xml-parser";
import type { EvidenceItem, NewsSearchInput } from "@/lib/types";
import { classifyEvidenceForYes } from "@/lib/sentiment";
import { isValidExternalUrl } from "@/lib/utils";

const stopWords = new Set([
  "will",
  "the",
  "and",
  "for",
  "with",
  "from",
  "this",
  "that",
  "market",
  "resolve",
  "hit",
  "reach",
  "reaches",
  "reached",
  "dip",
  "dips",
  "price",
  "above",
  "below",
  "over",
  "under",
  "before",
  "after",
  "april",
  "may",
  "june",
  "july",
  "august",
  "september",
  "october",
  "november",
  "december",
  "january",
  "february",
  "march"
]);

export function extractNewsKeywords(marketQuestion: string) {
  const cleaned = marketQuestion
    .replace(/[^\w\s$.-]/g, " ")
    .split(/\s+/)
    .map((word) => word.trim())
    .filter(Boolean)
    .filter((word) => word.length > 2)
    .filter((word) => !stopWords.has(word.toLowerCase()));

  return Array.from(new Set(cleaned)).slice(0, 8);
}

function getMatchedKeywords(title: string, summary: string, keywords: string[]) {
  const haystack = `${title} ${summary}`.toLowerCase();
  return keywords.filter((keyword) => haystack.includes(keyword.toLowerCase()));
}

function buildQuery(input: NewsSearchInput) {
  return input.keywords && input.keywords.length > 0
    ? input.keywords
    : extractNewsKeywords(input.marketQuestion);
}

function toGdeltDate(value?: string) {
  const date = value
    ? new Date(value)
    : new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  const yyyy = date.getUTCFullYear();
  const mm = String(date.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(date.getUTCDate()).padStart(2, "0");
  const hh = String(date.getUTCHours()).padStart(2, "0");
  const mi = String(date.getUTCMinutes()).padStart(2, "0");
  const ss = String(date.getUTCSeconds()).padStart(2, "0");
  return `${yyyy}${mm}${dd}${hh}${mi}${ss}`;
}

async function fetchNewsApi(input: NewsSearchInput, keywords: string[]) {
  const apiKey = process.env.NEWS_API_KEY;
  if (!apiKey) return [];

  const url = new URL("https://newsapi.org/v2/everything");
  url.searchParams.set("q", keywords.slice(0, 5).join(" OR "));
  url.searchParams.set("language", "en");
  url.searchParams.set("sortBy", "publishedAt");
  url.searchParams.set("pageSize", "12");
  if (input.startDate) url.searchParams.set("from", input.startDate.slice(0, 10));
  if (input.endDate) url.searchParams.set("to", input.endDate.slice(0, 10));

  const response = await fetch(url, {
    headers: { "X-Api-Key": apiKey },
    next: { revalidate: 300 }
  });
  if (!response.ok) return [];
  const data = (await response.json()) as {
    articles?: Array<{
      title?: string;
      description?: string;
      content?: string;
      url?: string;
      publishedAt?: string;
      source?: { name?: string };
    }>;
  };

  return (
    data.articles?.map((article, index) =>
      toEvidenceItem({
        input,
        title: article.title,
        source: article.source?.name,
        url: article.url,
        publishedAt: article.publishedAt,
        summary: article.description ?? article.content,
        keywords,
        idPrefix: "newsapi",
        index,
        dataSource: "newsapi"
      })
    ) ?? []
  ).filter(Boolean) as EvidenceItem[];
}

async function fetchGdelt(input: NewsSearchInput, keywords: string[]) {
  const url = new URL("https://api.gdeltproject.org/api/v2/doc/doc");
  const query = keywords
    .slice(0, 4)
    .map((keyword) => (keyword.includes(" ") ? `"${keyword}"` : keyword))
    .join(" ");
  url.searchParams.set("query", query);
  url.searchParams.set("mode", "artlist");
  url.searchParams.set("format", "json");
  url.searchParams.set("sort", "datedesc");
  url.searchParams.set("maxrecords", "12");
  if (input.startDate || input.endDate) {
    url.searchParams.set("startdatetime", toGdeltDate(input.startDate));
    url.searchParams.set("enddatetime", toGdeltDate(input.endDate));
  } else {
    url.searchParams.set("timespan", "1week");
  }

  const response = await fetch(url, { next: { revalidate: 300 } });
  if (!response.ok) return [];
  const data = (await response.json().catch(() => null)) as
    | {
        articles?: Array<{
          title?: string;
          url?: string;
          domain?: string;
          seendate?: string;
          sourcecountry?: string;
        }>;
      }
    | null;

  return (
    data?.articles?.map((article, index) =>
      toEvidenceItem({
        input,
        title: article.title,
        source: article.domain,
        url: article.url,
        publishedAt: article.seendate,
        summary: article.sourcecountry
          ? `GDELT article match from ${article.sourcecountry}.`
          : "GDELT article match.",
        keywords,
        idPrefix: "gdelt",
        index,
        dataSource: "gdelt"
      })
    ) ?? []
  ).filter(Boolean) as EvidenceItem[];
}

async function fetchGoogleNewsRss(input: NewsSearchInput, keywords: string[]) {
  const url = new URL("https://news.google.com/rss/search");
  url.searchParams.set("q", keywords.slice(0, 6).join(" "));
  url.searchParams.set("hl", "en-US");
  url.searchParams.set("gl", "US");
  url.searchParams.set("ceid", "US:en");

  const response = await fetch(url, { next: { revalidate: 300 } });
  if (!response.ok) return [];
  const xml = await response.text();
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: "",
    textNodeName: "text"
  });
  const parsed = parser.parse(xml) as {
    rss?: {
      channel?: {
        item?: Array<{
          title?: string;
          link?: string;
          pubDate?: string;
          source?: string | { text?: string; url?: string };
          description?: string;
        }>;
      };
    };
  };
  const items = parsed.rss?.channel?.item ?? [];

  return items
    .slice(0, 12)
    .map((item, index) => {
      const source =
        typeof item.source === "string"
          ? item.source
          : item.source?.text ?? "Google News";
      return toEvidenceItem({
        input,
        title: item.title,
        source,
        url: item.link,
        publishedAt: item.pubDate,
        summary: item.description,
        keywords,
        idPrefix: "rss",
        index,
        dataSource: "rss"
      });
    })
    .filter(Boolean) as EvidenceItem[];
}

function stripHtml(value?: string) {
  return (value ?? "").replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

function parsePublishedAt(value?: string) {
  if (!value) return new Date();
  const normalized = value.trim();
  const compact = normalized.match(
    /^(\d{4})(\d{2})(\d{2})(?:T)?(\d{2})(\d{2})(\d{2})/
  );
  if (compact) {
    return new Date(
      Date.UTC(
        Number(compact[1]),
        Number(compact[2]) - 1,
        Number(compact[3]),
        Number(compact[4]),
        Number(compact[5]),
        Number(compact[6])
      )
    );
  }
  return new Date(normalized);
}

function toEvidenceItem({
  input,
  title,
  source,
  url,
  publishedAt,
  summary,
  keywords,
  idPrefix,
  index,
  dataSource
}: {
  input: NewsSearchInput;
  title?: string;
  source?: string;
  url?: string;
  publishedAt?: string;
  summary?: string;
  keywords: string[];
  idPrefix: string;
  index: number;
  dataSource: EvidenceItem["dataSource"];
}) {
  if (!title || !isValidExternalUrl(url)) return null;
  const realUrl = String(url);
  const cleanSummary = stripHtml(summary);
  const matchedKeywords = getMatchedKeywords(title, cleanSummary, keywords);
  if (matchedKeywords.length === 0) return null;
  const classification = classifyEvidenceForYes({
    marketQuestion: input.marketQuestion,
    yesOutcome: input.yesOutcome,
    noOutcome: input.noOutcome,
    evidenceTitle: title,
    evidenceSummary: cleanSummary
  });
  const date = parsePublishedAt(publishedAt);
  const timestamp = Number.isFinite(date.getTime())
    ? date.toISOString()
    : new Date().toISOString();

  return {
    id: `${idPrefix}-${index}-${Buffer.from(realUrl)
      .toString("base64url")
      .slice(0, 12)}`,
    title: stripHtml(title),
    source: source || new URL(realUrl).hostname,
    url: realUrl,
    publishedAt: timestamp,
    timestamp,
    summary: cleanSummary || "No article summary was returned by the source.",
    matchedKeywords,
    ...classification,
    dataSource
  } satisfies EvidenceItem;
}

function dedupeEvidence(items: EvidenceItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.url ?? ""}:${item.title}`.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function fallbackEvidence(input: NewsSearchInput, keywords: string[]) {
  const classification = classifyEvidenceForYes({
    marketQuestion: input.marketQuestion,
    yesOutcome: input.yesOutcome,
    noOutcome: input.noOutcome,
    evidenceTitle: `${keywords[0] ?? "Market"} background update`,
    evidenceSummary:
      "Live news retrieval did not return a usable source URL. This non-clickable item exists only to keep the benchmark pipeline demonstrable."
  });

  return [
    {
      id: "fallback-demo-evidence",
      title: "Fallback demo evidence: no live article returned",
      source: "Fallback demo mode",
      publishedAt: new Date().toISOString(),
      timestamp: new Date().toISOString(),
      summary:
        "No real news article with a valid URL was retrieved. This row is clearly labeled and should not be treated as real evidence.",
      matchedKeywords: keywords,
      ...classification,
      dataSource: "fallback-demo",
      isFallback: true
    } satisfies EvidenceItem
  ];
}

export async function searchNewsEvidence(input: NewsSearchInput) {
  const keywords = buildQuery(input);
  const batches = [
    await fetchNewsApi(input, keywords).catch(() => []),
    await fetchGdelt(input, keywords).catch(() => []),
    await fetchGoogleNewsRss(input, keywords).catch(() => [])
  ];
  const evidence = dedupeEvidence(batches.flat())
    .sort(
      (a, b) =>
        new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
    )
    .slice(0, 12);

  return evidence.length > 0 ? evidence : fallbackEvidence(input, keywords);
}
