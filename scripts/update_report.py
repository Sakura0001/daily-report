"""Daily Report Generator — fetches real-time market data and generates index.html.

Data sources:
  - CoinGecko (crypto, USD)
  - 东方财富 push2 (A-stock indices, US indices, gold/silver, metals, stock hot, sector hot, concept hot)
  - 今日头条热榜 (news hot, stock news)
  - aihot.virxact.com (AI hot list)

No external Python dependencies — uses only stdlib (urllib, json, datetime, html).
"""

import urllib.request
import json
import datetime
import html as html_mod
import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily-report")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(BASE_DIR, "index.html")

# ─── User-Agent strings ───
UA_BROWSER = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
UA_AIHOT = UA_BROWSER + " aihot-skill/0.2.0"

# ─── Beijing timezone (UTC+8) ───
BJT_OFFSET = datetime.timedelta(hours=8)


def bjt_now():
    """Current Beijing time."""
    return datetime.datetime.now(datetime.timezone.utc) + BJT_OFFSET


def bjt_str(fmt="%Y年%m月%d日"):
    """Beijing time as formatted string."""
    return bjt_now().strftime(fmt)


def bjt_time_str():
    """Beijing time HH:MM string."""
    return bjt_now().strftime("%H:%M")


# ─── HTTP helpers ───

def _fetch_json(url, ua=UA_BROWSER, timeout=15):
    """Fetch URL and parse JSON. Returns dict/list or None on error."""
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception as exc:
        log.warning("Fetch failed %s: %s", url[:80], exc)
        return None


def _fetch_json_safe(url, ua=UA_BROWSER, delay=0.5):
    """Fetch with delay for rate-limiting. Returns parsed JSON or None."""
    time.sleep(delay)
    return _fetch_json(url, ua)


# ─── Data fetchers ───

def fetch_crypto():
    """CoinGecko: BTC/ETH/SOL/BNB/DOGE prices in USD + 24h change."""
    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&ids=bitcoin,ethereum,solana,binancecoin,dogecoin"
        "&order=market_cap_desc&per_page=5&page=1&sparkline=false"
        "&price_change_percentage=24h"
    )
    data = _fetch_json_safe(url, delay=0)
    if not data:
        return []
    return [
        {
            "symbol": item["symbol"].upper(),
            "price": item["current_price"],
            "change_pct": item.get("price_change_percentage_24h_in_currency", 0) or 0,
        }
        for item in data
    ]


def fetch_ai_hot():
    """aihot.virxact.com: top 10 AI news items."""
    since = (bjt_now() - datetime.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://aihot.virxact.com/api/public/items?mode=selected&since={since}&take=10"
    data = _fetch_json_safe(url, ua=UA_AIHOT, delay=0)
    if not data or not isinstance(data, dict):
        return []
    items = data.get("items", [])
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "category": item.get("category", ""),
            "summary": item.get("summary", ""),
            "selected": item.get("selected", False),
        }
        for item in items[:10]
    ]


def fetch_a_stock_indices():
    """东方财富: 上证/深证/创业板/沪深300."""
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        "?fltt=2&secids=1.000001,0.399001,0.399006,1.000300"
        "&fields=f2,f3,f4,f6,f12,f14"
    )
    data = _fetch_json_safe(url)
    if not data or "data" not in data or "diff" not in data["data"]:
        return []
    return [
        {
            "name": d.get("f14", ""),
            "value": d.get("f2", "-"),
            "change_pct": d.get("f3", 0),
        }
        for d in data["data"]["diff"]
    ]


def fetch_us_stock_indices():
    """东方财富: 标普500/纳斯达克/道琼斯."""
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        "?fltt=2&secids=100.SPX,100.NDX,100.DJIA"
        "&fields=f2,f3,f4,f6,f12,f14"
    )
    data = _fetch_json_safe(url)
    if not data or "data" not in data or "diff" not in data["data"]:
        return []
    return [
        {
            "name": d.get("f14", ""),
            "value": d.get("f2", "-"),
            "change_pct": d.get("f3", 0),
        }
        for d in data["data"]["diff"]
    ]


def fetch_gold_silver():
    """东方财富: 沪金/沪银主连 + K线昨日收盘."""
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        "?fltt=2&secids=113.aum,113.agm"
        "&fields=f2,f3,f4,f6,f12,f14"
    )
    data = _fetch_json_safe(url)
    if not data or "data" not in data or "diff" not in data["data"]:
        return []

    items = []
    for d in data["data"]["diff"]:
        code = d.get("f12", "")
        price = d.get("f2", 0)
        change_pct = d.get("f3", 0)
        # 白银单位是元/千克，需÷1000转为元/克
        unit = "元/克"
        display_price = price
        if code == "agm":
            display_price = round(price / 1000, 2) if price else 0
        # 反推昨收
        yesterday = round(price / (1 + change_pct / 100), 2) if price and change_pct else price
        if code == "agm":
            yesterday_display = round(yesterday / 1000, 2) if yesterday else 0
        else:
            yesterday_display = yesterday
        items.append({
            "name": d.get("f14", ""),
            "price": display_price,
            "unit": unit,
            "change_pct": change_pct,
            "yesterday": yesterday_display,
            "code": code,
        })
    return items


def fetch_metals():
    """东方财富期货: 沪铜/沪铝/沪锌/沪镍主连 (直接secids查询)."""
    # 直接查询4个期货主连品种，而非遍历全市场
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        "?fltt=2&secids=113.cum,113.alm,113.znm,113.nim"
        "&fields=f2,f3,f4,f6,f12,f14"
    )
    data = _fetch_json_safe(url)
    if not data or "data" not in data or "diff" not in data["data"]:
        return []

    items = []
    for d in data["data"]["diff"]:
        code = d.get("f12", "")
        price = d.get("f2", 0)
        change_pct = d.get("f3", 0)
        yesterday = round(price / (1 + change_pct / 100), 0) if price and change_pct else price
        items.append({
            "name": d.get("f14", ""),
            "price": price,
            "unit": "元/吨",
            "change_pct": change_pct,
            "yesterday": int(yesterday) if yesterday else 0,
            "code": code,
        })
    return items


def fetch_news_hot():
    """今日头条热榜: top 10 时事."""
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    data = _fetch_json_safe(url, delay=1)
    if not data or "data" not in data:
        return []
    board = data["data"]
    items_raw = board if isinstance(board, list) else []
    if not items_raw:
        return []
    # Sort by HotValue desc
    items_raw = sorted(items_raw, key=lambda x: x.get("HotValue", 0), reverse=True)[:10]
    return [
        {
            "title": item.get("Title", ""),
            "url": item.get("Url", ""),
            "label": item.get("Label", ""),
        }
        for item in items_raw
    ]


def fetch_stock_news():
    """今日头条财经热榜: top 10 股市新闻."""
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc&category_name=finance"
    data = _fetch_json_safe(url, delay=1)
    if not data or "data" not in data:
        return []
    board = data["data"]
    items_raw = board if isinstance(board, list) else []
    if not items_raw:
        return []
    items_raw = sorted(items_raw, key=lambda x: x.get("HotValue", 0), reverse=True)[:10]
    return [
        {
            "title": item.get("Title", ""),
            "url": item.get("Url", ""),
            "label": item.get("Label", ""),
        }
        for item in items_raw
    ]


def fetch_stock_hot():
    """东方财富: A股成交额排行前10."""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get"
        "?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f6"
        "&fs=m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:7+f:!2,m:1+t:3+f:!2"
        "&fields=f2,f3,f4,f6,f12,f14"
    )
    data = _fetch_json_safe(url)
    if not data or "data" not in data or "diff" not in data["data"]:
        return []
    return [
        {
            "name": d.get("f14", ""),
            "code": d.get("f12", ""),
            "change_pct": d.get("f3", 0),
        }
        for d in data["data"]["diff"][:10]
    ]


def fetch_sector_hot():
    """东方财富: 行业板块涨跌幅排行前10."""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get"
        "?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f3"
        "&fs=m:90+t:1"
        "&fields=f2,f3,f4,f6,f12,f14"
    )
    data = _fetch_json_safe(url)
    if not data or "data" not in data or "diff" not in data["data"]:
        return []
    return [
        {
            "name": d.get("f14", ""),
            "change_pct": d.get("f3", 0),
        }
        for d in data["data"]["diff"][:10]
    ]


def fetch_concept_hot():
    """东方财富: 概念板块涨跌幅排行前10."""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get"
        "?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f3"
        "&fs=m:90+t:3"
        "&fields=f2,f3,f4,f6,f12,f14"
    )
    data = _fetch_json_safe(url)
    if not data or "data" not in data or "diff" not in data["data"]:
        return []
    return [
        {
            "name": d.get("f14", ""),
            "change_pct": d.get("f3", 0),
            "code": d.get("f12", ""),
        }
        for d in data["data"]["diff"][:10]
    ]


# ─── Formatting helpers ───

def _change_badge(pct, prefix="market"):
    """Generate rise/fall badge HTML."""
    if pct is None or pct == "-":
        return ""
    pct = float(pct)
    direction = "rise" if pct >= 0 else "fall"
    arrow = "▲" if pct >= 0 else "▼"
    sign = "+" if pct >= 0 else ""
    if prefix == "crypto":
        return f'<span class="crypto-badge {direction}">{arrow} {sign}{pct:.2f}%</span>'
    if prefix == "sector":
        if pct > 1:
            label, badge_cls = "强势", "rise"
        elif pct > 0:
            label, badge_cls = "稳健", "rise"
        elif pct > -1:
            label, badge_cls = "分化", "mixed"
        else:
            label, badge_cls = "承压", "fall"
        return f'<span class="sector-badge {badge_cls}">{label}</span>'
    return f'<span class="{prefix}-badge {direction}">{arrow} {sign}{pct:.2f}%</span>'


def _change_text(pct):
    """Generate rise/fall change text for concepts."""
    pct = float(pct)
    direction = "rise" if pct >= 0 else "fall"
    arrow = "▲" if pct >= 0 else "▼"
    sign = "+" if pct >= 0 else ""
    return f'<span class="theme-change {direction}">{arrow} {sign}{pct:.2f}%</span>'


def _fmt_price(value, decimal=2):
    """Format price with commas."""
    if value is None or value == "-":
        return "-"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return str(value)
    if v >= 1000:
        return f"{v:,.{decimal}f}"
    if v < 0.01:
        return f"{v:.4f}"
    return f"{v:.{decimal}f}"


def _esc(text):
    """HTML-escape text."""
    return html_mod.escape(str(text), quote=True)


# ─── Category label mapping ───

CATEGORY_MAP = {
    "ai-models": "模型",
    "ai-products": "产品",
    "industry": "行业",
    "paper": "论文",
    "tip": "观点",
}


# ─── CSS (static, copied from current design) ───

CSS = """
    :root {
      --c-bg:            oklch(1.000 0.000 0);
      --c-surface:       oklch(0.97 0.005 42);
      --c-surface-el:    oklch(0.95 0.008 42);
      --c-surface-hover: oklch(0.93 0.012 42);
      --c-ink:           oklch(0.18 0.015 42);
      --c-ink-soft:      oklch(0.40 0.010 42);
      --c-primary:       oklch(0.72 0.22 42);
      --c-primary-dark:  oklch(0.55 0.20 42);
      --c-primary-soft:  oklch(0.92 0.06 42);
      --c-primary-glow:  oklch(0.72 0.22 42 / 0.08);
      --c-accent:        oklch(0.50 0.15 250);
      --c-accent-soft:   oklch(0.92 0.03 250);
      --c-muted:         oklch(0.50 0.010 42);
      --c-rise:          oklch(0.55 0.20 15);
      --c-rise-bg:       oklch(0.95 0.05 15);
      --c-fall:          oklch(0.48 0.14 165);
      --c-fall-bg:       oklch(0.94 0.04 165);
      --c-border:        oklch(0.85 0.010 42);
      --c-border-hover:  oklch(0.75 0.020 42);
      --c-shadow:        oklch(0.18 0.010 42 / 0.06);
      --f-display: 'EB Garamond', 'Noto Serif SC', Georgia, serif;
      --f-body:    'Figtree', 'Noto Sans SC', system-ui, sans-serif;
      --f-data:    'JetBrains Mono', 'Menlo', 'Consolas', monospace;
      --s-1: 0.5rem; --s-2: 0.75rem; --s-3: 1rem; --s-4: 1.25rem;
      --s-5: 1.5rem; --s-6: 2rem; --s-7: 2.5rem; --s-8: 3rem;
      --s-9: 4rem; --s-10: 5rem;
      --t-label: 0.75rem; --t-data: 0.85rem; --t-small: 0.875rem;
      --t-body: 1rem; --t-title: 1.25rem; --t-headline: 1.5rem;
      --t-section: 1.75rem; --t-hero: clamp(1.75rem, 3.5vw, 2.75rem);
      --r-sm: 4px; --r-md: 8px; --r-lg: 12px;
      --ease: cubic-bezier(0.25, 0.1, 0.25, 1);
      --dur: 0.2s; --dur-slow: 0.35s;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; }
    html { font-size: 16px; scroll-behavior: smooth; -webkit-font-smoothing: antialiased; }
    body { font-family: var(--f-body); font-weight: 400; color: var(--c-ink); background: var(--c-bg); line-height: 1.6; max-width: 76rem; margin: 0 auto; padding: var(--s-4) var(--s-5) var(--s-10); }

    header { margin-bottom: var(--s-5); }
    .header-content { display: flex; justify-content: space-between; align-items: baseline; padding: var(--s-4) 0 var(--s-3); }
    .brand h1 { font-family: var(--f-display); font-size: clamp(2.5rem, 6vw, 4rem); font-weight: 700; line-height: 1; letter-spacing: -0.03em; color: var(--c-ink); }
    .brand-en { font-family: var(--f-data); font-size: var(--t-label); font-weight: 500; color: var(--c-muted); letter-spacing: 0.08em; text-transform: uppercase; margin-left: var(--s-2); }
    .date-info { font-family: var(--f-body); font-size: var(--t-small); color: var(--c-muted); text-align: right; }
    .date-info time { font-weight: 600; color: var(--c-ink-soft); }
    .header-rule { border: none; height: 3px; background: var(--c-primary); box-shadow: 0 1px 0 var(--c-primary-soft); }

    .market-bar { background: var(--c-surface-el); border: 1px solid var(--c-border); border-radius: var(--r-md); padding: var(--s-4) var(--s-5); margin-bottom: var(--s-7); box-shadow: 0 1px 3px var(--c-shadow); }
    .market-row { display: flex; flex-wrap: wrap; gap: var(--s-3) var(--s-5); align-items: center; }
    .market-row + .market-row { margin-top: var(--s-3); padding-top: var(--s-3); border-top: 1px solid var(--c-border); }
    .market-label { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; color: var(--c-muted); letter-spacing: 0.06em; text-transform: uppercase; min-width: 4.5rem; }
    .market-item { display: flex; align-items: baseline; gap: var(--s-2); white-space: nowrap; }
    .market-name { font-size: var(--t-small); font-weight: 500; color: var(--c-ink-soft); }
    .market-value { font-family: var(--f-data); font-size: var(--t-data); font-weight: 600; color: var(--c-ink); }
    .market-badge { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; padding: 0.2rem 0.5rem; border-radius: var(--r-sm); letter-spacing: 0.02em; }
    .market-badge.rise { color: var(--c-rise); background: var(--c-rise-bg); }
    .market-badge.fall { color: var(--c-fall); background: var(--c-fall-bg); }

    .content-grid { display: grid; grid-template-columns: 5fr 3fr; gap: var(--s-6); }

    .card { background: var(--c-bg); border: 1px solid var(--c-border); border-radius: var(--r-md); padding: var(--s-5); box-shadow: 0 1px 3px var(--c-shadow); transition: border-color var(--dur) var(--ease), box-shadow var(--dur-slow) var(--ease), background var(--dur) var(--ease); }
    .card:hover { border-color: var(--c-border-hover); background: var(--c-surface); box-shadow: 0 2px 8px oklch(0.72 0.22 42 / 0.08), 0 1px 3px var(--c-shadow); }
    .card + .card { margin-top: var(--s-5); }

    .section-title { font-family: var(--f-display); font-size: var(--t-section); font-weight: 700; line-height: 1.2; color: var(--c-ink); margin-bottom: var(--s-5); text-wrap: balance; }
    .section-title::before { content: ''; display: inline-block; width: 3px; height: 1em; background: var(--c-primary); border-radius: 1px; margin-right: var(--s-3); vertical-align: middle; }

    .update-time { font-family: var(--f-data); font-size: var(--t-label); color: var(--c-muted); text-align: right; margin-top: var(--s-3); }

    .hero { grid-column: 1; }
    .hero-lead { background: linear-gradient(135deg, oklch(1.000 0.000 0), oklch(0.96 0.035 42)); border: 1px solid oklch(0.85 0.025 42); border-top: 3px solid var(--c-primary); border-radius: var(--r-lg); padding: var(--s-7) var(--s-8); margin-bottom: var(--s-5); box-shadow: 0 2px 8px oklch(0.72 0.22 42 / 0.06); }
    .hero-headline { font-family: var(--f-display); font-size: var(--t-hero); font-weight: 700; line-height: 1.15; color: var(--c-ink); margin-bottom: var(--s-4); text-wrap: balance; }
    .hero-headline a { color: var(--c-ink); }
    .hero-headline a:hover { color: var(--c-primary-dark); }
    .hero-desc { font-size: var(--t-small); color: var(--c-muted); line-height: 1.55; max-width: 55ch; }

    .ai-list, .ranked-list { list-style: none; counter-reset: ai-rank; padding: 0; }
    .ai-list li, .ranked-list li { counter-increment: ai-rank; display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); border-bottom: 1px solid oklch(0.92 0.005 42); transition: background var(--dur) var(--ease); }
    .ai-list li:hover, .ranked-list li:hover { background: var(--c-surface); }
    .ai-list li:last-child, .ranked-list li:last-child { border-bottom: none; }
    .ai-list li::before, .ranked-list li::before { content: counter(ai-rank); font-family: var(--f-display); font-size: var(--t-title); font-weight: 700; color: var(--c-primary); min-width: 1.5rem; }

    .ai-item-title { font-size: var(--t-body); font-weight: 500; color: var(--c-ink); line-height: 1.4; flex: 1; }
    .ai-item-title a { color: var(--c-ink); }
    .ai-item-title a:hover { color: var(--c-accent); }
    .ai-item-tag { font-family: var(--f-data); font-size: var(--t-label); font-weight: 500; color: var(--c-accent); background: var(--c-accent-soft); padding: 0.2rem 0.55rem; border-radius: var(--r-sm); letter-spacing: 0.02em; white-space: nowrap; }

    .sidebar { grid-column: 2; }
    .sidebar-title { font-family: var(--f-display); font-size: var(--t-title); font-weight: 700; color: var(--c-ink); margin-bottom: var(--s-4); }
    .sidebar-title::before { content: ''; display: inline-block; width: 3px; height: 0.8em; background: var(--c-primary); border-radius: 1px; margin-right: var(--s-2); vertical-align: middle; }
    .data-row { display: flex; justify-content: space-between; align-items: baseline; padding: var(--s-3) 0; }
    .data-row + .data-row { border-top: 1px solid oklch(0.92 0.005 42); }
    .data-label { font-size: var(--t-small); font-weight: 500; color: var(--c-muted); }
    .data-value-group { text-align: right; }
    .data-price { font-family: var(--f-data); font-size: var(--t-data); font-weight: 600; color: var(--c-ink); }
    .data-unit { font-family: var(--f-body); font-size: var(--t-label); color: var(--c-muted); }
    .data-badge { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; padding: 0.2rem 0.5rem; border-radius: var(--r-sm); margin-left: var(--s-1); }
    .data-badge.rise { color: var(--c-rise); background: var(--c-rise-bg); }
    .data-badge.fall { color: var(--c-fall); background: var(--c-fall-bg); }
    .yesterday { font-family: var(--f-body); font-size: var(--t-label); color: var(--c-muted); display: block; margin-top: 0.15rem; }

    .news-hot, .stock-hot, .sectors, .themes { grid-column: auto; }
    .rank-item-title { font-size: var(--t-body); font-weight: 500; color: var(--c-ink); line-height: 1.4; flex: 1; }
    .rank-item-title a { color: var(--c-ink); }
    .rank-item-title a:hover { color: var(--c-accent); }
    .rank-item-title .hot-label { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; color: var(--c-rise); background: var(--c-rise-bg); padding: 0.15rem 0.4rem; border-radius: var(--r-sm); margin-left: var(--s-2); }

    .stock-badge { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; padding: 0.2rem 0.5rem; border-radius: var(--r-sm); white-space: nowrap; }
    .stock-badge.rise { color: var(--c-rise); background: var(--c-rise-bg); }
    .stock-badge.fall { color: var(--c-fall); background: var(--c-fall-bg); }
    .stock-sector { font-family: var(--f-data); font-size: var(--t-label); font-weight: 500; color: var(--c-accent); background: var(--c-accent-soft); padding: 0.2rem 0.5rem; border-radius: var(--r-sm); white-space: nowrap; }

    .sector-badge { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; padding: 0.2rem 0.55rem; border-radius: var(--r-sm); white-space: nowrap; }
    .sector-badge.rise { color: oklch(1 0 0); background: var(--c-rise); }
    .sector-badge.fall { color: oklch(1 0 0); background: var(--c-fall); }
    .sector-badge.mixed { color: var(--c-ink); background: var(--c-surface-el); border: 1px solid var(--c-border); }
    .sector-change { font-family: var(--f-data); font-size: var(--t-label); color: var(--c-muted); margin-left: var(--s-2); }
    .sector-change.rise { color: var(--c-rise); }
    .sector-change.fall { color: var(--c-fall); }

    .crypto-bar { background: oklch(0.14 0.035 300); border: 1px solid oklch(0.25 0.05 300); border-radius: var(--r-md); padding: var(--s-4) var(--s-5); margin-bottom: var(--s-7); }
    .crypto-row { display: grid; grid-template-columns: auto repeat(5, minmax(7rem, 1fr)); gap: 0 var(--s-5); align-items: baseline; }
    .crypto-label { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; color: oklch(0.65 0.15 300); letter-spacing: 0.06em; text-transform: uppercase; }
    .crypto-item { display: flex; flex-direction: column; gap: var(--s-1); align-items: baseline; }
    .crypto-name { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; color: oklch(0.70 0.10 300); letter-spacing: 0.04em; }
    .crypto-price-row { display: flex; align-items: baseline; gap: var(--s-2); }
    .crypto-value { font-family: var(--f-data); font-size: var(--t-data); font-weight: 600; color: oklch(0.95 0.02 300); }
    .crypto-badge { font-family: var(--f-data); font-size: var(--t-label); font-weight: 600; padding: 0.15rem 0.45rem; border-radius: var(--r-sm); letter-spacing: 0.02em; }
    .crypto-badge.rise { color: oklch(0.70 0.20 100); background: oklch(0.20 0.06 100); }
    .crypto-badge.fall { color: oklch(0.60 0.15 200); background: oklch(0.20 0.05 200); }
    .crypto-unit { font-family: var(--f-body); font-size: var(--t-label); color: oklch(0.55 0.05 300); }

    .theme-item { flex-direction: column; gap: var(--s-1); padding: var(--s-4) var(--s-4) !important; }
    .theme-item-header { display: flex; align-items: center; gap: var(--s-2); }
    .theme-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--c-accent); flex-shrink: 0; }
    .theme-desc { font-size: var(--t-label); color: var(--c-muted); margin-top: 0.125rem; }
    .theme-change { font-family: var(--f-data); font-size: var(--t-label); font-weight: 500; white-space: nowrap; }
    .theme-change.rise { color: var(--c-rise); }

    footer { margin-top: var(--s-9); padding-top: var(--s-5); border-top: 3px solid var(--c-primary); text-align: center; }
    .footer-brand { font-family: var(--f-display); font-size: var(--t-headline); font-weight: 700; color: var(--c-ink); }
    .footer-sub { font-size: var(--t-label); color: var(--c-muted); margin-top: var(--s-1); }

    a { color: var(--c-accent); text-decoration: none; transition: color var(--dur) var(--ease); }
    a:hover { color: oklch(0.40 0.18 250); }
    a:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; border-radius: var(--r-sm); }

    @media (max-width: 768px) {
      body { padding: var(--s-3) var(--s-3) var(--s-8); }
      .header-content { flex-direction: column; gap: var(--s-2); }
      .date-info { text-align: left; }
      .brand-en { display: block; margin-left: 0; margin-top: var(--s-1); }
      .content-grid { grid-template-columns: 1fr; gap: var(--s-6); }
      .hero, .sidebar, .news-hot, .stock-hot, .sectors, .stock-news, .themes { grid-column: 1; }
      .hero-lead { padding: var(--s-5) var(--s-5); }
      .hero-headline { font-size: clamp(1.5rem, 5vw, 2.25rem); }
      .card { padding: var(--s-4); }
      .market-row { gap: var(--s-2) var(--s-3); }
      .market-item { flex-wrap: wrap; }
      .crypto-row { gap: var(--s-2) var(--s-3); }
      .crypto-row { grid-template-columns: 1fr 1fr; }
      .crypto-label { display: none; }
    }
    @media (max-width: 480px) {
      .market-bar { padding: var(--s-3); }
      .market-label { min-width: auto; }
      .data-row { flex-direction: column; gap: var(--s-1); }
      .data-value-group { text-align: left; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
    }
    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); border: 0; }
"""


# ─── HTML section generators ───

def _render_header(date_str, update_time):
    """Page header with brand and date."""
    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_map[bjt_now().weekday()]
    return f"""
  <header>
    <div class="header-content">
      <div class="brand">
        <h1>日报<span class="brand-en">Daily Report</span></h1>
      </div>
      <div class="date-info">
        <time datetime="{bjt_now().strftime('%Y-%m-%d')}">{date_str}</time> · {weekday} · {update_time} 更新
      </div>
    </div>
    <hr class="header-rule">
  </header>"""


def _render_crypto_bar(crypto_items):
    """Crypto price bar section."""
    if not crypto_items:
        return ""
    cells = ""
    for c in crypto_items:
        price_str = _fmt_price(c["price"])
        badge = _change_badge(c["change_pct"], "crypto")
        cells += f"""
      <div class="crypto-item">
        <span class="crypto-name">{_esc(c["symbol"])}</span>
        <div class="crypto-price-row">
          <span class="crypto-value">${_esc(price_str)}</span>
          {badge}
        </div>
      </div>"""
    return f"""
  <section class="crypto-bar" aria-label="加密货币价格">
    <div class="crypto-row">
      <span class="crypto-label">加密</span>
{cells}
    </div>
  </section>"""


def _render_market_bar(a_indices, us_indices):
    """A-stock + US-stock indices bar."""
    update_t = bjt_time_str()
    a_row = ""
    if a_indices:
        for idx in a_indices:
            val_str = _fmt_price(idx["value"])
            badge = _change_badge(idx["change_pct"], "market")
            a_row += f"""
        <div class="market-item">
          <span class="market-name">{_esc(idx["name"])}</span>
          <span class="market-value">{_esc(val_str)}</span>
          {badge}
        </div>"""
    us_row = ""
    if us_indices:
        for idx in us_indices:
            val_str = _fmt_price(idx["value"])
            badge = _change_badge(idx["change_pct"], "market")
            us_row += f"""
        <div class="market-item">
          <span class="market-name">{_esc(idx["name"])}</span>
          <span class="market-value">{_esc(val_str)}</span>
          {badge}
        </div>"""
    return f"""
  <section class="market-bar" aria-label="市场指数概览">
    <div class="market-row">
      <span class="market-label">A股</span>
{a_row}
    </div>
    <div class="market-row">
      <span class="market-label">美股</span>
{us_row}
    </div>
  </section>"""


def _render_ai_hot(ai_items):
    """AI hot list: hero lead + ranked list."""
    if not ai_items:
        return '<section class="hero" aria-label="今日焦点"><h2 class="section-title">今日焦点 · AI 热榜</h2></section>'

    # First selected item as hero lead
    hero = ai_items[0] if ai_items[0].get("selected") else ai_items[0]
    hero_title = _esc(hero["title"])
    hero_url = _esc(hero.get("url", ""))
    hero_desc = _esc(hero.get("summary", ""))
    hero_link = f'<a href="{hero_url}">{hero_title}</a>' if hero_url else hero_title
    hero_html = f"""
      <article class="hero-lead">
        <h3 class="hero-headline">{hero_link}</h3>
        <p class="hero-desc">{hero_desc}</p>
      </article>"""

    # Remaining items as ranked list
    list_html = ""
    for item in ai_items:
        title = _esc(item["title"])
        url = _esc(item.get("url", ""))
        tag = CATEGORY_MAP.get(item.get("category", ""), item.get("category", ""))
        link = f'<a href="{url}">{title}</a>' if url else title
        list_html += f"""
          <li>
            <span class="ai-item-title">{link}</span>
            <span class="ai-item-tag">{_esc(tag)}</span>
          </li>"""

    return f"""
    <section class="hero" aria-label="今日焦点">
      <h2 class="section-title">今日焦点 · AI 热榜</h2>
{hero_html}
      <div class="card">
        <ol class="ai-list">
{list_html}
        </ol>
        <p class="update-time">数据来源：aihot.virxact.com · 更新 {bjt_time_str()}</p>
      </div>
    </section>"""


def _render_sidebar(gold_items, metal_items):
    """Gold/Silver + Metals sidebar."""
    update_t = bjt_time_str()
    gold_html = ""
    if gold_items:
        for g in gold_items:
            badge = _change_badge(g["change_pct"], "data")
            yesterday_str = f"昨收 {_fmt_price(g['yesterday'])}" if g.get("yesterday") else ""
            gold_html += f"""
        <div class="data-row">
          <span class="data-label">{_esc(g["name"])}</span>
          <div class="data-value-group">
            <span class="data-price">{_esc(_fmt_price(g["price"]))}</span>
            <span class="data-unit">{_esc(g["unit"])}</span>
            {badge}
            <span class="yesterday">{yesterday_str}</span>
          </div>
        </div>"""
    metal_html = ""
    if metal_items:
        for m in metal_items:
            badge = _change_badge(m["change_pct"], "data")
            yesterday_str = f"昨收 {_fmt_price(m['yesterday'])}" if m.get("yesterday") else ""
            metal_html += f"""
        <div class="data-row">
          <span class="data-label">{_esc(m["name"])}</span>
          <div class="data-value-group">
            <span class="data-price">{_esc(_fmt_price(m["price"], 0))}</span>
            <span class="data-unit">{_esc(m["unit"])}</span>
            {badge}
            <span class="yesterday">{yesterday_str}</span>
          </div>
        </div>"""

    return f"""
    <aside class="sidebar" aria-label="商品价格">
      <div class="card">
        <h2 class="sidebar-title">金价动态</h2>
{gold_html}
        <p class="update-time">沪金/沪银主连 · 更新 {update_t}</p>
      </div>

      <div class="card">
        <h2 class="sidebar-title">重金属价格</h2>
{metal_html}
        <p class="update-time">沪铜/沪铝/沪锌/沪镍主连 · 更新 {update_t}</p>
      </div>
    </aside>"""


def _render_news_hot(news_items):
    """时事热榜."""
    if not news_items:
        return '<section class="news-hot" aria-label="时事热榜"><h2 class="section-title">时事热榜</h2></section>'
    list_html = ""
    for item in news_items:
        title = _esc(item["title"])
        url = _esc(item.get("url", ""))
        label = item.get("label", "")
        hot_tag = f'<span class="hot-label">{_esc(label)}</span>' if label else ""
        link = f'<a href="{url}">{title}</a>' if url else title
        list_html += f"""
          <li><span class="rank-item-title">{link}{hot_tag}</span></li>"""
    return f"""
    <section class="news-hot" aria-label="时事热榜">
      <h2 class="section-title">时事热榜</h2>
      <div class="card">
        <ol class="ranked-list">
{list_html}
        </ol>
        <p class="update-time">数据来源：今日头条热榜 · 更新 {bjt_time_str()}</p>
      </div>
    </section>"""


def _render_stock_hot(stock_items):
    """A股热榜 (成交额排行)."""
    if not stock_items:
        return '<section class="stock-hot" aria-label="A股热榜"><h2 class="section-title">A股热榜</h2></section>'
    list_html = ""
    for item in stock_items:
        badge = _change_badge(item["change_pct"], "stock")
        list_html += f"""
          <li><span class="rank-item-title">{_esc(item["name"])}</span>{badge}</li>"""
    return f"""
    <section class="stock-hot" aria-label="A股热榜">
      <h2 class="section-title">A股热榜</h2>
      <div class="card">
        <ol class="ranked-list">
{list_html}
        </ol>
        <p class="update-time">成交额排行前10 · 更新 {bjt_time_str()}</p>
      </div>
    </section>"""


def _render_sector_hot(sector_items):
    """股市热榜 (行业板块)."""
    if not sector_items:
        return '<section class="sectors" aria-label="股市热榜"><h2 class="section-title">股市热榜</h2></section>'
    list_html = ""
    for item in sector_items:
        badge = _change_badge(item["change_pct"], "sector")
        pct = float(item["change_pct"])
        direction = "rise" if pct >= 0 else "fall"
        arrow = "▲" if pct >= 0 else "▼"
        sign = "+" if pct >= 0 else ""
        change_html = f'<span class="sector-change {direction}">{arrow} {sign}{pct:.2f}%</span>'
        list_html += f"""
          <li><span class="rank-item-title">{_esc(item["name"])}</span>{badge}{change_html}</li>"""
    return f"""
    <section class="sectors" aria-label="股市热榜">
      <h2 class="section-title">股市热榜</h2>
      <div class="card">
        <ol class="ranked-list">
{list_html}
        </ol>
        <p class="update-time">行业板块涨跌幅排行 · 更新 {bjt_time_str()}</p>
      </div>
    </section>"""


def _render_stock_news(news_items):
    """股市新闻."""
    if not news_items:
        return '<section class="stock-news" aria-label="股市新闻"><h2 class="section-title">股市新闻</h2></section>'
    list_html = ""
    for item in news_items:
        title = _esc(item["title"])
        url = _esc(item.get("url", ""))
        label = item.get("label", "")
        hot_tag = f'<span class="hot-label">{_esc(label)}</span>' if label else ""
        link = f'<a href="{url}">{title}</a>' if url else title
        list_html += f"""
          <li><span class="rank-item-title">{link}{hot_tag}</span></li>"""
    return f"""
    <section class="stock-news" aria-label="股市新闻">
      <h2 class="section-title">股市新闻</h2>
      <div class="card">
        <ol class="ranked-list">
{list_html}
        </ol>
        <p class="update-time">数据来源：今日头条财经热榜 · 更新 {bjt_time_str()}</p>
      </div>
    </section>"""


def _render_concept_hot(concept_items):
    """热门题材 (概念板块)."""
    if not concept_items:
        return '<section class="themes" aria-label="热门题材"><h2 class="section-title">热门题材</h2></section>'
    list_html = ""
    for item in concept_items:
        pct = float(item["change_pct"])
        change_html = _change_text(item["change_pct"])
        list_html += f"""
          <li class="theme-item">
            <div class="theme-item-header"><span class="theme-dot"></span><span class="rank-item-title">{_esc(item["name"])}</span>{change_html}</div>
          </li>"""
    return f"""
    <section class="themes" aria-label="热门题材">
      <h2 class="section-title">热门题材</h2>
      <div class="card">
        <ol class="ranked-list">
{list_html}
        </ol>
        <p class="update-time">概念板块涨跌幅排行 · 更新 {bjt_time_str()}</p>
      </div>
    </section>"""


# ─── Full page renderer ───

def render_full_html(data):
    """Assemble complete HTML page from fetched data dict."""
    date_str = bjt_str()
    update_time = bjt_time_str()

    sections = [
        _render_header(date_str, update_time),
        _render_crypto_bar(data.get("crypto", [])),
        _render_market_bar(data.get("a_indices", []), data.get("us_indices", [])),
        "<main class=\"content-grid\">",
        _render_ai_hot(data.get("ai_hot", [])),
        _render_sidebar(data.get("gold", []), data.get("metals", [])),
        _render_news_hot(data.get("news_hot", [])),
        _render_stock_hot(data.get("stock_hot", [])),
        _render_sector_hot(data.get("sector_hot", [])),
        _render_stock_news(data.get("stock_news", [])),
        _render_concept_hot(data.get("concept_hot", [])),
        "</main>",
        f"""
  <footer>
    <p class="footer-brand">日报</p>
    <p class="footer-sub">每日精选资讯 · 数据来源仅供参考 · {date_str} {update_time}</p>
  </footer>""",
    ]

    body_content = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>日报 · Daily Report — {date_str}</title>
  <meta name="description" content="每日精选资讯 — AI热榜、金价、A股、美股、重金属、时事热榜、股市热榜、热门题材">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Figtree:wght@400;500;600;700&family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>{CSS}
  </style>
</head>
<body>
{body_content}
</body>
</html>"""


# ─── Main orchestrator ───

def main():
    """Fetch all data, generate HTML, write to index.html."""
    log.info("Starting data fetch...")
    data = {}

    data["crypto"] = fetch_crypto() or []
    log.info("Crypto: %d items", len(data["crypto"]))

    data["ai_hot"] = fetch_ai_hot() or []
    log.info("AI hot: %d items", len(data["ai_hot"]))

    data["a_indices"] = fetch_a_stock_indices() or []
    log.info("A-stock indices: %d items", len(data["a_indices"]))

    data["us_indices"] = fetch_us_stock_indices() or []
    log.info("US indices: %d items", len(data["us_indices"]))

    data["gold"] = fetch_gold_silver() or []
    log.info("Gold/Silver: %d items", len(data["gold"]))

    data["metals"] = fetch_metals() or []
    log.info("Metals: %d items", len(data["metals"]))

    data["news_hot"] = fetch_news_hot() or []
    log.info("News hot: %d items", len(data["news_hot"]))

    data["stock_news"] = fetch_stock_news() or []
    log.info("Stock news: %d items", len(data["stock_news"]))

    data["stock_hot"] = fetch_stock_hot() or []
    log.info("Stock hot: %d items", len(data["stock_hot"]))

    data["sector_hot"] = fetch_sector_hot() or []
    log.info("Sector hot: %d items", len(data["sector_hot"]))

    data["concept_hot"] = fetch_concept_hot() or []
    log.info("Concept hot: %d items", len(data["concept_hot"]))

    log.info("Generating HTML...")
    html_content = render_full_html(data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    log.info("Written to %s (%d bytes)", OUTPUT_PATH, len(html_content))
    return 0


if __name__ == "__main__":
    sys.exit(main())