import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { Calendar, ChevronLeft, Loader, RefreshCw, TrendingUp, TrendingDown,
         ExternalLink, Newspaper, Users, BarChart2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useSEO } from '../hooks/useSEO';

function LangToggle({ lang, setLang }) {
  return (
    <div className="flex items-center gap-1 bg-panel border border-border rounded-lg p-0.5">
      {['ja','en'].map(l => (
        <button key={l} onClick={() => setLang(l)}
          className={`px-3 py-1 text-xs font-mono rounded-md transition ${
            lang===l ? 'bg-green text-ink font-700' : 'text-muted hover:text-dim'}`}>
          {l==='ja' ? '日本語' : 'English'}
        </button>
      ))}
    </div>
  );
}

// ── TradingViewウィジェット + Yahoo Financeリンク ────────
function TradingViewWidget({ ticker }) {
  const cid = `tv_${ticker}`;
  return (
    <div className="my-6 not-prose rounded-xl overflow-hidden border border-border bg-ink">
      <div className="font-mono text-xs text-muted px-4 py-2.5 border-b border-border flex items-center justify-between">
        <span>{ticker} — Chart by TradingView</span>
        <div className="flex items-center gap-3">
          <a href={`https://finance.yahoo.com/quote/${ticker}`}
             target="_blank" rel="noopener noreferrer"
             className="text-amber hover:underline flex items-center gap-1">
            Yahoo Finance <ExternalLink size={9}/>
          </a>
          <a href={`https://www.tradingview.com/chart/?symbol=${ticker}`}
             target="_blank" rel="noopener noreferrer"
             className="text-green hover:underline flex items-center gap-1">
            詳細チャート <ExternalLink size={9}/>
          </a>
        </div>
      </div>
      <div dangerouslySetInnerHTML={{__html:`
        <div class="tradingview-widget-container">
          <div id="${cid}" style="height:380px;"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({
            "width":"100%","height":380,"symbol":"${ticker}",
            "interval":"D","timezone":"America/New_York","theme":"dark","style":"1",
            "locale":"ja","toolbar_bg":"#0E1318","enable_publishing":false,
            "hide_side_toolbar":true,"allow_symbol_change":false,"save_image":false,
            "container_id":"${cid}",
            "overrides":{"paneProperties.background":"#080C10","paneProperties.backgroundType":"solid"}
          });
          </script>
        </div>
      `}}/>
      {/* 株価確認リンク */}
      <div className="px-4 py-2.5 border-t border-border flex items-center gap-2">
        <span className="font-mono text-xs text-muted">正確な株価・出来高はこちら →</span>
        <a href={`https://finance.yahoo.com/quote/${ticker}`}
           target="_blank" rel="noopener noreferrer"
           className="font-mono text-xs text-amber hover:underline flex items-center gap-1">
          Yahoo Finance <ExternalLink size={9}/>
        </a>
        <a href={`https://finance.yahoo.com/quote/${ticker}/financials/`}
           target="_blank" rel="noopener noreferrer"
           className="font-mono text-xs text-muted hover:text-dim flex items-center gap-1">
          財務諸表 <ExternalLink size={9}/>
        </a>
        <a href={`https://finance.yahoo.com/quote/${ticker}/analysis/`}
           target="_blank" rel="noopener noreferrer"
           className="font-mono text-xs text-muted hover:text-dim flex items-center gap-1">
          アナリスト予想 <ExternalLink size={9}/>
        </a>
      </div>
    </div>
  );
}

// ── VCPスコア推移グラフ ──────────────────────────────────
function StockHistoryChart({ history, lang }) {
  if (!history?.length) return null;
  const data = [...history].reverse().slice(-30).map(h => ({
    date: h.date?.slice(5), vcp: h.vcp??0, rs: h.rs??0,
  }));
  return (
    <div className="my-4 bg-ink border border-border rounded-xl p-4 not-prose">
      <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
        <TrendingUp size={11}/> {lang==='ja'?'スコア推移（直近30日）':'Score History (30d)'}
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[{key:'vcp',color:'#22C55E',max:105,label:'VCP'},
          {key:'rs', color:'#3B82F6',max:99, label:'RS'}].map(c => (
          <div key={c.key}>
            <div className="font-mono text-xs mb-1" style={{color:c.color}}>{c.label}</div>
            <ResponsiveContainer width="100%" height={70}>
              <LineChart data={data}>
                <XAxis dataKey="date" tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false} axisLine={false} interval="preserveStartEnd"/>
                <YAxis domain={[0,c.max]} tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false} axisLine={false} width={18}/>
                <Tooltip contentStyle={{background:'#0E1318',border:'1px solid #1C2530',borderRadius:'6px',fontSize:'10px'}} labelStyle={{color:'#7A90A8'}}/>
                <ReferenceLine y={c.key==='vcp'?70:80} stroke={c.color} strokeDasharray="3 3" strokeOpacity={0.3}/>
                <Line type="monotone" dataKey={c.key} stroke={c.color} strokeWidth={1.5} dot={false}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 銘柄スコアパネル（派生データのみ・価格なし）─────────
function StockDataPanel({ data, lang }) {
  if (!data?.ticker) return null;
  const bd   = data.vcp_breakdown ?? {};
  const an   = data.analyst       ?? {};
  const fund = data.fundamentals  ?? {};
  const own  = data.ownership     ?? {};
  const news = data.news          ?? [];

  return (
    <div className="my-6 not-prose space-y-3">

      {/* スコアカード */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {[
          {label:'VCP Score', val:`${data.vcp}/105`,      hi:data.vcp>=70,  color:'text-green'},
          {label:'RS Rating', val:`${data.rs}/99`,        hi:data.rs>=80,   color:'text-blue'},
          {label:'SES',       val:`${data.ses ?? '—'}/100`, hi:(data.ses??0)>=60, color:'text-purple-400',
           desc: lang==='ja'?'効率性スコア':'Efficiency Score'},
          {label:'ECR Rank',  val:`${data.ecr_rank ?? '—'}/100`, hi:(data.ecr_rank??0)>=70, color:'text-blue',
           desc: data.ecr_phase ?? ''},
        ].map(c => (
          <div key={c.label} className="bg-panel border border-border rounded-xl p-3">
            <div className="font-mono text-xs text-muted mb-1">{c.label}</div>
            <div className={`font-display text-2xl font-700 ${c.hi?c.color:'text-bright'}`}>{c.val}</div>
            {c.desc && <div className="font-mono text-xs text-muted mt-0.5">{c.desc}</div>}
          </div>
        ))}
      </div>

      {/* ステータス + ECRフェーズ */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-panel border border-border rounded-xl p-3">
          <div className="font-mono text-xs text-muted mb-1">STATUS</div>
          <div className={`font-display text-2xl font-700 ${data.status==='ACTION'?'text-green':'text-amber'}`}>
            {data.status}
          </div>
        </div>
        {data.ecr_phase && (
          <div className="bg-panel border border-border rounded-xl p-3">
            <div className="font-mono text-xs text-muted mb-1">ECR PHASE</div>
            <div className={`font-mono text-base font-700 ${
              data.ecr_phase==='ACCUMULATION'?'text-green':
              data.ecr_phase==='IGNITION'?'text-blue':
              data.ecr_phase==='RELEASE'?'text-amber':'text-muted'}`}>
              {data.ecr_phase}
            </div>
            {data.ecr_strategy && data.ecr_strategy !== 'NONE' && (
              <div className="font-mono text-xs text-muted mt-0.5">Strategy: {data.ecr_strategy}</div>
            )}
          </div>
        )}
      </div>

      {/* トレードパラメータ（ATR倍率・Rで表示） */}
      <div className="bg-panel border border-border rounded-xl p-4">
        <div className="font-mono text-xs text-muted mb-3 flex items-center gap-1.5">
          <TrendingUp size={11}/>
          {lang==='ja'?'トレードパラメータ（派生値 — 価格非表示）':'Trade Parameters (Derived — No raw price)'}
        </div>
        <div className="grid grid-cols-3 gap-3 mb-3">
          {[
            {l:lang==='ja'?'ピボット乖離':'Pivot Dist.',
             v:data.pivot_dist_pct!=null?`${data.pivot_dist_pct>0?'+':''}${data.pivot_dist_pct}%`:'—',
             c:'text-bright', d:lang==='ja'?'直近高値からの距離':'From recent high'},
            {l:lang==='ja'?'ストップライン':'Stop Line',
             v:data.stop_atr_mult?`−${data.stop_atr_mult}×ATR`:'—',
             c:'text-red',   d:lang==='ja'?'ATR倍率ベース':'ATR multiple'},
            {l:lang==='ja'?'ターゲット':'Target',
             v:data.target_r?`+${data.target_r}R`:'—',
             c:'text-green', d:lang==='ja'?'リスク倍率':'Risk multiple'},
          ].map(p => (
            <div key={p.l} className="text-center">
              <div className="font-mono text-xs text-muted">{p.l}</div>
              <div className={`font-mono text-sm font-700 mt-0.5 ${p.c}`}>{p.v}</div>
              <div className="font-mono text-xs text-muted/60 mt-0.5">{p.d}</div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
          {[
            {l:'MA50乖離',  v:data.ma50_ratio},
            {l:'MA200乖離', v:data.ma200_ratio},
            {l:'ATR%',      v:data.atr_pct, fmt:v=>`${v}%`},
          ].map(m => m.v!=null && (
            <div key={m.l} className="text-center">
              <div className="font-mono text-xs text-muted">{m.l}</div>
              <div className={`font-mono text-sm font-700 ${
                m.l==='ATR%'?'text-amber':(m.v>=0?'text-green':'text-red')}`}>
                {m.l==='ATR%'?`${m.v}%`:`${m.v>=0?'+':''}${m.v}%`}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* VCPブレイクダウン */}
      <div className="bg-panel border border-border rounded-xl p-4">
        <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'VCPスコア内訳':'VCP Breakdown'}</div>
        <div className="space-y-2.5">
          {[{l:'Tightness',d:lang==='ja'?'値動き収縮':'Price tightness',v:bd.tight??0,max:40},
            {l:'Volume',   d:lang==='ja'?'出来高収縮':'Volume dry-up',  v:bd.vol??0,  max:30},
            {l:'MA Align', d:lang==='ja'?'移動平均の並び':'MA alignment',v:bd.ma??0,   max:30},
            {l:'Pivot',    d:lang==='ja'?'ピボット近接':'Pivot proximity',v:bd.pivot??0,max:5},
          ].map(b => (
            <div key={b.l}>
              <div className="flex justify-between mb-0.5">
                <span className="font-mono text-xs text-dim">{b.l} <span className="text-muted/60">{b.d}</span></span>
                <span className={`font-mono text-xs font-700 ${b.v/b.max>=0.8?'text-green':b.v/b.max>=0.5?'text-amber':'text-dim'}`}>{b.v}/{b.max}</span>
              </div>
              <div className="h-1.5 bg-border rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{
                  width:`${Math.min(100,(b.v/b.max)*100)}%`,
                  background:b.v/b.max>=0.8?'#22C55E':b.v/b.max>=0.5?'#F59E0B':'#3D4F63'
                }}/>
              </div>
            </div>
          ))}
          <div className="flex justify-between pt-2 border-t border-border font-mono text-xs">
            <span className="text-muted">{lang==='ja'?'合計':'Total'}</span>
            <span className={`font-700 ${data.vcp>=70?'text-green':data.vcp>=50?'text-amber':'text-muted'}`}>{data.vcp}/105</span>
          </div>
        </div>
        {data.signals?.length>0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border">
            {data.signals.map(s=><span key={s} className="font-mono text-xs px-2 py-0.5 rounded bg-green/10 border border-green/20 text-green">{s}</span>)}
          </div>
        )}
      </div>

      {/* ファンダメンタル */}
      {Object.keys(fund).length>0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <BarChart2 size={11}/> {lang==='ja'?'ファンダメンタル':'Fundamentals'}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {[
              {l:lang==='ja'?'予想PER':'Fwd P/E',      v:fund.pe_forward,         fmt:v=>`${v}x`},
              {l:lang==='ja'?'売上成長率':'Rev Growth', v:fund.revenue_growth_yoy, fmt:v=>{const n=parseFloat(v);return <span className={n>=0?'text-green':'text-red'}>{n>=0?'+':''}{v}%</span>;}},
              {l:lang==='ja'?'利益成長率':'EPS Growth', v:fund.earnings_growth_yoy,fmt:v=>{const n=parseFloat(v);return <span className={n>=0?'text-green':'text-red'}>{n>=0?'+':''}{v}%</span>;}},
              {l:'ROE',              v:fund.roe,        fmt:v=>`${v}%`},
              {l:lang==='ja'?'粗利率':'Gross Margin',  v:fund.gross_margin,       fmt:v=>`${v}%`},
              {l:lang==='ja'?'時価総額':'Mkt Cap',     v:fund.market_cap_b,       fmt:v=>`$${v}B`},
            ].map(f=>f.v!=null&&(
              <div key={f.l} className="bg-ink rounded-lg p-2.5">
                <div className="font-mono text-xs text-muted">{f.l}</div>
                <div className="font-mono text-sm font-700 text-bright mt-0.5">{typeof f.fmt(f.v)==='object'?f.fmt(f.v):f.fmt(f.v)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* アナリスト */}
      {Object.keys(an).length>0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <Users size={11}/> {lang==='ja'?`アナリスト評価（${an.analyst_count||0}名）`:`Analyst (${an.analyst_count||0})`}
          </div>
          <div className="flex items-center gap-4 mb-3">
            <span className={`font-display text-2xl font-700 ${an.consensus==='Buy'?'text-green':an.consensus==='Sell'?'text-red':'text-amber'}`}>{an.consensus}</span>
            {an.target_pct!=null&&<div>
              <div className="font-mono text-xs text-muted">{lang==='ja'?'目標株価乖離':'Upside/Down'}</div>
              <div className={`font-mono text-sm font-700 ${an.target_pct>=0?'text-green':'text-red'}`}>{an.target_pct>=0?'+':''}{an.target_pct}%</div>
            </div>}
          </div>
          {(an.buy||an.hold||an.sell)&&(()=>{const t=(an.buy||0)+(an.hold||0)+(an.sell||0);return(
            <div>
              <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
                <div className="bg-green" style={{width:`${((an.buy||0)/t)*100}%`}}/>
                <div className="bg-amber" style={{width:`${((an.hold||0)/t)*100}%`}}/>
                <div className="bg-red"   style={{width:`${((an.sell||0)/t)*100}%`}}/>
              </div>
              <div className="flex justify-between mt-1 font-mono text-xs text-muted">
                <span className="text-green">Buy {an.buy||0}</span>
                <span className="text-amber">Hold {an.hold||0}</span>
                <span className="text-red">Sell {an.sell||0}</span>
              </div>
            </div>
          );})()}
        </div>
      )}

      {/* 投資家動向 */}
      {Object.keys(own).some(k=>own[k]!=null)&&(
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <TrendingDown size={11}/> {lang==='ja'?'投資家動向':'Investor Activity'}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {[
              {l:lang==='ja'?'機関投資家':'Institutional',v:own.institutional_pct,  fmt:v=>`${v}%`},
              {l:lang==='ja'?'インサイダー':'Insider',    v:own.insider_pct,        fmt:v=>`${v}%`},
              {l:lang==='ja'?'空売り比率':'Short Float',  v:own.short_float_pct,    fmt:v=><span className={parseFloat(v)>15?'text-red':parseFloat(v)>8?'text-amber':'text-green'}>{v}%</span>},
              {l:lang==='ja'?'空売り日数':'Days Cover',   v:own.short_days_to_cover,fmt:v=>`${v}d`},
            ].map(f=>f.v!=null&&(
              <div key={f.l} className="bg-ink rounded-lg p-2.5">
                <div className="font-mono text-xs text-muted">{f.l}</div>
                <div className="font-mono text-sm font-700 text-bright mt-0.5">{typeof f.fmt(f.v)==='object'?f.fmt(f.v):f.fmt(f.v)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ニュース */}
      {news.length>0&&(
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <Newspaper size={11}/> {lang==='ja'?'直近ニュース':'Recent News'}
          </div>
          <div className="space-y-2">
            {news.slice(0,4).map((n,i)=>(
              <a key={i} href={n.url} target="_blank" rel="noopener noreferrer" className="block group">
                <div className="flex items-start gap-2">
                  <ExternalLink size={10} className="text-muted mt-1 shrink-0 group-hover:text-green transition"/>
                  <div>
                    <p className="font-body text-xs text-dim group-hover:text-text transition leading-snug">{n.title}</p>
                    <p className="font-mono text-xs text-muted mt-0.5">{n.source} · {n.published_at?.slice(0,10)}</p>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── VCPランキングテーブル（価格なし） ───────────────────
function VCPRankingTable({ ranking, lang }) {
  if (!ranking?.length) return null;
  return (
    <div className="my-6 not-prose">
      <div className="bg-ink border border-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <span className="font-mono text-xs text-muted">{lang==='ja'?'VCPスコアランキング':'VCP Ranking'}</span>
          <span className="font-mono text-xs text-muted">{lang==='ja'?'↑ ティッカーで個別ページへ':'↑ Click ticker for details'}</span>
        </div>
        <div className="grid grid-cols-[28px_64px_1fr_64px_56px_72px] gap-2 px-4 py-2 border-b border-border/50">
          {['#','Ticker','Name','VCP','RS','Status'].map(h=>(
            <span key={h} className="font-mono text-xs text-muted">{h}</span>
          ))}
        </div>
        <div className="divide-y divide-border/30">
          {ranking.slice(0,20).map(r=>(
            <div key={r.ticker} className="grid grid-cols-[28px_80px_1fr_64px_56px_72px] gap-2 px-4 py-2.5
                       hover:bg-panel/60 transition group items-center">
              <span className="font-mono text-xs text-muted">{r.rank}</span>
              <div className="flex items-center gap-1">
                <Link to={`/blog/stock-${r.ticker.toLowerCase()}`}
                  className="font-mono text-xs text-bright font-700 group-hover:text-green transition">
                  {r.ticker}
                </Link>
                <a href={`https://finance.yahoo.com/quote/${r.ticker}`}
                   target="_blank" rel="noopener noreferrer"
                   className="text-amber/60 hover:text-amber transition" title="Yahoo Finance">
                  <ExternalLink size={8}/>
                </a>
              </div>
              <span className="font-body text-xs text-muted truncate">{r.name||r.ticker}</span>
              <div className="flex items-center gap-1">
                <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{width:`${(r.vcp/105)*100}%`,background:r.vcp>=80?'#22C55E':r.vcp>=60?'#F59E0B':'#3D4F63'}}/>
                </div>
                <span className={`font-mono text-xs font-700 w-6 text-right ${r.vcp>=80?'text-green':r.vcp>=60?'text-amber':'text-dim'}`}>{r.vcp}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                  <div className="h-full bg-blue rounded-full" style={{width:`${(r.rs/99)*100}%`}}/>
                </div>
                <span className="font-mono text-xs font-700 text-blue w-6 text-right">{r.rs}</span>
              </div>
              <span className={`font-mono text-xs px-1.5 py-0.5 rounded text-center border ${
                r.status==='ACTION'?'bg-green/10 border-green/20 text-green':'bg-amber/10 border-amber/20 text-amber'}`}>
                {r.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 日次データパネル ─────────────────────────────────────
function DailyDataPanel({ data, lang }) {
  if (!data) return null;
  const { index={}, sector=[], vcp_ranking=[] } = data;
  return (
    <div className="my-6 space-y-4 not-prose">
      {Object.keys(index).length>0 && (
        <div className="bg-ink border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'本日の指数パフォーマンス':'Index Performance Today'}</div>
          <div className="grid grid-cols-3 gap-3">
            {Object.values(index).map(d=>(
              <div key={d.name} className="text-center">
                <div className="font-mono text-xs text-muted">{d.name}</div>
                <div className={`font-mono text-base font-700 ${d.chg_1d>=0?'text-green':'text-red'}`}>{d.chg_1d>=0?'+':''}{d.chg_1d}%</div>
                <div className="font-mono text-xs text-muted">5d: {d.chg_5d>=0?'+':''}{d.chg_5d}%</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {sector.length>0 && (
        <div className="bg-ink border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'セクター強度（平均RS）':'Sector Strength (Avg RS)'}</div>
          <div className="space-y-2">
            {sector.slice(0,8).map(s=>(
              <div key={s.sector} className="flex items-center gap-3">
                <span className="font-mono text-xs text-dim w-28 truncate">{s.sector}</span>
                <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{width:`${Math.min(100,(s.avg_rs/99)*100)}%`,background:s.avg_rs>=85?'#22C55E':s.avg_rs>=70?'#F59E0B':'#3D4F63'}}/>
                </div>
                <span className="font-mono text-xs text-bright w-7 text-right font-700">{s.avg_rs}</span>
                {s.action_count>0&&<span className="font-mono text-xs text-green w-10">▲{s.action_count}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
      {vcp_ranking.length>0 && <VCPRankingTable ranking={vcp_ranking} lang={lang}/>}
    </div>
  );
}

// ── 週次データパネル ─────────────────────────────────────
function WeeklyDataPanel({ data, lang }) {
  if (!data) return null;
  const { index={}, sector=[], vcp_ranking=[] } = data;
  return (
    <div className="my-6 space-y-4 not-prose">
      {Object.keys(index).length>0 && (
        <div className="bg-ink border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'週次パフォーマンス（5d）':'Weekly Performance (5d)'}</div>
          <div className="grid grid-cols-3 gap-3">
            {Object.values(index).map(d=>(
              <div key={d.name} className="text-center">
                <div className="font-mono text-xs text-muted">{d.name}</div>
                <div className={`font-mono text-base font-700 ${(d.chg_5d??0)>=0?'text-green':'text-red'}`}>{(d.chg_5d??0)>=0?'+':''}{d.chg_5d}%</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {vcp_ranking.length>0 && <VCPRankingTable ranking={vcp_ranking} lang={lang}/>}
    </div>
  );
}

// ── メインページ ─────────────────────────────────────────
export default function ArticleDetail() {
  const { slug }  = useParams();
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lang,    setLang]    = useState('ja');

  useEffect(() => {
    let url = '';
    if      (slug.startsWith('daily-'))  url = `/content/daily/${slug.replace('daily-','')}.json`;
    else if (slug.startsWith('weekly-')) url = `/content/weekly/${slug.replace('weekly-','')}.json`;
    else if (slug.startsWith('stock-'))  url = `/content/stocks/${slug.replace('stock-','').toUpperCase()}.json`;
    if (!url) { setLoading(false); return; }
    fetch(url).then(r=>r.ok?r.json():null).then(d=>{setArticle(d);setLoading(false);}).catch(()=>setLoading(false));
  }, [slug]);

  const t = article?.[lang] ?? article?.ja;
  useSEO({ title:t?.title, description:t?.summary,
           type:article?'article':'website', lang,
           article:article?{published_at:article.published_at,ticker:article.ticker}:null });

  if (loading) return <div className="min-h-screen bg-ink pt-24 flex items-center justify-center"><Loader size={24} className="text-muted animate-spin"/></div>;
  if (!article) return (
    <div className="min-h-screen bg-ink pt-24 px-4">
      <div className="max-w-3xl mx-auto text-center mt-20">
        <p className="font-body text-muted">記事が見つかりません</p>
        <Link to="/blog" className="text-green font-mono text-xs hover:underline mt-2 block">← Back to Blog</Link>
      </div>
    </div>
  );

  const TYPE_LABEL = {
    daily:  {ja:'日次レポート',en:'Daily Report',  color:'text-green border-green/30 bg-green/10'},
    weekly: {ja:'週次レポート',en:'Weekly Report', color:'text-blue  border-blue/30  bg-blue/10'},
    stock:  {ja:'銘柄分析',    en:'Stock Analysis',color:'text-amber border-amber/30 bg-amber/10'},
  };
  const tm = TYPE_LABEL[article.type] ?? TYPE_LABEL.stock;

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-3xl mx-auto mb-4">
        <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block',width:'100%'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
               data-ad-format="horizontal" data-full-width-responsive="true"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto">
        <Link to="/blog" className="inline-flex items-center gap-1 font-mono text-xs text-muted hover:text-dim mb-6">
          <ChevronLeft size={12}/> {lang==='ja'?'レポート一覧':'All Reports'}
        </Link>

        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`font-mono text-xs px-2 py-0.5 rounded border ${tm.color}`}>{lang==='ja'?tm.ja:tm.en}</span>
            <span className="font-mono text-xs text-muted flex items-center gap-1"><Calendar size={10}/> {article.date}</span>
            {article.ticker&&<span className="font-mono text-xs text-amber font-700">{article.ticker}</span>}
            {article.name&&<span className="font-body text-xs text-muted">{article.name}</span>}
            {article.type==='stock'&&<span className="font-mono text-xs text-green/60 flex items-center gap-1"><RefreshCw size={9}/> {lang==='ja'?'毎日更新':'Daily update'}</span>}
          </div>
          <LangToggle lang={lang} setLang={setLang}/>
        </div>

        <h1 className="font-display font-700 text-bright text-2xl md:text-3xl leading-tight mb-3">{t?.title}</h1>
        <p className="font-body text-dim text-sm leading-relaxed mb-6 border-l-2 border-green/40 pl-4">{t?.summary}</p>

        {/* TradingViewチャート（銘柄ページのみ） */}
        {article.type==='stock' && article.ticker && <TradingViewWidget ticker={article.ticker}/>}

        {/* データパネル */}
        {article.type==='stock'  && <StockDataPanel data={article.data} lang={lang}/>}
        {article.type==='stock'  && <StockHistoryChart history={article.history} lang={lang}/>}
        {article.type==='daily'  && <DailyDataPanel  data={article.data} lang={lang}/>}
        {article.type==='weekly' && <WeeklyDataPanel data={article.data} lang={lang}/>}

        <div className="my-6 rounded-xl overflow-hidden bg-panel border border-border min-h-[250px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>

        <div className="prose prose-invert prose-sm max-w-none
          prose-headings:font-display prose-headings:text-bright prose-headings:font-700
          prose-p:font-body prose-p:text-dim prose-p:leading-relaxed
          prose-strong:text-text prose-code:font-mono prose-code:text-green
          prose-code:bg-panel prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
          prose-blockquote:border-green/40 prose-blockquote:text-muted
          prose-a:text-green prose-a:no-underline hover:prose-a:underline">
          <ReactMarkdown>{t?.body??''}</ReactMarkdown>
        </div>

        <div className="mt-8 rounded-xl overflow-hidden bg-panel border border-border min-h-[250px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>

        <div className="mt-6 p-4 bg-panel border border-border rounded-xl">
          <p className="font-body text-xs text-muted leading-relaxed">
            {lang==='ja'
              ? '⚠️ 本記事はAIによる自動生成を含む教育目的のコンテンツです。表示されるスコアは独自ロジックによる派生データであり、生の株価データではありません。投資助言ではありません。チャートはTradingViewが提供しています。'
              : '⚠️ AI-generated educational content. Scores are derived data from our proprietary logic, not raw price data. Not investment advice. Charts provided by TradingView.'}
          </p>
        </div>
      </div>
    </div>
  );
}
