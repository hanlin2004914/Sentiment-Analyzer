import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { PricePoint, TimeWindow } from "@/lib/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatProbability(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function formatSignedProbability(value: number) {
  const percentage = Math.round(value * 100);
  return `${percentage >= 0 ? "+" : ""}${percentage} pts`;
}

export function formatVolume(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
    notation: value >= 1000000 ? "compact" : "standard"
  }).format(value);
}

export function formatDateTime(value?: string) {
  if (!value) return "Unknown time";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

export function isValidExternalUrl(value?: string) {
  if (!value) return false;
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    return (
      ["http:", "https:"].includes(url.protocol) &&
      !host.endsWith("example.com") &&
      host !== "localhost" &&
      host !== "127.0.0.1"
    );
  } catch {
    return false;
  }
}

export function getTimeWindowHours(timeWindow: TimeWindow) {
  if (timeWindow === "1D") return 24;
  if (timeWindow === "7D") return 24 * 7;
  if (timeWindow === "30D") return 24 * 30;
  return Number.POSITIVE_INFINITY;
}

export function filterPriceSeriesByWindow(
  priceSeries: PricePoint[],
  timeWindow: TimeWindow
) {
  if (timeWindow === "All" || priceSeries.length === 0) return priceSeries;
  const lastTimestamp = new Date(priceSeries[priceSeries.length - 1].timestamp);
  const cutoff =
    lastTimestamp.getTime() - getTimeWindowHours(timeWindow) * 60 * 60 * 1000;
  return priceSeries.filter(
    (point) => new Date(point.timestamp).getTime() >= cutoff
  );
}

export function calculatePriceChange(priceSeries: PricePoint[]) {
  if (priceSeries.length < 2) {
    const price = priceSeries[0]?.yesPrice ?? 0;
    return { startPrice: price, endPrice: price, change: 0 };
  }

  const startPrice = priceSeries[0].yesPrice;
  const endPrice = priceSeries[priceSeries.length - 1].yesPrice;
  return { startPrice, endPrice, change: endPrice - startPrice };
}
