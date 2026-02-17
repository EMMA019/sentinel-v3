#!/usr/bin/env python3
"""
scripts/generate_backtest.py — 完全な売買シミュレーション（並列高速版）
======================================================
4手法（VCP/CANSLIM/SES/ECR）ごとの勝率比較 +
100万円スタート複利シミュレーションを並列実行で高速化。
"""
import sys, json, os, time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(str(Path(__file__).parent.parent / "shared"))

from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from engines.ecr_strategy import ECRStrategyEngine
from engines.canslim import CANSLIMAnalyzer
from engines.config import CONFIG, TICKERS

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 設定
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOOKBACK_DAYS  = 400   # 過去何日分をテストするか
START_DELAY    = 200   # MA計算に必要な初期期間
STOP_ATR_MULT  = CONFIG["STOP_LOSS_ATR"]
TARGET_R       = CONFIG["TARGET_R_MULTIPLE"]
INITIAL_CAPITAL = 1_000_000  # 100万円
POSITION_SIZE   = 0.10       # 残高の10%を毎回投入
MAX_WORKERS    = 5          # API負荷を考慮した同時並列数

# 手法ごとのエントリー条件
METHOD_FILTERS = {
    "vcp": lambda scores: scores["vcp"] >= 60 and scores["rs_pct"] >= 60,
    "canslim": lambda scores: scores["canslim"] >= 40,
    "ses": lambda scores: scores["ses"] >= 40,
    "ecr": lambda scores: scores["ecr_rank"] >= 55,
    "all": lambda scores: True,
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# シミュレーション・ロジック
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def score_ticker_at(ticker: str, past_df: pd.DataFrame) -> dict:
    """特定時点での全スコアを一括計算"""
    try:
        vcp     = VCPAnalyzer.calculate(past_df)
        pf      = StrategyValidator.run(past_df)
        ses     = SentinelEfficiencyAnalyzer.calculate(past_df)
        ecr     = ECRStrategyEngine.analyze_single(ticker, past_df)
        canslim = CANSLIMAnalyzer.calculate(ticker, past_df)

        rs_raw = RSAnalyzer.get_raw_score(past_df)
        rs_pct = int(np.clip((rs_raw + 0.3) * 100, 0, 100)) if rs_raw != -999.0 else 0

        return {
            "vcp":      vcp["score"],
            "atr":      vcp["atr"],
            "pf":       pf,
            "ses":      ses["score"],
            "ecr_rank": ecr["sentinel_rank"],
            "ecr_phase":ecr["phase"],
            "canslim":  canslim["score"],
            "rs_pct":   rs_pct,
        }
    except:
        return None

def run_simulation_for_ticker(ticker: str):
    """1銘柄のバックテスト実行ユニット"""
    try:
        df = core_fmp.get_historical_data(ticker, days=LOOKBACK_DAYS)
        if df is None or len(df) < START_DELAY + 20:
            return []

        trades = []
        position = None
        df_reset = df.reset_index()

        for i in range(START_DELAY, len(df_reset) - 1):
            today = df_reset.iloc[i]
            date_str = today["date"].strftime("%Y-%m-%d")

            if position:
                # 決済判定
                low, high = today["Low"], today["High"]
                exit_price, result_type = None, ""

                if low <= position["stop_price"]:
                    exit_price = min(today["Open"], position["stop_price"])
                    result_type = "LOSS"
                elif high >= position["target_price"]:
                    exit_price = position["target_price"]
                    result_type = "WIN"

                if exit_price:
                    pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"] * 100
                    trades.append({
                        "ticker": ticker,
                        "entry_date": position["date"],
                        "exit_date": date_str,
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "pnl_pct": round(pnl_pct, 2),
                        "type": result_type,
                        "method_scores": position["scores"],
                    })
                    position = None
                continue

            # エントリー判定
            close = today["Close"]
            # 50日移動平均チェック
            ma50 = df_reset["Close"].iloc[:i+1].rolling(50).mean().iloc[-1]
            if close < ma50: continue

            past_df = df_reset.iloc[:i+1].set_index("date")
            scores = score_ticker_at(ticker, past_df)
            if not scores: continue

            # 基本フィルタ
            roc_63 = (close / df_reset.iloc[i-63]["Close"] - 1) * 100 if i > 63 else 0
            if roc_63 < 10 or scores["pf"] < 0.8 or scores["vcp"] < 40:
                continue

            # ポジション構築
            atr = scores["atr"]
            stop_price = close - (atr * STOP_ATR_MULT)
            risk = close - stop_price
            target_price = close + (risk * TARGET_R)

            position = {
                "entry_price": close,
                "stop_price": stop_price,
                "target_price": target_price,
                "date": date_str,
                "scores": scores,
            }
        return trades
    except Exception as e:
        print(f"  ❌ Error processing {ticker}: {e}")
        return []

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 集計・シミュレーション
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calc_stats(trades: list) -> dict:
    if not trades: return {"total_trades": 0}
    df = pd.DataFrame(trades)
    wins, loss = df[df["pnl_pct"] > 0], df[df["pnl_pct"] <= 0]
    total = len(df)
    pf = wins["pnl_pct"].sum() / abs(loss["pnl_pct"].sum()) if not loss.empty else float('inf')
    return {
        "total_trades": total,
        "win_rate": round(len(wins) / total * 100, 1),
        "profit_factor": round(pf, 2),
        "expectancy": round(df["pnl_pct"].mean(), 2),
        "avg_win": round(wins["pnl_pct"].mean(), 2) if not wins.empty else 0,
        "avg_loss": round(loss["pnl_pct"].mean(), 2) if not loss.empty else 0,
    }

def compound_simulation(trades: list, method_filter=None) -> dict:
    filtered = [t for t in trades if method_filter(t.get("method_scores", {}))] if method_filter else trades
    if not filtered: return {"final_capital": INITIAL_CAPITAL, "total_return": 0, "total_trades": 0}
    
    sorted_trades = sorted(filtered, key=lambda t: t["entry_date"])
    capital = peak = INITIAL_CAPITAL
    max_dd = 0.0
    
    for t in sorted_trades:
        invest = capital * POSITION_SIZE
        capital += invest * (t["pnl_pct"] / 100)
        peak = max(peak, capital)
        max_dd = max(max_dd, (peak - capital) / peak * 100)

    ret = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    cagr = ((capital / INITIAL_CAPITAL) ** (1 / (LOOKBACK_DAYS/365)) - 1) * 100
    return {
        "final_capital": round(capital),
        "total_return": round(ret, 1),
        "cagr": round(cagr, 1),
        "max_drawdown": round(max_dd, 1),
        "total_trades": len(sorted_trades)
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    start_time = time.time()
    print(f"===== PARALLEL BACKTEST START ({datetime.now().strftime('%Y-%m-%d')}) =====")
    print(f"Tickers: {len(TICKERS)} / Workers: {MAX_WORKERS} / Stop: {STOP_ATR_MULT}xATR")

    all_trades = []
    processed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_ticker = {executor.submit(run_simulation_for_ticker, t): t for t in TICKERS}
        for future in as_completed(future_to_ticker):
            processed += 1
            all_trades.extend(future.result())
            if processed % 20 == 0:
                elapsed = time.time() - start_time
                print(f"  [{processed:>3}/{len(TICKERS)}] {elapsed:.0f}s elapsed / {len(all_trades)} trades")

    print("-" * 60)
    if not all_trades:
        print("❌ No trades generated.")
        return

    # 統計
    stats = calc_stats(all_trades)
    print(f"📊 OVERALL: {stats['total_trades']} trades / WR: {stats['win_rate']}% / PF: {stats['profit_factor']} / E: {stats['expectancy']}%")

    # 手法比較 & 複利シミュ
    method_results = {}
    print(f"\n📈 COMPOUND SIMULATION (¥{INITIAL_CAPITAL:,.0f} start)")
    for name, filt in METHOD_FILTERS.items():
        sim = compound_simulation(all_trades, method_filter=filt)
        method_results[name] = sim
        print(f"  {name.upper():8s}: ¥{sim['final_capital']:>12,.0f} ({sim['total_return']:>+7.1f}%) CAGR: {sim['cagr']:>+6.1f}% DD: -{sim['max_drawdown']}%")

    # 保存
    out_file = Path(__file__).parent.parent / "frontend" / "public" / "content" / "backtest.json"
    out_file.write_text(json.dumps({
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "overall": stats,
        "methods": method_results,
        "trades": all_trades[:200] # 容量削減のため一部のみ保存
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Done. Total Time: {(time.time() - start_time)/60:.1f} min")

if __name__ == "__main__":
    main()

