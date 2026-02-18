"""
scripts/debug_mag7_strategies.py
Magnificent 7 が generate_strategies.py の処理フローの中で
どのように判定され、なぜ最終出力から除外されているのかを特定する診断ツール。
"""
import sys, os
import pandas as pd
import numpy as np
from pathlib import Path

# パス設定: shared を読み込めるようにする
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from engines.ecr_strategy import ECRStrategyEngine
from engines.canslim import CANSLIMAnalyzer
from engines.config import CONFIG

# 診断対象：Magnificent 7
TARGETS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

def diagnose_ticker(ticker):
    print(f"\n{'='*60}")
    print(f"🔍 Analyzing: {ticker}")
    print(f"{'='*60}")

    # ---------------------------------------------------------
    # 1. データ取得フェーズ
    # ---------------------------------------------------------
    print(f"Step 1: Data Fetching...")
    df = core_fmp.get_historical_data(ticker, days=700)
    
    if df is None or len(df) < 200:
        print(f"  ❌ FAILED: データ取得失敗またはデータ不足 ({len(df) if df is not None else 'None'} rows)")
        return
    
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    price = float(df["Close"].iloc[-1])
    print(f"  ✅ SUCCESS: {len(df)} rows found. Latest: {latest_date}, Price: ${price:.2f}")

    # ---------------------------------------------------------
    # 2. ロジック判定フェーズ（Status決定）
    # ---------------------------------------------------------
    print(f"Step 2: Logic & Status Check...")
    
    # generate_strategies.py と同じロジック
    pivot = float(df["High"].iloc[-20:].max())  # 直近20日の最高値
    dist  = (price - pivot) / pivot             # ピボットからの乖離率
    
    # 判定ロジック
    if -0.05 <= dist <= 0.03:
        status = "ACTION"
        judge = "✅ INCLUDED (Ranking対象)"
    elif dist < -0.05:
        status = "WAIT"
        judge = "✅ INCLUDED (Ranking対象)"
    else:
        status = "EXTENDED"
        judge = "❌ EXCLUDED (Ranking除外対象)"

    print(f"  📊 Price Analysis:")
    print(f"     - Current Price: ${price:.2f}")
    print(f"     - Pivot (20d High): ${pivot:.2f}")
    print(f"     - Distance: {dist*100:+.2f}%")
    print(f"     👉 Determined Status: [{status}]")
    print(f"     👉 Final Verdict: {judge}")

    if status == "EXTENDED":
        print(f"     ⚠️  理由: 株価が直近高値より3%以上高い (+{dist*100:.2f}%) ため、\n           「高値掴み防止」のロジックによりリストから除外されています。")

    # ---------------------------------------------------------
    # 3. スコアリングフェーズ（ファンダメンタルズ含む）
    # ---------------------------------------------------------
    print(f"Step 3: Scoring & Fundamentals...")
    
    try:
        # VCP
        vcp = VCPAnalyzer.calculate(df)
        
        # CANSLIM (Fundametal取得確認)
        fund = core_fmp.get_fundamentals(ticker)
        own = core_fmp.get_ownership(ticker)
        
        has_fund = "✅ Yes" if fund else "❌ No (None)"
        # Institutional OwnershipはStarterプランだと取れないことがある
        inst_pct = own.get("institutional_pct") if own else None
        has_own  = f"✅ Yes ({inst_pct}%)" if inst_pct is not None else "⚠️ Partial/No (None returned)"

        canslim = CANSLIMAnalyzer.calculate(ticker, df, fund=fund or {}, own=own or {})
        
        # ECR
        ecr = ECRStrategyEngine.analyze_single(ticker, df)
        
        print(f"     - Fundamentals Data: {has_fund}")
        print(f"     - Ownership Data:    {has_own}")
        print(f"     - VCP Score: {vcp['score']}")
        print(f"     - CANSLIM Score: {canslim['score']} (Grade: {canslim['grade']})")
        print(f"     - ECR Rank: {ecr['sentinel_rank']}")
        
    except Exception as e:
        print(f"  ❌ SCORING ERROR: 計算中にエラーが発生しました: {e}")

def main():
    print("=== STARTING MAG7 DIAGNOSIS ===")
    for t in TARGETS:
        diagnose_ticker(t)
    print("\n=== DIAGNOSIS COMPLETE ===")

if __name__ == "__main__":
    main()


