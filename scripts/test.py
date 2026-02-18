import pandas as pd
import numpy as np
from typing import Dict, List

# =========================
# 設定
# =========================

INITIAL_CAPITAL = 100000
RISK_PER_TRADE = 0.10
MAX_HOLD_DAYS = 20
STOP_LOSS = 0.07
TAKE_PROFIT = 0.20
MAX_CONCURRENT = 5


# =========================
# ユーティリティ
# =========================

def calculate_drawdown(equity_curve: pd.Series):
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    return dd.min()


def calc_metrics(trades: List[dict], equity_curve: pd.Series):
    if len(trades) == 0:
        return {}

    df = pd.DataFrame(trades)
    wins = df[df["return"] > 0]
    losses = df[df["return"] <= 0]

    pf = wins["return"].sum() / abs(losses["return"].sum()) if not losses.empty else np.inf
    expectancy = df["return"].mean()
    std = df["return"].std()
    sharpe_like = expectancy / std if std > 0 else 0
    win_rate = len(wins) / len(df)

    max_dd = calculate_drawdown(equity_curve)

    return {
        "trades": len(df),
        "win_rate": round(win_rate * 100, 2),
        "pf": round(pf, 2),
        "expectancy": round(expectancy, 4),
        "sharpe_like": round(sharpe_like, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "final_equity": round(equity_curve.iloc[-1], 2)
    }


# =========================
# エントリーロジック例
# =========================

def vcp_signal(df):
    ma50 = df["Close"].rolling(50).mean()
    contraction = df["Close"].rolling(20).std()
    return (df["Close"] > ma50) & (contraction < contraction.rolling(50).mean())


def canslim_signal(df):
    ma50 = df["Close"].rolling(50).mean()
    volume_spike = df["Volume"] > df["Volume"].rolling(50).mean() * 1.5
    return (df["Close"] > ma50) & volume_spike


def ses_signal(df):
    momentum = df["Close"].pct_change(20)
    return momentum > 0.15


def ecr_signal(df):
    breakout = df["Close"] > df["High"].rolling(50).max().shift(1)
    return breakout


METHODS = {
    "VCP": vcp_signal,
    "CANSLIM": canslim_signal,
    "SES": ses_signal,
    "ECR": ecr_signal
}


# =========================
# シミュレーション
# =========================

def run_backtest(data: Dict[str, pd.DataFrame], method_name: str):
    capital = INITIAL_CAPITAL
    equity_curve = []
    open_positions = []
    trades = []

    for ticker, df in data.items():
        df = df.copy().reset_index(drop=True)
        signal = METHODS[method_name](df)

        for i in range(50, len(df) - MAX_HOLD_DAYS - 1):

            if len(open_positions) >= MAX_CONCURRENT:
                break

            if signal.iloc[i]:
                entry_price = df["Open"].iloc[i + 1]
                size = capital * RISK_PER_TRADE
                shares = size / entry_price

                exit_price = entry_price
                exit_day = i + 1

                for j in range(i + 1, min(i + 1 + MAX_HOLD_DAYS, len(df))):
                    change = (df["Close"].iloc[j] - entry_price) / entry_price

                    if change <= -STOP_LOSS:
                        exit_price = entry_price * (1 - STOP_LOSS)
                        exit_day = j
                        break

                    if change >= TAKE_PROFIT:
                        exit_price = entry_price * (1 + TAKE_PROFIT)
                        exit_day = j
                        break

                    exit_price = df["Close"].iloc[j]
                    exit_day = j

                pnl = (exit_price - entry_price) * shares
                ret = pnl / capital

                capital += pnl
                equity_curve.append(capital)

                trades.append({
                    "ticker": ticker,
                    "entry_index": i,
                    "exit_index": exit_day,
                    "return": ret
                })

    if len(equity_curve) == 0:
        equity_curve = [INITIAL_CAPITAL]

    equity_series = pd.Series(equity_curve)

    metrics = calc_metrics(trades, equity_series)
    return metrics


# =========================
# 実行
# =========================

def run_all_methods(data):
    results = {}
    for name in METHODS.keys():
        metrics = run_backtest(data, name)
        results[name] = metrics

    return pd.DataFrame(results).T


# =========================
# 使用例
# =========================

# data = {
#     "AAPL": pd.read_csv("AAPL.csv"),
#     "MSFT": pd.read_csv("MSFT.csv"),
# }

# result = run_all_methods(data)
# print(result)