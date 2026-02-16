import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell, ReferenceLine, RadarChart,
  Radar, PolarGrid, PolarAngleAxis,
} from 'recharts';
import { FlaskConical, TrendingUp, TrendingDown, Zap,
         Trophy, AlertTriangle, ExternalLink } from 'lucide-react';
import { useSEO } from '../hooks/useSEO';

// ── 手法メタ ─────────────────────────────────────────────
const METHODS = {
  vcp_rs:  { label:'VCP × RS',  color:'#22C55E', short:'VCP' },
  ecr:     { label:'ECR',       color:'#3B82F6', short:'ECR' },
  canslim: { label:'CANSLIM',   color:'#F59E0B', short:'CAN' },
  ses:     { label:'SES',       color:'#8B5CF6', short:'SES' },
};

// ── ダークトップのカスタムTooltip ─────────────────────────
const DarkTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-ink border border-border rounded-lg p-2.5 font-mono text-xs space-y-1">
      <div className="text-muted mb-1">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{color:p.color||p.fill}}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
          {p.name?.includes('率') || p.name?.includes('Rate') ? '%' : ''}
        </div>
      ))}
    </div>
  );
};

// ── 統計カード ────────────────────────────────────────────
function StatCard({ label, value, unit='', color='text-bright', sub }) {
  return (
    <div className="bg-panel border border-border rounded-xl p-4 text-center">
      <div className="font-mono text-xs text-muted mb-1">{label}</div>
      <div className={`font-display font-800 text-2xl ${color}`}>
        {value ?? '—'}{value != null ? unit : ''}
      </div>
      {sub && <div className="font-mono text-xs text-muted/60 mt-1">{sub}</div>}
    </div>
  );
}

// ── 手法比較バーチャート ──────────────────────────────────
function MethodComparisonChart({ data, metric, label, lang }) {
  if (!data?.length) return null;
  return (
    <div>
      <div className="font-mono text-xs text-muted mb-2">{label}</div>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} margin={{top:4,right:8,bottom:0,left:-8}}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1C2530" vertical={false}/>
          <XAxis dataKey="label" tick={{fontSize:9,fill:'#7A90A8'}} axisLine={false} tickLine={false}/>
          <YAxis tick={{fontSize:8,fill:'#3D4F63'}} axisLine={false} tickLine={false}/>
          <Tooltip content={<DarkTip/>}/>
          <ReferenceLine y={50} stroke="#3D4F63" strokeDasharray="3 3" strokeWidth={0.5}/>
          <Bar dataKey={metric} name={lang==='ja'?'勝率':'Win Rate'} radius={[4,4,0,0]} maxBarSize={40}>
            {data.map((d, i) => (
              <Cell key={i} fill={METHODS[d.method]?.color || '#3D4F63'}/>
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── スコア分布バーチャート ────────────────────────────────
function DistributionChart({ data, label, color }) {
  if (!data?.length) return null;
  return (
    <div>
      <div className="font-mono text-xs text-muted mb-2">{label}</div>
      <ResponsiveContainer width="100%" height={110}>
        <BarChart data={data} margin={{top:4,right:4,bottom:0,left:-16}}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1C2530" vertical={false}/>
          <XAxis dataKey="range" tick={{fontSize:8,fill:'#7A90A8'}} axisLine={false} tickLine={false}/>
          <YAxis tick={{fontSize:8,fill:'#3D4F63'}} axisLine={false} tickLine={false}/>
          <Tooltip content={<DarkTip/>}/>
          <ReferenceLine y={50} stroke="#3D4F63" strokeDasharray="3 3" strokeWidth={0.5}/>
          <Bar dataKey="win_rate" name="勝率" fill={color} radius={[3,3,0,0]} maxBarSize={32}/>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── 複数手法一致ヒートマップ ──────────────────────────────
function MultiMethodChart({ data, lang }) {
  if (!data) return null;
  const rows = [
    { key: 'methods_1plus', label: lang==='ja'?'1手法以上':'1+ methods' },
    { key: 'methods_2plus', label: lang==='ja'?'2手法以上':'2+ methods' },
    { key: 'methods_3plus', label: lang==='ja'?'3手法以上':'3+ methods' },
    { key: 'methods_4plus', label: lang==='ja'?'全4手法':'All 4 methods' },
  ].filter(r => data[r.key]?.count > 0);

  if (!rows.length) return null;
  return (
    <div className="space-y-2">
      {rows.map(r => {
        const s = data[r.key];
        const wr = s.win_rate || 0;
        const color = wr >= 65 ? '#22C55E' : wr >= 55 ? '#F59E0B' : '#EF4444';
        return (
          <div key={r.key} className="flex items-center gap-3">
            <span className="font-mono text-xs text-dim w-28">{r.label}</span>
            <div className="flex-1 h-4 bg-border rounded-full overflow-hidden flex">
              <div className="h-full rounded-full transition-all"
                   style={{width:`${wr}%`, background:color}}/>
            </div>
            <span className="font-mono text-xs font-700 w-10 text-right" style={{color}}>
              {wr}%
            </span>
            <span className="font-mono text-xs text-muted w-12 text-right">
              n={s.count}
            </span>
            <span className={`font-mono text-xs font-700 w-12 text-right ${
              (s.avg_return||0)>=0?'text-green':'text-red'}`}>
              {(s.avg_return||0)>=0?'+':''}{s.avg_return}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── 手法詳細パネル ────────────────────────────────────────
function MethodDetailPanel({ method, stats, distributions, extraStats, holdKey, lang }) {
  const s   = stats?.[method]?.[holdKey];
  const m   = METHODS[method];
  if (!s || !s.signal_count) return (
    <div className="bg-panel border border-border rounded-xl p-6 text-center">
      <p className="font-mono text-xs text-muted">データなし</p>
    </div>
  );

  const winColor = (s.win_rate||0) >= 60 ? '#22C55E'
                 : (s.win_rate||0) >= 50 ? '#F59E0B' : '#EF4444';

  return (
    <div className="bg-panel border border-border rounded-xl p-5 space-y-4">
      {/* ヘッダー */}
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full" style={{background:m.color}}/>
        <span className="font-display font-700 text-bright">{m.label}</span>
        <span className="font-mono text-xs text-muted ml-auto">n={s.signal_count}</span>
      </div>

      {/* メイン統計 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <StatCard label="勝率" value={s.win_rate} unit="%" color={
          (s.win_rate||0)>=60?'text-green':(s.win_rate||0)>=50?'text-amber':'text-red'}/>
        <StatCard label="平均リターン" value={s.avg_return} unit="%"
          color={(s.avg_return||0)>=0?'text-green':'text-red'}/>
        <StatCard label="Profit Factor" value={s.profit_factor} unit="x"
          color={(s.profit_factor||0)>=1.5?'text-green':(s.profit_factor||0)>=1?'text-amber':'text-red'}/>
        <StatCard label="期待値" value={s.expectancy} unit="%"
          color={(s.expectancy||0)>=0?'text-green':'text-red'}/>
      </div>

      {/* サブ統計 */}
      <div className="grid grid-cols-3 gap-2 text-center pt-2 border-t border-border">
        {[
          ['平均利益', s.avg_win, '%', 'text-green'],
          ['平均損失', s.avg_loss, '%', 'text-red'],
          ['最大損失', s.max_loss, '%', 'text-red'],
        ].map(([l,v,u,c])=>(
          <div key={l}>
            <div className="font-mono text-xs text-muted">{l}</div>
            <div className={`font-mono text-sm font-700 ${c}`}>
              {v!=null?`${v}${u}`:'—'}
            </div>
          </div>
        ))}
      </div>

      {/* スコア分布 */}
      {method === 'vcp_rs' && distributions?.vcp_rs && (
        <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border">
          <DistributionChart data={distributions.vcp_rs.vcp_bins}
            label="VCPスコア帯別勝率" color={m.color}/>
          <DistributionChart data={distributions.vcp_rs.rs_bins}
            label="RS帯別勝率" color="#3B82F6"/>
        </div>
      )}
      {method === 'ecr' && (
        <div className="pt-2 border-t border-border">
          {distributions?.ecr?.rank_bins && (
            <DistributionChart data={distributions.ecr.rank_bins}
              label="ECRランク帯別勝率" color={m.color}/>
          )}
          {extraStats?.ecr_phase_stats && (
            <div className="mt-3">
              <div className="font-mono text-xs text-muted mb-2">フェーズ別勝率</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(extraStats.ecr_phase_stats).map(([phase, ps]) => (
                  <div key={phase} className="bg-ink rounded-lg p-2.5 text-center">
                    <div className="font-mono text-xs" style={{color:m.color}}>{phase}</div>
                    <div className={`font-mono text-lg font-700 ${ps.win_rate>=55?'text-green':'text-amber'}`}>
                      {ps.win_rate}%
                    </div>
                    <div className="font-mono text-xs text-muted">n={ps.count}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {method === 'canslim' && (
        <div className="pt-2 border-t border-border space-y-3">
          {distributions?.canslim?.score_bins && (
            <DistributionChart data={distributions.canslim.score_bins}
              label="CANSLIMスコア帯別勝率" color={m.color}/>
          )}
          {extraStats?.canslim_grade_stats && (
            <div>
              <div className="font-mono text-xs text-muted mb-2">グレード別勝率</div>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(extraStats.canslim_grade_stats).map(([grade, gs]) => (
                  <div key={grade} className="bg-ink rounded-lg p-2 text-center min-w-[60px]">
                    <div className="font-mono text-xs font-700" style={{color:m.color}}>{grade}</div>
                    <div className={`font-mono text-sm font-700 ${gs.win_rate>=55?'text-green':'text-amber'}`}>
                      {gs.win_rate}%
                    </div>
                    <div className="font-mono text-xs text-muted">n={gs.count}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {method === 'ses' && distributions?.ses?.score_bins && (
        <div className="pt-2 border-t border-border">
          <DistributionChart data={distributions.ses.score_bins}
            label="SESスコア帯別勝率" color={m.color}/>
        </div>
      )}
    </div>
  );
}

// ── メインページ ──────────────────────────────────────────
export default function Backtest() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [holdKey, setHoldKey] = useState('d10');
  const [lang,    setLang]    = useState('ja');
  const [activeMethod, setActiveMethod] = useState('vcp_rs');

  useSEO({
    title: lang==='ja'
      ? 'バックテスト検証 4手法比較 — SENTINEL PRO'
      : 'Backtest Verification 4-Method Comparison — SENTINEL PRO',
    description: lang==='ja'
      ? 'VCP×RS・ECR・CANSLIM・SESの4手法を同一銘柄群で過去1年バックテスト。手法別勝率・期待値・複数手法一致シグナルの優位性を公開。'
      : 'Backtest of 4 strategies (VCP×RS, ECR, CANSLIM, SES) on 120+ tickers. Win rates, expectancy, and multi-method confirmation signals.',
  });

  useEffect(() => {
    fetch('/content/backtest.json')
      .then(r => r.ok ? r.json() : null)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  // 比較チャート用データ
  const compData = data?.comparison?.[holdKey] ?? [];

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-4xl mx-auto">

        {/* AdSense top */}
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
              <FlaskConical size={14} className="text-green"/>
              <span className="font-mono text-xs text-green">BACKTEST / 4-METHOD COMPARISON</span>
            </div>
            <h1 className="font-display font-700 text-bright text-2xl md:text-3xl">
              {lang==='ja' ? '手法別バックテスト検証' : 'Multi-Strategy Backtest'}
            </h1>
            <p className="font-body text-xs text-muted mt-1">
              {lang==='ja'
                ? `120銘柄・過去${data?.lookback_days||365}日 — 4手法を同一条件で検証`
                : `${data?.ticker_count||120} tickers × ${data?.lookback_days||365}d — 4 strategies, same conditions`}
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1 bg-panel border border-border rounded-lg p-0.5">
              {['ja','en'].map(l=>(
                <button key={l} onClick={()=>setLang(l)}
                  className={`px-3 py-1 text-xs font-mono rounded-md transition ${
                    lang===l?'bg-green text-ink font-700':'text-muted hover:text-dim'}`}>
                  {l==='ja'?'日本語':'EN'}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1 bg-panel border border-border rounded-lg p-0.5">
              {[['d5','5日'],['d10','10日'],['d20','20日']].map(([k,lb])=>(
                <button key={k} onClick={()=>setHoldKey(k)}
                  className={`px-3 py-1 text-xs font-mono rounded-md transition ${
                    holdKey===k?'bg-green text-ink font-700':'text-muted hover:text-dim'}`}>
                  {lb}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-6 h-6 border-2 border-green border-t-transparent rounded-full animate-spin"/>
            <p className="font-mono text-xs text-muted">Loading backtest data...</p>
          </div>
        ) : !data ? (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <FlaskConical size={32} className="text-muted mx-auto mb-3"/>
            <p className="font-body text-muted text-sm mb-2">
              {lang==='ja'?'バックテストデータはまだ生成されていません。':'Backtest data not yet generated.'}
            </p>
            <p className="font-mono text-xs text-muted">
              {lang==='ja'?'毎週土曜日に自動更新されます。':'Auto-updated every Saturday.'}
            </p>
          </div>
        ) : (
          <div className="space-y-5">

            {/* ① 手法比較サマリー（一覧） */}
            <div className="bg-panel border border-border rounded-xl p-5">
              <div className="font-mono text-xs text-muted mb-4 flex items-center gap-2">
                <Trophy size={11}/> {lang==='ja'?`手法別勝率比較（${holdKey.replace('d','')}日保有）`:`Win Rate by Method (${holdKey.replace('d','')}d hold)`}
              </div>
              {compData.length > 0 ? (
                <>
                  <div className="space-y-3 mb-4">
                    {compData.map((d, i) => {
                      const wr = d.win_rate || 0;
                      const color = METHODS[d.method]?.color || '#3D4F63';
                      const winColor = wr>=60?'text-green':wr>=50?'text-amber':'text-red';
                      const medal = i===0?'🥇':i===1?'🥈':i===2?'🥉':'';
                      return (
                        <div key={d.method}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-xs text-dim flex items-center gap-1.5">
                              {medal && <span>{medal}</span>}
                              <span style={{color}}>{d.label}</span>
                            </span>
                            <div className="flex items-center gap-3 font-mono text-xs">
                              <span className={`font-700 ${winColor}`}>{wr.toFixed(1)}%</span>
                              <span className={`${(d.avg_return||0)>=0?'text-green':'text-red'}`}>
                                avg {(d.avg_return||0)>=0?'+':''}{d.avg_return}%
                              </span>
                              <span className="text-muted">PF {d.profit_factor}x</span>
                              <span className="text-muted/60">n={d.signal_count}</span>
                            </div>
                          </div>
                          <div className="h-2 bg-border rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all"
                                 style={{width:`${wr}%`, background:color}}/>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {/* バーチャート */}
                  <div className="grid grid-cols-2 gap-4 pt-3 border-t border-border">
                    <MethodComparisonChart data={compData} metric="win_rate"
                      label={lang==='ja'?'勝率 (%)':'Win Rate (%)'} lang={lang}/>
                    <MethodComparisonChart data={compData} metric="avg_return"
                      label={lang==='ja'?'平均リターン (%)':'Avg Return (%)'} lang={lang}/>
                  </div>
                </>
              ) : (
                <p className="font-mono text-xs text-muted text-center py-4">データなし</p>
              )}
            </div>

            {/* ② 複数手法一致の優位性 */}
            {data.multi_method_stats && (
              <div className="bg-panel border border-border rounded-xl p-5">
                <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
                  <Zap size={11} className="text-amber"/>
                  {lang==='ja'
                    ? '複数手法一致シグナルの優位性（10日保有）'
                    : 'Multi-Method Confirmation Advantage (10d hold)'}
                </div>
                <p className="font-body text-xs text-muted mb-3">
                  {lang==='ja'
                    ? '複数の手法が同じ銘柄を同時にシグナル → 信頼度が上がるか？'
                    : 'Do signals confirmed by multiple methods outperform single-method signals?'}
                </p>
                <MultiMethodChart data={data.multi_method_stats} lang={lang}/>
              </div>
            )}

            {/* AdSense mid */}
            <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
              <ins className="adsbygoogle" style={{display:'block',width:'100%'}}
                   data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
                   data-ad-format="horizontal" data-full-width-responsive="true"/>
              <span className="font-mono text-xs text-muted/40">Ad</span>
            </div>

            {/* ③ 手法別詳細タブ */}
            <div>
              <div className="flex gap-1 mb-3 flex-wrap">
                {Object.entries(METHODS).map(([key, m]) => (
                  <button key={key} onClick={() => setActiveMethod(key)}
                    className={`font-mono text-xs px-4 py-2 rounded-lg border transition font-700 ${
                      activeMethod===key
                        ? 'border-transparent text-ink'
                        : 'border-border text-muted hover:text-dim'}`}
                    style={activeMethod===key ? {background:m.color} : {}}>
                    {m.short}
                    {data.method_stats?.[key]?.[holdKey]?.win_rate != null && (
                      <span className="ml-2 opacity-80">
                        {data.method_stats[key][holdKey].win_rate}%
                      </span>
                    )}
                  </button>
                ))}
              </div>
              <MethodDetailPanel
                method={activeMethod}
                stats={data.method_stats}
                distributions={data.distributions}
                extraStats={{
                  ecr_phase_stats:     data.ecr_phase_stats,
                  canslim_grade_stats: data.canslim_grade_stats,
                }}
                holdKey={holdKey}
                lang={lang}
              />
            </div>

            {/* ④ 最新シグナル一覧 */}
            {data.recent_signals?.length > 0 && (
              <div className="bg-panel border border-border rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-border font-mono text-xs text-muted flex items-center gap-2">
                  <TrendingUp size={11}/> {lang==='ja'?'最新シグナル（直近30件）':'Recent Signals (last 30)'}
                </div>
                <div className="divide-y divide-border/30 max-h-80 overflow-y-auto">
                  {data.recent_signals.map((s, i) => {
                    const ret10 = s.returns?.d10;
                    return (
                      <div key={i} className="flex items-center gap-2 px-4 py-2.5 hover:bg-ink/40 transition">
                        <Link to={`/blog/stock-${s.ticker.toLowerCase()}`}
                          className="font-mono text-xs text-bright font-700 w-12 hover:text-green transition">
                          {s.ticker}
                        </Link>
                        <a href={`https://finance.yahoo.com/quote/${s.ticker}`}
                           target="_blank" rel="noopener noreferrer"
                           className="text-amber/50 hover:text-amber transition">
                          <ExternalLink size={8}/>
                        </a>
                        <span className="font-mono text-xs text-muted w-20">{s.date}</span>
                        <div className="flex gap-1 flex-1">
                          {s.methods?.map(m => (
                            <span key={m} className="font-mono text-xs px-1.5 py-0.5 rounded border"
                              style={{
                                color:       METHODS[m]?.color,
                                borderColor: `${METHODS[m]?.color}40`,
                                background:  `${METHODS[m]?.color}10`,
                              }}>
                              {METHODS[m]?.short || m}
                            </span>
                          ))}
                        </div>
                        {ret10 != null && (
                          <span className={`font-mono text-xs font-700 w-14 text-right ${
                            ret10>=0?'text-green':'text-red'}`}>
                            {ret10>=0?'+':''}{ret10}%
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* AdSense bottom */}
            <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[250px] flex items-center justify-center">
              <ins className="adsbygoogle" style={{display:'block'}}
                   data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"/>
              <span className="font-mono text-xs text-muted/40">Ad</span>
            </div>

            {/* 免責 */}
            <div className="p-4 bg-panel border border-border rounded-xl">
              <div className="flex items-start gap-2">
                <AlertTriangle size={12} className="text-amber mt-0.5 flex-shrink-0"/>
                <p className="font-body text-xs text-muted leading-relaxed">
                  {lang==='ja'
                    ? `⚠️ 本バックテストは教育目的です。スリッページ・手数料・税金は未考慮。RS値は全銘柄比較ではなく単銘柄の過去値で近似。過去のパフォーマンスは将来の結果を保証しません。検証期間: 過去${data.lookback_days}日 / 銘柄数: ${data.ticker_count}銘柄 / 総シグナル数: ${data.signal_count_total}件`
                    : `⚠️ Educational purposes only. Excludes slippage, fees, taxes. RS is approximated per-ticker. Past performance ≠ future results. Period: ${data.lookback_days}d / Tickers: ${data.ticker_count} / Total signals: ${data.signal_count_total}`}
                </p>
              </div>
            </div>

            {/* 関連リンク */}
            <div className="grid grid-cols-2 gap-2">
              <Link to="/strategies"
                className="card p-4 hover:border-muted transition group flex items-center gap-2">
                <span className="font-mono text-xs text-dim group-hover:text-green transition">
                  → {lang==='ja'?'手法別ランキング（本日）':'Strategy Rankings (Today)'}
                </span>
              </Link>
              <Link to="/market"
                className="card p-4 hover:border-muted transition group flex items-center gap-2">
                <span className="font-mono text-xs text-dim group-hover:text-green transition">
                  → {lang==='ja'?'指数インパクト分析':'Index Impact Analysis'}
                </span>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
