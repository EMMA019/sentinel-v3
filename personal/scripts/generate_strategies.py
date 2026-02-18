#!/usr/bin/env python3
"""
generate_strategies.py — 完全版
================================
- 30日履歴保存
- 全数値必ず出力（ma50_ratio, ma200_ratio など）
- 並列処理対応（MAX_WORKERS=2）

出力:
  - frontend/public/content/strategies.json
  - frontend/public/content/strategies_history/{date}.json (30日分)
"""
import sys, json, time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

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
HIST    = CONTENT / "strategies_history"

# 全銘柄スキャン（最大600銘柄）
SCAN_TICKERS = TICKERS
MAX_WORKERS  = 2  # API制限考慮


def process_ticker(ticker: str):
    """1銘柄の全手法計算（並列用）"""
    try:
        df = core_fmp.get_historical_data(ticker, days=700)
        if df is None or len(df) < 200:
            return None

        # 各手法計算
        vcp     = VCPAnalyzer.calculate(df)
        pf      = StrategyValidator.run(df)
        ses     = SentinelEfficiencyAnalyzer.calculate(df)
        ecr     = ECRStrategyEngine.analyze_single(ticker, df)
        rs_raw  = RSAnalyzer.get_raw_score(df)
        
        fund    = core_fmp.get_fundamentals(ticker) or {}
        own     = core_fmp.get_ownership(ticker) or {}
        canslim = CANSLIMAnalyzer.calculate(ticker, df, fund=fund, own=own)
        profile = core_fmp.get_company_profile(ticker) or {}

        # 価格計算（全数値必ず出力）
        price  = float(df["Close"].iloc[-1])
        pivot  = float(df["High"].iloc[-20:].max())
        dist   = (price - pivot) / pivot
        status = "ACTION" if -0.05 <= dist <= 0.03 else ("WAIT" if dist < -0.05 else "EXTENDED")

        # MA比率（必ず計算・Noneを避ける）
        ma50  = df["Close"].rolling(50).mean().iloc[-1]
        ma200 = df["Close"].rolling(200).mean().iloc[-1]
        ma50_ratio  = round((price / ma50  - 1) * 100, 1) if pd.notna(ma50)  and ma50  > 0 else 0.0
        ma200_ratio = round((price / ma200 - 1) * 100, 1) if pd.notna(ma200) and ma200 > 0 else 0.0

        # ATR比率（必ず計算）
        atr = vcp.get("atr", 0)
        atr_pct = round(atr / price * 100, 2) if price > 0 else 0.0

        return {
            "ticker": ticker,
            "raw_rs": rs_raw,
            "data": {
                "ticker":       ticker,
                "name":         profile.get("companyName", ticker)[:25],
                "sector":       profile.get("sector", "N/A"),
                "status":       status,
                "scores": {
                    "vcp":        vcp["score"],
                    "ses":        ses["score"],
                    "ecr_rank":   ecr["sentinel_rank"],
                    "canslim":    canslim["score"],
                    "pf":         round(pf, 2),
                },
                "ecr_phase":     ecr["phase"],
                "ecr_strategy":  ecr["strategy"],
                "canslim_grade": canslim["grade"],
                "atr_pct":       atr_pct,
                "pivot_dist_pct": round(dist * 100, 2),
                "ma50_ratio":    ma50_ratio,
                "ma200_ratio":   ma200_ratio,
            }
        }
    except Exception as e:
        print(f"    ❌ {ticker}: {e}")
        return None


def scan_all():
    """並列スキャン"""
    print(f"  Starting scan: {len(SCAN_TICKERS)} tickers (Workers={MAX_WORKERS})...")
    
    raw_results = []
    processed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_ticker, t): t for t in SCAN_TICKERS}
        
        for future in as_completed(futures):
            processed += 1
            res = future.result()
            if res:
                raw_results.append(res)
            
            if processed % 50 == 0:
                print(f"    {processed}/{len(SCAN_TICKERS)} processed")

    # RS percentile計算
    print(f"  Calculating RS percentiles...")
    rs_input = [{"ticker": r["ticker"], "raw_rs": r["raw_rs"]} for r in raw_results]
    scored_rs = RSAnalyzer.assign_percentiles(rs_input)
    rs_map = {s["ticker"]: s["rs_rating"] for s in scored_rs}

    # 最終データ構築
    final_results = []
    for r in raw_results:
        d = r["data"]
        rs = rs_map.get(r["ticker"], 0)
        d["scores"]["rs"] = rs

        # 総合スコア
        vcp_rs_norm = min(100, (d["scores"]["vcp"] / 105 * 50) + (rs / 99 * 50))
        composite = (
            vcp_rs_norm * 0.35 +
            d["scores"]["ecr_rank"] * 0.35 +
            d["scores"]["canslim"] * 0.30
        )
        d["scores"]["composite"] = round(composite, 1)

        # 手法ヒット数
        d["method_hits"] = sum([
            d["scores"]["vcp"] >= 70 and rs >= 80,
            d["scores"]["ecr_rank"] >= 70,
            d["scores"]["canslim"] >= 60,
            d["scores"]["ses"] >= 60,
        ])
        
        final_results.append(d)

    return final_results


def build_rankings(results):
    valid = [r for r in results if r["status"] in ("ACTION", "WAIT")]
    def top(key_fn, n=30):
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


def build_phase_summary(results):
    phases = {}
    for r in results:
        p = r.get("ecr_phase", "WATCH")
        if p not in phases:
            phases[p] = []
        phases[p].append(r)
    return {p: sorted(v, key=lambda x: x["scores"]["ecr_rank"], reverse=True)[:20] 
            for p, v in phases.items()}


def build_method_comparison(results):
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


def save_history(results):
    """30日履歴保存"""
    HIST.mkdir(parents=True, exist_ok=True)
    
    # 簡略化（スコアのみ）
    simplified = [{
        "ticker": r["ticker"],
        "scores": r["scores"],
        "status": r["status"],
    } for r in results]
    
    hist_file = HIST / f"{TODAY}.json"
    hist_file.write_text(json.dumps(simplified, ensure_ascii=False, indent=2))
    
    # 古い履歴削除（30日より前）
    all_hist = sorted(HIST.glob("*.json"))
    if len(all_hist) > 30:
        for old in all_hist[:-30]:
            old.unlink()
    
    print(f"  💾 History saved: {hist_file.name} ({len(all_hist)} days)")


def main():
    print(f"===== STRATEGIES FULL SCAN {TODAY} =====")
    
    results = scan_all()
    print(f"✅ Scored: {len(results)}/{len(SCAN_TICKERS)} tickers")

    rankings = build_rankings(results)
    phases   = build_phase_summary(results)
    method_cmp = build_method_comparison(results)

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
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    
    # 履歴保存
    save_history(results)
    
    print(f"✅ strategies.json saved")
    print(f"===== Done =====")


if __name__ == "__main__":
    main()
