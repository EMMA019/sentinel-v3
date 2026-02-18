#!/usr/bin/env python3
"""
scripts/ai_judge.py — AI判断エンジン
====================================
OpenAI APIにVCP/CANSLIM/ECRの全ルール + 最新ニュースを渡して
BUY / WAIT / SELL の判定を取得

環境変数:
  OPENAI_API_KEY    : OpenAI APIキー
  OPENAI_BASE_URL   : (optional) カスタムエンドポイント
  OPENAI_MODEL      : (optional) デフォルト gpt-4o

使い方:
  python scripts/ai_judge.py NVDA
  → nvda_judgment.json を出力
"""
import os, json, sys, requests
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent / "shared"))
from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer
from engines.canslim import CANSLIMAnalyzer
from engines.ecr_strategy import ECRStrategyEngine
from engines.sentinel_efficiency import SentinelEfficiencyAnalyzer

# ── 設定 ──────────────────────────────────────────────────
API_KEY  = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL    = os.environ.get("OPENAI_MODEL", "gpt-4o")

SYSTEM_PROMPT = """あなたはプロのトレーダーです。以下の投資手法ルールに従って銘柄を分析し、BUY/WAIT/SELLの判断を下してください。

【VCP（Volatility Contraction Pattern）ルール】
1. 価格レンジが3段階以上収縮している（20% → 10% → 5%）
2. 出来高が減少している（Dry-up）
3. MA20/50の上に価格がある
4. Pivot（直近高値）を上抜ける準備ができている
5. スコア: Tight(40) + Volume(30) + MA(30) + Pivot(5) = 105点満点

【CANSLIM（William O'Neil 手法）】
C: Current Earnings（直近EPS成長 +25%以上で満点）
A: Annual Sales Growth（年次売上成長 +20%以上）
N: New High（52週高値の3%以内）
S: Supply/Demand（出来高急増日が上昇を伴う）
L: Leader（RS Rating 90以上）
I: Institutional（機関投資家保有30-80%）

【ECR（Earnings/Capital/Risk）】
- Earnings Phase: ACCUMULATION（蓄積期）→ MARKUP（上昇期）
- Strategy: PBVH（Pivot Break with Volume & Hold）
- Rank 70以上でACCUMULATION なら最強

【SES（Sentinel Efficiency Score）】
- Fractal Efficiency: 価格効率性
- True Force: 真の力（価格×出来高）
- Volatility Squeeze: ボラティリティ圧縮
- 70以上で効率的な上昇トレンド

【ニュース分析】
- ポジティブ材料: 決算beat、新製品、M&A、格上げ
- ネガティブ材料: 決算miss、訴訟、格下げ、規制

【判定基準】
BUY: VCP>=80 かつ RS>=85 かつ ニュース好材料 かつ Pivot付近
WAIT: VCPパターン形成中 または ニュース材料待ち または Pivot到達前
SELL: VCP崩壊 または 重大ネガティブニュース または MA200割れ

必ず以下のJSON形式で回答してください:
{
  "judgment": "BUY" | "WAIT" | "SELL",
  "confidence": 0-100,
  "reasoning": "判断理由（200字以内）",
  "entry_plan": "エントリープラン（BUYの場合）",
  "risks": ["リスク1", "リスク2"],
  "catalysts": ["材料1", "材料2"]
}
"""


def get_news_summary(ticker: str) -> str:
    """FMP + Yahoo Financeからニュース取得"""
    news = core_fmp.get_news(ticker, limit=10)
    if not news:
        return "最近のニュースなし"
    
    lines = ["【最新ニュース（過去7日）】"]
    for n in news[:5]:
        lines.append(f"- {n['published_at'][:10]}: {n['title']}")
        if n.get('text'):
            lines.append(f"  {n['text'][:150]}...")
    
    return "\n".join(lines)


def scrape_seeking_alpha(ticker: str) -> str:
    """Seeking Alpha の最新記事タイトルを取得（簡易版）"""
    try:
        url = f"https://seekingalpha.com/symbol/{ticker}/news"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        
        # 簡易パース（BeautifulSoupなしでタイトルのみ抽出）
        if '<h3' in resp.text:
            import re
            titles = re.findall(r'<h3[^>]*>([^<]+)</h3>', resp.text)
            if titles:
                return "【Seeking Alpha 最新】\n" + "\n".join(f"- {t}" for t in titles[:3])
    except:
        pass
    return ""


def build_context(ticker: str) -> dict:
    """テクニカル + ファンダメンタル + ニュースのコンテキスト構築"""
    df = core_fmp.get_historical_data(ticker, days=400)
    if df is None or len(df) < 200:
        return None
    
    # テクニカル
    vcp     = VCPAnalyzer.calculate(df)
    rs_raw  = RSAnalyzer.get_raw_score(df)
    rs_pct  = int((rs_raw + 0.3) * 100) if rs_raw != -999.0 else 0
    canslim = CANSLIMAnalyzer.calculate(ticker, df)
    ecr     = ECRStrategyEngine.analyze_single(ticker, df)
    ses     = SentinelEfficiencyAnalyzer.calculate(df)
    
    # ファンダメンタル
    profile = core_fmp.get_company_profile(ticker) or {}
    fund    = core_fmp.get_fundamentals(ticker) or {}
    analyst = core_fmp.get_analyst_consensus(ticker) or {}
    
    # ニュース
    news_fmp = get_news_summary(ticker)
    news_sa  = scrape_seeking_alpha(ticker)
    
    price = float(df["Close"].iloc[-1])
    pivot = float(df["High"].iloc[-20:].max())
    
    return {
        "ticker": ticker,
        "name":   profile.get("companyName", ticker),
        "sector": profile.get("sector", "N/A"),
        "price":  round(price, 2),
        "pivot":  round(pivot, 2),
        "scores": {
            "vcp":      vcp["score"],
            "rs":       rs_pct,
            "canslim":  canslim["score"],
            "ecr_rank": ecr["sentinel_rank"],
            "ses":      ses["score"],
        },
        "vcp_signals":   vcp.get("signals", []),
        "canslim_grade": canslim["grade"],
        "ecr_phase":     ecr["phase"],
        "ecr_strategy":  ecr["strategy"],
        "fundamentals": {
            "pe":          fund.get("pe_forward"),
            "eps_growth":  canslim["metrics"].get("eps_growth"),
            "rev_growth":  canslim["metrics"].get("rev_growth"),
            "market_cap":  fund.get("market_cap_b"),
        },
        "analyst": {
            "consensus":   analyst.get("consensus"),
            "target":      analyst.get("target_mean"),
            "upside_pct":  analyst.get("target_pct"),
        },
        "news": {
            "fmp":     news_fmp,
            "seeking": news_sa,
        },
    }


def ask_ai(context: dict) -> dict:
    """OpenAI APIで判断を取得"""
    user_msg = f"""
銘柄: {context['ticker']} ({context['name']})
セクター: {context['sector']}
現在値: ${context['price']}
Pivot: ${context['pivot']} (距離: {(context['pivot'] - context['price']) / context['price'] * 100:.1f}%)

【テクニカルスコア】
VCP: {context['scores']['vcp']}/105
RS:  {context['scores']['rs']}/99
CANSLIM: {context['scores']['canslim']}/100 (Grade: {context['canslim_grade']})
ECR: {context['scores']['ecr_rank']}/100 (Phase: {context['ecr_phase']}, Strategy: {context['ecr_strategy']})
SES: {context['scores']['ses']}/100

VCPシグナル: {', '.join(context['vcp_signals'])}

【ファンダメンタル】
予想PER: {context['fundamentals']['pe']}
EPS成長率: {context['fundamentals']['eps_growth']}%
売上成長率: {context['fundamentals']['rev_growth']}%
時価総額: ${context['fundamentals']['market_cap']}B

【アナリスト評価】
コンセンサス: {context['analyst']['consensus']}
目標株価: ${context['analyst']['target']} (上昇余地: {context['analyst']['upside_pct']}%)

【ニュース】
{context['news']['fmp']}

{context['news']['seeking']}

上記の情報を元に、BUY/WAIT/SELLの判断をJSON形式で回答してください。
"""

    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    
    if resp.status_code != 200:
        raise Exception(f"OpenAI API error: {resp.status_code} {resp.text}")
    
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def main():
    if len(sys.argv) < 2:
        print("Usage: python ai_judge.py TICKER")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    print(f"=== AI Judge: {ticker} ===")
    
    # コンテキスト構築
    print("📊 テクニカル・ファンダメンタル分析中...")
    context = build_context(ticker)
    if not context:
        print(f"❌ {ticker}: データ不足")
        sys.exit(1)
    
    # AI判断
    print("🤖 AI判断中...")
    judgment = ask_ai(context)
    
    # 結果
    print(f"\n{'='*60}")
    print(f"銘柄: {context['ticker']} ({context['name']})")
    print(f"現在値: ${context['price']} / Pivot: ${context['pivot']}")
    print(f"VCP={context['scores']['vcp']} RS={context['scores']['rs']} CANSLIM={context['scores']['canslim']}")
    print(f"{'='*60}")
    print(f"判定: {judgment['judgment']} (信頼度: {judgment['confidence']}%)")
    print(f"理由: {judgment['reasoning']}")
    if judgment.get('entry_plan'):
        print(f"エントリープラン: {judgment['entry_plan']}")
    if judgment.get('risks'):
        print(f"リスク: {', '.join(judgment['risks'])}")
    if judgment.get('catalysts'):
        print(f"材料: {', '.join(judgment['catalysts'])}")
    
    # JSON保存
    out = {
        "generated_at": datetime.now().isoformat(),
        "ticker":       ticker,
        "context":      context,
        "judgment":     judgment,
    }
    
    out_file = Path(__file__).parent.parent / "frontend" / "public" / "content" / f"{ticker.lower()}_judgment.json"
    out_file.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n✅ Saved: {out_file}")


if __name__ == "__main__":
    main()
