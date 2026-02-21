#!/usr/bin/env python3
"""
generate_historical_20yf_full.py — FMP完全排除・yfinanceのみ・高速版
固定20銘柄で直近3ヶ月分の過去データを生成（計算ロジックは本番と同じ）
"""
import sys, json, time
from pathlib import Path
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent / "shared"))

from engines.analysis import VCPAnalyzer, RSAnalyzer
from engines.canslim import CANSLIMAnalyzer
from engines.ecr_strategy import ECRStrategyEngine
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer

# ====================== 固定20銘柄 ======================
FIXED_TICKERS = [
    "SMH", "WMT", "MRSH", "RGLD", "SHEL", "ELV", "INTU", "KMB", "BABA", "ZTS",
    "GEV", "QQQ", "CRWD", "PNC", "SLV", "VCIT", "JPM", "BP", "APH", "MO"
]

OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "public" / "content" / "strategies_history"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SLEEP_SECONDS = 4.0   # 取得時は少し丁寧に

def prefetch_all_data():
    """全20銘柄のデータを最初に1回だけ取得（高速化の核心）"""
    print(f"📥 {len(FIXED_TICKERS)}銘柄の全期間データを一括取得中...")
    data_map = {}
    fetch_start = "2025-08-01"   # 3ヶ月＋バッファ

    for ticker in FIXED_TICKERS:
        try:
            df = yf.download(ticker, start=fetch_start, end="2026-02-19", 
                             progress=False, threads=False)
            if not df.empty:
                data_map[ticker] = df
                print(f"  ✅ {ticker} 取得完了 ({len(df)}日分)")
            time.sleep(1.5)
        except Exception as e:
            print(f"  ❌ {ticker} 取得失敗: {e}")
    return data_map

def run_backtest():
    all_data = prefetch_all_data()

    current = datetime(2025, 11, 1)
    end = datetime(2026, 2, 18)

    print("\n🚀 Walk-forward生成開始...\n")

    while current <= end:
        target_str = current.strftime("%Y-%m-%d")
        results = []

        for ticker in FIXED_TICKERS:
            if ticker not in all_data:
                continue
            full_df = all_data[ticker]
            # 先読み防止：target_date 以前のデータのみ使用
            df_sliced = full_df[full_df.index <= target_str].copy()

            if len(df_sliced) < 130:
                continue

            try:
                vcp = VCPAnalyzer.calculate(df_sliced)
                rs_raw = RSAnalyzer.get_raw_score(df_sliced)
                rs_pct = min(99, max(0, int((rs_raw + 0.3) * 100))) if rs_raw != -999.0 else 0

                canslim = CANSLIMAnalyzer.calculate(ticker, df_sliced)
                ecr = ECRStrategyEngine.analyze_single(ticker, df_sliced)
                ses = SentinelEfficiencyAnalyzer.calculate(df_sliced)

                price = float(df_sliced["Close"].iloc[-1])
                pivot = float(df_sliced["High"].iloc[-50:].max())
                dist_pct = round((price - pivot) / pivot * 100, 2)

                results.append({
                    "ticker": ticker,
                    "scores": {
                        "vcp": vcp["score"],
                        "rs": rs_pct,
                        "canslim": canslim["score"],
                        "ecr_rank": ecr["sentinel_rank"],
                        "ses": ses["score"],
                        "composite": round(vcp["score"]*0.35 + rs_pct*0.35 + canslim["score"]*0.3, 1)
                    },
                    "status": "ACTION" if dist_pct <= 5 and vcp["score"] >= 55 else "WAIT",
                    "vcp_details": vcp,
                    "ses_details": ses,
                    "ecr_phase": ecr["phase"]
                })
            except:
                pass

        if results:
            file_path = OUTPUT_DIR / f"{target_str}.json"
            file_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"✅ {target_str}: {len(results)}銘柄保存")

        current += timedelta(days=1)

if __name__ == "__main__":
    start_time = time.time()
    run_backtest()
    elapsed = time.time() - start_time
    print(f"\n🎉 完了！ 所要時間: {elapsed/60:.1f} 分")