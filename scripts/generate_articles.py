#!/usr/bin/env python3
"""
scripts/generate_articles.py — 毎日実行
====================================
VCP×RSスキャン + AI記事生成
修正点: JSON化できないDataFrameオブジェクトを保存データから除外
"""
import sys, json, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# パス設定: 親ディレクトリの shared を読み込めるようにする
sys.path.append(str(Path(__file__).parent.parent / "shared"))

# エンジン群のインポート
from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from engines.ecr_strategy import ECRStrategyEngine
from engines.canslim import CANSLIMAnalyzer
from engines.config import CONFIG, TICKERS

# タイムゾーン設定 (JST)
JST      = timezone(timedelta(hours=9))
TODAY    = datetime.now(JST).strftime("%Y-%m-%d")

# 出力先設定
CONTENT  = Path(__file__).parent.parent / "frontend" / "public" / "content"
OUT_DIR  = CONTENT
CONTENT.mkdir(parents=True, exist_ok=True)

# AI設定
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "gpt-4")


def get_latest_trading_date() -> str:
    """
    FMPから取得できる最新の取引日を特定する。
    休場日（祝日・週末）に実行された場合、直近の営業日を返す。
    """
    print("\n=== Detecting latest trading date ===")

    # SPYのデータを使って市場が開いていた最新日を確認（最大5回リトライ）
    for attempt in range(5):
        df = core_fmp.get_historical_data("SPY", days=10)
        if df is not None and len(df) > 0:
            latest = df.index[-1].strftime("%Y-%m-%d")
            print(f"✅ FMP latest data: {latest}")
            print(f"   (Executed on: {TODAY})")

            if latest != TODAY:
                print(f"⚠️  Market closed on {TODAY}, using {latest} data")

            return latest

        if attempt < 4:
            print(f"   Retry {attempt+1}/5...")
            time.sleep(5)

    # 万が一SPYが取れない場合のフォールバック（日付計算）
    print("❌ Cannot fetch SPY data after 5 retries")
    dt = datetime.now(JST)
    if dt.weekday() == 5:  # 土曜なら金曜
        fallback = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    elif dt.weekday() == 6:  # 日曜なら金曜
        fallback = (dt - timedelta(days=2)).strftime("%Y-%m-%d")
    else:
        fallback = TODAY

    print(f"   Using fallback: {fallback}")
    return fallback


def scan_all_tickers(report_date: str):
    print(f"\n=== Scanning {len(TICKERS)} tickers ===")
    print(f"Report date: {report_date}")

    # 接続テスト (最初の3銘柄)
    print("\n--- Pre-scan test (first 3 tickers) ---")
    for i, ticker in enumerate(TICKERS[:3]):
        df = core_fmp.get_historical_data(ticker, days=10)
        if df is not None and len(df) > 0:
            latest = df.index[-1].strftime("%Y-%m-%d")
            price  = float(df["Close"].iloc[-1])
            print(f"  [{i+1}] {ticker:6s}: ✅ {len(df):2d} days, latest={latest}, price=${price:.2f}")
        else:
            print(f"  [{i+1}] {ticker:6s}: ❌ Data fetch failed")

    # 本番スキャン
    print("\n--- Full scan starting ---")
    raw_list = []
    failed_count = 0

    for i, ticker in enumerate(TICKERS):
        # 過去700日分取得（200日移動平均線などのために十分な期間）
        df = core_fmp.get_historical_data(ticker, days=700)
        
        # データ不足（上場直後など）はスキップ
        if df is None or len(df) < 200:
            failed_count += 1
            continue

        # RSスコア計算
        rs_raw = RSAnalyzer.get_raw_score(df)
        if rs_raw != -999.0:
            raw_list.append({"ticker": ticker, "df": df, "raw_rs": rs_raw})

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(TICKERS)} ({len(raw_list)} valid, {failed_count} failed)")

    print(f"\n--- RS assignment ---")
    print(f"  Total scanned: {len(raw_list)}")
    print(f"  Failed:        {failed_count}")

    if not raw_list:
        print("❌ No valid tickers found")
        return {"qualified":[], "actions":[], "waits":[], "all_scored":[]}

    # RSスコアの正規化（1-99）
    scored = RSAnalyzer.assign_percentiles(raw_list)
    print(f"  RS assigned:   {len(scored)}")

    print("\n--- Multi-strategy scoring ---")
    qualified, all_scored = [], []

    for i, item in enumerate(scored):
        # 各種戦略エンジンの実行
        vcp     = VCPAnalyzer.calculate(item["df"])
        pf      = StrategyValidator.run(item["df"])
        ses     = SentinelEfficiencyAnalyzer.calculate(item["df"])
        ecr     = ECRStrategyEngine.analyze_single(item["ticker"], item["df"])
        canslim = CANSLIMAnalyzer.calculate(item["ticker"], item["df"])

        # 各種数値の計算
        price = float(item["df"]["Close"].iloc[-1])
        pivot = float(item["df"]["High"].iloc[-20:].max()) # 簡易ピボット
        entry = round(pivot * 1.002, 2)
        
        # ATRベースの損切りライン
        stop  = round(entry - vcp["atr"] * CONFIG["STOP_LOSS_ATR"], 2)
        target= round(entry + (entry - stop) * CONFIG["TARGET_R_MULTIPLE"], 2)
        
        # ピボットからの距離
        dist  = (price - pivot) / pivot
        status= "ACTION" if -0.05<=dist<=0.03 else ("WAIT" if dist<-0.05 else "EXTENDED")

        # 表示用データ
        atr_pct       = round(vcp["atr"] / price * 100, 2) if price else None
        pivot_dist_pct= round(dist * 100, 2)
        stop_atr_mult = round(CONFIG["STOP_LOSS_ATR"], 2)
        target_r      = round(CONFIG["TARGET_R_MULTIPLE"], 1)

        close = item["df"]["Close"]
        ma50_ratio  = round(price / float(close.rolling(50).mean().iloc[-1]) * 100 - 100, 1) \
                      if len(close) >= 50 else None
        ma200_ratio = round(price / float(close.rolling(200).mean().iloc[-1]) * 100 - 100, 1) \
                      if len(close) >= 200 else None

        profile = core_fmp.get_company_profile(item["ticker"]) or {}

        # 【修正】JSON化できない "df" (DataFrame) を除外しました
        row = {
            "ticker":  item["ticker"],
            "status":  status,
            "rs":      item["rs_rating"],
            "vcp":     vcp["score"],
            "pf":      round(pf, 2),
            "sector":  profile.get("sector",  "N/A"),
            "industry":profile.get("industry","N/A"),
            "name":    profile.get("companyName", item["ticker"]),
            "vcp_detail": vcp,
            # "df": item["df"],  <-- ここにあったDataFrameを削除
            "atr_pct":        atr_pct,
            "pivot_dist_pct": pivot_dist_pct,
            "stop_atr_mult":  stop_atr_mult,
            "target_r":       target_r,
            "ma50_ratio":     ma50_ratio,
            "ma200_ratio":    ma200_ratio,
            "ses":            ses["score"],
            "ses_breakdown":  ses.get("breakdown", {}),
            "ecr_rank":       ecr["sentinel_rank"],
            "ecr_phase":      ecr["phase"],
            "ecr_strategy":   ecr["strategy"],
            "canslim_score":  canslim["score"],
            "canslim_grade":  canslim["grade"],
            "canslim_breakdown": canslim.get("breakdown", {}),
            # 総合スコア
            "composite": round(
                (vcp["score"] / 105 * 100) * 0.35 +
                ecr["sentinel_rank"]        * 0.35 +
                canslim["score"]            * 0.30,
                1
            ),
            "_price":  price,
            "_entry":  entry,
            "_stop":   stop,
            "_target": target,
        }

        all_scored.append(row)

        # フィルタリング（最低基準を満たすか）
        if (item["rs_rating"]>=CONFIG["MIN_RS_RATING"] and
                vcp["score"]>=CONFIG["MIN_VCP_SCORE"] and pf>=CONFIG["MIN_PROFIT_FACTOR"]):
            qualified.append(row)

        if (i + 1) % 100 == 0:
            print(f"  Scored: {i+1}/{len(scored)}")

    # ソート順: ACTION優先、次いで VCP+RS の合計スコア
    qualified.sort(key=lambda x:(x["status"]=="ACTION", x["vcp"]+x["rs"]), reverse=True)
    all_scored.sort(key=lambda x: x["vcp"]+x["rs"]*0.5, reverse=True)
    
    actions = [q for q in qualified if q["status"]=="ACTION"]
    waits   = [q for q in qualified if q["status"]=="WAIT"]

    print(f"\n--- Final results ---")
    print(f"  Total scored:  {len(all_scored)}")
    print(f"  Qualified:     {len(qualified)}")
    print(f"    - ACTION:    {len(actions)}")
    print(f"    - WAIT:      {len(waits)}")

    return {"qualified":qualified, "actions":actions, "waits":waits, "all_scored":all_scored}


def get_index_data():
    """主要指数の騰落率を取得"""
    result = {}
    for ticker, name in {"SPY":"S&P500","QQQ":"NASDAQ100","IWM":"Russell2000"}.items():
        try:
            df = core_fmp.get_historical_data(ticker, days=120)
            if df is None or len(df) < 5: continue
            close = df["Close"]
            result[ticker] = {
                "name": name,
                "ret_1d":  round((close.iloc[-1]/close.iloc[-2]-1)*100, 2) if len(close)>1 else None,
                "ret_5d":  round((close.iloc[-1]/close.iloc[-6]-1)*100, 2) if len(close)>5 else None,
                "ret_1m":  round((close.iloc[-1]/close.iloc[-21]-1)*100,2) if len(close)>20 else None,
            }
        except: pass
    return result


def build_vcp_ranking(all_scored: list, n: int = 20) -> list:
    """VCPスコアランキングの作成"""
    ranked = sorted(all_scored, key=lambda x: x["vcp"]+x["rs"], reverse=True)[:n]
    return [{
        "rank":   i+1,
        "ticker": r["ticker"],
        "name":   r["name"],
        "vcp":    r["vcp"],
        "rs":     r["rs"],
        "pf":     r["pf"],
        "status": r["status"],
    } for i, r in enumerate(ranked)]


def build_sector_summary(all_scored: list) -> list:
    """セクター別分析の作成"""
    sec = {}
    for r in all_scored:
        s = r.get("sector", "N/A")
        if s == "N/A": continue
        if s not in sec: sec[s] = {"count":0, "vcp_sum":0, "rs_sum":0, "action_count":0}
        sec[s]["count"] += 1
        sec[s]["vcp_sum"] += r["vcp"]
        sec[s]["rs_sum"]  += r["rs"]
        if r["status"] == "ACTION": sec[s]["action_count"] += 1

    return sorted([{
        "sector":       s,
        "avg_vcp":      round(v["vcp_sum"] / v["count"], 1),
        "avg_rs":       round(v["rs_sum"]  / v["count"], 1),
        "count":        v["count"],
        "action_count": v["action_count"],
    } for s, v in sec.items()], key=lambda x: x["avg_vcp"], reverse=True)


def generate_daily_ai_report(actions: list, index: dict, sector: list, 
                              ranking: list, report_date: str, lang: str = "ja"):
    """AIによる市況コメント生成"""
    import requests
    idx_str  = ", ".join([f"{v['name']} {v.get('ret_1d','?')}%" for v in index.values()])
    sec_str  = ", ".join([f"{s['sector']}" for s in sector[:3]])
    act_str  = ", ".join([a["ticker"] for a in actions[:5]])

    system = (
        "あなたは米国株式市場の専門アナリストです。"
        "以下の情報をもとに、教育的でバランスの取れた日次レポートを執筆してください。"
        "特定銘柄の売買推奨は行わず、市場動向とパターン分析に焦点を当ててください。"
        "株価・ドル金額は一切記載しないでください。"
    ) if lang == "ja" else (
        "You are a US equity market analyst. Write an educational daily report based on the data below. "
        "Do not include specific buy/sell recommendations or price targets. "
        "Do not include any dollar amounts or stock prices."
    )

    prompt = (
        f"日付: {report_date}\n"
        f"主要指数: {idx_str}\n"
        f"強いセクター: {sec_str}\n"
        f"VCPシグナル（ACTION）: {len(actions)}銘柄 {act_str if actions else 'なし'}\n\n"
        f"以下の3セクションで600-800文字のレポートを作成:\n"
        f"## ①指数動向\n## ②VCP×RSシグナル\n## ③セクター分析"
    ) if lang == "ja" else (
        f"Date: {report_date}\n"
        f"Indices: {idx_str}\n"
        f"Top sectors: {sec_str}\n"
        f"VCP signals: {len(actions)} stocks\n\n"
        f"Write a 300-400 word report with:\n"
        f"## ① Index\n## ② Signals\n## ③ Sectors"
    )

    try:
        resp = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": OPENAI_MODEL, "max_tokens": 1500,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user",   "content": prompt}]},
            timeout=60
        )
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"AI error: {e}")
        return "（レポート生成失敗）" if lang == "ja" else "(Report generation failed)"


def main():
    # 1. 最新の取引日を取得（祝日なら直近営業日）
    REPORT_DATE = get_latest_trading_date()

    print(f"\n{'='*60}")
    print(f"SENTINEL DAILY {REPORT_DATE}")
    print(f"{'='*60}")

    # 2. 全銘柄スキャン＆スコアリング
    result = scan_all_tickers(REPORT_DATE)

    print("\n=== Generating daily report ===")
    index   = get_index_data()
    ranking = build_vcp_ranking(result["all_scored"])
    sector  = build_sector_summary(result["all_scored"])

    idx_ret = list(index.values())[0].get("ret_1d", "?") if index else "?"

    # 3. AIコメント生成
    daily_ja = generate_daily_ai_report(result["actions"], index, sector, ranking, REPORT_DATE, "ja")
    daily_en = generate_daily_ai_report(result["actions"], index, sector, ranking, REPORT_DATE, "en")

    # 4. JSON構築
    daily_article = {
        "slug": f"daily-{REPORT_DATE}",
        "type": "daily",
        "date": REPORT_DATE,
        "published_at": datetime.now(JST).isoformat(),
        "ja": {
            "title": f"{REPORT_DATE} 米国株レポート — SPY {idx_ret}% / ACTION {len(result['actions'])}銘柄",
            "summary": f"S&P500 {idx_ret}%、強いセクター:{sector[0]['sector'] if sector else ''}。VCPシグナルACTION {len(result['actions'])}銘柄。",
            "body": daily_ja,
        },
        "en": {
            "title": f"US Market {REPORT_DATE} — SPY {idx_ret}% / {len(result['actions'])} ACTION",
            "summary": f"S&P500 {idx_ret}%, top sectors:{sector[0]['sector'] if sector else ''}. {len(result['actions'])} ACTION signals.",
            "body": daily_en,
        },
        "data": {
            "action_count": len(result["actions"]),
            "wait_count":   len(result["waits"]),
            "actions":      result["actions"][:10],
            "index":        index,
            "sector":       sector,
            "vcp_ranking":  ranking,
        }
    }

    # 5. ファイル保存
    (OUT_DIR / f"daily-{REPORT_DATE}.json").write_text(
        json.dumps(daily_article, ensure_ascii=False, indent=2)
    )
    print("✅ Daily report saved")

    # 6. index.json 更新（破損対策済み）
    index_file = OUT_DIR / "index.json"
    if index_file.exists():
        try:
            idx = json.loads(index_file.read_text())
            if not isinstance(idx, dict) or "articles" not in idx:
                idx = {"articles": []}
            if not isinstance(idx["articles"], list):
                idx = {"articles": []}
        except:
            idx = {"articles": []}
    else:
        idx = {"articles": []}

    # 重複削除＆先頭に追加
    idx["articles"] = [a for a in idx["articles"] if a.get("slug") != daily_article["slug"]]
    idx["articles"].insert(0, {
        "slug": daily_article["slug"],
        "type": daily_article["type"],
        "date": daily_article["date"],
        "published_at": daily_article["published_at"],
        "title_ja": daily_article["ja"]["title"],
        "title_en": daily_article["en"]["title"],
    })

    # 過去100件まで保持
    idx["articles"] = idx["articles"][:100]
    index_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2))
    print(f"index.json: {len(idx['articles'])} entries")

    print(f"\n{'='*60}")
    print(f"Done: 1 article")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()