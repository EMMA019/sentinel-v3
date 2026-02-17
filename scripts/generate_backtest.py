#!/usr/bin/env python3
"""
scripts/generate_backtest.py — 完全な売買シミュレーション
======================================================
4手法（VCP/CANSLIM/SES/ECR）ごとの勝率比較 +
100万円スタート複利シミュレーション
"""
import sys, json, os, time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

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

# 手法ごとのエントリー条件
METHOD_FILTERS = {
    "vcp": lambda scores: scores["vcp"] >= 60 and scores["rs_pct"] >= 60,
    "canslim": lambda scores: scores["canslim"] >= 40,
    "ses": lambda scores: scores["ses"] >= 40,
    "ecr": lambda scores: scores["ecr_rank"] >= 55,
    "all": lambda scores: True,  # 全トレード
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# シミュレーション本体
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def score_ticker_at(ticker: str, past_df: pd.DataFrame) -> dict:
    """1時点でのスコアを計算"""
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


def run_simulation(ticker: str, df: pd.DataFrame) -> list:
    """1銘柄の全期間をシミュレーション → トレードリスト"""
    trades   = []
    position = None
    df       = df.reset_index()

    for i in range(START_DELAY, len(df) - 1):
        today    = df.iloc[i]
        date_str = today["date"].strftime("%Y-%m-%d")

        # ── ポジション保有中: 決済判定 ────────────────────
        if position:
            low  = today["Low"]
            high = today["High"]
            exit_price  = None
            result_type = ""

            if low <= position["stop_price"]:
                exit_price  = min(today["Open"], position["stop_price"])
                result_type = "LOSS"
            elif high >= position["target_price"]:
                exit_price  = position["target_price"]
                result_type = "WIN"

            if exit_price:
                pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"] * 100
                trades.append({
                    "ticker":       ticker,
                    "entry_date":   position["date"],
                    "exit_date":    date_str,
                    "entry_price":  position["entry_price"],
                    "exit_price":   exit_price,
                    "pnl_pct":      round(pnl_pct, 2),
                    "type":         result_type,
                    "method_scores":position["scores"],
                })
                position = None
            continue

        # ── ノーポジ: エントリー判定 ──────────────────────
        close = today["Close"]
        ma50  = df["Close"].iloc[:i+1].rolling(50).mean().iloc[-1]
        if close < ma50:
            continue

        past_df = df.iloc[:i+1].set_index("date")
        scores  = score_ticker_at(ticker, past_df)
        if scores is None:
            continue

        # 最低限の条件（過去データに基づくROC）
        roc_63 = (close / df.iloc[i-63]["Close"] - 1) * 100 if i > 63 else 0
        if roc_63 < 10:
            continue

        pf = StrategyValidator.run(past_df)
        if pf < 0.8:
            continue

        vcp_result = VCPAnalyzer.calculate(past_df)
        if vcp_result["score"] < 40:
            continue

        atr         = vcp_result["atr"]
        stop_price  = close - (atr * STOP_ATR_MULT)
        risk        = close - stop_price
        target_price= close + (risk * TARGET_R)

        position = {
            "entry_price":  close,
            "stop_price":   stop_price,
            "target_price": target_price,
            "date":         date_str,
            "scores":       scores,
        }

    return trades


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 統計計算
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calc_stats(trades: list) -> dict:
    """トレードリストから統計を算出"""
    if not trades:
        return {
            "total_trades": 0, "win_rate": None,
            "profit_factor": None, "expectancy": None,
            "avg_win": None, "avg_loss": None, "max_loss": None,
        }

    df   = pd.DataFrame(trades)
    wins = df[df["pnl_pct"] > 0]
    loss = df[df["pnl_pct"] <= 0]

    win_count  = len(wins)
    loss_count = len(loss)
    total      = len(df)

    avg_win  = float(wins["pnl_pct"].mean()) if win_count > 0 else 0
    avg_loss = float(loss["pnl_pct"].mean()) if loss_count > 0 else 0

    gross_profit = float(wins["pnl_pct"].sum()) if win_count > 0 else 0
    gross_loss   = abs(float(loss["pnl_pct"].sum())) if loss_count > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    return {
        "total_trades":  total,
        "win_rate":      round(win_count / total * 100, 1),
        "profit_factor": round(pf, 2),
        "expectancy":    round(float(df["pnl_pct"].mean()), 2),
        "avg_win":       round(avg_win, 2),
        "avg_loss":      round(avg_loss, 2),
        "max_loss":      round(float(df["pnl_pct"].min()), 2),
    }


def compound_simulation(trades: list, method_filter=None) -> dict:
    """
    複利シミュレーション
    100万円スタート、毎回残高の10%を投入
    """
    if method_filter:
        filtered = [t for t in trades if method_filter(t.get("method_scores", {}))]
    else:
        filtered = trades

    if not filtered:
        return {
            "initial_capital": INITIAL_CAPITAL,
            "final_capital":   INITIAL_CAPITAL,
            "total_return":    0.0,
            "max_drawdown":    0.0,
            "cagr":            0.0,
            "total_trades":    0,
            "equity_curve":    [INITIAL_CAPITAL],
            "monthly":         [],
        }

    # 時系列順にソート
    sorted_trades = sorted(filtered, key=lambda t: t["entry_date"])

    capital      = INITIAL_CAPITAL
    peak_capital = INITIAL_CAPITAL
    max_drawdown = 0.0
    equity_curve = [INITIAL_CAPITAL]
    monthly_pnl  = {}

    for trade in sorted_trades:
        invest  = capital * POSITION_SIZE
        pnl     = invest * (trade["pnl_pct"] / 100)
        capital += pnl

        # ドローダウン
        if capital > peak_capital:
            peak_capital = capital
        dd = (peak_capital - capital) / peak_capital * 100
        if dd > max_drawdown:
            max_drawdown = dd

        equity_curve.append(round(capital))

        # 月別集計
        month = trade["entry_date"][:7]  # "2025-08"
        if month not in monthly_pnl:
            monthly_pnl[month] = {"trades": 0, "pnl_sum": 0.0, "wins": 0}
        monthly_pnl[month]["trades"] += 1
        monthly_pnl[month]["pnl_sum"] += trade["pnl_pct"]
        if trade["pnl_pct"] > 0:
            monthly_pnl[month]["wins"] += 1

    total_return = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    years        = LOOKBACK_DAYS / 365
    cagr         = ((capital / INITIAL_CAPITAL) ** (1 / years) - 1) * 100

    monthly_list = [{
        "month":     m,
        "trades":    v["trades"],
        "pnl_sum":   round(v["pnl_sum"], 1),
        "win_rate":  round(v["wins"] / v["trades"] * 100, 1) if v["trades"] > 0 else 0,
    } for m, v in sorted(monthly_pnl.items())]

    return {
        "initial_capital": INITIAL_CAPITAL,
        "final_capital":   round(capital),
        "total_return":    round(total_return, 1),
        "max_drawdown":    round(max_drawdown, 1),
        "cagr":            round(cagr, 1),
        "position_size":   POSITION_SIZE,
        "total_trades":    len(sorted_trades),
        "equity_curve":    equity_curve,
        "monthly":         monthly_list,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print(f"===== P&L BACKTEST ({datetime.now().strftime('%Y-%m-%d')}) =====")
    print(f"Target: {len(TICKERS)} tickers / Period: Last {LOOKBACK_DAYS} days")
    print(f"Strategy: Stop={STOP_ATR_MULT}xATR / Target={TARGET_R}xRisk")
    print(f"Simulation: ¥{INITIAL_CAPITAL:,.0f} start / {POSITION_SIZE*100:.0f}% position")
    print("-" * 60)

    all_trades  = []
    processed   = 0
    start_time  = time.time()

    for ticker in TICKERS:
        processed += 1

        df = core_fmp.get_historical_data(ticker, days=LOOKBACK_DAYS)
        if df is None or len(df) < START_DELAY + 20:
            continue

        trades = run_simulation(ticker, df)
        all_trades.extend(trades)

        if processed % 10 == 0:
            elapsed = time.time() - start_time
            print(f"  [{processed:>3}/{len(TICKERS)}] {elapsed:.0f}s elapsed / {len(all_trades)} trades so far")

    print("-" * 60)

    if not all_trades:
        print("❌ No trades generated.")
        return

    # ── 全体統計 ─────────────────────────────────────────
    overall_stats = calc_stats(all_trades)

    print(f"\n📊 OVERALL PERFORMANCE ({overall_stats['total_trades']} trades)")
    print(f"  Win Rate:       {overall_stats['win_rate']}%")
    print(f"  Profit Factor:  {overall_stats['profit_factor']}")
    print(f"  Avg Win:       +{overall_stats['avg_win']}%")
    print(f"  Avg Loss:       {overall_stats['avg_loss']}%")
    print(f"  Expectancy:    {'+' if overall_stats['expectancy']>0 else ''}{overall_stats['expectancy']}%")

    # ── 手法別統計 ───────────────────────────────────────
    print(f"\n📊 METHOD COMPARISON")
    method_stats = {}
    for method, filt in METHOD_FILTERS.items():
        filtered = [t for t in all_trades if filt(t.get("method_scores", {}))]
        stats    = calc_stats(filtered)
        method_stats[method] = stats
        wr  = stats.get("win_rate", 0) or 0
        pf  = stats.get("profit_factor", 0) or 0
        exp = stats.get("expectancy", 0) or 0
        n   = stats.get("total_trades", 0)
        print(f"  {method.upper():10s}: {n:>4}trades  WR={wr:>5.1f}%  PF={pf:>5.2f}  E={exp:>+.2f}%")

    # ── 複利シミュレーション ─────────────────────────────
    print(f"\n📈 COMPOUND SIMULATION (¥{INITIAL_CAPITAL:,.0f} / {POSITION_SIZE*100:.0f}% sizing)")
    sim_results = {}
    for method, filt in METHOD_FILTERS.items():
        sim = compound_simulation(all_trades, method_filter=filt)
        sim_results[method] = sim
        ret = sim["total_return"]
        dd  = sim["max_drawdown"]
        cagr= sim["cagr"]
        n   = sim["total_trades"]
        final = sim["final_capital"]
        print(f"  {method.upper():10s}: ¥{final:>12,.0f}  ({ret:>+.1f}%)  CAGR={cagr:>+.1f}%  MaxDD=-{dd:.1f}%  ({n}trades)")

    # ── トップ/ワーストトレード ──────────────────────────
    df_all = pd.DataFrame(all_trades)
    print(f"\n🏆 Top 5 Best Trades:")
    for _, t in df_all.nlargest(5, "pnl_pct").iterrows():
        print(f"  {t['ticker']:6s} {t['entry_date']} → {t['exit_date']} : +{t['pnl_pct']}%")

    print(f"\n💀 Worst 3 Trades:")
    for _, t in df_all.nsmallest(3, "pnl_pct").iterrows():
        print(f"  {t['ticker']:6s} {t['entry_date']} → {t['exit_date']} : {t['pnl_pct']}%")

    # ── JSON保存 ─────────────────────────────────────────
    out_file = Path(__file__).parent.parent / "frontend" / "public" / "content" / "backtest.json"
    out_file.write_text(json.dumps({
        "generated_at":   datetime.now().strftime("%Y-%m-%d"),
        "lookback_days":  LOOKBACK_DAYS,
        "ticker_count":   len(TICKERS),
        "overall":        overall_stats,
        "method_stats":   method_stats,
        "simulations":    sim_results,
        "top_trades":     df_all.nlargest(10, "pnl_pct")[
                              ["ticker","entry_date","exit_date","pnl_pct","type"]
                          ].to_dict("records"),
        "worst_trades":   df_all.nsmallest(5, "pnl_pct")[
                              ["ticker","entry_date","exit_date","pnl_pct","type"]
                          ].to_dict("records"),
    }, indent=2, ensure_ascii=False))

    print(f"\n✅ backtest.json saved")
    print(f"===== Done =====")


if __name__ == "__main__":
    main()
