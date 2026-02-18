#!/usr/bin/env python3

import os
import sys
import json
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API KEY CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if not os.getenv("FMP_API_KEY"):
    print("❌ FMP_API_KEY not set")
    sys.exit(1)

print("✅ FMP_API_KEY detected")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PATH FIX (GitHub Actions対応)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BASE_DIR = Path(__file__).resolve().parent.parent

# ルートを追加
sys.path.insert(0, str(BASE_DIR))

# sharedを追加
sys.path.insert(0, str(BASE_DIR / "shared"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IMPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from shared.engines import core_fmp
from shared.engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from shared.engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from shared.engines.ecr_strategy import ECRStrategyEngine
from shared.engines.canslim import CANSLIMAnalyzer
from shared.engines.config import CONFIG, TICKERS

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SETTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOOKBACK_DAYS = 400
START_DELAY = 200
MAX_WORKERS = 5

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCORE CALC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def score_all(ticker, df):
    try:
        vcp = VCPAnalyzer.calculate(df)
        pf = StrategyValidator.run(df)
        ses = SentinelEfficiencyAnalyzer.calculate(df)
        ecr = ECRStrategyEngine.analyze_single(ticker, df)
        canslim = CANSLIMAnalyzer.calculate(ticker, df)

        rs_raw = RSAnalyzer.get_raw_score(df)
        rs_pct = int(np.clip((rs_raw + 0.3) * 100, 0, 100)) if rs_raw != -999 else 0

        return {
            "vcp": vcp["score"],
            "ses": ses["score"],
            "ecr": ecr["sentinel_rank"],
            "canslim": canslim["score"],
            "rs_pct": rs_pct,
            "pf": pf
        }
    except Exception as e:
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLE TICKER BACKTEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def backtest_ticker(ticker):
    trades = []

    df = core_fmp.get_historical_data(ticker, days=LOOKBACK_DAYS)
    if df is None or len(df) < START_DELAY + 5:
        return trades

    df = df.reset_index()

    for i in range(START_DELAY, len(df)-1):
        close = df.iloc[i]["Close"]
        past = df.iloc[:i+1].set_index("date")

        scores = score_all(ticker, past)
        if not scores:
            continue

        # 最低条件
        if scores["pf"] < 0.8 or scores["vcp"] < 40:
            continue

        entry = close
        exit_price = df.iloc[i+1]["Close"]
        pnl = (exit_price - entry) / entry * 100

        trades.append({
            "ticker": ticker,
            "date": df.iloc[i]["date"].strftime("%Y-%m-%d"),
            "pnl_pct": round(pnl, 2),
            "scores": scores
        })

    return trades

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATISTICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calc_stats(trades):
    if not trades:
        return {}

    df = pd.DataFrame(trades)
    wins = df[df["pnl_pct"] > 0]
    losses = df[df["pnl_pct"] <= 0]

    pf = wins["pnl_pct"].sum() / abs(losses["pnl_pct"].sum()) if not losses.empty else float("inf")

    return {
        "total_trades": len(df),
        "win_rate": round(len(wins)/len(df)*100, 1),
        "profit_factor": round(pf, 2),
        "expectancy": round(df["pnl_pct"].mean(), 2)
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("🚀 Running Backtest...")
    start = time.time()

    all_trades = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(backtest_ticker, t) for t in TICKERS]
        for f in as_completed(futures):
            all_trades.extend(f.result())

    stats = calc_stats(all_trades)

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "overall": stats,
        "sample_trades": all_trades[:200]
    }

    output = BASE_DIR / "backtest.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("📊 Result:")
    print(json.dumps(stats, indent=2))
    print(f"📁 JSON saved: {output}")
    print(f"⏱ Done in {(time.time()-start)/60:.1f} min")

if __name__ == "__main__":
    main()