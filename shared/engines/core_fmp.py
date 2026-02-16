"""
core_fmp.py — Financial Modeling Prep API クライアント
Starter プラン（$19/mo）: 300 req/min, 5年履歴, 米国株
"""
import os, time, requests, pickle, pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

FMP_API_KEY  = os.environ.get("FMP_API_KEY", "")
BASE_URL     = "https://financialmodelingprep.com/api/v3"
BASE_URL_V4  = "https://financialmodelingprep.com/api/v4"
CACHE_DIR    = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)

# 300 req/min → 250ms間隔
_last_call   = 0.0
_MIN_INTERVAL = 0.25

def _throttle():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.time()

def _get(url: str, params: dict = {}, cache_key: str = "", ttl: int = 0) -> dict | list | None:
    """汎用GETリクエスト（キャッシュ対応）"""
    if cache_key:
        cf = CACHE_DIR / f"{cache_key}.pkl"
        if cf.exists() and (time.time() - cf.stat().st_mtime < ttl):
            try:
                with open(cf, "rb") as f: return pickle.load(f)
            except Exception: pass
    try:
        _throttle()
        resp = requests.get(url, params={**params, "apikey": FMP_API_KEY}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if cache_key and data:
            with open(CACHE_DIR / f"{cache_key}.pkl", "wb") as f: pickle.dump(data, f)
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print(f"Rate limit hit, sleeping 60s...")
            time.sleep(60)
        else:
            print(f"HTTP {e.response.status_code}: {url}")
        return None
    except Exception as e:
        print(f"FMP error: {e}")
        return None


# ── OHLCVデータ（12時間キャッシュ）──────────────────────
def get_historical_data(ticker: str, days: int = 700) -> pd.DataFrame | None:
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date   = datetime.now().strftime("%Y-%m-%d")
    data = _get(f"{BASE_URL}/historical-price-full/{ticker}",
                {"from": from_date, "to": to_date},
                cache_key=f"hist_{ticker}", ttl=12*3600)
    if not data or "historical" not in data or not data["historical"]:
        return None
    df = pd.DataFrame(data["historical"])
    df = df.rename(columns={"date":"Date","open":"Open","high":"High",
                             "low":"Low","close":"Close","volume":"Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df[["Open","High","Low","Close","Volume"]].copy()


# ── リアルタイムクォート ──────────────────────────────────
def get_quote(ticker: str) -> dict | None:
    data = _get(f"{BASE_URL}/quote/{ticker}")
    return data[0] if isinstance(data, list) and data else None


# ── 会社プロフィール（24時間キャッシュ）─────────────────
def get_company_profile(ticker: str) -> dict | None:
    data = _get(f"{BASE_URL}/profile/{ticker}",
                cache_key=f"profile_{ticker}", ttl=24*3600)
    return data[0] if isinstance(data, list) and data else None


# ── アナリスト評価・目標株価（24時間キャッシュ）──────────
def get_analyst_consensus(ticker: str) -> dict | None:
    """
    Returns: {
      consensus: 'Buy'|'Sell'|'Hold',
      analyst_count: int,
      target_high: float, target_low: float, target_mean: float,
      target_pct: float  (目標株価と現在値の乖離%)
    }
    """
    data = _get(f"{BASE_URL}/analyst-stock-recommendations/{ticker}",
                cache_key=f"analyst_{ticker}", ttl=24*3600)
    if not isinstance(data, list) or not data:
        return None
    # 直近3ヶ月の集計
    buy = sell = hold = 0
    for r in data[:6]:  # 直近6レコード（月次）
        buy  += r.get("analystRatingsbuy", 0) + r.get("analystRatingsStrongBuy", 0)
        hold += r.get("analystRatingsHold", 0)
        sell += r.get("analystRatingsSell", 0) + r.get("analystRatingsStrongSell", 0)
    total = buy + hold + sell
    if total == 0: return None

    # 目標株価
    tp = _get(f"{BASE_URL}/price-target-consensus/{ticker}",
              cache_key=f"pricetarget_{ticker}", ttl=24*3600)
    target_mean = tp[0].get("targetConsensus") if isinstance(tp, list) and tp else None
    target_high = tp[0].get("targetHigh")      if isinstance(tp, list) and tp else None
    target_low  = tp[0].get("targetLow")       if isinstance(tp, list) and tp else None

    # 現在値取得して乖離%計算
    quote = get_quote(ticker)
    price = float(quote.get("price", 0)) if quote else 0
    target_pct = round((target_mean - price) / price * 100, 1) if target_mean and price else None

    consensus = "Buy" if buy > sell and buy > hold else \
                "Sell" if sell > buy and sell > hold else "Hold"

    return {
        "consensus":     consensus,
        "analyst_count": total,
        "buy":  buy, "hold": hold, "sell": sell,
        "target_mean": round(target_mean, 2) if target_mean else None,
        "target_high": round(target_high, 2) if target_high else None,
        "target_low":  round(target_low,  2) if target_low  else None,
        "target_pct":  target_pct,
    }


# ── ファンダメンタルズ（TTM）────────────────────────────
def get_fundamentals(ticker: str) -> dict | None:
    """
    Returns: {
      pe_forward, pe_ttm, eps_ttm,
      revenue_growth_yoy, earnings_growth_yoy,
      gross_margin, profit_margin,
      debt_to_equity, current_ratio,
      market_cap_b (10億ドル単位)
    }
    """
    # Key Metrics TTM
    km = _get(f"{BASE_URL}/key-metrics-ttm/{ticker}",
              cache_key=f"keymetrics_{ticker}", ttl=24*3600)
    km = km[0] if isinstance(km, list) and km else {}

    # Income statement growth
    ig = _get(f"{BASE_URL}/income-statement-growth/{ticker}",
              {"limit": 2},
              cache_key=f"incgrowth_{ticker}", ttl=24*3600)
    ig = ig[0] if isinstance(ig, list) and ig else {}

    # Financial ratios TTM
    fr = _get(f"{BASE_URL}/ratios-ttm/{ticker}",
              cache_key=f"ratios_{ticker}", ttl=24*3600)
    fr = fr[0] if isinstance(fr, list) and fr else {}

    def _pct(v):
        return round(float(v)*100, 1) if v is not None else None
    def _rnd(v, n=2):
        return round(float(v), n) if v is not None else None

    return {
        "pe_forward":          _rnd(km.get("peRatioTTM")),
        "pe_ttm":              _rnd(fr.get("priceEarningsRatioTTM")),
        "eps_ttm":             _rnd(km.get("epsTTM")),
        "revenue_growth_yoy":  _pct(ig.get("growthRevenue")),
        "earnings_growth_yoy": _pct(ig.get("growthNetIncome")),
        "gross_margin":        _pct(fr.get("grossProfitMarginTTM")),
        "profit_margin":       _pct(fr.get("netProfitMarginTTM")),
        "debt_to_equity":      _rnd(fr.get("debtEquityRatioTTM")),
        "current_ratio":       _rnd(fr.get("currentRatioTTM")),
        "market_cap_b":        _rnd(km.get("marketCapTTM", 0) / 1e9, 1) if km.get("marketCapTTM") else None,
        "revenue_per_share":   _rnd(km.get("revenuePerShareTTM")),
        "roe":                 _pct(fr.get("returnOnEquityTTM")),
        "roa":                 _pct(fr.get("returnOnAssetsTTM")),
    }


# ── 機関投資家・インサイダー保有（24時間キャッシュ）──────
def get_ownership(ticker: str) -> dict | None:
    """
    Returns: {
      institutional_pct: float,   # 機関投資家保有率%
      insider_pct: float,         # インサイダー保有率%
      short_float_pct: float,     # 空売り比率%
      short_days_to_cover: float, # 空売り日数
    }
    """
    # 機関投資家保有率
    inst = _get(f"{BASE_URL}/institutional-holder/{ticker}",
                cache_key=f"inst_{ticker}", ttl=24*3600)

    # 空売りデータ
    short = _get(f"{BASE_URL}/short-float/{ticker}",
                 cache_key=f"short_{ticker}", ttl=24*3600)
    short = short[0] if isinstance(short, list) and short else {}

    # プロフィールから保有率取得（最も確実）
    profile = get_company_profile(ticker) or {}

    inst_pct   = None
    insider_pct = None
    # 機関保有率はプロフィールに含まれる場合がある
    if profile.get("institutionalOwnershipPercentage"):
        inst_pct = round(float(profile["institutionalOwnershipPercentage"]) * 100, 1)

    # 空売り
    short_float = None
    short_days  = None
    if short.get("shortFloatPercent"):
        short_float = round(float(short["shortFloatPercent"]), 1)
    if short.get("shortDaysToCover"):
        short_days = round(float(short["shortDaysToCover"]), 1)

    return {
        "institutional_pct":   inst_pct,
        "insider_pct":         insider_pct,
        "short_float_pct":     short_float,
        "short_days_to_cover": short_days,
    }


# ── 直近ニュース（6時間キャッシュ）──────────────────────
def get_news(ticker: str, limit: int = 5) -> list:
    """
    Returns: [{"title", "publishedDate", "source", "url", "summary"}, ...]
    """
    data = _get(f"{BASE_URL}/stock_news",
                {"tickers": ticker, "limit": limit},
                cache_key=f"news_{ticker}", ttl=6*3600)
    if not isinstance(data, list):
        return []
    return [{
        "title":         d.get("title", ""),
        "published_at":  d.get("publishedDate", ""),
        "source":        d.get("site", ""),
        "url":           d.get("url", ""),
        "summary":       d.get("text", "")[:200] if d.get("text") else "",
    } for d in data[:limit]]


# ── チャート用ローソク足データ（直近90日）────────────────
def get_candles_for_chart(ticker: str, days: int = 120) -> list:
    df = get_historical_data(ticker, days=days)
    if df is None: return []
    return [{
        "date":   d.strftime("%Y-%m-%d"),
        "open":   round(float(r["Open"]),  2),
        "high":   round(float(r["High"]),  2),
        "low":    round(float(r["Low"]),   2),
        "close":  round(float(r["Close"]), 2),
        "volume": int(r["Volume"]),
    } for d, r in df.iterrows()]
