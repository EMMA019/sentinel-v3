"""
core_fmp.py — FMP API Client (Starter Plan)
============================================
FMPの新エンドポイント (/stable/) 対応版。
確認済み:
  - 過去株価: /stable/historical-price-eod/full?symbol={ticker}
  - ニュース: /stable/news/stock-latest?page=0&limit={limit}
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
# キャッシュ付きGET
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get(url: str, params: dict = None, cache_key: str = None, ttl: int = 3600):
    params = params or {}
    if cache_key:
        h = hashlib.md5(cache_key.encode()).hexdigest()
        cache_file = CACHE_DIR / f"{h}.json"
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime < ttl):
            return json.loads(cache_file.read_text())

    try:
        resp = requests.get(url, params={**params, "apikey": FMP_API_KEY}, timeout=15)
        if resp.status_code == 403:
            print(f"HTTP 403: {url}")
            return None
        resp.raise_for_status()
        data = resp.json()
        if cache_key and data:
            cache_file.write_text(json.dumps(data))
        return data
    except Exception as e:
        print(f"FMP error {url}: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 過去株価（OHLCV）— 確認済み ✅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_historical_data(ticker: str, days: int = 365) -> pd.DataFrame | None:
    """
    /stable/historical-price-eod/full?symbol={ticker}
    返り値: DatetimeIndex付きDataFrame (OHLCV)
    """
    data = _get(f"{BASE_URL}/historical-price-eod/full", {"symbol": ticker})
    if not data or "historical" not in data:
        return None
    
    hist = data["historical"]
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
    パラメータ: symbol={ticker} or tickers={ticker} を試行
    6時間キャッシュ
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
    Returns: {price, change, changesPercentage, volume, dayHigh, dayLow, ...}
    """
    data = _get(f"{BASE_URL}/quote", {"symbol": ticker})
    
    # レスポンスが配列の場合
    if isinstance(data, list) and data:
        return data[0]
    
    # レスポンスが単一オブジェクトの場合
    if isinstance(data, dict):
        return data
    
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 会社プロフィール
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_company_profile(ticker: str) -> dict | None:
    """
    /stable/profile?symbol={ticker} を試行
    24時間キャッシュ
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
    /stable/price-target-summary?symbol={ticker} — 目標株価平均
    /stable/analyst-stock-recommendations?symbol={ticker} — Buy/Hold/Sell内訳（Hannah確認中）
    24時間キャッシュ
    """
    # 目標株価サマリー（確認済み）
    target = _get(f"{BASE_URL}/price-target-summary",
                  {"symbol": ticker},
                  cache_key=f"target_{ticker}", ttl=24*3600)
    
    # アナリスト内訳（試行 — 403ならスキップ）
    recommendations = _get(f"{BASE_URL}/analyst-stock-recommendations",
                           {"symbol": ticker},
                           cache_key=f"analyst_{ticker}", ttl=24*3600)
    
    # Buy/Hold/Sell集計
    buy = sell = hold = 0
    if isinstance(recommendations, list) and recommendations:
        for r in recommendations[:6]:  # 直近6レコード
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
    
    # どちらか片方でもデータがあれば返す
    if not consensus and not target_mean:
        return None
    
    return {
        "consensus":     consensus or "N/A",
        "analyst_count": total if total > 0 else None,
        "buy":  buy if total > 0 else None,
        "hold": hold if total > 0 else None,
        "sell": sell if total > 0 else None,
        "target_mean": round(target_mean, 2) if target_mean else None,
        "target_high": None,  # price-target-summaryには含まれない
        "target_low":  None,  # price-target-summaryには含まれない
        "target_pct":  target_pct,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ファンダメンタルズ — 確認済み ✅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_fundamentals(ticker: str) -> dict | None:
    """
    /stable/key-metrics?symbol={ticker}&period=annual&limit=1
    /stable/income-statement-growth?symbol={ticker}&limit=1
    24時間キャッシュ
    """
    # Key Metrics (最新年度)
    km = _get(f"{BASE_URL}/key-metrics",
              {"symbol": ticker, "period": "annual", "limit": 1},
              cache_key=f"keymetrics_{ticker}", ttl=24*3600)
    km = km[0] if isinstance(km, list) and km else {}
    
    # Income Statement Growth (最新年度)
    ig = _get(f"{BASE_URL}/income-statement-growth",
              {"symbol": ticker, "period": "annual", "limit": 1},
              cache_key=f"incgrowth_{ticker}", ttl=24*3600)
    ig = ig[0] if isinstance(ig, list) and ig else {}
    
    def _pct(v):
        return round(float(v)*100, 1) if v is not None else None
    def _rnd(v, n=2):
        return round(float(v), n) if v is not None else None
    
    # レスポンス構造に合わせてマッピング
    return {
        "pe_forward":          _rnd(km.get("peRatioTTM")),
        "eps_ttm":             None,  # key-metricsには含まれない
        "revenue_growth_yoy":  _pct(ig.get("growthRevenue")),
        "earnings_growth_yoy": _pct(ig.get("growthNetIncome")),
        "gross_margin":        _pct(km.get("grossProfitMarginTTM")),
        "profit_margin":       None,  # 取れない可能性
        "debt_to_equity":      _rnd(km.get("debtToEquityTTM")),
        "current_ratio":       _rnd(km.get("currentRatioTTM")),
        "market_cap_b":        _rnd(km.get("marketCapTTM", 0) / 1e9, 1) if km.get("marketCapTTM") else None,
        "roe":                 _pct(km.get("returnOnEquityTTM")),
        "roa":                 _pct(km.get("returnOnAssetsTTM")),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 機関投資家保有（プロフィールから取得）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_ownership(ticker: str) -> dict | None:
    """
    プロフィールに含まれる機関保有率を使用
    空売りデータはStarterでは取れないのでNone
    """
    profile = get_company_profile(ticker) or {}
    
    inst_pct = None
    if profile.get("institutionalOwnershipPercentage"):
        inst_pct = round(float(profile["institutionalOwnershipPercentage"]) * 100, 1)
    
    return {
        "institutional_pct":   inst_pct,
        "insider_pct":         None,  # Starterでは非対応
        "short_float_pct":     None,  # Starterでは非対応
        "short_days_to_cover": None,  # Starterでは非対応
    }
