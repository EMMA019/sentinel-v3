#!/usr/bin/env python3
"""
scripts/generate_articles.py
============================
【平日】スキャン → 日次レポート（指数+セクター+VCPランキング）
         + 銘柄ページ累積更新（TICKER.json を上書き）
【土曜】週次レポート（先週振り返り + 翌週展望）
"""
import sys, json, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent.parent / "shared"))
sys.path.append(str(Path(__file__).parent))
from engines import core_fmp
from engines.analysis            import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer
from engines.ecr_strategy        import ECRStrategyEngine
from engines.canslim             import CANSLIMAnalyzer
from engines.config              import CONFIG, TICKERS
try:
    from generate_chart import generate_candle_chart
    CHART_ENABLED = True
except ImportError:
    CHART_ENABLED = False
    print("Chart generation disabled (mplfinance not installed)")

JST   = timezone(timedelta(hours=9))
NOW   = datetime.now(JST)
TODAY = NOW.strftime("%Y-%m-%d")
IS_SATURDAY = NOW.weekday() == 5

CONTENT_DIR = Path(__file__).parent.parent / "frontend" / "public" / "content"
DAILY_DIR   = CONTENT_DIR / "daily"
STOCKS_DIR  = CONTENT_DIR / "stocks"
WEEKLY_DIR  = CONTENT_DIR / "weekly"
INDEX_FILE  = CONTENT_DIR / "index.json"
for d in [DAILY_DIR, STOCKS_DIR, WEEKLY_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def call_ai(prompt, max_tokens=1500, system=""):
    api_key  = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    model    = os.environ.get("OPENAI_MODEL", "deepseek-chat")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client   = OpenAI(api_key=api_key, base_url=base_url)
        messages = ([{"role":"system","content":system}] if system else [])
        messages.append({"role":"user","content":prompt})
        res = client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=messages, temperature=0.7)
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI error: {e}"); return ""


def run_scan():
    print(f"Scanning {len(TICKERS)} tickers...")
    raw_list = []
    for t in TICKERS:
        df = core_fmp.get_historical_data(t, days=700)
        if df is None or len(df) < 200:
            continue
        rs_raw = RSAnalyzer.get_raw_score(df)
        if rs_raw != -999.0:
            raw_list.append({"ticker": t, "df": df, "raw_rs": rs_raw})
    if not raw_list:
        return {"qualified":[], "actions":[], "waits":[], "all_scored":[]}

    scored = RSAnalyzer.assign_percentiles(raw_list)
    qualified, all_scored = [], []
    for item in scored:
        vcp   = VCPAnalyzer.calculate(item["df"])
        pf    = StrategyValidator.run(item["df"])
        # ── 追加手法スコア ───────────────────────────────
        ses      = SentinelEfficiencyAnalyzer.calculate(item["df"])
        ecr      = ECRStrategyEngine.analyze_single(item["ticker"], item["df"])
        # CANSLIMはファンダデータなしでも動く（Nance/S/L要素で部分スコア）
        canslim  = CANSLIMAnalyzer.calculate(item["ticker"], item["df"])
        # ── 価格は内部計算のみ使用・JSONには出力しない ───
        price = float(item["df"]["Close"].iloc[-1])
        pivot = float(item["df"]["High"].iloc[-20:].max())
        entry = round(pivot * 1.002, 2)
        stop  = round(entry - vcp["atr"] * CONFIG["STOP_LOSS_ATR"], 2)
        target= round(entry + (entry - stop) * CONFIG["TARGET_R_MULTIPLE"], 2)
        dist  = (price - pivot) / pivot
        status= "ACTION" if -0.05<=dist<=0.03 else ("WAIT" if dist<-0.05 else "EXTENDED")

        # 派生データのみ保持（価格は保存しない）
        atr_pct       = round(vcp["atr"] / price * 100, 2) if price else None
        pivot_dist_pct= round(dist * 100, 2)               # ピボットからの乖離%
        stop_atr_mult = round(CONFIG["STOP_LOSS_ATR"], 2)  # ストップ = entry - N×ATR
        target_r      = round(CONFIG["TARGET_R_MULTIPLE"], 1) # ターゲット = entry + R×リスク

        # MA情報（派生データ）
        close = item["df"]["Close"]
        ma50_ratio  = round(price / float(close.rolling(50).mean().iloc[-1]) * 100 - 100, 1) \
                      if len(close) >= 50 else None
        ma200_ratio = round(price / float(close.rolling(200).mean().iloc[-1]) * 100 - 100, 1) \
                      if len(close) >= 200 else None

        profile = core_fmp.get_company_profile(item["ticker"]) or {}
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
            "df":      item["df"],
            # 派生データ（価格を含まない）
            "atr_pct":        atr_pct,
            "pivot_dist_pct": pivot_dist_pct,
            "stop_atr_mult":  stop_atr_mult,
            "target_r":       target_r,
            "ma50_ratio":     ma50_ratio,
            "ma200_ratio":    ma200_ratio,
            # 追加手法スコア（派生データ）
            "ses":            ses["score"],
            "ses_breakdown":  ses.get("breakdown", {}),
            "ecr_rank":       ecr["sentinel_rank"],
            "ecr_phase":      ecr["phase"],
            "ecr_strategy":   ecr["strategy"],
            "canslim_score":  canslim["score"],
            "canslim_grade":  canslim["grade"],
            "canslim_breakdown": canslim.get("breakdown", {}),
            # 総合複合スコア（3手法の正規化平均）
            # VCP×RS(0-105→0-100正規化), ECR(0-100), CANSLIM(0-100)
            "composite": round(
                (vcp["score"] / 105 * 100) * 0.35 +
                ecr["sentinel_rank"]        * 0.35 +
                canslim["score"]            * 0.30,
                1
            ),
            # 内部計算用のみ（JSON保存では除外）
            "_price":  price,
            "_entry":  entry,
            "_stop":   stop,
            "_target": target,
        }
        all_scored.append(row)
        if (item["rs_rating"]>=CONFIG["MIN_RS_RATING"] and
                vcp["score"]>=CONFIG["MIN_VCP_SCORE"] and pf>=CONFIG["MIN_PROFIT_FACTOR"]):
            qualified.append(row)

    qualified.sort(key=lambda x:(x["status"]=="ACTION", x["vcp"]+x["rs"]), reverse=True)
    all_scored.sort(key=lambda x: x["vcp"]+x["rs"]*0.5, reverse=True)
    actions = [q for q in qualified if q["status"]=="ACTION"]
    waits   = [q for q in qualified if q["status"]=="WAIT"]
    print(f"ACTION:{len(actions)} WAIT:{len(waits)} Scored:{len(all_scored)}")
    return {"qualified":qualified, "actions":actions, "waits":waits, "all_scored":all_scored}


def get_index_data():
    result = {}
    for ticker, name in {"SPY":"S&P500","QQQ":"NASDAQ100","IWM":"Russell2000"}.items():
        try:
            df = core_fmp.get_historical_data(ticker, days=30)
            if df is None or len(df)<6: continue
            c = df["Close"]
            result[ticker] = {
                "name":name, "price":round(float(c.iloc[-1]),2),
                "chg_1d": round((float(c.iloc[-1])/float(c.iloc[-2])-1)*100,2),
                "chg_5d": round((float(c.iloc[-1])/float(c.iloc[-6])-1)*100,2),
                "chg_20d":round((float(c.iloc[-1])/float(c.iloc[-21])-1)*100,2) if len(c)>=21 else None,
            }
        except Exception as e:
            print(f"Index error {ticker}: {e}")
    return result


def calc_sector_summary(all_scored):
    sectors = {}
    for item in all_scored:
        s = item.get("sector","N/A")
        if s=="N/A": continue
        if s not in sectors:
            sectors[s] = {"rs_sum":0,"vcp_sum":0,"count":0,"actions":0}
        sectors[s]["rs_sum"]  += item["rs"]
        sectors[s]["vcp_sum"] += item["vcp"]
        sectors[s]["count"]   += 1
        if item["status"]=="ACTION": sectors[s]["actions"]+=1
    result = []
    for s,v in sectors.items():
        n=v["count"]
        result.append({"sector":s,"avg_rs":round(v["rs_sum"]/n,1),
                        "avg_vcp":round(v["vcp_sum"]/n,1),"count":n,"action_count":v["actions"]})
    return sorted(result, key=lambda x:x["avg_rs"], reverse=True)


def build_vcp_ranking(all_scored, top_n=30):
    return [{"rank":i+1, "ticker":r["ticker"], "name":r["name"],
             "vcp":r["vcp"], "rs":r["rs"], "status":r["status"],
             "sector":r["sector"],
             "atr_pct":      r.get("atr_pct"),
             "pivot_dist_pct":r.get("pivot_dist_pct"),
             "ma50_ratio":   r.get("ma50_ratio"),
             "pf":           r.get("pf")}
            for i,r in enumerate(all_scored[:top_n])]


def generate_daily_report(scan, index_data, sector_data):
    actions = scan["actions"]; waits = scan["waits"]
    ranking = build_vcp_ranking(scan["all_scored"])
    at = ", ".join(q["ticker"] for q in actions[:10]) or "なし"
    wt = ", ".join(q["ticker"] for q in waits[:8])   or "なし"
    top_sectors = " / ".join(s["sector"] for s in sector_data[:3])

    idx_ja = "\n".join(
        f"{d['name']}: {'+' if d['chg_1d']>=0 else ''}{d['chg_1d']}% (5日:{'+' if d['chg_5d']>=0 else ''}{d['chg_5d']}%)"
        for d in index_data.values())
    idx_en = "\n".join(
        f"{d['name']}: {'+' if d['chg_1d']>=0 else ''}{d['chg_1d']}% (5d:{'+' if d['chg_5d']>=0 else ''}{d['chg_5d']}%)"
        for d in index_data.values())

    sys_msg = "あなたは米国株の定量アナリストです。データを正確に解釈し、教育的かつ読みやすい文章を書いてください。投資助言は絶対にしないでください。"
    p_ja = f"""本日（{TODAY}）の米国株市場レポートを作成してください。

【指数動向】
{idx_ja}

【スキャン結果】ACTIONシグナル:{len(actions)}銘柄({at}) / WAIT:{len(waits)}銘柄({wt})
【強いセクター上位3】{top_sectors}

700〜900文字。見出し3つ(## ①指数動向 ②VCP×RSシグナル ③セクター分析)。
VCPとRSの意味を自然に説明。断定表現禁止。末尾に1行免責事項。Markdown出力。"""

    p_en = f"""Write today's ({TODAY}) US stock market report.
【Index】{idx_en}
【Signals】ACTION:{len(actions)}({at}) WAIT:{len(waits)}({wt})
【Top Sectors】{top_sectors}
350-450 words, 3 headings (##①Index ②Signals ③Sectors), explain VCP/RS,
no recommendations, 1-line disclaimer. Markdown."""

    print("Generating daily report...")
    body_ja = call_ai(p_ja, 1400, sys_msg) or f"""## {TODAY} 指数動向\n{idx_ja}\n## VCP×RSシグナル\nACTION **{len(actions)}銘柄**: {at}\n## セクター分析\n強いセクター: {top_sectors}\n⚠️ 教育目的であり、投資助言ではありません。"""
    body_en = call_ai(p_en, 900) or f"""## Index {TODAY}\n{idx_en}\n## Signals\nACTION:{len(actions)} {at}\n## Sectors\nLeading: {top_sectors}\n⚠️ Not investment advice."""

    spx = index_data.get("SPY",{}).get("chg_1d","?")
    slug = f"daily-{TODAY}"
    return {
        "slug":slug,"type":"daily","date":TODAY,"published_at":NOW.isoformat(),
        "ja":{"title":f"{TODAY} 米国株レポート — SPY {spx}% / ACTION {len(actions)}銘柄",
              "summary":f"S&P500 {spx}%、強いセクター:{top_sectors}。VCPシグナルACTION {len(actions)}銘柄。","body":body_ja},
        "en":{"title":f"US Market {TODAY} — SPY {spx}% / {len(actions)} ACTION",
              "summary":f"S&P500 {spx}%, top sectors:{top_sectors}. {len(actions)} ACTION signals.","body":body_en},
        "data":{"action_count":len(actions),"wait_count":len(waits),
                "actions":[{k:v for k,v in a.items() if k not in("vcp_detail","df")} for a in actions[:10]],
                "index":index_data,"sector":sector_data,"vcp_ranking":ranking},
    }


def update_stock_page(item):
    ticker = item["ticker"]
    vcp    = item["vcp_detail"]
    bd     = vcp.get("breakdown",{})
    sig_ja = " / ".join(vcp.get("signals",[])) or "なし"
    sig_en = " / ".join(vcp.get("signals",[])) or "none"
    stock_file = STOCKS_DIR / f"{ticker}.json"

    # 履歴保持
    history = []
    if stock_file.exists():
        try:
            ex = json.loads(stock_file.read_text(encoding="utf-8"))
            history = ex.get("history",[])
            if ex.get("date") and ex["date"] != TODAY:
                snap = {"date":ex["date"],"vcp":ex.get("data",{}).get("vcp"),
                        "rs":ex.get("data",{}).get("rs"),"price":ex.get("data",{}).get("price"),
                        "status":ex.get("data",{}).get("status")}
                history = ([snap]+history)[:90]
        except Exception:
            pass

    print(f"  Updating: {ticker} (fetching rich data)...")

    # ── リッチデータ取得（FMP Starter） ──────────────────
    analyst   = core_fmp.get_analyst_consensus(ticker) or {}
    fund      = core_fmp.get_fundamentals(ticker)      or {}
    ownership = core_fmp.get_ownership(ticker)         or {}
    news      = core_fmp.get_news(ticker, limit=5)

    # ── AI記事生成（価格なし・派生データのみ）────────────
    # ※ 価格($)は内部計算のみ使用、AIプロンプトにも生データを含めない
    analyst_str = ""
    if analyst:
        analyst_str = f"アナリスト評価:{analyst.get('consensus','N/A')}({analyst.get('analyst_count',0)}名) 目標株価乖離:{analyst.get('target_pct','N/A')}%"

    fund_str = ""
    if fund:
        fund_str = (f"予想PER:{fund.get('pe_forward','N/A')} 売上成長率:{fund.get('revenue_growth_yoy','N/A')}% "
                    f"利益成長率:{fund.get('earnings_growth_yoy','N/A')}% ROE:{fund.get('roe','N/A')}% "
                    f"粗利率:{fund.get('gross_margin','N/A')}% 時価総額:{fund.get('market_cap_b','N/A')}B USD")

    own_str = ""
    if ownership:
        own_str = (f"機関投資家保有率:{ownership.get('institutional_pct','N/A')}% "
                   f"空売り比率:{ownership.get('short_float_pct','N/A')}% "
                   f"空売り日数:{ownership.get('short_days_to_cover','N/A')}日")

    # 派生データのみでプロンプトを構成（価格を含まない）
    derived = (f"ATR%:{item.get('atr_pct','N/A')} ピボット乖離:{item.get('pivot_dist_pct','N/A')}% "
               f"MA50乖離:{item.get('ma50_ratio','N/A')}% MA200乖離:{item.get('ma200_ratio','N/A')}% "
               f"ストップ:{item.get('stop_atr_mult','N/A')}×ATR ターゲット:{item.get('target_r','N/A')}R")

    news_str = "\n".join(f"- {n['title']} ({n['source']})" for n in news[:3]) or "なし"

    sys_msg = "あなたは米国株のテクニカル・ファンダメンタルアナリストです。定量データを正確に解説し、初心者にも分かりやすい教育的コンテンツを書いてください。投資助言は絶対にしないでください。株価・ドル金額は一切記載しないでください。"

    p_ja = f"""{item['name']}（{ticker}）の総合分析レポート（1200〜1500文字）を書いてください。

【テクニカル】
VCPスコア:{item['vcp']}/105(T:{bd.get('tight',0)} V:{bd.get('vol',0)} MA:{bd.get('ma',0)} P:{bd.get('pivot',0)})
RS:{item['rs']}/99 PF:{item['pf']}x 状態:{item['status']}
{derived}
シグナル:{sig_ja} セクター:{item['sector']}/{item['industry']}

【ファンダメンタル】
{fund_str if fund_str else "データなし"}

【アナリスト評価】
{analyst_str if analyst_str else "データなし"}

【投資家動向】
{own_str if own_str else "データなし"}

【直近ニュース】
{news_str}

見出し5つ(##①企業・セクター概要 ②テクニカル分析（VCP詳細） ③ファンダメンタル ④アナリスト・投資家動向 ⑤注意点)。
断定的売買推奨と株価・ドル金額の記載は禁止。末尾に免責事項。Markdown出力。"""

    p_en = f"""Write a comprehensive analysis (600-700 words) for {item['name']} ({ticker}).
Note: Do NOT include any price/dollar amounts in the output.

[Technical] VCP:{item['vcp']}/105 RS:{item['rs']}/99 PF:{item['pf']}x Status:{item['status']}
{derived} Signals:{sig_en}

[Fundamentals] {fund_str or "N/A"}
[Analyst] {analyst_str or "N/A"}
[Ownership] {own_str or "N/A"}

5 headings(##①Overview ②Technical/VCP ③Fundamentals ④Analyst/Ownership ⑤Caution).
NO price/dollar amounts. No buy/sell recommendations. 1-line disclaimer. Markdown."""

    body_ja = call_ai(p_ja, 2200, sys_msg) or f"""## {item['name']}（{ticker}）\n## テクニカル分析\nVCP:{item['vcp']}/105 RS:{item['rs']}/99 状態:{item['status']}\n## ファンダメンタル\n{fund_str}\n## アナリスト\n{analyst_str}\n## 注意点\n⚠️ 投資助言ではありません。"""
    body_en = call_ai(p_en, 1400) or f"""## {ticker}\n## Technical\nVCP:{item['vcp']}/105 RS:{item['rs']}\n## Fundamentals\n{fund_str}\n## Analyst\n{analyst_str}\n## Caution\n⚠️ Not investment advice."""
    time.sleep(1.5)

    slug = f"stock-{ticker.lower()}"
    doc = {
        "slug":slug, "type":"stock", "ticker":ticker, "name":item["name"],
        "date":TODAY, "published_at":NOW.isoformat(),
        "ja":{
            "title":   f"{item['name']}（{ticker}）VCPスコア分析 {item['vcp']}点・RS{item['rs']}【{TODAY}更新】",
            "summary": f"{ticker} VCP:{item['vcp']}/105 RS:{item['rs']} {item['status']}。{analyst_str[:60] if analyst_str else ''}。{TODAY}更新。",
            "body":    body_ja,
        },
        "en":{
            "title":   f"{item['name']} ({ticker}) VCP Score Analysis {item['vcp']} RS{item['rs']} [{TODAY}]",
            "summary": f"{ticker} VCP:{item['vcp']}/105 RS:{item['rs']} {item['status']}. {TODAY}.",
            "body":    body_en,
        },
        "data":{
            # 派生データのみ（生の価格は一切含まない）
            "ticker":    ticker,
            "name":      item["name"],
            "status":    item["status"],
            "rs":        item["rs"],
            "vcp":       item["vcp"],
            "pf":        item["pf"],
            "sector":    item["sector"],
            "industry":  item["industry"],
            "vcp_breakdown": bd,
            "signals":   vcp.get("signals", []),
            # 派生データ
            "atr_pct":         item.get("atr_pct"),
            "pivot_dist_pct":  item.get("pivot_dist_pct"),
            "stop_atr_mult":   item.get("stop_atr_mult"),
            "target_r":        item.get("target_r"),
            "ma50_ratio":      item.get("ma50_ratio"),
            "ma200_ratio":     item.get("ma200_ratio"),
            # 追加手法スコア
            "ses":             item.get("ses"),
            "ses_breakdown":   item.get("ses_breakdown", {}),
            "ecr_rank":        item.get("ecr_rank"),
            "ecr_phase":       item.get("ecr_phase"),
            "ecr_strategy":    item.get("ecr_strategy"),
            # ファンダ・アナリスト・動向（派生データ）
            "analyst":         analyst,
            "fundamentals":    fund,
            "ownership":       ownership,
            "news":            news,
        },
        "history": history,
    }
    stock_file.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    return doc


def generate_weekly_report(scan, index_data, sector_data):
    actions = scan["actions"]
    ranking = build_vcp_ranking(scan["all_scored"], top_n=20)
    week_str = f"{(NOW-timedelta(days=6)).strftime('%m/%d')}〜{NOW.strftime('%m/%d')}"
    top_rank = "\n".join(f"{r['rank']}. {r['ticker']} VCP:{r['vcp']} RS:{r['rs']} [{r['status']}]" for r in ranking[:10])
    top_sectors = " / ".join(s["sector"] for s in sector_data[:3])
    spx5 = index_data.get("SPY",{}).get("chg_5d","N/A")
    qqq5 = index_data.get("QQQ",{}).get("chg_5d","N/A")
    iwm5 = index_data.get("IWM",{}).get("chg_5d","N/A")

    sys_msg = "あなたは米国株市場の週次レポートを作成するアナリストです。投資助言は厳禁です。"
    p_ja = f"""先週（{week_str}）の米国株振り返りと翌週展望レポート（1000〜1300文字）を作成してください。
指数: S&P500 {spx5}% / NASDAQ100 {qqq5}% / Russell2000 {iwm5}%
VCPランキング上位10:\n{top_rank}
強いセクター:{top_sectors}
見出し4つ(##①先週の振り返り ②注目銘柄 ③セクター動向 ④翌週の注目ポイント)。
翌週の市場環境も解説。断定表現禁止。末尾に免責事項。Markdown出力。"""

    p_en = f"""Weekly US stock review & outlook for {week_str} (500-650 words).
SPY:{spx5}% QQQ:{qqq5}% IWM:{iwm5}%
Top VCP:\n{top_rank}
Top sectors:{top_sectors}
4 headings(##①Review ②Stocks ③Sectors ④Outlook). No recommendations. Disclaimer. Markdown."""

    print("Generating weekly report...")
    body_ja = call_ai(p_ja, 2000, sys_msg) or f"""## 先週({week_str})の振り返り\nS&P500:{spx5}% NASDAQ:{qqq5}%\n## 注目銘柄\n{top_rank}\n## セクター動向\n{top_sectors}\n## 翌週の注目ポイント\nACTION:{len(actions)}銘柄\n⚠️ 投資助言ではありません。"""
    body_en = call_ai(p_en, 1200) or f"""## Week in Review ({week_str})\nSPY:{spx5}% QQQ:{qqq5}%\n## Top Stocks\n{top_rank}\n## Sectors\n{top_sectors}\n## Outlook\nACTION:{len(actions)}\n⚠️ Not investment advice."""

    slug = f"weekly-{TODAY}"
    return {
        "slug":slug,"type":"weekly","date":TODAY,"week":week_str,"published_at":NOW.isoformat(),
        "ja":{"title":f"週次レポート {week_str} — 振り返りと翌週展望",
              "summary":f"S&P500先週{spx5}%。強いセクター:{top_sectors}。翌週のVCP注目銘柄を解説。","body":body_ja},
        "en":{"title":f"Weekly Report {week_str} — Review & Outlook",
              "summary":f"S&P500 weekly {spx5}%. Top sectors:{top_sectors}. VCP outlook for next week.","body":body_en},
        "data":{"week":week_str,"index":index_data,"sector":sector_data,
                "vcp_ranking":ranking,"action_count":len(actions)},
    }


def update_index(new_articles):
    existing = []
    if INDEX_FILE.exists():
        try: existing = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception: pass
    ex_map = {a["slug"]:i for i,a in enumerate(existing)}
    for a in new_articles:
        entry = {k:v for k,v in a.items() if k not in ("ja","en","history","data")}
        if "ja" in a: entry["ja"] = {k:v for k,v in a["ja"].items() if k!="body"}
        if "en" in a: entry["en"] = {k:v for k,v in a["en"].items() if k!="body"}
        if "data" in a:
            entry["data"] = {k:v for k,v in a["data"].items()
                             if k not in ("actions","vcp_ranking") and not isinstance(v,list)}
            entry["data"]["action_count"] = a["data"].get("action_count",0)
        if a["slug"] in ex_map: existing[ex_map[a["slug"]]] = entry
        else: existing.insert(0, entry)
    existing.sort(key=lambda x: x.get("published_at",""), reverse=True)
    INDEX_FILE.write_text(json.dumps(existing[:300], ensure_ascii=False, indent=2))
    print(f"index.json: {len(existing)} entries")


def main():
    print(f"===== SENTINEL {'WEEKLY' if IS_SATURDAY else 'DAILY'} {TODAY} =====")
    new_articles = []
    scan        = run_scan()
    index_data  = get_index_data()
    sector_data = calc_sector_summary(scan["all_scored"])

    if IS_SATURDAY:
        weekly = generate_weekly_report(scan, index_data, sector_data)
        (WEEKLY_DIR / f"{TODAY}.json").write_text(json.dumps(weekly, ensure_ascii=False, indent=2))
        new_articles.append(weekly)
        print("✅ Weekly report saved")
    else:
        daily = generate_daily_report(scan, index_data, sector_data)
        (DAILY_DIR / f"{TODAY}.json").write_text(json.dumps(daily, ensure_ascii=False, indent=2))
        new_articles.append(daily)
        print("✅ Daily report saved")

        # ACTION上位5 + WAIT上位3 を累積更新
        for item in (scan["actions"][:5] + scan["waits"][:3]):
            try:
                doc = update_stock_page(item)
                new_articles.append(doc)
            except Exception as e:
                print(f"❌ {item['ticker']}: {e}")

    update_index(new_articles)
    print(f"===== Done: {len(new_articles)} articles =====")

if __name__ == "__main__":
    main()
