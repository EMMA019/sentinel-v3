#!/usr/bin/env python3
"""
scripts/generate_strategies.py — 全銘柄マルチ戦略スキャン
======================================================
VCP/CANSLIM/SES/ECR の4手法ですべての銘柄を評価します。
制限(200)を解除したフルスキャン版です。
"""
import sys, json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent.parent / "shared"))

from engines import core_fmp
from engines.analysis           import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from engines.ecr_strategy        import ECRStrategyEngine
from engines.canslim             import CANSLIMAnalyzer
from engines.config              import CONFIG, TICKERS

JST     = timezone(timedelta(hours=9))
TODAY   = datetime.now(JST).strftime("%Y-%m-%d")
CONTENT = Path(__file__).parent.parent / "frontend" / "public" / "content"
OUT     = CONTENT / "strategies.json"

# 【変更点】制限を解除し、全銘柄を対象にする
SCAN_TICKERS = TICKERS 


def scan_all() -> list:
    """全手法で全銘柄をスキャン"""
    print(f"  Phase 1: Fetching RS scores ({len(SCAN_TICKERS)} tickers)...")
    raw_rs_list = []
    df_cache    = {}

    for i, ticker in enumerate(SCAN_TICKERS):
        # 700日分のデータを取得
        df = core_fmp.get_historical_data(ticker, days=700)
        if df is None or len(df) < 200:
            continue
            
        rs_raw = RSAnalyzer.get_raw_score(df)
        if rs_raw != -999.0:
            raw_rs_list.append({"ticker": ticker, "df": df, "raw_rs": rs_raw})
            df_cache[ticker] = df
            
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(SCAN_TICKERS)} RS fetched")
        
        # API負荷軽減のための微小なスリープ
        time.sleep(0.02)

    # RSの偏差値（パーセンタイル）を計算
    scored_rs = RSAnalyzer.assign_percentiles(raw_rs_list)
    rs_map    = {s["ticker"]: s["rs_rating"] for s in scored_rs}

    print(f"  Phase 2: Multi-strategy scoring ({len(df_cache)} tickers)...")
    results = []

    for i, ticker in enumerate(df_cache):
        df = df_cache[ticker]
        try:
            # ── 各エンジンの計算 ──
            vcp     = VCPAnalyzer.calculate(df)
            pf      = StrategyValidator.run(df)
            ses     = SentinelEfficiencyAnalyzer.calculate(df)
            ecr     = ECRStrategyEngine.analyze_single(ticker, df)
            rs      = rs_map.get(ticker, 0)

            # ファンダメンタルズとプロフィールの取得
            fund    = core_fmp.get_fundamentals(ticker) or {}
            own     = core_fmp.get_ownership(ticker) or {}
            canslim = CANSLIMAnalyzer.calculate(ticker, df, fund=fund, own=own)
            profile = core_fmp.get_company_profile(ticker) or {}

            # 価格情報の整理
            price   = float(df["Close"].iloc[-1])
            pivot   = float(df["High"].iloc[-20:].max())
            dist    = (price - pivot) / pivot
            status  = "ACTION" if -0.05 <= dist <= 0.03 else ("WAIT" if dist < -0.05 else "EXTENDED")

            # 移動平均線からの乖離（null対策）
            ma50 = df["Close"].rolling(50).mean().iloc[-1]
            ma50_ratio = round((price / ma50 - 1) * 100, 2) if not np.isnan(ma50) else None

            # 総合スコアリング
            vcp_rs_normalized = min(100, (vcp["score"] / 105 * 50) + (rs / 99 * 50))
            composite = (
                vcp_rs_normalized      * 0.35 +
                ecr["sentinel_rank"]   * 0.35 +
                canslim["score"]       * 0.30
            )

            # 複数手法一致（コンセンサス）カウント
            method_hits = sum([
                vcp["score"] >= 70 and rs >= 80,
                ecr["sentinel_rank"] >= 70,
                canslim["score"] >= 60,
                ses["score"] >= 60,
            ])

            results.append({
                "ticker":       ticker,
                "name":         profile.get("companyName", ticker)[:25],
                "sector":       profile.get("sector", "N/A"),
                "status":       status,
                "scores": {
                    "vcp":           vcp["score"],
                    "rs":            rs,
                    "ses":           ses["score"],
                    "ecr_rank":      ecr["sentinel_rank"],
                    "canslim":       canslim["score"],
                    "composite":     round(composite, 1),
                    "pf":            round(pf, 2),
                },
                "ecr_phase":     ecr["phase"],
                "ecr_strategy":  ecr["strategy"],
                "canslim_grade": canslim["grade"],
                "method_hits":   method_hits,
                "atr_pct":       round(vcp.get("atr", 0) / price * 100, 2) if price > 0 else None,
                "pivot_dist_pct": round(dist * 100, 2),
                "ma50_ratio":    ma50_ratio,
            })

        except Exception as e:
            print(f"    ❌ {ticker}: {e}")
            continue

        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(df_cache)} scored")
            
        # 大量リクエストによるBAN防止のため、少し長めに休む
        time.sleep(0.1)

    return results


def build_rankings(results: list) -> dict:
    valid = [r for r in results if r["status"] in ("ACTION", "WAIT")]
    def top(key_fn, n=30): # 全銘柄にするのでランキング数も少し増やす
        return sorted(valid, key=key_fn, reverse=True)[:n]

    return {
        "vcp_rs":    top(lambda r: r["scores"]["vcp"] * 0.5 + r["scores"]["rs"] * 0.5),
        "ecr":       top(lambda r: r["scores"]["ecr_rank"]),
        "canslim":   top(lambda r: r["scores"]["canslim"]),
        "ses":       top(lambda r: r["scores"]["ses"]),
        "composite": top(lambda r: r["scores"]["composite"]),
        "consensus": sorted(valid, key=lambda r: (r["method_hits"], r["scores"]["composite"]),
                            reverse=True)[:30],
    }

# (build_phase_summary, build_method_comparison 関数は既存のまま)
def build_phase_summary(results: list) -> dict:
    phases = {}
    for r in results:
        p = r.get("ecr_phase", "WATCH")
        if p not in phases: phases[p] = []
        phases[p].append(r)
    return {p: sorted(v, key=lambda x: x["scores"]["ecr_rank"], reverse=True)[:20] for p, v in phases.items()}

def build_method_comparison(results: list) -> list:
    summary = []
    for method, key in [
        ("VCP×RS",  lambda r: r["scores"]["vcp"] * 0.5 + r["scores"]["rs"] * 0.5),
        ("ECR",     lambda r: r["scores"]["ecr_rank"]),
        ("CANSLIM", lambda r: r["scores"]["canslim"]),
        ("SES",     lambda r: r["scores"]["ses"]),
    ]:
        top30 = sorted(results, key=key, reverse=True)[:30]
        summary.append({
            "method":      method,
            "top_tickers": [r["ticker"] for r in top30],
            "avg_scores": {
                "vcp":     round(sum(r["scores"]["vcp"] for r in top30) / 30, 1),
                "ecr":     round(sum(r["scores"]["ecr_rank"] for r in top30) / 30, 1),
                "canslim": round(sum(r["scores"]["canslim"] for r in top30) / 30, 1),
                "ses":     round(sum(r["scores"]["ses"] for r in top30) / 30, 1),
            }
        })
    return summary

def main():
    print(f"===== STRATEGIES FULL SCAN {TODAY} =====")
    print(f"Scanning {len(SCAN_TICKERS)} tickers...")

    results = scan_all()
    print(f"Scored: {len(results)} tickers")

    rankings    = build_rankings(results)
    phases      = build_phase_summary(results)
    method_cmp  = build_method_comparison(results)

    output = {
        "generated_at":  TODAY,
        "ticker_count":  len(results),
        "action_count":  sum(1 for r in results if r["status"] == "ACTION"),
        "wait_count":    sum(1 for r in results if r["status"] == "WAIT"),
        "rankings":      rankings,
        "ecr_phases":    phases,
        "method_comparison": method_cmp,
    }

    CONTENT.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, preserve_ascii=False))
    print(f"✅ strategies.json saved (Full scan version)")

if __name__ == "__main__":
    main()

