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
# API KEY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if not os.getenv("FMP_API_KEY"):
    print("❌ FMP_API_KEY not set")
    sys.exit(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# パス設定
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from engines.ecr_strategy import ECRStrategyEngine
from engines.canslim import CANSLIMAnalyzer
from engines.config import CONFIG, TICKERS

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 設定
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOOKBACK_DAYS = 400
START_DELAY = 200
STOP_ATR_MULT = CONFIG["STOP_LOSS_ATR"]
TARGET_R = CONFIG["TARGET_R_MULTIPLE"]

MAX_WORKERS = 5

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# スコア取得
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
    except:
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 単銘柄バックテスト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def backtest_ticker(ticker):
    trades = []

    df = core_fmp.get_historical_data(ticker, days=LOOKBACK_DAYS)
    if df is None or len(df) < START_DELAY + 10:
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
# 統計
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calc_stats(trades):
    if not trades:
        return {}

    df = pd.DataFrame(trades)
    wins = df[df["pnl_pct"] > 0]
    loss = df[df["pnl_pct"] <= 0]

    pf = wins["pnl_pct"].sum() / abs(loss["pnl_pct"].sum()) if not loss.empty else float("inf")

    return {
        "total_trades": len(df),
        "win_rate": round(len(wins)/len(df)*100,1),
        "profit_factor": round(pf,2),
        "expectancy": round(df["pnl_pct"].mean(),2)
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
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
    print(f"✅ Done in {(time.time()-start)/60:.1f} min")
    print(f"📁 JSON saved: {output}")

if __name__ == "__main__":
    main()