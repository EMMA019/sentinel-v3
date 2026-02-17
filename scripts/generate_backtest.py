#!/usr/bin/env python3
"""
scripts/generate_backtest.py — 完全な売買シミュレーション
======================================================
VCPシグナルに基づいて架空の売買を行い、
「勝率」「PF」「トータルリターン」を算出します。
"""
import sys, json, os, time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# パス設定
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.config import CONFIG, TICKERS

# バックテスト設定
LOOKBACK_DAYS = 400     # 過去何日分をテストするか
START_DELAY   = 200     # 移動平均線の計算に必要な初期期間（スキップする日数）

# 資金管理ルール（config.pyの設定を使用）
STOP_ATR_MULT = CONFIG["STOP_LOSS_ATR"]      # 損切り（ATRの何倍か）
TARGET_R      = CONFIG["TARGET_R_MULTIPLE"]  # 利食い（リスクの何倍か）

def run_simulation(ticker: str, df: pd.DataFrame):
    """1銘柄の全期間をシミュレーション"""
    trades = []
    position = None # 現在のポジション {entry_price, stop_price, target_price, date}
    
    # 日付インデックスをリセットしてループしやすくする
    df = df.reset_index()
    
    # テクニカル指標の事前計算（ループ内での計算を減らすため）
    # ※厳密にはVCPは形状分析なので都度計算が必要だが、ここでは簡易化せず都度呼ぶ
    
    # メインループ
    for i in range(START_DELAY, len(df) - 1):
        today = df.iloc[i]
        date_str = today["date"].strftime("%Y-%m-%d")
        
        # --- 1. ポジション保有中の処理（決済判定） ---
        if position:
            low  = today["Low"]
            high = today["High"]
            
            # 判定順序: 
            # 1. ギャップダウンでストップ以下から始まったら始値で決済
            # 2. ザラ場でストップにヒットしたら決済
            # 3. ザラ場でターゲットに到達したら決済
            
            exit_price = None
            result_type = ""
            
            # 損切り判定
            if low <= position["stop_price"]:
                # 始値ですでにストップを割っていたら始値で決済（スリッページ）
                exit_price = min(today["Open"], position["stop_price"])
                result_type = "LOSS"
            
            # 利食い判定（損切りにかかっていなければ）
            elif high >= position["target_price"]:
                exit_price = position["target_price"]
                result_type = "WIN"
                
            # 決済実行
            if exit_price:
                pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"] * 100
                trades.append({
                    "ticker": ticker,
                    "entry_date": position["date"],
                    "exit_date": date_str,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "pnl_pct": round(pnl_pct, 2),
                    "type": result_type
                })
                position = None # ポジション解消
                
            continue # ポジションがある日は新規エントリーしない
            
        # --- 2. 新規エントリー判定（ノーポジの時） ---
        
        # 過去データの切り出し（当日を含める）
        # ※VCPAnalyzerは直近のデータを基準に判定するため
        past_df = df.iloc[:i+1].set_index("date")
        
        # 高速化: 明らかな下降トレンドはスキップ
        close = today["Close"]
        ma50  = past_df["Close"].rolling(50).mean().iloc[-1]
        if close < ma50:
            continue

        # 戦略判定
        # 1. Profit Factorチェック（軽い処理でフィルタ）
        pf = StrategyValidator.run(past_df)
        if pf < CONFIG["MIN_PROFIT_FACTOR"]:
            continue
            
        # 2. VCPチェック（重い処理）
        vcp = VCPAnalyzer.calculate(past_df)
        if vcp["score"] < CONFIG["MIN_VCP_SCORE"]:
            continue
            
        # 3. RSチェック（相対強度）
        # ※本来は全銘柄比較が必要だが、ここでは単独のモメンタムで代用
        # 簡易RS: 過去63日(1Q)の変化率
        roc_63 = (close / df.iloc[i-63]["Close"] - 1) * 100 if i > 63 else 0
        if roc_63 < 10: # 最低でも10%は上がっていないとRS高いとは言えない
            continue

        # エントリー条件成立
        atr = vcp["atr"]
        stop_price = close - (atr * STOP_ATR_MULT)
        risk = close - stop_price
        target_price = close + (risk * TARGET_R)
        
        position = {
            "entry_price": close, # 終値でエントリーと仮定
            "stop_price": stop_price,
            "target_price": target_price,
            "date": date_str
        }

    return trades

def main():
    print(f"===== P&L BACKTEST ({datetime.now().strftime('%Y-%m-%d')}) =====")
    print(f"Target: {len(TICKERS)} tickers / Period: Last {LOOKBACK_DAYS} days")
    print(f"Strategy: Stop={STOP_ATR_MULT}xATR / Target={TARGET_R}xRisk")
    print("-" * 60)
    
    all_trades = []
    processed = 0
    
    # 全銘柄ループ（時間がかかるので最初の50銘柄などでテストしてもよい）
    # 今回は Config の TICKERS を使用
    target_tickers = TICKERS # 全てやる場合
    
    start_time = time.time()
    
    for ticker in target_tickers:
        processed += 1
        
        # データ取得
        df = core_fmp.get_historical_data(ticker, days=LOOKBACK_DAYS)
        if df is None or len(df) < START_DELAY + 20:
            continue
            
        # シミュレーション実行
        trades = run_simulation(ticker, df)
        all_trades.extend(trades)
        
        # 進捗表示
        if processed % 10 == 0:
            elapsed = time.time() - start_time
            print(f"Processing... {processed}/{len(target_tickers)} ({elapsed:.1f}s)")

    print("-" * 60)
    
    # --- 集計結果 ---
    if not all_trades:
        print("❌ No trades generated.")
        return

    df_res = pd.DataFrame(all_trades)
    
    total_trades = len(df_res)
    wins = df_res[df_res["pnl_pct"] > 0]
    losses = df_res[df_res["pnl_pct"] <= 0]
    
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total_trades * 100
    
    avg_win = wins["pnl_pct"].mean() if win_count > 0 else 0
    avg_loss = losses["pnl_pct"].mean() if loss_count > 0 else 0
    
    # プロフィットファクター (総利益 / 総損失の絶対値)
    gross_profit = wins["pnl_pct"].sum()
    gross_loss = abs(losses["pnl_pct"].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # 期待値 (1トレードあたりの平均損益%)
    expectancy = df_res["pnl_pct"].mean()

    print(f"📊 PERFORMANCE SUMMARY")
    print(f"  Total Trades:   {total_trades}")
    print(f"  Win Rate:       {win_rate:.1f}% ({win_count}W - {loss_count}L)")
    print(f"  Profit Factor:  {pf:.2f}")
    print(f"  Avg Win:       +{avg_win:.2f}%")
    print(f"  Avg Loss:       {avg_loss:.2f}%")
    print(f"  Expectancy:    {'+' if expectancy>0 else ''}{expectancy:.2f}% per trade")
    print("-" * 60)
    
    # 成績上位のトレード
    print("🏆 Top 5 Best Trades:")
    top_trades = df_res.sort_values("pnl_pct", ascending=False).head(5)
    for _, t in top_trades.iterrows():
        print(f"  {t['ticker']:6s} {t['entry_date']} -> {t['exit_date']} : +{t['pnl_pct']}%")

    # 成績下位のトレード
    print("\n💀 Worst 3 Trades:")
    worst_trades = df_res.sort_values("pnl_pct", ascending=True).head(3)
    for _, t in worst_trades.iterrows():
        print(f"  {t['ticker']:6s} {t['entry_date']} -> {t['exit_date']} : {t['pnl_pct']}%")

    # JSON保存
    out_file = Path(__file__).parent.parent / "frontend" / "public" / "content" / "backtest.json"
    out_file.write_text(json.dumps({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(pf, 2),
            "expectancy": round(expectancy, 2)
        },
        "trades": all_trades
    }, indent=2))
    print(f"\n✅ Results saved to backtest.json")

if __name__ == "__main__":
    main()