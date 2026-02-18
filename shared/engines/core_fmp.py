"""
core_fmp.py — FMP API Client (Starter Plan)
============================================
FMPの新エンドポイント (/stable/) 対応版。
機関投資家データの取得ロジックを強化し、Mag7等の大型株に対応。
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
# キャッシュ付きGET（429リトライ機能付き）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get(url: str, params: dict = None, cache_key: str = None, ttl: int = 3600):
    params = params or {}
    if cache_key:
        h = hashlib.md5(cache_key.encode()).hexdigest()
        cache_file = CACHE_DIR / f"{h}.json"
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime < ttl):
            try:
                return json.loads(cache_file.read_text())
            except:
                pass  # キャッシュ破損時は無視

    # --- 429対策: リクエスト前に常に短いウェイトを置く ---
    time.sleep(0.25)

    max_retries = 5
    for i in range(max_retries):
        try:
            resp = requests.get(url, params={**params, "apikey": FMP_API_KEY}, timeout=15)

            # 429 (Too Many Requests) の場合は指数バックオフでリトライ
            if resp.status_code == 429:
                wait_time = (2 ** i)
                print(f"  ⚠️ Rate limit hit (429). Waiting {wait_time}s... (Retry {i+1}/{max_retries})")
                time.sleep(wait_time)
                continue

            if resp.status_code == 403:
                # print(f"HTTP 403: {url}") # ノイズになるためコメントアウト
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

    # 【修正】Stable API はリストが直接返ってくる、それ以外は "historical" キーを探す
    hist = None
    if isinstance(data, list):
        hist = data
    elif isinstance(data, dict) and "historical" in data:
        hist = data["historical"]

    if not hist:
        return None

    df = pd.DataFrame(hist)
    
    # 日付変換エラー対策
    try:
        df["date"] = pd.to_datetime(df["date"])
    except Exception:
        return None

    df = df.set_index("date").sort_index()

    # カラム名マッピング（存在チェック付き）
    rename_map = {
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume"
    }
    
    # 必要なカラムが揃っているか確認
    if not all(col in df.columns for col in rename_map.keys()):
        return None

    df = df.rename(columns=rename_map)

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
    /stable/analyst-stock-recommendations?symbol={ticker} — Buy/Hold/Sell内訳
    24時間キャッシュ
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
        for r in recommendations[:6]:  # 直近6レコード
            buy  += r.get("analystRatingsbuy", 0) + r.get("analystRatingsStrongBuy", 0)
            hold += r.get("analystRatingsHold", 0)
            sell += r.get("analystRatingsSell", 0) + r.get("analystRatingsStrongSell", 0)

    total = buy + hold + sell
    consensus = None
    if total > 0:
        consensus = "Buy" if buy > sell and buy > hold else \
                    "Sell" if sell > buy and sell > hold else "Hold"

    # 目標株価の正規化（List or Dict）
    target_data = {}
    if isinstance(target, list) and target:
        target_data = target[0]
    elif isinstance(target, dict):
        target_data = target
    
    target_mean = target_data.get("lastMonthAvgPriceTarget")
    target_pct  = None

    # 現在値との乖離%計算
    if target_mean:
        quote = get_quote(ticker)
        if quote and quote.get("price"):
            price = float(quote["price"])
            if price > 0:
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
# 機関投資家保有（修正版）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_ownership(ticker: str) -> dict | None:
    """
    1. プロフィールからの取得を試みる
    2. 失敗した場合、/institutional-ownership エンドポイントを試みる（フォールバック）
    ※Starterプランでは大型株のProfileにデータが入っていない場合があるため
    """
    # 試行1: プロフィール (軽量)
    profile = get_company_profile(ticker) or {}
    inst_pct = None
    
    if profile.get("institutionalOwnershipPercentage"):
        val = profile["institutionalOwnershipPercentage"]
        try:
            inst_pct = round(float(val) * 100, 1)
        except:
            pass

    # 試行2: 専用エンドポイント (フォールバック)
    if inst_pct is None:
        # キャッシュキーは inst_own_{ticker} で管理
        own_data = _get(f"{BASE_URL}/institutional-ownership",
                        {"symbol": ticker, "limit": 1},
                        cache_key=f"inst_own_{ticker}", ttl=24*3600)
        
        # 形式: [{"symbol": "AAPL", "ownershipPercent": 0.58, ...}]
        if own_data and isinstance(own_data, list):
            item = own_data[0]
            # フィールド名の揺れに対応 (ownershipPercent または institutionalOwnershipPercentage)
            val = item.get("institutionalOwnershipPercentage") or item.get("ownershipPercent")
            if val:
                try:
                    inst_pct = round(float(val) * 100, 1)
                except:
                    pass

    return {
        "institutional_pct":   inst_pct,
        "insider_pct":         None,  # Starterでは非対応
        "short_float_pct":     None,  # Starterでは非対応
        "short_days_to_cover": None,  # Starterでは非対応
    }


