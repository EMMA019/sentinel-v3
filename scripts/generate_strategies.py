#!/usr/bin/env python3
"""
generate_strategies.py
======================
複数手法による銘柄スキャンと比較検証データを生成する。
毎日実行（generate_articles.py と同じスケジュール）

出力: frontend/public/content/strategies.json
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

# スキャン対象（主要200銘柄に絞って高速化）
SCAN_TICKERS = TICKERS[:200] if len(TICKERS) > 200 else TICKERS


def scan_all() -> list:
    """全手法で全銘柄をスキャンし、統合スコアを計算する"""
    # RS percentile 計算のため全銘柄の生スコアを先に収集
    print(f"  Phase 1: Fetching RS scores ({len(SCAN_TICKERS)} tickers)...")
    raw_rs_list = []
    df_cache    = {}

    for i, ticker in enumerate(SCAN_TICKERS):
        df = core_fmp.get_historical_data(ticker, days=700)
        if df is None or len(df) < 200:
            continue
        rs_raw = RSAnalyzer.get_raw_score(df)
        if rs_raw != -999.0:
            raw_rs_list.append({"ticker": ticker, "df": df, "raw_rs": rs_raw})
            df_cache[ticker] = df
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(SCAN_TICKERS)} RS done")

    # RS percentile を全銘柄比較で付与
    scored_rs = RSAnalyzer.assign_percentiles(raw_rs_list)
    rs_map    = {s["ticker"]: s["rs_rating"] for s in scored_rs}

    print(f"  Phase 2: Multi-strategy scoring ({len(df_cache)} qualified tickers)...")
    results = []

    for i, ticker in enumerate(df_cache):
        df  = df_cache[ticker]
        try:
            # ── 各手法のスコア計算 ──────────────────────────────
            vcp     = VCPAnalyzer.calculate(df)
            pf      = StrategyValidator.run(df)
            ses     = SentinelEfficiencyAnalyzer.calculate(df)
            ecr     = ECRStrategyEngine.analyze_single(ticker, df)
            rs      = rs_map.get(ticker, 0)

            # ファンダ・保有データ（CANSLIMに必要・24hキャッシュ済み）
            fund    = core_fmp.get_fundamentals(ticker) or {}
            own     = core_fmp.get_ownership(ticker) or {}
            canslim = CANSLIMAnalyzer.calculate(ticker, df, fund=fund, own=own)
            profile = core_fmp.get_company_profile(ticker) or {}

            # ── 価格・状態（内部計算のみ・JSON非保存）──────────
            price   = float(df["Close"].iloc[-1])
            pivot   = float(df["High"].iloc[-20:].max())
            dist    = (price - pivot) / pivot
            status  = "ACTION" if -0.05 <= dist <= 0.03 else ("WAIT" if dist < -0.05 else "EXTENDED")

            # ── 総合スコア（複数手法の加重平均）────────────────
            # VCP×RS: 35% / ECR: 35% / CANSLIM: 30%
            vcp_rs_normalized = min(100, (vcp["score"] / 105 * 50) + (rs / 99 * 50))
            composite = (
                vcp_rs_normalized      * 0.35 +
                ecr["sentinel_rank"]   * 0.35 +
                canslim["score"]       * 0.30
            )

            # ── アクティブ手法カウント（複数手法で上位 = 信頼度高）
            method_hits = sum([
                vcp["score"] >= 70 and rs >= 80,          # VCP×RS
                ecr["sentinel_rank"] >= 70,                # ECR
                canslim["score"] >= 60,                    # CANSLIM
                ses["score"] >= 60,                        # SES単体
            ])

            results.append({
                "ticker":       ticker,
                "name":         profile.get("companyName", ticker)[:25],
                "sector":       profile.get("sector", "N/A"),
                "status":       status,
                # 手法別スコア（派生データのみ）
                "scores": {
                    "vcp":           vcp["score"],
                    "rs":            rs,
                    "ses":           ses["score"],
                    "ecr_rank":      ecr["sentinel_rank"],
                    "canslim":       canslim["score"],
                    "composite":     round(composite, 1),
                    "pf":            round(pf, 2),
                },
                # ECR フェーズ情報
                "ecr_phase":     ecr["phase"],
                "ecr_strategy":  ecr["strategy"],
                # CANSLIM グレード
                "canslim_grade": canslim["grade"],
                # メタ情報
                "method_hits":   method_hits,    # 何手法で上位？
                "atr_pct":       round(vcp.get("atr", 0) / price * 100, 2) if price > 0 else None,
                "pivot_dist_pct": round(dist * 100, 2),
                "ma50_ratio":    None,  # 必要なら後で追加
            })

        except Exception as e:
            print(f"    ❌ {ticker}: {e}")
            continue

        if (i + 1) % 30 == 0:
            print(f"    {i+1}/{len(df_cache)} scored")
        time.sleep(0.15)

    return results


def build_rankings(results: list) -> dict:
    """手法別 + 総合のランキングを生成"""
    valid = [r for r in results if r["status"] in ("ACTION", "WAIT")]

    def top(key_fn, n=20):
        return sorted(valid, key=key_fn, reverse=True)[:n]

    return {
        "vcp_rs":    top(lambda r: r["scores"]["vcp"] * 0.5 + r["scores"]["rs"] * 0.5),
        "ecr":       top(lambda r: r["scores"]["ecr_rank"]),
        "canslim":   top(lambda r: r["scores"]["canslim"]),
        "ses":       top(lambda r: r["scores"]["ses"]),
        "composite": top(lambda r: r["scores"]["composite"]),
        # 複数手法で同時に上位 = 信頼度最高
        "consensus": sorted(valid, key=lambda r: (r["method_hits"], r["scores"]["composite"]),
                            reverse=True)[:20],
    }


def build_phase_summary(results: list) -> dict:
    """ECRフェーズ別の銘柄集計"""
    phases: dict = {}
    for r in results:
        p = r.get("ecr_phase", "WATCH")
        if p not in phases:
            phases[p] = []
        phases[p].append({
            "ticker":   r["ticker"],
            "name":     r["name"],
            "ecr_rank": r["scores"]["ecr_rank"],
            "strategy": r.get("ecr_strategy", "NONE"),
            "vcp":      r["scores"]["vcp"],
            "rs":       r["scores"]["rs"],
        })
    # 各フェーズ内をECRランク順でソート
    return {p: sorted(v, key=lambda x: x["ecr_rank"], reverse=True)[:15]
            for p, v in phases.items()}


def build_method_comparison(results: list) -> list:
    """
    手法別の分布比較データ（フロントエンドのグラフ用）
    各手法の上位20銘柄が他の手法でどのスコアか
    """
    summary = []
    for method, key in [
        ("VCP×RS",  lambda r: r["scores"]["vcp"] * 0.5 + r["scores"]["rs"] * 0.5),
        ("ECR",     lambda r: r["scores"]["ecr_rank"]),
        ("CANSLIM", lambda r: r["scores"]["canslim"]),
        ("SES",     lambda r: r["scores"]["ses"]),
    ]:
        top20 = sorted(results, key=key, reverse=True)[:20]
        summary.append({
            "method":      method,
            "top_tickers": [r["ticker"] for r in top20],
            "avg_scores": {
                "vcp":     round(sum(r["scores"]["vcp"]     for r in top20) / 20, 1),
                "ecr":     round(sum(r["scores"]["ecr_rank"]for r in top20) / 20, 1),
                "canslim": round(sum(r["scores"]["canslim"] for r in top20) / 20, 1),
                "ses":     round(sum(r["scores"]["ses"]     for r in top20) / 20, 1),
            }
        })
    return summary


def main():
    print(f"===== STRATEGIES SCAN {TODAY} =====")
    print(f"Scanning {len(SCAN_TICKERS)} tickers with 4 strategies...")

    results = scan_all()
    print(f"Scored: {len(results)} tickers")

    rankings    = build_rankings(results)
    phases      = build_phase_summary(results)
    method_cmp  = build_method_comparison(results)

    # ACTION数サマリー
    action_count = sum(1 for r in results if r["status"] == "ACTION")
    wait_count   = sum(1 for r in results if r["status"] == "WAIT")

    output = {
        "generated_at":  TODAY,
        "ticker_count":  len(results),
        "action_count":  action_count,
        "wait_count":    wait_count,
        "rankings":      rankings,
        "ecr_phases":    phases,
        "method_comparison": method_cmp,
    }

    CONTENT.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"✅ strategies.json saved")
    print(f"   Rankings: " + " / ".join(f"{k}:{len(v)}" for k, v in rankings.items()))
    print("===== Done =====")


if __name__ == "__main__":
    main()
