import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell, CartesianGrid,
  BarChart
} from 'recharts';
import { useSEO } from '../hooks/useSEO';
import { Activity, TrendingUp, TrendingDown, Zap,
         ExternalLink, ChevronRight, Loader } from 'lucide-react';

// ── ローソク足チャート（ComposedChart + Bar trick） ──────
function CandleChart({ candles, color, label }) {
  if (!candles?.length) return null;

  // 直近90日
  const data = candles.slice(-90).map(c => {
    const up    = c.close >= c.open;
    const body  = Math.abs(c.close - c.open);
    const bodyLo = Math.min(c.open, c.close);
    return {
      date:    c.date.slice(5),       // MM-DD
      low:     c.low,
      high:    c.high,
      open:    c.open,
      close:   c.close,
      up,
      // recharts用: [ひげ下, ボディ下, ボディ高さ, ひげ上]
      wickRange:  [c.low,  c.high],
      bodyRange:  [bodyLo, bodyLo + body],
      bodyLo,
      bodyHi:  bodyLo + body,
      wickLo:  c.low,
      wickHi:  c.high,
      volume:  c.volume,
    };
  });

  // 価格の範囲
  const allLow  = Math.min(...data.map(d => d.wickLo));
  const allHigh = Math.max(...data.map(d => d.wickHi));
  const pad     = (allHigh - allLow) * 0.05;
  const maxVol  = Math.max(...data.map(d => d.volume));

  const DarkTooltip = ({ active, payload, label: lb }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    const chg = ((d.close - d.open) / d.open * 100).toFixed(2);
    return (
      <div className="bg-ink border border-border rounded-lg p-2 font-mono text-xs space-y-0.5">
        <div className="text-muted mb-1">{lb}</div>
        <div className="text-bright">O: ${d.open} H: ${d.high}</div>
        <div className="text-bright">L: ${d.low}  C: ${d.close}</div>
        <div className={d.up ? 'text-green' : 'text-red'}>{d.up?'+':''}{chg}%</div>
        <div className="text-muted">Vol: {(d.volume/1e6).toFixed(1)}M</div>
      </div>
    );
  };

  return (
    <div className="bg-ink border border-border rounded-xl p-4">
      <div className="font-mono text-xs text-muted mb-3" style={{color}}>
        {label} — 直近90日チャート
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{top:4,right:4,bottom:0,left:-8}}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1C2530" vertical={false}/>
          <XAxis dataKey="date" tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false}
                 axisLine={false} interval={Math.floor(data.length/6)}/>
          <YAxis yAxisId="price" domain={[allLow-pad, allHigh+pad]}
                 tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false} axisLine={false}
                 tickFormatter={v=>`$${v.toFixed(0)}`} width={42}/>
          <YAxis yAxisId="vol"   orientation="right" domain={[0, maxVol*4]}
                 tick={false} axisLine={false} tickLine={false} width={0}/>
          <Tooltip content={<DarkTooltip/>}/>

          {/* 出来高バー */}
          <Bar yAxisId="vol" dataKey="volume" radius={0} maxBarSize={6}>
            {data.map((d,i) => (
              <Cell key={i} fill={d.up ? '#22C55E30' : '#EF444430'}/>
            ))}
          </Bar>

          {/* ひげ（高値・安値レンジ） */}
          <Bar yAxisId="price" dataKey="wickHi" stackId="wick"
               fill="transparent" stroke="transparent" maxBarSize={2}/>
          {data.map((d,i) => null)}

          {/* ローソクボディ */}
          <Bar yAxisId="price" dataKey="bodyHi" stackId="body"
               fill="transparent" stroke="transparent" maxBarSize={5}/>
        </ComposedChart>
      </ResponsiveContainer>

      {/* シンプルな代替: 折れ線チャート（フォールバック） */}
      <div className="mt-1 -mt-[228px] pointer-events-none">
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={data} margin={{top:4,right:4,bottom:0,left:-8}}>
            <Line yAxisId="p" type="monotone" dataKey="close"
                  stroke={color} strokeWidth={1.5} dot={false}/>
            <YAxis yAxisId="p" hide domain={[allLow-pad, allHigh+pad]}/>
            <XAxis dataKey="date" hide/>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── シンプルな終値折れ線チャート ───────────────────────────
function PriceLineChart({ candles, color, label }) {
  if (!candles?.length) return null;
  const data = candles.slice(-90).map(c => ({
    date:  c.date.slice(5),
    close: c.close,
    vol:   c.volume,
  }));
  const allClose = data.map(d=>d.close);
  const minP = Math.min(...allClose);
  const maxP = Math.max(...allClose);
  const pad  = (maxP - minP) * 0.08;
  const maxVol = Math.max(...data.map(d=>d.vol));

  const baseClose = data[0]?.close ?? 1;

  return (
    <div className="bg-ink border border-border rounded-xl p-4">
      <div className="font-mono text-xs mb-3 flex items-center justify-between" style={{color}}>
        <span>{label} — 直近90日</span>
        <span className="text-muted">
          ${data[data.length-1]?.close}
          {(() => {
            const chg = (data[data.length-1]?.close/baseClose-1)*100;
            return <span className={chg>=0?' text-green':' text-red'}> {chg>=0?'+':''}{chg.toFixed(1)}%</span>;
          })()}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={data} margin={{top:4,right:0,bottom:0,left:-12}}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1C2530" vertical={false}/>
          <XAxis dataKey="date" tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false}
                 axisLine={false} interval={Math.floor(data.length/5)}/>
          <YAxis yAxisId="p" domain={[minP-pad, maxP+pad]}
                 tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false} axisLine={false}
                 tickFormatter={v=>`$${v.toFixed(0)}`} width={40}/>
          <YAxis yAxisId="v" orientation="right" domain={[0,maxVol*5]}
                 hide/>
          <Tooltip
            contentStyle={{background:'#0E1318',border:'1px solid #1C2530',borderRadius:'8px',fontSize:'10px'}}
            labelStyle={{color:'#7A90A8'}} itemStyle={{color}}
            formatter={(v,n) => n==='vol' ? `${(v/1e6).toFixed(1)}M` : `$${v}`}/>
          <Bar yAxisId="v" dataKey="vol" fill={`${color}20`} radius={0} maxBarSize={4}/>
          <Line yAxisId="p" type="monotone" dataKey="close" name="Close"
                stroke={color} strokeWidth={2} dot={false}/>
          <ReferenceLine yAxisId="p" y={baseClose} stroke="#3D4F63"
                         strokeDasharray="4 4" strokeWidth={0.5}/>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── 構成銘柄ランキングテーブル ────────────────────────────
function ComponentTable({ items, title, type, lang }) {
  if (!items?.length) return null;
  const isGain = type === 'gainer';
  return (
    <div>
      <div className={`font-mono text-xs mb-2 flex items-center gap-1.5 ${isGain?'text-green':'text-red'}`}>
        {isGain ? <TrendingUp size={11}/> : <TrendingDown size={11}/>}
        {title}
      </div>
      <div className="space-y-1">
        {items.slice(0,6).map((c,i) => (
          <div key={i} className="flex items-center gap-2 group hover:bg-panel/40 rounded-lg px-1.5 py-1 transition">
            <Link to={`/blog/stock-${c.ticker.toLowerCase()}`}
              className="font-mono text-xs text-bright font-700 w-10 group-hover:text-green transition">
              {c.ticker}
            </Link>
            <a href={`https://finance.yahoo.com/quote/${c.ticker}`}
               target="_blank" rel="noopener noreferrer"
               className="text-amber/50 hover:text-amber transition" title="Yahoo Finance">
              <ExternalLink size={8}/>
            </a>
            <span className="font-body text-xs text-muted flex-1 truncate">{c.name?.slice(0,14)}</span>
            <span className={`font-mono text-xs font-700 ${(c.ret_1m||0)>=0?'text-green':'text-red'}`}>
              {(c.ret_1m||0)>=0?'+':''}{c.ret_1m}%
            </span>
            {c.vol_ratio && c.vol_ratio > 1.5 && (
              <span className="font-mono text-xs text-amber flex items-center gap-0.5">
                <Zap size={8}/>{c.vol_ratio}x
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 出来高急増テーブル ────────────────────────────────────
function VolSurgeTable({ items, lang }) {
  if (!items?.length) return null;
  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className="font-mono text-xs text-amber mb-3 flex items-center gap-1.5">
        <Zap size={11}/> {lang==='ja'?'出来高急増銘柄（指数変動の背景候補）':'Volume Surge (Index movement drivers)'}
      </div>
      <div className="space-y-1.5">
        {items.map((c,i) => (
          <div key={i} className="flex items-center gap-2 group hover:bg-ink/50 rounded-lg px-1 py-1 transition">
            <Link to={`/blog/stock-${c.ticker.toLowerCase()}`}
              className="font-mono text-xs text-bright font-700 w-10 group-hover:text-green transition">{c.ticker}</Link>
            <a href={`https://finance.yahoo.com/quote/${c.ticker}`}
               target="_blank" rel="noopener noreferrer"
               className="text-amber/50 hover:text-amber transition" title="Yahoo Finance">
              <ExternalLink size={8}/>
            </a>
            <span className="font-body text-xs text-muted flex-1 truncate">{c.sector?.slice(0,12)}</span>
            <div className="flex items-center gap-1">
              <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                <div className="h-full bg-amber rounded-full"
                     style={{width:`${Math.min(100,(c.vol_ratio||0)/3*100)}%`}}/>
              </div>
              <span className="font-mono text-xs text-amber w-8">×{c.vol_ratio}</span>
            </div>
            <span className={`font-mono text-xs font-700 w-12 text-right ${(c.ret_1m||0)>=0?'text-green':'text-red'}`}>
              {(c.ret_1m||0)>=0?'+':''}{c.ret_1m}%
            </span>
          </div>
        ))}
      </div>
      <p className="font-mono text-xs text-muted/60 mt-3">
        ※ {lang==='ja'?'直近5日出来高が過去20日平均に対して何倍かを示す':'5d avg volume vs 20d avg volume ratio'}
      </p>
    </div>
  );
}

// ── メインページ ─────────────────────────────────────────
export default function Market() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [active,  setActive]  = useState('SP500');
  const [lang,    setLang]    = useState('ja');

  useSEO({
    title: lang==='ja'
      ? '指数インパクト分析 S&P500・NASDAQ・Russell2000 — SENTINEL PRO'
      : 'Index Impact Analysis S&P500 NASDAQ Russell2000 — SENTINEL PRO',
    description: lang==='ja'
      ? 'S&P500・NASDAQ100・Russell2000の構成銘柄が指数に与えた価格インパクトを毎日分析。出来高急増銘柄・上昇/下落寄与ランキングとAIによる「なぜ動いたか」解説を公開。'
      : 'Daily analysis of component stocks impacting S&P500, NASDAQ100, Russell2000. Volume surge, gainer/loser rankings, and AI explanation of why the index moved.',
    lang,
  });

  useEffect(() => {
    fetch('/content/market.json')
      .then(r => r.ok ? r.json() : null)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const idx = data?.indices?.[active];
  const perf = idx?.performance ?? {};

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-4xl mx-auto">

        {/* AdSense */}
        <div className="mb-6 rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block',width:'100%'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
               data-ad-format="horizontal" data-full-width-responsive="true"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>

        {/* ヘッダー */}
        <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Activity size={14} className="text-green"/>
              <span className="font-mono text-xs text-green">MARKET / INDEX IMPACT</span>
            </div>
            <h1 className="font-display font-700 text-bright text-2xl md:text-3xl">
              {lang==='ja' ? '指数インパクト分析' : 'Index Impact Analysis'}
            </h1>
            <p className="font-body text-xs text-muted mt-1">
              {lang==='ja'
                ? '構成銘柄が指数に与えた価格変動を毎日分析。AIが「なぜ動いたか」を解説。'
                : 'Daily analysis of which stocks moved the index and why.'}
            </p>
          </div>
          <div className="flex items-center gap-1 bg-panel border border-border rounded-lg p-0.5">
            {['ja','en'].map(l => (
              <button key={l} onClick={() => setLang(l)}
                className={`px-3 py-1 text-xs font-mono rounded-md transition ${
                  lang===l ? 'bg-green text-ink font-700' : 'text-muted hover:text-dim'}`}>
                {l==='ja' ? '日本語' : 'English'}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-6 h-6 border-2 border-green border-t-transparent rounded-full animate-spin"/>
            <p className="font-mono text-xs text-muted">Loading market data...</p>
          </div>
        ) : !data ? (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <Activity size={32} className="text-muted mx-auto mb-3"/>
            <p className="font-body text-muted text-sm mb-2">
              {lang==='ja' ? '市場データはまだ生成されていません。' : 'Market data not yet generated.'}
            </p>
            <p className="font-mono text-xs text-muted">
              {lang==='ja' ? '毎営業日 JST15時に自動更新されます。' : 'Auto-updated every trading day at JST 15:00.'}
            </p>
          </div>
        ) : (
          <div className="space-y-5">

            {/* 指数タブ */}
            <div className="flex gap-1 flex-wrap">
              {data.indices && Object.entries(data.indices).map(([k, v]) => (
                <button key={k} onClick={() => setActive(k)}
                  className={`font-mono text-xs px-4 py-2 rounded-lg border transition font-700 ${
                    active===k ? 'border-transparent text-ink' : 'border-border text-muted hover:text-dim'}`}
                  style={active===k ? {background: v.color} : {}}>
                  {v.label}
                  {v.performance?.ret_1d != null && (
                    <span className={`ml-2 ${(v.performance.ret_1d||0)>=0?'text-ink':'text-ink'}`}>
                      {(v.performance.ret_1d||0)>=0?'+':''}{v.performance.ret_1d}%
                    </span>
                  )}
                </button>
              ))}
            </div>

            {idx && (
              <>
                {/* パフォーマンスサマリー */}
                <div className="grid grid-cols-4 gap-2">
                  {[
                    {l:lang==='ja'?'1日':'1D', v:perf.ret_1d},
                    {l:lang==='ja'?'5日':'5D', v:perf.ret_5d},
                    {l:lang==='ja'?'1ヶ月':'1M',v:perf.ret_1m},
                    {l:lang==='ja'?'3ヶ月':'3M',v:perf.ret_3m},
                  ].map(p => (
                    <div key={p.l} className="bg-panel border border-border rounded-xl p-3 text-center">
                      <div className="font-mono text-xs text-muted">{p.l}</div>
                      <div className={`font-mono text-base font-700 mt-1 ${
                        p.v==null?'text-muted':(p.v>=0?'text-green':'text-red')}`}>
                        {p.v==null ? '—' : `${p.v>=0?'+':''}${p.v}%`}
                      </div>
                    </div>
                  ))}
                </div>

                {/* チャート */}
                <PriceLineChart candles={idx.candles} color={idx.color} label={idx.label}/>

                {/* 上昇・下落寄与テーブル */}
                <div className="bg-panel border border-border rounded-xl p-4 grid md:grid-cols-2 gap-6">
                  <ComponentTable
                    items={idx.gainers} type="gainer"
                    title={lang==='ja'?`上昇寄与 TOP${Math.min(6,idx.gainers?.length||0)}（1ヶ月）`:`Top Gainers (1M)`}
                    lang={lang}/>
                  <ComponentTable
                    items={idx.losers} type="loser"
                    title={lang==='ja'?`下落寄与 TOP${Math.min(6,idx.losers?.length||0)}（1ヶ月）`:`Top Losers (1M)`}
                    lang={lang}/>
                </div>

                {/* 出来高急増（なぜ動いたかの手がかり） */}
                {(idx.vol_surge?.length > 0) && (
                  <VolSurgeTable items={idx.vol_surge} lang={lang}/>
                )}

                {/* AdSense mid */}
                <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
                  <ins className="adsbygoogle" style={{display:'block',width:'100%'}}
                       data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
                       data-ad-format="horizontal" data-full-width-responsive="true"/>
                  <span className="font-mono text-xs text-muted/40">Ad</span>
                </div>

                {/* AI解説「なぜ動いたか」 */}
                {idx.analysis && (
                  <div className="bg-panel border border-border rounded-xl p-5">
                    <div className="font-mono text-xs text-muted mb-4 flex items-center gap-2">
                      <Activity size={11}/> AI {lang==='ja'?'解説 — なぜ動いたか':'Analysis — Why did it move?'}
                    </div>
                    <div className="prose prose-invert prose-sm max-w-none
                      prose-headings:font-display prose-headings:text-bright prose-headings:font-700 prose-headings:text-base
                      prose-p:font-body prose-p:text-dim prose-p:leading-relaxed prose-p:text-sm
                      prose-strong:text-text prose-a:text-green">
                      <ReactMarkdown>{idx.analysis[lang] ?? idx.analysis.ja ?? ''}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* AdSense bottom */}
                <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[250px] flex items-center justify-center">
                  <ins className="adsbygoogle" style={{display:'block'}}
                       data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"/>
                  <span className="font-mono text-xs text-muted/40">Ad</span>
                </div>

                {/* 関連リンク */}
                <div className="bg-panel border border-border rounded-xl p-4">
                  <div className="font-mono text-xs text-muted mb-3">
                    {lang==='ja'?'関連コンテンツ':'Related'}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Link to="/backtest"
                      className="flex items-center gap-2 p-3 bg-ink border border-border rounded-lg
                                 hover:border-muted transition group">
                      <span className="font-mono text-xs text-dim group-hover:text-green transition">
                        {lang==='ja'?'→ バックテスト検証':'→ Backtest Verification'}
                      </span>
                    </Link>
                    <Link to="/blog"
                      className="flex items-center gap-2 p-3 bg-ink border border-border rounded-lg
                                 hover:border-muted transition group">
                      <span className="font-mono text-xs text-dim group-hover:text-green transition">
                        {lang==='ja'?'→ 日次レポート':'→ Daily Reports'}
                      </span>
                    </Link>
                  </div>
                </div>
              </>
            )}

            {/* 免責 */}
            <div className="p-4 bg-panel border border-border rounded-xl">
              <p className="font-body text-xs text-muted leading-relaxed">
                {lang==='ja'
                  ? `⚠️ 本ページはAIを活用した教育目的のコンテンツです。データはFMP APIを使用しており、遅延・誤差が含まれる場合があります。指数インパクトの寄与度分析は概算であり、実際の時価総額加重計算とは異なります。最終更新: ${data?.generated_at}`
                  : `⚠️ Educational content using AI analysis. Data via FMP API may contain delays. Impact analysis is approximate, not weighted by market cap. Last updated: ${data?.generated_at}`}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
