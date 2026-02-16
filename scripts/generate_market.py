#!/usr/bin/env python3
"""
generate_market.py — 毎日実行
S&P500 / NASDAQ100 / Russell2000 の指数分析データ生成
・指数ETFのOHLCV（120日）
・構成銘柄の寄与度ランキング
・「なぜ動いたか」AI解説
→ content/market.json に保存
"""
import sys, json, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent.parent / "shared"))
from engines import core_fmp

JST     = timezone(timedelta(hours=9))
NOW     = datetime.now(JST)
TODAY   = NOW.strftime("%Y-%m-%d")
CONTENT = Path(__file__).parent.parent / "frontend" / "public" / "content"
OUT     = CONTENT / "market.json"
CONTENT.mkdir(parents=True, exist_ok=True)

# ── 指数設定 ───────────────────────────────────────────────
INDICES = {
    "SP500": {
        "etf":   "SPY",
        "label": "S&P 500",
        "color": "#22C55E",
        "components": [
            "NVDA","MSFT","AAPL","AMZN","META","GOOGL","TSLA","AVGO","BRK-B","JPM",
            "LLY","UNH","V","XOM","COST","MA","JNJ","HD","WMT","BAC",
            "PG","ABBV","NFLX","CRM","CVX","MRK","KO","PEP","ORCL","ACN",
        ],
    },
    "NASDAQ": {
        "etf":   "QQQ",
        "label": "NASDAQ 100",
        "color": "#3B82F6",
        "components": [
            "NVDA","MSFT","AAPL","AMZN","META","GOOGL","GOOG","TSLA","AVGO","COST",
            "NFLX","TMUS","AMD","ADBE","INTU","CSCO","TXN","QCOM","AMAT","ISRG",
            "PANW","MU","LRCX","MRVL","KLAC","ON","REGN","SNPS","CDNS","CRWD",
        ],
    },
    "RUSSELL": {
        "etf":   "IWM",
        "label": "Russell 2000",
        "color": "#F59E0B",
        "components": [
            "SMCI","HIMS","CAVA","AXSM","DDOG","APP","GTLB","EXPI","CELH","BOOT",
            "ONON","DECK","FTCI","ENVX","GLBE","BRZE","IOT","MNDY","RXRX","ACLS",
            "TMDX","NARI","SWAV","INSP","AMBA","VNET","ARWR","XPOF","BYRN","CTKB",
        ],
    },
}


def call_ai(prompt: str, system: str = "", max_tokens: int = 1200) -> str:
    api_key  = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    model    = os.environ.get("OPENAI_MODEL",    "deepseek-chat")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client   = OpenAI(api_key=api_key, base_url=base_url)
        messages = ([{"role":"system","content":system}] if system else [])
        messages.append({"role":"user","content":prompt})
        res = client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=messages, temperature=0.65)
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI error: {e}"); return ""


def get_candles_json(ticker: str, days: int = 120) -> list:
    """チャート用OHLCVをJSONシリアライズ可能な形式で返す"""
    df = core_fmp.get_historical_data(ticker, days=days)
    if df is None: return []
    return [{
        "date":   d.strftime("%Y-%m-%d"),
        "open":   round(float(r["Open"]),  2),
        "high":   round(float(r["High"]),  2),
        "low":    round(float(r["Low"]),   2),
        "close":  round(float(r["Close"]), 2),
        "volume": int(r["Volume"]),
    } for d, r in df.iterrows()]


def analyze_component(ticker: str, days: int = 60) -> dict | None:
    """構成銘柄の個別データ取得"""
    df = core_fmp.get_historical_data(ticker, days=days + 10)
    if df is None or len(df) < 10:
        return None
    profile = core_fmp.get_company_profile(ticker) or {}
    close   = df["Close"]
    price   = round(float(close.iloc[-1]), 2)

    def chg(n): return round((float(close.iloc[-1])/float(close.iloc[-n])-1)*100, 2) if len(close)>n else None

    # 出来高変化（直近5日 vs 前20日平均）
    avg_vol_20 = float(df["Volume"].iloc[-25:-5].mean()) if len(df)>25 else None
    avg_vol_5  = float(df["Volume"].iloc[-5:].mean())   if len(df)>5  else None
    vol_ratio  = round(avg_vol_5/avg_vol_20, 2) if avg_vol_20 and avg_vol_5 and avg_vol_20>0 else None

    # ATR%（直近20日の平均値幅/価格）
    if len(df) >= 20:
        atr_pct = round(float((df["High"].iloc[-20:]-df["Low"].iloc[-20:]).mean())/price*100, 1)
    else:
        atr_pct = None

    return {
        "ticker":    ticker,
        "name":      profile.get("companyName", ticker)[:30],
        "sector":    profile.get("sector", ""),
        "price":     price,
        "ret_1d":    chg(2),
        "ret_5d":    chg(6),
        "ret_1m":    chg(22),
        "vol_ratio": vol_ratio,   # >1.5 = 出来高急増
        "atr_pct":   atr_pct,
    }


def build_index_analysis(key: str, cfg: dict) -> dict:
    """1指数の分析データを構築"""
    print(f"  [{key}] Fetching ETF data...")
    etf_candles = get_candles_json(cfg["etf"], days=120)

    # ETFのリターン計算
    if len(etf_candles) >= 22:
        c  = [d["close"] for d in etf_candles]
        ret_1d = round((c[-1]/c[-2]-1)*100, 2) if len(c)>=2  else None
        ret_5d = round((c[-1]/c[-6]-1)*100, 2) if len(c)>=6  else None
        ret_1m = round((c[-1]/c[-22]-1)*100,2) if len(c)>=22 else None
        ret_3m = round((c[-1]/c[-63]-1)*100,2) if len(c)>=63 else None
    else:
        ret_1d = ret_5d = ret_1m = ret_3m = None

    # 構成銘柄の分析
    print(f"  [{key}] Analyzing {len(cfg['components'])} components...")
    components = []
    for ticker in cfg["components"]:
        d = analyze_component(ticker)
        if d:
            components.append(d)
        time.sleep(0.3)  # レート制限

    # 寄与度ランキング（1m リターンの絶対値順）
    gainers = sorted([c for c in components if (c["ret_1m"] or 0) > 0],
                     key=lambda x: x["ret_1m"] or 0, reverse=True)[:8]
    losers  = sorted([c for c in components if (c["ret_1m"] or 0) < 0],
                     key=lambda x: x["ret_1m"] or 0)[:8]
    # 出来高急増銘柄（指数変動の火種候補）
    vol_surge = sorted([c for c in components if (c["vol_ratio"] or 0) > 1.3],
                       key=lambda x: x["vol_ratio"] or 0, reverse=True)[:6]
    # 高ボラ銘柄
    high_vol  = sorted([c for c in components if c["atr_pct"]],
                       key=lambda x: x["atr_pct"] or 0, reverse=True)[:6]

    # 「なぜ動いたか」AI解説
    top3_gain = ", ".join(f"{c['ticker']}({c['ret_1m']:+.1f}%)" for c in gainers[:3])
    top3_loss = ", ".join(f"{c['ticker']}({c['ret_1m']:+.1f}%)" for c in losers[:3])
    vol_names = ", ".join(f"{c['ticker']}(×{c['vol_ratio']})" for c in vol_surge[:3])

    sys_msg = "あなたは米国株市場のアナリストです。指数の動きを構成銘柄の動向から教育的に解説してください。断定的な相場予測や投資推奨はしないでください。"
    prompt_ja = f"""{cfg['label']}（{cfg['etf']}）の{TODAY}時点の分析レポートを作成してください。

【指数パフォーマンス】
直近1日: {ret_1d}% / 5日: {ret_5d}% / 1ヶ月: {ret_1m}% / 3ヶ月: {ret_3m}%

【上昇寄与銘柄 TOP3（1ヶ月）】
{top3_gain}

【下落寄与銘柄 TOP3（1ヶ月）】
{top3_loss}

【出来高急増銘柄（指数変動の背景候補）】
{vol_names if vol_names else "特になし"}

【執筆条件】
- 600〜800文字
- 見出し3つ（## ①指数動向の概要 ②主要寄与銘柄の動き ③出来高・ボラティリティから読む背景）
- 「なぜこの指数がこう動いたか」をデータから推察して解説
- 断定的な相場予測や売買推奨は禁止
- 末尾に1行免責事項
Markdown出力。"""

    prompt_en = f"""Write an analysis of {cfg['label']} ({cfg['etf']}) as of {TODAY}.
1d:{ret_1d}% 5d:{ret_5d}% 1m:{ret_1m}% 3m:{ret_3m}%
Top gainers: {top3_gain} | Top losers: {top3_loss} | Vol surge: {vol_names or 'none'}
300-400 words, 3 headings (##①Overview ②Key Contributors ③Volume/Volatility Context).
Explain WHY the index moved. No predictions or recommendations. 1-line disclaimer. Markdown."""

    print(f"  [{key}] Generating AI analysis...")
    ai_ja = call_ai(prompt_ja, sys_msg, 1200) or f"""## {cfg['label']}（{cfg['etf']}）動向\n1m: {ret_1m}%\n## 上昇寄与\n{top3_gain}\n## 下落・背景\n{top3_loss}\n⚠️ 投資助言ではありません。"""
    ai_en = call_ai(prompt_en, "", 700) or f"""## {cfg['label']} Overview\n1m: {ret_1m}%\n## Gainers\n{top3_gain}\n## Losers\n{top3_loss}\n⚠️ Not investment advice."""
    time.sleep(1.5)

    return {
        "key":      key,
        "etf":      cfg["etf"],
        "label":    cfg["label"],
        "color":    cfg["color"],
        "date":     TODAY,
        "performance": {
            "ret_1d": ret_1d, "ret_5d": ret_5d,
            "ret_1m": ret_1m, "ret_3m": ret_3m,
        },
        "candles":   etf_candles,
        "components": components,
        "gainers":   gainers,
        "losers":    losers,
        "vol_surge": vol_surge,
        "high_vol":  high_vol,
        "analysis": {
            "ja": ai_ja,
            "en": ai_en,
        },
    }


def main():
    print(f"===== MARKET ANALYSIS {TODAY} =====")
    result = {
        "generated_at": TODAY,
        "indices": {},
    }
    for key, cfg in INDICES.items():
        try:
            result["indices"][key] = build_index_analysis(key, cfg)
            print(f"  ✅ {key} done")
        except Exception as e:
            print(f"  ❌ {key}: {e}")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"✅ market.json saved ({len(result['indices'])} indices)")
    print("===== Done =====")


if __name__ == "__main__":
    main()
