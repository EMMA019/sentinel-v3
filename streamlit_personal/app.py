#!/usr/bin/env python3
"""
SENTINEL PRO — 個人用フル機能Streamlitアプリ
==========================================
【公開サイトとの違い】
- 株価・ローソク足チャート（mplfinance）を完全表示
- エントリー/ストップ/ターゲット価格をドル直接表示
- アナリスト目標株価（$表示）
- 全銘柄スキャン結果をリアルタイム表示
- ウォッチリスト管理

【使い方】
  pip install -r requirements.txt
  FMP_API_KEY=xxx streamlit run app.py
"""
import sys, os, io
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "shared"))

import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta

from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.config import CONFIG, TICKERS

# ── ページ設定 ────────────────────────────────────────────
st.set_page_config(
    page_title="SENTINEL PRO — Personal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

JST = timezone(timedelta(hours=9))

# ── セッション初期化 ──────────────────────────────────────
if "watchlist"  not in st.session_state: st.session_state.watchlist  = []
if "scan_cache" not in st.session_state: st.session_state.scan_cache = None
if "scan_date"  not in st.session_state: st.session_state.scan_date  = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ヘルパー関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_full(ticker: str):
    df      = core_fmp.get_historical_data(ticker, days=700)
    quote   = core_fmp.get_quote(ticker)
    profile = core_fmp.get_company_profile(ticker) or {}
    analyst = core_fmp.get_analyst_consensus(ticker) or {}
    fund    = core_fmp.get_fundamentals(ticker) or {}
    own     = core_fmp.get_ownership(ticker) or {}
    news    = core_fmp.get_news(ticker, limit=6)
    return df, quote, profile, analyst, fund, own, news


def calc_all(df):
    if df is None or len(df) < 200:
        return None, None
    vcp = VCPAnalyzer.calculate(df)
    pf  = StrategyValidator.run(df)
    return vcp, pf


def get_trade_params(df, vcp):
    price  = float(df["Close"].iloc[-1])
    pivot  = float(df["High"].iloc[-20:].max())
    entry  = round(pivot * 1.002, 2)
    stop   = round(entry - vcp["atr"] * CONFIG["STOP_LOSS_ATR"], 2)
    target = round(entry + (entry - stop) * CONFIG["TARGET_R_MULTIPLE"], 2)
    rr     = round((target - entry) / (entry - stop), 2) if entry != stop else 0
    dist   = (price - pivot) / pivot
    status = "ACTION" if -0.05 <= dist <= 0.03 else ("WAIT" if dist < -0.05 else "EXTENDED")
    return price, entry, stop, target, rr, dist, status


def plot_candle(df, ticker, entry=None, stop=None, target=None, days=90):
    try:
        import mplfinance as mpf
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as mpatches

        df_plot = df.iloc[-days:].copy()
        df_plot["MA20"]  = df_plot["Close"].rolling(20).mean()
        df_plot["MA50"]  = df_plot["Close"].rolling(50).mean()
        df_plot["MA200"] = df_plot["Close"].rolling(200).mean()

        mc = mpf.make_marketcolors(
            up="#22C55E", down="#EF4444",
            edge={"up":"#22C55E","down":"#EF4444"},
            wick={"up":"#22C55E","down":"#EF4444"},
            volume={"up":"#22C55E30","down":"#EF444430"},
        )
        s = mpf.make_mpf_style(
            marketcolors=mc, facecolor="#0E1318", edgecolor="#1C2530",
            figcolor="#080C10", gridcolor="#1C2530", gridstyle="--",
            y_on_right=True,
            rc={"font.family":"monospace","font.size":8,
                "axes.labelcolor":"#7A90A8","xtick.color":"#3D4F63","ytick.color":"#3D4F63"},
        )
        adds = [
            mpf.make_addplot(df_plot["MA20"],  color="#3B82F6", width=1.0),
            mpf.make_addplot(df_plot["MA50"],  color="#F59E0B", width=1.0),
            mpf.make_addplot(df_plot["MA200"], color="#EF4444", width=0.8, linestyle="--"),
        ]
        fig, axes = mpf.plot(
            df_plot, type="candle", style=s, volume=True,
            addplot=adds, figratio=(14, 7), tight_layout=True,
            returnfig=True, datetime_format="%m/%d",
        )
        ax = axes[0]
        price_now = float(df_plot["Close"].iloc[-1])
        chg_90    = (price_now / float(df_plot["Close"].iloc[0]) - 1) * 100
        ax.set_title(f"{ticker}  ${price_now:.2f}  {chg_90:+.1f}% (90d)",
                     color="#EBF4FF", fontsize=10, fontweight="bold", loc="left", pad=8)

        xlim = ax.get_xlim()
        for val, color, label in [
            (entry,  "#22C55E", f"Entry ${entry}"),
            (stop,   "#EF4444", f"Stop  ${stop}"),
            (target, "#F59E0B", f"Target ${target}"),
        ]:
            if val:
                ax.axhline(y=val, color=color, linewidth=1.2, linestyle="--", alpha=0.9, xmin=0.75)
                ax.text(xlim[1] * 0.99, val, f" {label}", color=color, fontsize=7, va="center", ha="right")

        legend_handles = [
            mpatches.Patch(color="#3B82F6", label="MA20"),
            mpatches.Patch(color="#F59E0B", label="MA50"),
            mpatches.Patch(color="#EF4444", label="MA200"),
        ]
        ax.legend(handles=legend_handles, loc="upper left", framealpha=0.0,
                  fontsize=7, labelcolor=["#3B82F6","#F59E0B","#EF4444"])

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                    facecolor="#080C10", edgecolor="none")
        buf.seek(0)
        import matplotlib.pyplot as plt
        plt.close(fig)
        return buf
    except ImportError:
        return None


def run_full_scan():
    raw_list = []
    pb = st.progress(0, text="スキャン開始...")
    for i, t in enumerate(TICKERS):
        pb.progress(i / len(TICKERS), text=f"{t} ({i+1}/{len(TICKERS)})")
        df = core_fmp.get_historical_data(t, days=700)
        if df is None or len(df) < 200: continue
        rs_raw = RSAnalyzer.get_raw_score(df)
        if rs_raw != -999.0:
            raw_list.append({"ticker": t, "df": df, "raw_rs": rs_raw})
    pb.empty()

    scored = RSAnalyzer.assign_percentiles(raw_list)
    results = []
    for item in scored:
        vcp  = VCPAnalyzer.calculate(item["df"])
        pf   = StrategyValidator.run(item["df"])
        price, entry, stop, target, rr, dist, status = get_trade_params(item["df"], vcp)
        profile = core_fmp.get_company_profile(item["ticker"]) or {}
        results.append({
            "ticker":  item["ticker"],
            "name":    profile.get("companyName", item["ticker"])[:22],
            "status":  status,
            "rs":      item["rs_rating"],
            "vcp":     vcp["score"],
            "pf":      round(pf, 2),
            "price":   round(price, 2),
            "entry":   entry,
            "stop":    stop,
            "target":  target,
            "rr":      rr,
            "atr":     round(vcp["atr"], 2),
            "sector":  profile.get("sector", "N/A"),
            "df":      item["df"],
            "vcp_detail": vcp,
        })
    results.sort(key=lambda x: (x["status"] == "ACTION", x["vcp"] + x["rs"]), reverse=True)
    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# サイドバー
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.sidebar:
    st.markdown("## 🛡️ SENTINEL PRO\n**個人用フル機能版**")
    api_ok = bool(os.environ.get("FMP_API_KEY", ""))
    st.caption(f"FMP API: {'✅ 設定済み' if api_ok else '❌ FMP_API_KEY を設定してください'}")
    st.divider()

    mode = st.radio(
        "モード",
        ["📊 個別銘柄スキャン", "🔭 全銘柄スキャン", "⭐ ウォッチリスト"],
        label_visibility="collapsed",
    )
    st.divider()

    if st.session_state.watchlist:
        st.markdown("**⭐ ウォッチリスト**")
        for t in list(st.session_state.watchlist):
            c1, c2 = st.columns([3, 1])
            c1.caption(t)
            if c2.button("×", key=f"rm_{t}"):
                st.session_state.watchlist.remove(t)
                st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# モード①: 個別銘柄スキャン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if mode == "📊 個別銘柄スキャン":
    st.title("📊 個別銘柄スキャン")

    c_in, c_btn = st.columns([3, 1])
    ticker  = c_in.text_input("ティッカーシンボル", value="NVDA", label_visibility="collapsed").upper().strip()
    run_btn = c_btn.button("🚀 スキャン実行", type="primary", use_container_width=True)

    # ウォッチリスト追加
    if ticker and ticker not in st.session_state.watchlist:
        if st.button(f"⭐ {ticker} をウォッチリストに追加"):
            st.session_state.watchlist.append(ticker)
            st.success(f"{ticker} を追加しました")

    if run_btn and ticker:
        with st.spinner(f"{ticker} のデータを取得中..."):
            df, quote, profile, analyst, fund, own, news = fetch_stock_full(ticker)

        if df is None:
            st.error(f"{ticker}: データ取得失敗"); st.stop()

        vcp, pf = calc_all(df)
        if vcp is None:
            st.error(f"{ticker}: データ不足（200日以上必要）"); st.stop()

        price_live = float(quote.get("price", 0)) if quote and quote.get("price") else float(df["Close"].iloc[-1])
        price, entry, stop, target, rr, dist, status = get_trade_params(df, vcp)

        name   = profile.get("companyName", ticker)
        sector = profile.get("sector", "N/A")

        st.markdown(f"### {name}　({ticker})")
        st.caption(f"{sector} / {profile.get('industry','N/A')}")

        # ── メインスコア ──────────────────────────────────
        c1,c2,c3,c4,c5 = st.columns(5)
        chg_pct = float(quote.get("changesPercentage", 0)) if quote else 0.0
        c1.metric("💰 現在値",    f"${price_live:,.2f}", delta=f"{chg_pct:+.2f}%")
        c2.metric("🎯 VCPスコア", f"{vcp['score']}/105")
        c3.metric("📈 RS Rating",  f"{vcp.get('rs_approx', '-')}")
        c4.metric("✏️ PF",         f"×{pf:.2f}")
        status_icon = "🟢" if status=="ACTION" else "🟡" if status=="WAIT" else "🔴"
        c5.metric("📍 ステータス", f"{status_icon} {status}")

        st.divider()

        # ── ローソク足チャート ─────────────────────────────
        chart_buf = plot_candle(df, ticker, entry=entry, stop=stop, target=target, days=90)
        if chart_buf:
            st.image(chart_buf, use_container_width=True, caption=f"{ticker} — 90日チャート (MA20/50/200 + Entry/Stop/Target)")
        else:
            st.info("チャートを表示するには `pip install mplfinance` を実行してください")

        st.divider()

        # ── トレードパラメータ ─────────────────────────────
        st.markdown("#### 📐 トレードパラメータ")
        t1,t2,t3,t4,t5 = st.columns(5)
        t1.metric("エントリー目安",   f"${entry:,.2f}")
        t2.metric("ストップロス",     f"${stop:,.2f}",   delta=f"-{(entry-stop)/entry*100:.1f}%", delta_color="inverse")
        t3.metric("ターゲット",       f"${target:,.2f}", delta=f"+{(target-entry)/entry*100:.1f}%")
        t4.metric("RR比",             f"1:{rr}")
        t5.metric("ATR",              f"${vcp['atr']:.2f}")

        st.divider()

        # ── VCPブレイクダウン ──────────────────────────────
        bd = vcp.get("breakdown", {})
        st.markdown("#### 🔬 VCPスコア内訳")
        v1,v2,v3,v4 = st.columns(4)
        v1.metric("⚡ TIGHTNESS", f"{bd.get('tight',0)}点 / 40")
        v2.metric("📊 VOLUME",    f"{bd.get('vol',0)}点 / 30")
        v3.metric("📉 MA",        f"{bd.get('ma',0)}点 / 30")
        v4.metric("🎯 PIVOT",     f"{bd.get('pivot',0)}点 / 5")

        if vcp.get("signals"):
            st.markdown("**シグナル:** " + "  ".join(f"`{s}`" for s in vcp["signals"]))

        st.divider()

        # ── ファンダメンタル ───────────────────────────────
        if fund:
            st.markdown("#### 📈 ファンダメンタル")
            f1,f2,f3,f4,f5,f6 = st.columns(6)
            f1.metric("予想PER",   f"{fund.get('pe_forward','N/A')}x")
            rev_g = fund.get("revenue_growth_yoy")
            f2.metric("売上成長率", f"{rev_g:+.1f}%" if rev_g is not None else "N/A")
            eps_g = fund.get("earnings_growth_yoy")
            f3.metric("利益成長率", f"{eps_g:+.1f}%" if eps_g is not None else "N/A")
            f4.metric("ROE",       f"{fund.get('roe','N/A')}%")
            f5.metric("粗利率",    f"{fund.get('gross_margin','N/A')}%")
            f6.metric("時価総額",  f"${fund.get('market_cap_b','N/A')}B")

        # ── アナリスト評価 ─────────────────────────────────
        if analyst:
            st.markdown("#### 👥 アナリスト評価")
            a1,a2,a3,a4,a5 = st.columns(5)
            a1.metric("コンセンサス",     analyst.get("consensus","N/A"))
            a2.metric("アナリスト数",     f"{analyst.get('analyst_count',0)}名")
            a3.metric("目標株価（平均）", f"${analyst.get('target_mean','N/A')}")
            a4.metric("目標株価（高値）", f"${analyst.get('target_high','N/A')}")
            a5.metric("目標株価（安値）", f"${analyst.get('target_low','N/A')}")
            if analyst.get("target_pct") is not None:
                pct = analyst["target_pct"]
                st.metric("現在値からの目標乖離", f"{pct:+.1f}%",
                          delta_color="normal" if pct >= 0 else "inverse")
            buy  = analyst.get("buy",  0)
            hold = analyst.get("hold", 0)
            sell = analyst.get("sell", 0)
            total = buy + hold + sell
            if total:
                st.markdown(f"Buy **{buy}** / Hold **{hold}** / Sell **{sell}**")
                bar_html = f"""
                <div style='display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px'>
                  <div style='width:{buy/total*100:.0f}%;background:#22C55E'></div>
                  <div style='width:{hold/total*100:.0f}%;background:#F59E0B'></div>
                  <div style='width:{sell/total*100:.0f}%;background:#EF4444'></div>
                </div>"""
                st.markdown(bar_html, unsafe_allow_html=True)

        # ── 投資家動向 ─────────────────────────────────────
        if any(v is not None for v in own.values()):
            st.markdown("#### 🏦 投資家動向")
            o1,o2,o3,o4 = st.columns(4)
            o1.metric("機関投資家保有率",  f"{own.get('institutional_pct','N/A')}%")
            o2.metric("インサイダー保有率", f"{own.get('insider_pct','N/A')}%")
            sf = own.get("short_float_pct")
            o3.metric("空売り比率",        f"{sf}%" if sf is not None else "N/A")
            o4.metric("空売り日数",        f"{own.get('short_days_to_cover','N/A')}日")

        # ── 直近ニュース ───────────────────────────────────
        if news:
            st.markdown("#### 📰 直近ニュース")
            for n in news[:5]:
                st.markdown(f"- [{n['title']}]({n['url']})  \n  *{n['source']} · {n['published_at'][:10]}*")

        # ── 外部リンク ─────────────────────────────────────
        st.divider()
        st.markdown("#### 🔗 正確な株価・詳細チャートはこちら")
        lc1,lc2,lc3,lc4 = st.columns(4)
        lc1.link_button("📊 Yahoo Finance",  f"https://finance.yahoo.com/quote/{ticker}",           use_container_width=True)
        lc2.link_button("📈 TradingView",    f"https://www.tradingview.com/chart/?symbol={ticker}", use_container_width=True)
        lc3.link_button("🏢 MarketWatch",   f"https://www.marketwatch.com/investing/stock/{ticker.lower()}", use_container_width=True)
        lc4.link_button("📰 Seeking Alpha", f"https://seekingalpha.com/symbol/{ticker}",            use_container_width=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# モード②: 全銘柄スキャン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
elif mode == "🔭 全銘柄スキャン":
    st.title("🔭 全銘柄スキャン")
    st.info(f"対象: {len(TICKERS)}銘柄 / 完了まで約10〜20分（APIレート制限あり）")

    today = datetime.now(JST).strftime("%Y-%m-%d")
    if st.session_state.scan_date == today and st.session_state.scan_cache:
        results = st.session_state.scan_cache
        st.success(f"✅ 本日のスキャン済み結果 ({len(results)}件) — 再スキャンは下のボタンから")
    else:
        results = None

    if st.button("🚀 全銘柄スキャン開始", type="primary"):
        results = run_full_scan()
        st.session_state.scan_cache = results
        st.session_state.scan_date  = today
        st.success(f"✅ スキャン完了 ({len(results)}銘柄)")

    if not results:
        st.stop()

    # フィルター
    cf1,cf2,cf3 = st.columns(3)
    status_filter = cf1.multiselect("ステータス", ["ACTION","WAIT","EXTENDED"], default=["ACTION","WAIT"])
    min_vcp = cf2.slider("最小VCPスコア", 0, 105, 60)
    min_rs  = cf3.slider("最小RS",       0,  99, 70)

    filtered = [r for r in results
                if r["status"] in status_filter
                and r["vcp"]  >= min_vcp
                and r["rs"]   >= min_rs]
    st.caption(f"表示: {len(filtered)}件 / 全{len(results)}件")

    if filtered:
        df_disp = pd.DataFrame([{
            "Ticker":    r["ticker"],
            "社名":      r["name"],
            "Status":    r["status"],
            "VCP":       r["vcp"],
            "RS":        r["rs"],
            "PF":        r["pf"],
            "価格":      f"${r['price']:,.2f}",
            "エントリー":f"${r['entry']:,.2f}",
            "ストップ":  f"${r['stop']:,.2f}",
            "ターゲット":f"${r['target']:,.2f}",
            "RR":        f"1:{r['rr']}",
            "ATR":       f"${r['atr']:.2f}",
            "セクター":  r["sector"],
        } for r in filtered])

        st.dataframe(
            df_disp, hide_index=True, use_container_width=True,
            column_config={
                "VCP": st.column_config.ProgressColumn("VCP", min_value=0, max_value=105, format="%d"),
                "RS":  st.column_config.ProgressColumn("RS",  min_value=0, max_value=99,  format="%d"),
            }
        )
        csv = df_disp.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSVダウンロード", csv,
                           f"sentinel_scan_{today}.csv", "text/csv")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# モード③: ウォッチリスト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
elif mode == "⭐ ウォッチリスト":
    st.title("⭐ ウォッチリスト")

    # 手動追加
    add_col, add_btn = st.columns([3, 1])
    new_ticker = add_col.text_input("ティッカーを追加", label_visibility="collapsed",
                                     placeholder="例: AAPL").upper().strip()
    if add_btn.button("追加") and new_ticker and new_ticker not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_ticker)
        st.rerun()

    if not st.session_state.watchlist:
        st.info("ウォッチリストは空です。上のフォームまたは個別スキャンから追加できます。")
        st.stop()

    if st.button("🔄 全銘柄を更新", type="secondary"):
        st.cache_data.clear()
        st.rerun()

    for ticker in list(st.session_state.watchlist):
        with st.expander(f"📊 {ticker}", expanded=False):
            with st.spinner(f"{ticker} 読み込み中..."):
                df, quote, profile, analyst, fund, own, news = fetch_stock_full(ticker)

            if df is None:
                st.error("データ取得失敗"); continue

            vcp, pf = calc_all(df)
            if vcp is None:
                st.error("データ不足"); continue

            price_live = float(quote.get("price", df["Close"].iloc[-1])) if quote else float(df["Close"].iloc[-1])
            _, entry, stop, target, rr, _, status = get_trade_params(df, vcp)

            m1,m2,m3,m4,m5,m6,m7 = st.columns(7)
            m1.metric("価格",    f"${price_live:,.2f}")
            m2.metric("VCP",     f"{vcp['score']}/105")
            m3.metric("RS",      f"{vcp.get('rs_approx','-')}")
            m4.metric("Status",  status)
            m5.metric("Entry",   f"${entry:,.2f}")
            m6.metric("Stop",    f"${stop:,.2f}")
            m7.metric("Target",  f"${target:,.2f}")

            chart_buf = plot_candle(df, ticker, entry=entry, stop=stop, target=target, days=60)
            if chart_buf:
                st.image(chart_buf, use_container_width=True)

            lc1,lc2 = st.columns(2)
            lc1.link_button("📊 Yahoo Finance",
                            f"https://finance.yahoo.com/quote/{ticker}",
                            use_container_width=True)
            lc2.link_button("📈 TradingView",
                            f"https://www.tradingview.com/chart/?symbol={ticker}",
                            use_container_width=True)
