"""
core_fmp.py — FMP API Client (Starter Plan)
============================================
FMPの新エンドポイント (/stable/) 対応版。
- 429エラー対策（スロットリングと指数バックオフリトライ）
- Stable API特有の「リスト直接返却」パースに対応
"""
import os, requests, json, hashlib, time
from pathlib import Path
import pandas as pd

FMP_API_KEY  = os.environ.get("FMP_API_KEY", "")
BASE_URL     = "https://financialmodelingprep.com/stable"
BASE_URL_V3  = "https://financialmodelingprep.com/api/v3"  # フォールバック用
CACHE_DIR    = Path(__file__).parent.parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# キャッシュ付きGET（完全版）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get(url: str, params: dict = None, cache_key: str = None, ttl: int = 3600):
    params = params or {}
    if cache_key:
        h = hashlib.md5(cache_key.encode()).hexdigest()
        cache_file = CACHE_DIR / f"{h}.json"
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime < ttl):
            return json.loads(cache_file.read_text())

    # --- 429対策: リクエスト前に常に短いウェイトを置く (300req/min = 0.2s) ---
    time.sleep(0.25)

    max_retries = 5
    for i in range(max_retries):
        try:
            resp = requests.get(url, params={**params, "apikey": FMP_API_KEY}, timeout=15)
            
            # 429 (Too Many Requests) の場合は指数バックオフでリトライ
            if resp.status_code == 429:
                wait_time = (2 ** i)  # 1s, 2s, 4s, 8s, 16s
                print(f"  ⚠️ Rate limit hit (429). Waiting {wait_time}s... (Retry {i+1}/{max_retries})")
                time.sleep(wait_time)
                continue

            if resp.status_code == 403:
                print(f"HTTP 403: {url}")
                return None
                
            resp.raise_for_status()
            data = resp.json()
            if cache_key and data:
                cache_file.write_text(json.dumps(data))
            return data

        except Exception as e:
            if i == max_retries - 1:
                print(f"FMP error {url}: {e}")
            else:
                time.sleep(1) # 一時的なネットワークエラー用
                continue
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 過去株価（OHLCV）— Stableのリスト形式に対応 ✅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_historical_data(ticker: str, days: int = 365) -> pd.DataFrame | None:
    """
    /stable/historical-price-eod/full?symbol={ticker}
    返り値: DatetimeIndex付きDataFrame (OHLCV)
    """
    data = _get(f"{BASE_URL}/historical-price-eod/full", {"symbol": ticker})
    
    # 重要修正: Stable API はリストが直接返ってくる
    if isinstance(data, list):
        hist = data
    elif isinstance(data, dict) and "historical" in data:
        hist = data["historical"]
    else:
        return None

    if not hist:
        return None

    df = pd.DataFrame(hist)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df.rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume"
    })

    # 直近days日分
    if len(df) > days:
        df = df.iloc[-days:]

    return df[["Open", "High", "Low", "Close", "Volume"]]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ニュース — 確認済み ✅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_news(ticker: str, limit: int = 5) -> list:
    """
    /stable/news/stock-latest?page=0&limit={limit}
    """
    # 試行1: symbol=AAPL
    data = _get(f"{BASE_URL}/news/stock-latest",
                {"page": 0, "limit": limit, "symbol": ticker},
                cache_key=f"news_{ticker}", ttl=6*3600)

    # 試行2: tickers=AAPL（v3互換）
    if not data or not isinstance(data, list):
        data = _get(f"{BASE_URL}/news/stock-latest",
                    {"page": 0, "limit": limit, "tickers": ticker},
                    cache_key=f"news2_{ticker}", ttl=6*3600)

    if not isinstance(data, list):
        return []

    return [{
        "title":        d.get("title", ""),
        "published_at": d.get("publishedDate", d.get("date", "")),
        "source":       d.get("site", d.get("source", "")),
        "url":          d.get("url", ""),
        "summary":      (d.get("text", d.get("summary", "")) or "")[:200],
    } for d in data[:limit]]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 現在値（クォート）— 確認済み ✅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_quote(ticker: str) -> dict | None:
    """
    /stable/quote?symbol={ticker}
    """
    data = _get(f"{BASE_URL}/quote", {"symbol": ticker})

    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 会社プロフィール
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_company_profile(ticker: str) -> dict | None:
    """
    /stable/profile?symbol={ticker}
    """
    data = _get(f"{BASE_URL}/profile", {"symbol": ticker},
                cache_key=f"profile_{ticker}", ttl=24*3600)
    if data and isinstance(data, list) and data:
        return data[0]

    # フォールバック: /v3/profile/{ticker}
    data = _get(f"{BASE_URL_V3}/profile/{ticker}",
                cache_key=f"profile_v3_{ticker}", ttl=24*3600)
    return data[0] if isinstance(data, list) and data else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# アナリスト評価 — price-target-summary 確認済み ✅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_analyst_consensus(ticker: str) -> dict | None:
    """
    /stable/price-target-summary?symbol={ticker}
    /stable/analyst-stock-recommendations?symbol={ticker}
    """
    # 目標株価サマリー
    target = _get(f"{BASE_URL}/price-target-summary",
                  {"symbol": ticker},
                  cache_key=f"target_{ticker}", ttl=24*3600)

    # アナリスト内訳
    recommendations = _get(f"{BASE_URL}/analyst-stock-recommendations",
                           {"symbol": ticker},
                           cache_key=f"analyst_{ticker}", ttl=24*3600)

    # Buy/Hold/Sell集計
    buy = sell = hold = 0
    if isinstance(recommendations, list) and recommendations:
        for r in recommendations[:6]:
            buy  += r.get("analystRatingsbuy", 0) + r.get("analystRatingsStrongBuy", 0)
            hold += r.get("analystRatingsHold", 0)
            sell += r.get("analystRatingsSell", 0) + r.get("analystRatingsStrongSell", 0)

    total = buy + hold + sell
    consensus = None
    if total > 0:
        consensus = "Buy" if buy > sell and buy > hold else \
                    "Sell" if sell > buy and sell > hold else "Hold"

    # 目標株価
    target_mean = None
    target_pct  = None
    if isinstance(target, dict):
        target_mean = target.get("lastMonthAvgPriceTarget")
        # 現在値との乖離%計算
        quote = get_quote(ticker)
        if target_mean and quote and quote.get("price"):
            price = float(quote["price"])
            target_pct = round((target_mean - price) / price * 100, 1)
    elif isinstance(target, list) and target:
        target_mean = target[0].get("lastMonthAvgPriceTarget")
        quote = get_quote(ticker)
        if target_mean and quote and quote.get("price"):
            price = float(quote["price"])
            target_pct = round((target_mean - price) / price * 100, 1)

    if not consensus and not target_mean:
        return None

    return {
        "consensus":     consensus or "N/A",
        "analyst_count": total if total > 0 else None,
        "buy":  buy if total > 0 else None,
        "hold": hold if total > 0 else None,
        "sell": sell if total > 0 else None,
        "target_mean": round(target_mean, 2) if target_mean else None,
        "target_high": None,
        "target_low":  None,
        "target_pct":  target_pct,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ファンダメンタルズ — 確認済み ✅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_fundamentals(ticker: str) -> dict | None:
    """
    /stable/key-metrics?symbol={ticker}&period=annual&limit=1
    /stable/income-statement-growth?symbol={ticker}&limit=1
    """
    # Key Metrics
    km = _get(f"{BASE_URL}/key-metrics",
              {"symbol": ticker, "period": "annual", "limit": 1},
              cache_key=f"keymetrics_{ticker}", ttl=24*3600)
    km = km[0] if isinstance(km, list) and km else {}

    # Income Statement Growth
    ig = _get(f"{BASE_URL}/income-statement-growth",
              {"symbol": ticker, "period": "annual", "limit": 1},
              cache_key=f"incgrowth_{ticker}", ttl=24*3600)
    ig = ig[0] if isinstance(ig, list) and ig else {}

    def _pct(v):
        return round(float(v)*100, 1) if v is not None else None
    def _rnd(v, n=2):
        return round(float(v), n) if v is not None else None

    return {
        "pe_forward":          _rnd(km.get("peRatioTTM")),
        "eps_ttm":             None,
        "revenue_growth_yoy":  _pct(ig.get("growthRevenue")),
        "earnings_growth_yoy": _pct(ig.get("growthNetIncome")),
        "gross_margin":        _pct(km.get("grossProfitMarginTTM")),
        "profit_margin":       None,
        "debt_to_equity":      _rnd(km.get("debtToEquityTTM")),
        "current_ratio":       _rnd(km.get("currentRatioTTM")),
        "market_cap_b":        _rnd(km.get("marketCapTTM", 0) / 1e9, 1) if km.get("marketCapTTM") else None,
        "roe":                 _pct(km.get("returnOnEquityTTM")),
        "roa":                 _pct(km.get("returnOnAssetsTTM")),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 機関投資家保有
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_ownership(ticker: str) -> dict | None:
    """
    プロフィールに含まれる機関保有率を使用
    """
    profile = get_company_profile(ticker) or {}

    inst_pct = None
    if profile.get("institutionalOwnershipPercentage"):
        inst_pct = round(float(profile["institutionalOwnershipPercentage"]) * 100, 1)

    return {
        "institutional_pct":   inst_pct,
        "insider_pct":         None,
        "short_float_pct":     None,
        "short_days_to_cover": None,
    }
