"""
Stock price fetcher using Yahoo Finance's public chart API.
Returns the same price data Robinhood / brokers display (real market data).
"""
import requests
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}


def parse_publish_date(s):
    """Try several date formats common in RSS feeds."""
    if not s:
        return None
    s = s.strip()
    # RFC 2822 (most RSS feeds)
    try:
        dt = parsedate_to_datetime(s)
        return dt.replace(tzinfo=None)
    except Exception:
        pass
    # ISO 8601 variants
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.split("+")[0].split(".")[0].strip(), fmt)
        except ValueError:
            continue
    return None


def fetch_price_movement(ticker, publish_date_str, days_before=2, days_after=7):
    """
    Fetch daily closing prices for `ticker` around `publish_date_str`.
    Returns dict with before/after prices, change %, and daily points,
    or None if no data is available.
    """
    if not ticker:
        return None
    publish_date = parse_publish_date(publish_date_str) or datetime.now()
    start = publish_date - timedelta(days=days_before)
    # widen end to absorb weekends/holidays
    end = publish_date + timedelta(days=days_after + 3)

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
    params = {
        "period1": int(start.timestamp()),
        "period2": int(end.timestamp()),
        "interval": "1d",
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception as e:
        print(f"Price fetch error for {ticker}: {e}")
        return None

    chart = data.get("chart", {})
    if chart.get("error") or not chart.get("result"):
        return None

    result = chart["result"][0]
    timestamps = result.get("timestamp", [])
    indicators = result.get("indicators", {}).get("quote", [{}])[0]
    closes = indicators.get("close", [])

    points = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        points.append({
            "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
            "close": round(float(close), 2),
        })

    if len(points) < 2:
        return None

    # Find closest point ≤ publish_date as "before", and final available as "after"
    publish_str = publish_date.strftime("%Y-%m-%d")
    before_idx = 0
    for i, p in enumerate(points):
        if p["date"] <= publish_str:
            before_idx = i

    before = points[before_idx]["close"]
    after = points[-1]["close"]
    change = after - before
    change_pct = (change / before * 100) if before else 0

    return {
        "ticker": ticker.upper(),
        "publish_date": publish_str,
        "before_price": before,
        "after_price": after,
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "points": points,
    }
