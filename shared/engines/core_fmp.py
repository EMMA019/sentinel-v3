"""
core_fmp.py — Financial Modeling Prep API クライアント (2026年 最終確定版)
Starter プラン（$19/mo）: 300 req/min, 5年履歴, 米国株
大量スキャン時の安定性と、プラン制限下での実数抽出を極限まで強化。
"""
import os, time, requests, pickle, pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path

# 環境変数からキーを取得
FMP_API_KEY  = os.environ.get("FMP_API_KEY", "")

# ベースURL設定
BASE_URL_STABLE = "https://financialmodelingprep.com/stable"
BASE_URL_V3     = "https://financialmodelingprep.com/api/v3"
BASE_URL_V4     = "https://financialmodelingprep.com/api/v4"

# キャッシュディレクトリ
CACHE_DIR    = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# 制限: 300 req/min → 安全のため 300ms 間隔（実質 200 req/min）に緩和
_last_call   = 0.0
_MIN_INTERVAL = 0.3 

def _throttle():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.time()

def _get(endpoint: str, params: dict = {}, cache_key: str = "", ttl: int = 0, use_path: bool = None, debug: bool = False) -> dict | list | None:
    """
    Stable / v3 / v4 を自動判別してリクエスト（キャッシュ対応）。
    """
    if not FMP_API_KEY:
        return None

    if cache_key:
        cf = CACHE_DIR / f"{cache_key}.pkl"
        if cf.exists() and (time.time() - cf.stat().st_mtime < ttl):
            try:
                with open(cf, "rb") as f: return pickle.load(f)
            except Exception: pass

    try:
        _throttle()
        
        # エンドポイント判別
        is_v3 = endpoint.startswith("v3/")
        if endpoint.startswith("v4/"):
            url = f"{BASE_URL_V4}/{endpoint.replace('v4/', '')}"
        elif is_v3:
            url = f"{BASE_URL_V3}/{endpoint.replace('v3/', '')}"
        else:
            url = f"{BASE_URL_STABLE}/{endpoint.replace('stable/', '')}"

        # パス形式かクエリ形式かの決定
        if use_path is None:
            # 歴史的に v3/historical-price-full や v3/quote はパス形式必須
            # ただし、特定のV3統計系はクエリ形式の方が安定する場合があるため、個別に指定可能にする
            use_path = True if is_v3 else False

        symbol = params.get("symbol")
        params_to_send = params.copy()

        if symbol:
            if use_path:
                url = f"{url}/{symbol}"
                if "symbol" in params_to_send: del params_to_send["symbol"]

        full_params = {**params_to_send, "apikey": FMP_API_KEY}
        resp = requests.get(url, params=full_params, timeout=15)
        
        if resp.status_code != 200:
            if debug: print(f"DEBUG [HTTP {resp.status_code}]: {url}")
            return None
            
        data = resp.json()
        
        # エラーメッセージが含まれている場合は失敗とみなす
        if isinstance(data, dict) and ("Error Message" in data or "error" in data):
            if debug: print(f"DEBUG [FMP Error]: {data.get('Error Message') or data.get('error')}")
            return None

        if cache_key and data:
            with open(CACHE_DIR / f"{cache_key}.pkl", "wb") as f: 
                pickle.dump(data, f)
        return data
    except Exception as e:
        if debug: print(f"FMP exception: {e}")
        return None

# ── OHLCVデータ（12時間キャッシュ）──────────────────────
def get_historical_data(ticker: str, days: int = 700) -> pd.DataFrame | None:
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date   = datetime.now().strftime("%Y-%m-%d")
    data = _get("v3/historical-price-full", 
                {"symbol": ticker, "from": from_date, "to": to_date},
                cache_key=f"hist_{ticker}", ttl=12*3600, use_path=True)
    
    if not data or not isinstance(data, dict) or "historical" not in data:
        return None
    df = pd.DataFrame(data["historical"])
    if df.empty: return None
    
    df = df.rename(columns={"date":"Date","open":"Open","high":"High",
                             "low":"Low","close":"Close","volume":"Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df[["Open","High","Low","Close","Volume"]].copy()

# ── リアルタイムクォート ──────────────────────────────────
def get_quote(ticker: str) -> dict | None:
    data = _get("v3/quote", {"symbol": ticker}, use_path=True)
    return data[0] if isinstance(data, list) and data else None

# ── 会社プロフィール ────────────────────────────────────
def get_company_profile(ticker: str) -> dict | None:
    data = _get("v3/profile", {"symbol": ticker},
                cache_key=f"profile_{ticker}", ttl=24*3600, use_path=True)
    return data[0] if isinstance(data, list) and data else None

# ── アナリスト分析（Starter実数対応版）──────────────────────
def get_analyst_consensus(ticker: str) -> dict | None:
    """
    Starterプランの制限を回避しつつ、実数データを抽出。
    """
    buy = sell = hold = 0
    total_analysts = 0
    
    # 1. 人数（numAnalystsEps）の取得 - パス形式が安定
    est_data = _get("v3/analyst-estimates", {"symbol": ticker, "period": "annual"},
                    cache_key=f"est_{ticker}", ttl=24*3600, use_path=True)
    if est_data and isinstance(est_data, list):
        counts = [e.get("numAnalystsEps", 0) or 0 for e in est_data]
        total_analysts = max(counts) if counts else 0

    # 2. 内訳の抽出 (price-target-summary: クエリ形式)
    pts = _get("stable/price-target-summary", {"symbol": ticker},
               cache_key=f"pts_{ticker}", ttl=24*3600, use_path=False)
    
    if pts and isinstance(pts, list) and len(pts) > 0:
        publishers = pts[0].get("publishers", [])
        if isinstance(publishers, list):
            for entry in publishers:
                rating = str(entry.get("rating", "")).lower() if isinstance(entry, dict) else str(entry).lower()
                if any(x in rating for x in ["buy", "overweight", "outperform", "positive"]):
                    buy += 1
                elif any(x in rating for x in ["sell", "underweight", "underperform", "negative"]):
                    sell += 1
                elif any(x in rating for x in ["hold", "neutral", "equal-weight"]):
                    hold += 1
    
    # 3. 目標株価の取得 (V3 consensus)
    tp = _get("v3/price-target-consensus", {"symbol": ticker},
              cache_key=f"pt_{ticker}", ttl=24*3600, use_path=True)
    tp_data = tp[0] if isinstance(tp, list) and tp else {}
    target_mean = tp_data.get("targetConsensus")
    target_high = tp_data.get("targetHigh")
    target_low  = tp_data.get("targetLow")

    # 4. 乖離率の計算
    quote = get_quote(ticker)
    price = float(quote.get("price", 0)) if quote else 0
    target_pct = round((target_mean - price) / price * 100, 1) if target_mean and price else None

    consensus = "Hold"
    if buy > sell and buy > hold:
        consensus = "Buy"
    elif target_pct is not None:
        if target_pct > 15: consensus = "Buy"
        elif target_pct < -5: consensus = "Sell"

    return {
        "consensus":     consensus,
        "analyst_count": total_analysts or (buy + hold + sell),
        "buy": buy, "hold": hold, "sell": sell,
        "target_mean":   round(target_mean, 2) if target_mean else None,
        "target_high":   round(target_high, 2) if target_high else None,
        "target_low":    round(target_low,  2) if target_low  else None,
        "target_pct":    target_pct,
    }

# ── ファンダメンタルズ（TTM）────────────────────────────
def get_fundamentals(ticker: str) -> dict | None:
    # 銘柄スキャンを通過させるため、リクエストとフォールバックを強化
    km = _get("v3/key-metrics-ttm", {"symbol": ticker}, cache_key=f"km_{ticker}", ttl=24*3600, use_path=True)
    ig = _get("v3/income-statement-growth", {"symbol": ticker, "limit": 2}, cache_key=f"ig_{ticker}", ttl=24*3600, use_path=True)
    fr = _get("v3/ratios-ttm", {"symbol": ticker}, cache_key=f"fr_{ticker}", ttl=24*3600, use_path=True)
    
    km = km[0] if isinstance(km, list) and km else {}
    ig = ig[0] if isinstance(ig, list) and ig else {}
    fr = fr[0] if isinstance(fr, list) and fr else {}

    def _pct(v): return round(float(v)*100, 1) if v is not None else None
    def _rnd(v, n=2): return round(float(v), n) if v is not None else None

    # 時価総額のフォールバック (kmから取れない場合はquoteから取得)
    market_cap = km.get("marketCapTTM")
    if not market_cap:
        q = get_quote(ticker)
        if q: market_cap = q.get("marketCap")

    return {
        "pe_forward":        _rnd(km.get("peRatioTTM")),
        "pe_ttm":            _rnd(fr.get("priceEarningsRatioTTM")),
        "eps_ttm":           _rnd(km.get("epsTTM")),
        "revenue_growth_yoy": _pct(ig.get("growthRevenue")),
        "earnings_growth_yoy":_pct(ig.get("growthNetIncome")),
        "gross_margin":      _pct(fr.get("grossProfitMarginTTM")),
        "profit_margin":     _pct(fr.get("netProfitMarginTTM")),
        "debt_to_equity":    _rnd(fr.get("debtEquityRatioTTM")),
        "current_ratio":     _rnd(fr.get("currentRatioTTM")),
        "market_cap_b":      _rnd(float(market_cap) / 1e9, 1) if market_cap else 0.0,
        "roe":               _pct(fr.get("returnOnEquityTTM")),
    }

# ── 保有・空売りデータ ──────────────────────────────────
def get_ownership(ticker: str) -> dict | None:
    short = _get("v4/short-float", {"symbol": ticker}, cache_key=f"short_{ticker}", ttl=24*3600, use_path=False)
    short_data = short[0] if isinstance(short, list) and short else {}
    profile = get_company_profile(ticker) or {}
    return {
        "institutional_pct":   round(float(profile.get("institutionalOwnershipPercentage", 0)) * 100, 1),
        "short_float_pct":     round(float(short_data.get("shortFloatPercent", 0)), 1) if short_data.get("shortFloatPercent") else None,
    }

# ── 直近ニュース ──────────────────────────────────────
def get_news(ticker: str, limit: int = 5) -> list:
    data = _get("v3/stock_news", {"tickers": ticker, "limit": limit},
                cache_key=f"news_{ticker}", ttl=6*3600, use_path=False)
    if not isinstance(data, list): return []
    return [{
        "title":         d.get("title", ""),
        "published_at":  d.get("publishedDate", ""),
        "source":        d.get("site", ""),
        "url":           d.get("url", ""),
        "summary":       d.get("text", "")[:200] if d.get("text") else "",
    } for d in data[:limit]]

# ── チャート用ヘルパー ──────────────────────────────────
def get_candles_for_chart(ticker: str, days: int = 120) -> list:
    df = get_historical_data(ticker, days=days)
    if df is None or df.empty: return []
    return [{
        "date":   d.strftime("%Y-%m-%d"),
        "open":   round(float(r["Open"]),  2),
        "high":   round(float(r["High"]),  2),
        "low":    round(float(r["Low"]),   2),
        "close":  round(float(r["Close"]), 2),
        "volume": int(r["Volume"]),
    } for d, r in df.iterrows()]
