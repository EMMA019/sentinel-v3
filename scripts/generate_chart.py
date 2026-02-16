"""
generate_chart.py
OHLCVデータからローソク足チャート画像を生成してBase64で返す
matplotlib + mplfinance 使用
"""
import base64, io
import pandas as pd
import numpy as np
from pathlib import Path


def generate_candle_chart(df: pd.DataFrame, ticker: str, vcp_score: int,
                          entry: float = None, stop: float = None,
                          target: float = None, days: int = 90) -> str:
    """
    ローソク足チャートをPNG Base64で返す
    - ダークテーマ (ink background)
    - 20MA / 50MA / 200MA
    - 出来高バー
    - エントリー/ストップ/ターゲットライン（任意）
    Returns: base64 encoded PNG string
    """
    try:
        import mplfinance as mpf
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("mplfinance not installed, skipping chart")
        return ""

    # 直近N日
    df_plot = df.iloc[-days:].copy()
    if len(df_plot) < 20:
        return ""

    # 移動平均
    df_plot["MA20"]  = df_plot["Close"].rolling(20).mean()
    df_plot["MA50"]  = df_plot["Close"].rolling(50).mean()
    df_plot["MA200"] = df_plot["Close"].rolling(200).mean()

    # スタイル設定（ダークテーマ）
    mc = mpf.make_marketcolors(
        up="#22C55E", down="#EF4444",
        edge={"up":"#22C55E","down":"#EF4444"},
        wick={"up":"#22C55E","down":"#EF4444"},
        volume={"up":"#22C55E40","down":"#EF444440"},
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor="#0E1318",
        edgecolor="#1C2530",
        figcolor="#080C10",
        gridcolor="#1C2530",
        gridstyle="--",
        gridaxis="both",
        y_on_right=True,
        rc={
            "axes.labelcolor":  "#7A90A8",
            "xtick.color":      "#3D4F63",
            "ytick.color":      "#3D4F63",
            "font.family":      "monospace",
            "font.size":        8,
        }
    )

    # 追加プロット（MA線）
    add_plots = [
        mpf.make_addplot(df_plot["MA20"],  color="#3B82F6", width=1.0, linestyle="-"),
        mpf.make_addplot(df_plot["MA50"],  color="#F59E0B", width=1.0, linestyle="-"),
        mpf.make_addplot(df_plot["MA200"], color="#EF4444", width=0.8, linestyle="--"),
    ]

    # チャート描画
    fig, axes = mpf.plot(
        df_plot,
        type="candle",
        style=s,
        volume=True,
        addplot=add_plots,
        figratio=(12, 7),
        figscale=1.0,
        tight_layout=True,
        returnfig=True,
        datetime_format="%m/%d",
        xrotation=0,
    )

    ax_main = axes[0]

    # タイトル
    price = float(df_plot["Close"].iloc[-1])
    chg   = (price / float(df_plot["Close"].iloc[0]) - 1) * 100
    sign  = "+" if chg >= 0 else ""
    color = "#22C55E" if chg >= 0 else "#EF4444"
    ax_main.set_title(
        f"{ticker}  ${price:.2f}  {sign}{chg:.1f}%  VCP {vcp_score}/105",
        color="#EBF4FF", fontsize=10, fontweight="bold", loc="left", pad=8
    )

    # エントリー / ストップ / ターゲットライン
    xlim = ax_main.get_xlim()
    if entry:
        ax_main.axhline(y=entry, color="#22C55E", linewidth=1.0,
                        linestyle="--", alpha=0.8, xmin=0.8)
        ax_main.text(xlim[1]*0.99, entry, f" E ${entry:.2f}",
                     color="#22C55E", fontsize=7, va="center", ha="right")
    if stop:
        ax_main.axhline(y=stop, color="#EF4444", linewidth=1.0,
                        linestyle="--", alpha=0.8, xmin=0.8)
        ax_main.text(xlim[1]*0.99, stop, f" S ${stop:.2f}",
                     color="#EF4444", fontsize=7, va="center", ha="right")
    if target:
        ax_main.axhline(y=target, color="#F59E0B", linewidth=1.0,
                        linestyle="--", alpha=0.8, xmin=0.8)
        ax_main.text(xlim[1]*0.99, target, f" T ${target:.2f}",
                     color="#F59E0B", fontsize=7, va="center", ha="right")

    # 凡例
    legend_handles = [
        mpatches.Patch(color="#3B82F6", label="MA20"),
        mpatches.Patch(color="#F59E0B", label="MA50"),
        mpatches.Patch(color="#EF4444", label="MA200"),
    ]
    ax_main.legend(handles=legend_handles, loc="upper left",
                   framealpha=0.0, fontsize=7,
                   labelcolor=["#3B82F6","#F59E0B","#EF4444"])

    # PNG → Base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="#080C10", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
