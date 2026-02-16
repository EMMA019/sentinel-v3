#!/usr/bin/env python3
"""
generate_backtest.py — 毎週土曜実行
====================================
4手法の過去シグナルを一括バックテスト。

手法別に独立してシグナル判定 → フォワードリターンを集計:
  vcp_rs   : VCP≥60 かつ RS≥70
  ecr      : ECR sentinel_rank≥65 かつ phase∈{IGNITION,ACCUMULATION}
  canslim  : CANSLIM score≥50
  ses      : SES score≥65

出力: frontend/public/content/backtest.json
"""
import sys, json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent.parent / "shared"))
from engines import core_fmp
from engines.analysis            import VCPAnalyzer, RSAnalyzer
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from engines.ecr_strategy        import ECRStrategyEngine
from engines.canslim             import CANSLIMAnalyzer
from engines.config              import TICKERS

JST      = timezone(timedelta(hours=9))
TODAY    = datetime.now(JST).strftime("%Y-%m-%d")
CONTENT  = Path(__file__).parent.parent / "frontend" / "public" / "content"
OUT_FILE = CONTENT / "backtest.json"
CONTENT.mkdir(parents=True, exist_ok=True)

# ── パラメータ ──────────────────────────────────────────────
HOLD_DAYS     = [5, 10, 20]
LOOKBACK_DAYS = 365
SCAN_STEP     = 20          # 20営業日ごとにウィンドウ評価

# 手法別シグナル閾値
THRESHOLDS = {
    "vcp_rs":  lambda vcp, rs, ecr, canslim, ses: vcp >= 60 and rs >= 70,
    "ecr":     lambda vcp, rs, ecr, canslim, ses: (
                   ecr["sentinel_rank"] >= 65 and
                   ecr["phase"] in {"IGNITION", "ACCUMULATION"}
               ),
    "canslim": lambda vcp, rs, ecr, canslim, ses: canslim["score"] >= 50,
    "ses":     lambda vcp, rs, ecr, canslim, ses: ses["score"] >= 65,
}

# テスト銘柄（代表的な100銘柄）
BT_TICKERS = [
    "NVDA","AMD","MSFT","AAPL","AMZN","META","GOOGL","TSLA","AVGO","NFLX",
    "CRM","NOW","ADBE","INTU","PANW","CRWD","DDOG","SNOW","MDB","GTLB",
    "SMCI","CELH","AXSM","HIMS","CAVA","APP","ONON","DECK","BOOT","RXRX",
    "LRCX","AMAT","KLAC","MRVL","QCOM","TXN","ASML","SNPS","CDNS","ANSS",
    "MELI","SE","NU","BIDU","JD","PDD","GRAB","LAZR","RIVN","LCID",
    "V","MA","PYPL","SQ","COIN","HOOD","SOFI","UPST","AFRM","LC",
    "UNH","LLY","ABBV","MRK","PFE","AMGN","GILD","REGN","VRTX","BIIB",
    "JPM","GS","MS","BAC","C","WFC","BLK","SCHW","COF","AXP",
    "XOM","CVX","COP","EOG","SLB","HAL","OXY","DVN","FANG","MPC",
    "COST","WMT","TGT","AMZN","HD","LOW","NKE","LULU","TPR","RL",
]
# TICKERS から補完（重複除去）
for t in TICKERS:
    if t not in BT_TICKERS:
        BT_TICKERS.append(t)
    if len(BT_TICKERS) >= 120:
        break


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# コア関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fwd_return(df, idx: int, days: int) -> float | None:
    end = idx + days
    if end >= len(df):
        return None
    entry = float(df["Close"].iloc[idx])
    exit_ = float(df["Close"].iloc[end])
    if entry <= 0:
        return None
    return round((exit_ - entry) / entry * 100, 2)


def backtest_ticker(ticker: str) -> list:
    """1銘柄を全手法でバックテスト → シグナルリストを返す"""
    df = core_fmp.get_historical_data(ticker, days=LOOKBACK_DAYS + 80)
    if df is None or len(df) < 250:
        return []

    signals = []
    indices  = list(range(200, len(df) - max(HOLD_DAYS) - 1, SCAN_STEP))

    for i in indices:
        window = df.iloc[:i + 1]
        try:
            # ── 全手法のスコアを一度に計算 ────────────────
            rs_raw   = RSAnalyzer.get_raw_score(window)
            if rs_raw == -999.0:
                continue
            rs_approx = min(99, max(1, int((rs_raw + 1) * 50)))

            vcp      = VCPAnalyzer.calculate(window)
            ses      = SentinelEfficiencyAnalyzer.calculate(window)
            ecr      = ECRStrategyEngine.analyze_single(ticker, window)
            canslim  = CANSLIMAnalyzer.calculate(ticker, window)

            # ── フォワードリターン ─────────────────────────
            returns = {}
            valid   = False
            for hd in HOLD_DAYS:
                r = fwd_return(df, i, hd)
                if r is not None:
                    returns[f"d{hd}"] = r
                    valid = True
            if not valid:
                continue

            date = df.index[i].strftime("%Y-%m-%d")

            # ── 手法ごとにシグナル判定 ─────────────────────
            triggered = {
                name: int(fn(vcp["score"], rs_approx, ecr, canslim, ses))
                for name, fn in THRESHOLDS.items()
            }

            # 何かの手法でシグナルが立っていれば記録
            if not any(triggered.values()):
                continue

            signals.append({
                "ticker":        ticker,
                "date":          date,
                # スコア（派生データ）
                "vcp":           vcp["score"],
                "rs":            rs_approx,
                "ses":           ses["score"],
                "ecr_rank":      ecr["sentinel_rank"],
                "ecr_phase":     ecr["phase"],
                "canslim":       canslim["score"],
                "canslim_grade": canslim["grade"],
                # 手法フラグ
                "triggered":     triggered,
                # フォワードリターン
                "returns":       returns,
            })

        except Exception:
            continue

    return signals


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 集計関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def aggregate(signals: list, method: str, hold_key: str = "d10") -> dict:
    """指定手法・保有期間のシグナルを集計"""
    subset = [s for s in signals if s["triggered"].get(method) and hold_key in s["returns"]]
    if not subset:
        return {"signal_count": 0, "win_rate": None, "avg_return": None,
                "avg_win": None, "avg_loss": None, "profit_factor": None,
                "max_loss": None, "expectancy": None}

    rets    = [s["returns"][hold_key] for s in subset]
    wins    = [r for r in rets if r > 0]
    losses  = [r for r in rets if r <= 0]
    n       = len(rets)

    win_rate = round(len(wins) / n * 100, 1) if n else None
    avg_ret  = round(sum(rets) / n, 2) if n else None
    avg_win  = round(sum(wins) / len(wins), 2) if wins else None
    avg_loss = round(sum(losses) / len(losses), 2) if losses else None

    gross_win  = sum(wins)
    gross_loss = abs(sum(losses))
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (
        99.0 if gross_win > 0 else 0.0
    )

    expectancy = round(
        (win_rate / 100 * (avg_win or 0)) +
        ((1 - win_rate / 100) * (avg_loss or 0)),
        2
    ) if win_rate is not None else None

    max_loss = round(min(rets), 2) if rets else None

    return {
        "signal_count":  n,
        "win_rate":      win_rate,
        "avg_return":    avg_ret,
        "avg_win":       avg_win,
        "avg_loss":      avg_loss,
        "profit_factor": pf,
        "max_loss":      max_loss,
        "expectancy":    expectancy,
    }


def build_method_stats(signals: list) -> dict:
    """全手法 × 全保有期間の統計を生成"""
    result = {}
    for method in THRESHOLDS:
        result[method] = {}
        for hd in HOLD_DAYS:
            result[method][f"d{hd}"] = aggregate(signals, method, f"d{hd}")
    return result


def score_distribution(signals: list, method: str,
                        score_key: str, bins: list,
                        hold_key: str = "d10") -> list:
    """スコア帯別の勝率分布"""
    subset = [s for s in signals
              if s["triggered"].get(method) and hold_key in s["returns"]]
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        group = [s for s in subset if lo <= s.get(score_key, 0) < hi]
        if not group:
            continue
        rets = [s["returns"][hold_key] for s in group]
        wins = [r for r in rets if r > 0]
        rows.append({
            "range":     f"{lo}-{hi}",
            "count":     len(group),
            "win_rate":  round(len(wins) / len(rets) * 100, 1),
            "avg_return": round(sum(rets) / len(rets), 2),
        })
    return rows


def build_comparison_chart(method_stats: dict, hold_key: str = "d10") -> list:
    """手法比較用データ（フロントのバーチャート用）"""
    labels = {
        "vcp_rs":   "VCP × RS",
        "ecr":      "ECR",
        "canslim":  "CANSLIM",
        "ses":      "SES",
    }
    colors = {
        "vcp_rs":  "#22C55E",
        "ecr":     "#3B82F6",
        "canslim": "#F59E0B",
        "ses":     "#8B5CF6",
    }
    result = []
    for method, label in labels.items():
        s = method_stats.get(method, {}).get(hold_key, {})
        if s.get("signal_count", 0) == 0:
            continue
        result.append({
            "method":        method,
            "label":         label,
            "color":         colors[method],
            "signal_count":  s["signal_count"],
            "win_rate":      s["win_rate"],
            "avg_return":    s["avg_return"],
            "profit_factor": s["profit_factor"],
            "expectancy":    s["expectancy"],
        })
    return sorted(result, key=lambda x: (x["win_rate"] or 0), reverse=True)


def build_recent_signals(signals: list, n: int = 30) -> list:
    """最新シグナル一覧（フロント表示用）"""
    sorted_sigs = sorted(signals, key=lambda x: x["date"], reverse=True)
    result = []
    for s in sorted_sigs[:n]:
        methods = [m for m, v in s["triggered"].items() if v]
        result.append({
            "ticker":   s["ticker"],
            "date":     s["date"],
            "methods":  methods,
            "vcp":      s["vcp"],
            "rs":       s["rs"],
            "ecr_rank": s["ecr_rank"],
            "canslim":  s["canslim"],
            "returns":  s["returns"],
        })
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print(f"===== BACKTEST {TODAY} =====")
    print(f"Tickers: {len(BT_TICKERS)} / Lookback: {LOOKBACK_DAYS}d / Step: {SCAN_STEP}d")

    all_signals = []
    for i, ticker in enumerate(BT_TICKERS):
        sigs = backtest_ticker(ticker)
        all_signals.extend(sigs)
        print(f"  [{i+1:3d}/{len(BT_TICKERS)}] {ticker:6s}: {len(sigs):3d} signals")
        time.sleep(0.4)  # レート制限

    print(f"\nTotal signals: {len(all_signals)}")

    # ── 集計 ────────────────────────────────────────────────
    method_stats = build_method_stats(all_signals)

    # 比較チャート（保有期間別）
    comparison = {
        f"d{hd}": build_comparison_chart(method_stats, f"d{hd}")
        for hd in HOLD_DAYS
    }

    # スコア分布（手法別）
    distributions = {
        "vcp_rs": {
            "vcp_bins": score_distribution(
                all_signals, "vcp_rs", "vcp",
                [60, 70, 80, 90, 106], "d10"
            ),
            "rs_bins": score_distribution(
                all_signals, "vcp_rs", "rs",
                [70, 80, 90, 100], "d10"
            ),
        },
        "ecr": {
            "rank_bins": score_distribution(
                all_signals, "ecr", "ecr_rank",
                [65, 70, 80, 90, 101], "d10"
            ),
        },
        "canslim": {
            "score_bins": score_distribution(
                all_signals, "canslim", "canslim",
                [50, 60, 70, 80, 101], "d10"
            ),
        },
        "ses": {
            "score_bins": score_distribution(
                all_signals, "ses", "ses",
                [65, 70, 80, 90, 101], "d10"
            ),
        },
    }

    # ECRフェーズ別勝率
    ecr_phase_stats = {}
    for phase in ["IGNITION", "ACCUMULATION"]:
        subset = [
            s for s in all_signals
            if s["triggered"].get("ecr") and s["ecr_phase"] == phase
            and "d10" in s["returns"]
        ]
        if subset:
            rets = [s["returns"]["d10"] for s in subset]
            wins = [r for r in rets if r > 0]
            ecr_phase_stats[phase] = {
                "count":      len(rets),
                "win_rate":   round(len(wins) / len(rets) * 100, 1),
                "avg_return": round(sum(rets) / len(rets), 2),
            }

    # CANSLIM グレード別勝率
    canslim_grade_stats = {}
    for grade in ["A+", "A", "B+", "B"]:
        subset = [
            s for s in all_signals
            if s["triggered"].get("canslim") and s.get("canslim_grade") == grade
            and "d10" in s["returns"]
        ]
        if subset:
            rets = [s["returns"]["d10"] for s in subset]
            wins = [r for r in rets if r > 0]
            canslim_grade_stats[grade] = {
                "count":      len(rets),
                "win_rate":   round(len(wins) / len(rets) * 100, 1),
                "avg_return": round(sum(rets) / len(rets), 2),
            }

    # 複数手法一致シグナルの勝率
    multi_method_stats = {}
    for count in [1, 2, 3, 4]:
        subset = [
            s for s in all_signals
            if sum(s["triggered"].values()) >= count
            and "d10" in s["returns"]
        ]
        if subset:
            rets = [s["returns"]["d10"] for s in subset]
            wins = [r for r in rets if r > 0]
            multi_method_stats[f"methods_{count}plus"] = {
                "count":      len(rets),
                "win_rate":   round(len(wins) / len(rets) * 100, 1),
                "avg_return": round(sum(rets) / len(rets), 2),
            }

    output = {
        "generated_at":      TODAY,
        "lookback_days":     LOOKBACK_DAYS,
        "ticker_count":      len(BT_TICKERS),
        "signal_count_total": len(all_signals),

        # ── 手法別統計（全保有期間）──
        "method_stats":      method_stats,

        # ── 手法比較チャート用（期間別） ──
        "comparison":        comparison,

        # ── スコア分布 ──
        "distributions":     distributions,

        # ── 追加分析 ──
        "ecr_phase_stats":       ecr_phase_stats,
        "canslim_grade_stats":   canslim_grade_stats,
        "multi_method_stats":    multi_method_stats,

        # ── 最新シグナル一覧 ──
        "recent_signals":    build_recent_signals(all_signals, 30),

        # ── 後方互換（旧Backtest.jsxのstats.d10キー） ──
        "stats": method_stats.get("vcp_rs", {}),
    }

    OUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    total_methods = {m: sum(s["triggered"].get(m, 0) for s in all_signals) for m in THRESHOLDS}
    print(f"\nSignals per method: {total_methods}")
    print(f"✅ backtest.json saved")
    print("===== Done =====")


if __name__ == "__main__":
    main()
