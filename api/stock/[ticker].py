import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / 'shared'))

from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer
from engines.config import CONFIG
import pandas as pd


def handler(request):
    ticker = request.path_params.get('ticker', '').upper().strip()
    if not ticker:
        return {"error": "ticker is required"}, 400

    df = core_fmp.get_historical_data(ticker, days=700)
    if df is None or len(df) < 200:
        return {"error": f"Insufficient data for {ticker}"}, 404

    vcp      = VCPAnalyzer.calculate(df)
    rs_raw   = RSAnalyzer.get_raw_score(df)
    rs_rating = min(99, max(1, int((rs_raw + 1) * 50)))

    # 最新クォート（リアルタイム価格優先）
    quote = core_fmp.get_quote(ticker)
    price = float(quote.get('price', 0)) if quote else float(df['Close'].iloc[-1])
    if not price:
        price = float(df['Close'].iloc[-1])

    # トレードレベル計算
    pivot  = float(df['High'].iloc[-20:].max())
    entry  = round(pivot * 1.002, 2)
    stop   = round(entry - vcp['atr'] * CONFIG['STOP_LOSS_ATR'], 2)
    target = round(entry + (entry - stop) * CONFIG['TARGET_R_MULTIPLE'], 2)
    dist   = (price - pivot) / pivot * 100
    status = "ACTION" if -5 <= dist <= 3 else ("WAIT" if dist < -5 else "EXTENDED")

    # ローソク足データ（直近180日）
    cutoff  = df.index[-1] - pd.DateOffset(days=180)
    df_plot = df[df.index >= cutoff]
    candles = [
        {
            "date":   d.strftime("%Y-%m-%d"),
            "open":   round(float(r["Open"]),  2),
            "high":   round(float(r["High"]),  2),
            "low":    round(float(r["Low"]),   2),
            "close":  round(float(r["Close"]), 2),
            "volume": int(r["Volume"]),
        }
        for d, r in df_plot.iterrows()
    ]

    # 会社プロフィール
    profile = core_fmp.get_company_profile(ticker) or {}

    return {
        "ticker":   ticker,
        "status":   status,
        "price":    round(price, 2),
        "dist_pct": round(dist, 2),
        "vcp":      vcp,
        "rs":       rs_rating,
        "trade": {
            "entry":  entry,
            "stop":   stop,
            "target": target,
        },
        "profile": {
            "sector":      profile.get("sector", "N/A"),
            "industry":    profile.get("industry", "N/A"),
            "description": profile.get("description", ""),
            "exchange":    profile.get("exchangeShortName", ""),
        },
        "candles": candles,
    }
