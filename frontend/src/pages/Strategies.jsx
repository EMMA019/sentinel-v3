import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, CartesianGrid,
} from 'recharts';
import { useSEO } from '../hooks/useSEO';
import { FlaskConical, Zap, TrendingUp, Award, ExternalLink,
         ChevronRight, Activity } from 'lucide-react';

// ── 手法の定義 ────────────────────────────────────────────
const METHODS = {
  vcp_rs: {
    key:   'vcp_rs',
    label: 'VCP × RS',
    icon:  TrendingUp,
    color: '#22C55E',
    desc:  'Mark Minerviniのボラティリティ収縮パターン × 相対強度。収縮後のブレイクアウトを狙う。',
    scoreKey: r => r.scores.vcp * 0.5 + r.scores.rs * 0.5,
    badges: ['ブレイクアウト', 'トレンドフォロー', 'ミネルヴィニ系'],
  },
  ecr: {
    key:   'ecr',
    label: 'ECR（エネルギー圧縮）',
    icon:  Zap,
    color: '#3B82F6',
    desc:  'VCP×SES×RSの複合スコア。機関の買い集め（ACCUMULATION）→初動（IGNITION）のフェーズを検出。',
    scoreKey: r => r.scores.ecr_rank,
    badges: ['機関投資家', 'フェーズ検出', '複合スコア'],
  },
  canslim: {
    key:   'canslim',
    label: 'CANSLIM簡易版',
    icon:  Award,
    color: '#F59E0B',
    desc:  "William O'Neil手法。利益成長・売上成長・新高値・出来高・RSの5軸で評価。",
    scoreKey: r => r.scores.canslim,
    badges: ['ファンダ×テクニカル', 'オニール系', '成長株'],
  },
  ses: {
    key:   'ses',
    label: 'SES（効率性）',
    icon:  Activity,
    color: '#8B5CF6',
    desc:  '価格の効率的な動き(ER)×出来高圧力×ボラ収縮×バークオリティ。機関の買い集めを純粋に定量化。',
    scoreKey: r => r.scores.ses,
    badges: ['機関検出', 'ノイズ除去', 'フラクタル'],
  },
  composite: {
    key:   'composite',
    label: '総合スコア',
    icon:  FlaskConical,
    color: '#EC4899',
    desc:  '全手法を加重平均（VCP×RS 35% + ECR 35% + CANSLIM 30%）。複数手法で上位 = 最高信頼度。',
    scoreKey: r => r.scores.composite,
    badges: ['複数手法合議', '最高信頼度', '総合'],
  },
};

// ── ECRフェーズの定義 ──────────────────────────────────────
const ECR_PHASES = {
  ACCUMULATION: { color: '#22C55E', label: 'ACCUMULATION', desc: '高ランク+低ボラ+ピボット圏。最も注目すべきフェーズ。' },
  IGNITION:     { color: '#3B82F6', label: 'IGNITION',     desc: 'ランク急上昇または出来高を伴う初動。' },
  RELEASE:      { color: '#F59E0B', label: 'RELEASE',      desc: 'ピボット突破済みでモメンタム鈍化。トレーリング戦略。' },
  'HOLD/WATCH': { color: '#6B7280', label: 'HOLD/WATCH',   desc: 'ランク65以上だが条件未達。継続監視。' },
  WATCH:        { color: '#374151', label: 'WATCH',        desc: '監視圏内。' },
};

// ── DarkTooltip ──────────────────────────────────────────
const DarkTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-ink border border-border rounded-lg px-3 py-2 font-mono text-xs space-y-0.5">
      {label && <div className="text-muted mb-1">{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || '#EBF4FF' }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </div>
      ))}
    </div>
  );
};

// ── 銘柄ランキング行 ──────────────────────────────────────
function RankRow({ rank, r, activeMethod, lang }) {
  const m = METHODS[activeMethod];
  const score = m ? Math.round(m.scoreKey(r)) : r.scores.composite;
  const phase = ECR_PHASES[r.ecr_phase] ?? ECR_PHASES.WATCH;
  return (
    <div className="grid grid-cols-[28px_72px_1fr_64px_64px_80px] gap-2 px-4 py-2.5
                    hover:bg-panel/60 transition group items-center border-b border-border/30 last:border-0">
      <span className="font-mono text-xs text-muted">{rank}</span>
      <div className="flex items-center gap-1">
        <Link to={`/blog/stock-${r.ticker.toLowerCase()}`}
          className="font-mono text-xs text-bright font-700 group-hover:text-green transition">
          {r.ticker}
        </Link>
        <a href={`https://finance.yahoo.com/quote/${r.ticker}`}
           target="_blank" rel="noopener noreferrer"
           className="text-amber/50 hover:text-amber transition">
          <ExternalLink size={8}/>
        </a>
      </div>
      <span className="font-body text-xs text-muted truncate">{r.name}</span>
      {/* スコアバー */}
      <div className="flex items-center gap-1">
        <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all"
               style={{ width: `${Math.min(100, score)}%`, background: m?.color ?? '#EC4899' }}/>
        </div>
        <span className="font-mono text-xs font-700 w-5 text-right" style={{ color: m?.color ?? '#EC4899' }}>
          {score}
        </span>
      </div>
      {/* ECRフェーズ */}
      <span className="font-mono text-xs px-1.5 py-0.5 rounded text-center border"
            style={{ color: phase.color, borderColor: `${phase.color}40`, background: `${phase.color}10` }}>
        {r.ecr_phase?.replace('HOLD/WATCH','H/W') ?? '—'}
      </span>
      {/* ステータス */}
      <span className={`font-mono text-xs px-1.5 py-0.5 rounded text-center border ${
        r.status === 'ACTION'
          ? 'bg-green/10 border-green/20 text-green'
          : 'bg-amber/10 border-amber/20 text-amber'}`}>
        {r.status}
      </span>
    </div>
  );
}

// ── 手法比較レーダーチャート ──────────────────────────────
function MethodRadar({ rankings, ticker }) {
  if (!rankings || !ticker) return null;
  // 指定ティッカーの各手法スコアを集める
  const allData = Object.values(rankings).flat();
  const found   = allData.find(r => r.ticker === ticker);
  if (!found) return null;

  const radarData = [
    { axis: 'VCP×RS',  val: Math.round(found.scores.vcp * 0.5 + found.scores.rs * 0.5) },
    { axis: 'ECR',     val: found.scores.ecr_rank },
    { axis: 'CANSLIM', val: found.scores.canslim },
    { axis: 'SES',     val: found.scores.ses },
    { axis: '総合',    val: Math.round(found.scores.composite) },
  ];

  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className="font-mono text-xs text-muted mb-2">{ticker} — 手法別スコアレーダー</div>
      <ResponsiveContainer width="100%" height={200}>
        <RadarChart data={radarData}>
          <PolarGrid stroke="#1C2530"/>
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 9, fill: '#7A90A8' }}/>
          <Radar dataKey="val" stroke="#22C55E" fill="#22C55E" fillOpacity={0.2}/>
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── 手法比較バーチャート ──────────────────────────────────
function MethodCompareChart({ data, lang }) {
  if (!data?.length) return null;
  const chartData = data.map(d => ({
    method:  d.method,
    VCP_RS:  d.avg_scores.vcp,
    ECR:     d.avg_scores.ecr,
    CANSLIM: d.avg_scores.canslim,
    SES:     d.avg_scores.ses,
  }));
  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className="font-mono text-xs text-muted mb-1">
        {lang === 'ja' ? '各手法の上位20銘柄は他の手法でどのスコアか' : 'How does each strategy\'s top-20 score on other strategies?'}
      </div>
      <p className="font-body text-xs text-muted/70 mb-3">
        {lang === 'ja'
          ? '複数手法で高スコアを出す手法 = 銘柄の質が高い傾向'
          : 'Higher cross-method scores = higher quality picks'}
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 0, right: 8, bottom: 0, left: -12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1C2530" vertical={false}/>
          <XAxis dataKey="method" tick={{ fontSize: 8, fill: '#3D4F63' }} tickLine={false} axisLine={false}/>
          <YAxis tick={{ fontSize: 8, fill: '#3D4F63' }} tickLine={false} axisLine={false} domain={[0, 100]}/>
          <Tooltip content={<DarkTooltip/>}/>
          <Bar dataKey="VCP_RS"  name="VCP×RS"  fill="#22C55E" radius={[3,3,0,0]} fillOpacity={0.8}/>
          <Bar dataKey="ECR"     name="ECR"     fill="#3B82F6" radius={[3,3,0,0]} fillOpacity={0.8}/>
          <Bar dataKey="CANSLIM" name="CANSLIM" fill="#F59E0B" radius={[3,3,0,0]} fillOpacity={0.8}/>
          <Bar dataKey="SES"     name="SES"     fill="#8B5CF6" radius={[3,3,0,0]} fillOpacity={0.8}/>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── ECRフェーズサマリー ───────────────────────────────────
function ECRPhasePanel({ phases, lang }) {
  if (!phases) return null;
  const order = ['ACCUMULATION', 'IGNITION', 'RELEASE', 'HOLD/WATCH'];
  return (
    <div className="bg-panel border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-border">
        <div className="font-mono text-xs text-blue mb-1 flex items-center gap-1.5">
          <Zap size={11}/> ECR フェーズ分析
        </div>
        <div className="font-display font-700 text-bright text-sm">
          {lang === 'ja' ? '機関投資家の行動フェーズ別銘柄' : 'Stocks by Institutional Activity Phase'}
        </div>
      </div>
      <div className="p-4 space-y-4">
        {order.map(p => {
          const def   = ECR_PHASES[p] ?? ECR_PHASES.WATCH;
          const items = phases[p] ?? [];
          if (!items.length) return null;
          return (
            <div key={p}>
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-xs font-700 px-2 py-0.5 rounded border"
                      style={{ color: def.color, borderColor: `${def.color}40`, background: `${def.color}10` }}>
                  {def.label}
                </span>
                <span className="font-body text-xs text-muted">{def.desc}</span>
                <span className="font-mono text-xs text-muted ml-auto">{items.length}銘柄</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {items.slice(0, 10).map(item => (
                  <Link key={item.ticker} to={`/blog/stock-${item.ticker.toLowerCase()}`}
                    className="font-mono text-xs px-2 py-1 rounded-lg border border-border
                               hover:border-muted transition group flex items-center gap-1">
                    <span className="text-bright group-hover:text-green transition">{item.ticker}</span>
                    <span className="text-muted/60">{item.ecr_rank}</span>
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── コンセンサスパネル（複数手法で上位） ─────────────────
function ConsensusPanel({ items, lang }) {
  if (!items?.length) return null;
  return (
    <div className="bg-panel border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-border">
        <div className="font-mono text-xs text-pink-400 mb-1 flex items-center gap-1.5">
          <FlaskConical size={11}/> コンセンサス銘柄
        </div>
        <div className="font-display font-700 text-bright text-sm">
          {lang === 'ja'
            ? '複数手法で同時に上位 — 最高信頼度ランキング'
            : 'Top-ranked by multiple strategies — Highest confidence'}
        </div>
        <p className="font-body text-xs text-muted mt-1">
          {lang === 'ja'
            ? 'VCP×RS・ECR・CANSLIMのうち複数で上位に登場する銘柄。手法を問わず強い。'
            : 'Stocks appearing in top rankings across VCP×RS, ECR, and CANSLIM simultaneously.'}
        </p>
      </div>
      <div className="divide-y divide-border/30">
        {items.slice(0, 15).map((r, i) => (
          <div key={r.ticker}
            className="grid grid-cols-[28px_72px_1fr_48px_80px] gap-2 px-4 py-2.5 hover:bg-ink/40 transition items-center">
            <span className="font-mono text-xs text-muted">{i + 1}</span>
            <div className="flex items-center gap-1">
              <Link to={`/blog/stock-${r.ticker.toLowerCase()}`}
                className="font-mono text-xs text-bright font-700 hover:text-green transition">{r.ticker}</Link>
              <a href={`https://finance.yahoo.com/quote/${r.ticker}`}
                 target="_blank" rel="noopener noreferrer"
                 className="text-amber/50 hover:text-amber transition"><ExternalLink size={8}/></a>
            </div>
            <span className="font-body text-xs text-muted truncate">{r.name}</span>
            {/* 手法ヒット数バッジ */}
            <div className="flex gap-0.5">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className={`w-2 h-2 rounded-full ${j < r.method_hits ? 'bg-pink-400' : 'bg-border'}`}/>
              ))}
            </div>
            <span className={`font-mono text-xs px-1.5 py-0.5 rounded border text-center ${
              r.status === 'ACTION'
                ? 'bg-green/10 border-green/20 text-green'
                : 'bg-amber/10 border-amber/20 text-amber'}`}>
              {r.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── メインページ ─────────────────────────────────────────
export default function Strategies() {
  const [data,         setData]         = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [activeMethod, setActiveMethod] = useState('composite');
  const [radarTicker,  setRadarTicker]  = useState('');
  const [lang,         setLang]         = useState('ja');

  useSEO({
    title: lang === 'ja'
      ? '投資手法比較・戦略ランキング — SENTINEL PRO'
      : 'Strategy Comparison & Rankings — SENTINEL PRO',
    description: lang === 'ja'
      ? 'VCP×RS・ECR（エネルギー圧縮）・CANSLIM・SES（効率性）の4手法を同一銘柄に適用し定量比較。複数手法で上位に来る高信頼度銘柄を公開。'
      : 'Compare 4 strategies (VCP×RS, ECR, CANSLIM, SES) applied to the same stocks. Find stocks ranking high across multiple strategies.',
    lang,
  });

  useEffect(() => {
    fetch('/content/strategies.json')
      .then(r => r.ok ? r.json() : null)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const rankings = data?.rankings ?? {};
  const activeList = rankings[activeMethod] ?? [];

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-4xl mx-auto">

        {/* AdSense */}
        <div className="mb-6 rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{ display: 'block', width: '100%' }}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
               data-ad-format="horizontal" data-full-width-responsive="true"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>

        {/* ヘッダー */}
        <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FlaskConical size={14} className="text-green"/>
              <span className="font-mono text-xs text-green">STRATEGIES / COMPARISON</span>
            </div>
            <h1 className="font-display font-700 text-bright text-2xl md:text-3xl">
              {lang === 'ja' ? '投資手法 比較・検証' : 'Strategy Comparison'}
            </h1>
            <p className="font-body text-xs text-muted mt-1">
              {lang === 'ja'
                ? '4つの手法を同一銘柄に適用して比較。どの手法で上位か、複数手法での総合評価を公開。'
                : 'Apply 4 strategies to the same stocks. See which leads each ranking and the composite score.'}
            </p>
          </div>
          <div className="flex items-center gap-1 bg-panel border border-border rounded-lg p-0.5">
            {['ja', 'en'].map(l => (
              <button key={l} onClick={() => setLang(l)}
                className={`px-3 py-1 text-xs font-mono rounded-md transition ${
                  lang === l ? 'bg-green text-ink font-700' : 'text-muted hover:text-dim'}`}>
                {l === 'ja' ? '日本語' : 'English'}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-6 h-6 border-2 border-green border-t-transparent rounded-full animate-spin"/>
            <p className="font-mono text-xs text-muted">Loading strategy data...</p>
          </div>
        ) : !data ? (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <FlaskConical size={32} className="text-muted mx-auto mb-3"/>
            <p className="font-body text-muted text-sm mb-2">
              {lang === 'ja' ? '手法比較データはまだ生成されていません。' : 'Strategy data not yet generated.'}
            </p>
            <p className="font-mono text-xs text-muted">
              {lang === 'ja' ? '毎営業日 JST15時に自動更新されます。' : 'Auto-updated every trading day.'}
            </p>
          </div>
        ) : (
          <div className="space-y-5">

            {/* サマリー */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-panel border border-border rounded-xl p-4 text-center">
                <div className="font-mono text-xs text-muted">スキャン銘柄</div>
                <div className="font-display text-2xl font-700 text-bright mt-1">{data.ticker_count}</div>
              </div>
              <div className="bg-panel border border-border rounded-xl p-4 text-center">
                <div className="font-mono text-xs text-muted">ACTION銘柄</div>
                <div className="font-display text-2xl font-700 text-green mt-1">{data.action_count}</div>
              </div>
              <div className="bg-panel border border-border rounded-xl p-4 text-center">
                <div className="font-mono text-xs text-muted">手法数</div>
                <div className="font-display text-2xl font-700 text-blue mt-1">4</div>
              </div>
            </div>

            {/* 手法選択タブ */}
            <div className="flex flex-wrap gap-2">
              {Object.values(METHODS).map(m => {
                const Icon = m.icon;
                return (
                  <button key={m.key} onClick={() => setActiveMethod(m.key)}
                    className={`flex items-center gap-1.5 font-mono text-xs px-3 py-2 rounded-lg border transition ${
                      activeMethod === m.key
                        ? 'text-ink font-700 border-transparent'
                        : 'border-border text-muted hover:text-dim'}`}
                    style={activeMethod === m.key ? { background: m.color } : {}}>
                    <Icon size={11}/>
                    {m.label}
                    <span className={`text-xs ${activeMethod === m.key ? 'text-ink/60' : 'text-muted/60'}`}>
                      ({(rankings[m.key] ?? []).length})
                    </span>
                  </button>
                );
              })}
            </div>

            {/* アクティブ手法の説明 */}
            {METHODS[activeMethod] && (
              <div className="bg-panel border border-border rounded-xl p-4">
                <div className="flex items-start gap-3">
                  {(() => { const Icon = METHODS[activeMethod].icon; return <Icon size={14} style={{ color: METHODS[activeMethod].color }} className="mt-0.5 flex-shrink-0"/>; })()}
                  <div>
                    <div className="font-display font-700 text-bright text-sm mb-1">{METHODS[activeMethod].label}</div>
                    <p className="font-body text-xs text-muted leading-relaxed">{METHODS[activeMethod].desc}</p>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {METHODS[activeMethod].badges.map(b => (
                        <span key={b} className="font-mono text-xs px-2 py-0.5 rounded border border-border text-muted">{b}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ランキングテーブル */}
            <div className="bg-panel border border-border rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <span className="font-mono text-xs text-muted">
                  {METHODS[activeMethod]?.label} ランキング
                </span>
                <span className="font-mono text-xs text-muted">
                  Score / ECRフェーズ / Status
                </span>
              </div>
              <div className="grid grid-cols-[28px_72px_1fr_64px_64px_80px] gap-2 px-4 py-2 border-b border-border/50">
                {['#', 'Ticker', 'Name', 'Score', 'Phase', 'Status'].map(h => (
                  <span key={h} className="font-mono text-xs text-muted">{h}</span>
                ))}
              </div>
              {activeList.length === 0 ? (
                <div className="p-8 text-center font-mono text-xs text-muted">データなし</div>
              ) : (
                activeList.map((r, i) => (
                  <RankRow key={r.ticker} rank={i + 1} r={r} activeMethod={activeMethod} lang={lang}/>
                ))
              )}
            </div>

            {/* AdSense mid */}
            <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
              <ins className="adsbygoogle" style={{ display: 'block', width: '100%' }}
                   data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
                   data-ad-format="horizontal" data-full-width-responsive="true"/>
              <span className="font-mono text-xs text-muted/40">Ad</span>
            </div>

            {/* 手法比較チャート */}
            <MethodCompareChart data={data.method_comparison} lang={lang}/>

            {/* ECRフェーズパネル */}
            <ECRPhasePanel phases={data.ecr_phases} lang={lang}/>

            {/* コンセンサス */}
            <ConsensusPanel items={rankings.consensus} lang={lang}/>

            {/* レーダーチャート（ティッカー検索） */}
            <div className="bg-panel border border-border rounded-xl p-4">
              <div className="font-mono text-xs text-muted mb-3">
                {lang === 'ja' ? '銘柄別 手法レーダーチャート' : 'Per-stock Strategy Radar'}
              </div>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  placeholder="NVDA"
                  value={radarTicker}
                  onChange={e => setRadarTicker(e.target.value.toUpperCase())}
                  className="font-mono text-xs bg-ink border border-border rounded-lg px-3 py-2 text-bright w-32
                             focus:outline-none focus:border-green transition"
                />
                <span className="font-mono text-xs text-muted self-center">
                  {lang === 'ja' ? 'のレーダーを表示' : '— show radar'}
                </span>
              </div>
              {radarTicker && (
                <MethodRadar rankings={rankings} ticker={radarTicker}/>
              )}
            </div>

            {/* AdSense bottom */}
            <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[250px] flex items-center justify-center">
              <ins className="adsbygoogle" style={{ display: 'block' }}
                   data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"/>
              <span className="font-mono text-xs text-muted/40">Ad</span>
            </div>

            {/* 免責 */}
            <div className="p-4 bg-panel border border-border rounded-xl">
              <p className="font-body text-xs text-muted leading-relaxed">
                {lang === 'ja'
                  ? `⚠️ 本ページは複数の投資手法ロジックを定量的に比較する教育コンテンツです。スコアはすべて独自ロジックによる派生データであり、生の株価データではありません。手法の有効性は相場環境により変動します。過去のランキングは将来の結果を保証しません。投資助言ではありません。最終更新: ${data.generated_at}`
                  : `⚠️ Educational content comparing quantitative strategy logic. All scores are derived data from proprietary algorithms, not raw price data. Strategy effectiveness varies with market conditions. Not investment advice. Last updated: ${data.generated_at}`}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
