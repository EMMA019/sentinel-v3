import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Shield, TrendingUp, Zap, BarChart3, ArrowRight,
         ChevronRight, FlaskConical, Activity, Loader } from 'lucide-react';
import { useSEO } from '../hooks/useSEO';

const FEATURES = [
  { icon: BarChart3,  title: 'RS Rating',        body: '全銘柄を相対強度でランク付け。市場の上位銘柄だけをスキャン対象に絞り込む。' },
  { icon: TrendingUp, title: 'VCP スコアリング',  body: 'Mark Minerviniのボラティリティ収縮パターンを定量化。最大105点のスコアで可視化。' },
  { icon: Zap,        title: '毎日自動スキャン',  body: 'GitHub Actionsが600+銘柄を毎日スキャン。翌朝には結果とAI解説記事が更新される。' },
  { icon: FlaskConical,title:'バックテスト公開',  body: '過去1年のシグナル勝率・期待値を全公開。手法の有効性をデータで検証する透明なサイト。' },
];

// バックテストデータをサマリー表示するコンポーネント
function BacktestSummaryCard() {
  const [bt, setBt]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/content/backtest.json')
      .then(r => r.ok ? r.json() : null)
      .then(d => { setBt(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  // データが読み込まれるまでスケルトン表示
  if (loading) return (
    <div className="max-w-lg mx-auto card p-1 overflow-hidden animate-pulse">
      <div className="px-4 py-2 bg-border/40 rounded-t-lg border-b border-border h-9"/>
      <div className="p-5 grid grid-cols-2 gap-4">
        <div className="space-y-3">
          <div className="h-8 bg-border/40 rounded w-24"/>
          <div className="h-4 bg-border/30 rounded w-32"/>
          <div className="space-y-1.5 mt-4">
            {[1,2,3].map(i => <div key={i} className="h-3 bg-border/20 rounded"/>)}
          </div>
        </div>
        <div className="h-32 bg-border/20 rounded"/>
      </div>
    </div>
  );

  // バックテストデータがある場合 → 統計カード
  if (bt?.stats?.d10) {
    const s = bt.stats.d10;
    const winColor = s.win_rate >= 55 ? '#22C55E' : s.win_rate >= 45 ? '#F59E0B' : '#EF4444';
    const retPositive = s.avg_return > 0;

    return (
      <div className="max-w-lg mx-auto card p-1 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 bg-border/40 rounded-t-lg border-b border-border">
          <span className="font-mono text-xs text-dim flex items-center gap-1.5">
            <FlaskConical size={10} className="text-green"/> バックテスト検証データ（過去1年）
          </span>
          <span className="font-mono text-xs text-green flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse-dot"/>LIVE DATA
          </span>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-ink rounded-xl p-3 text-center">
              <div className="font-mono text-xs text-muted">勝率 (10日保有)</div>
              <div className="font-display font-800 text-3xl mt-1" style={{color: winColor}}>
                {s.win_rate}%
              </div>
            </div>
            <div className="bg-ink rounded-xl p-3 text-center">
              <div className="font-mono text-xs text-muted">平均リターン</div>
              <div className={`font-display font-800 text-3xl mt-1 ${retPositive ? 'text-green' : 'text-red'}`}>
                {retPositive ? '+' : ''}{s.avg_return}%
              </div>
            </div>
          </div>
          <div className="space-y-1.5">
            {[
              ['Profit Factor', `${s.profit_factor}x`],
              ['検証シグナル数', `${bt.signal_count}件`],
              ['対象銘柄数',    `${bt.ticker_count}銘柄`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="text-muted font-mono">{k}</span>
                <span className="text-bright font-mono font-700">{v}</span>
              </div>
            ))}
          </div>
          {/* 勝率バー */}
          <div className="mt-3 pt-3 border-t border-border">
            <div className="h-2 rounded-full bg-border overflow-hidden flex">
              <div className="h-full bg-green" style={{width:`${s.win_rate}%`}}/>
              <div className="h-full bg-red"   style={{width:`${100-s.win_rate}%`}}/>
            </div>
            <div className="flex justify-between mt-1 font-mono text-xs">
              <span className="text-green">勝 {s.win_rate}%</span>
              <span className="text-red">負 {(100-s.win_rate).toFixed(1)}%</span>
            </div>
          </div>
        </div>
        <div className="px-4 pb-3">
          <p className="text-xs text-muted font-body">
            ⚠️ 過去データは将来の結果を保証しません。スリッページ・手数料未考慮。教育目的。
          </p>
        </div>
      </div>
    );
  }

  // データなしのフォールバック（初回デプロイ時など）
  return (
    <div className="max-w-lg mx-auto card p-1 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-border/40 rounded-t-lg border-b border-border">
        <span className="font-mono text-xs text-dim flex items-center gap-1.5">
          <FlaskConical size={10} className="text-green"/> 検証データ準備中
        </span>
        <span className="font-mono text-xs text-amber flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-amber"/>PENDING
        </span>
      </div>
      <div className="p-6 text-center">
        <FlaskConical size={28} className="text-muted mx-auto mb-3"/>
        <p className="font-body text-sm text-dim mb-1">バックテストデータを生成中</p>
        <p className="font-mono text-xs text-muted">毎週土曜日に自動更新されます</p>
        <Link to="/backtest" className="inline-flex items-center gap-1 font-mono text-xs text-green mt-3 hover:underline">
          検証ページへ <ChevronRight size={10}/>
        </Link>
      </div>
    </div>
  );
}

export default function Landing() {
  useSEO({
    title: 'SENTINEL PRO — VCP×RSシグナルの定量検証サイト',
    description: 'VCP×RSレーティングシグナルを600+銘柄・過去1年で定量検証。勝率・期待値を全公開。日次・週次レポートと指数インパクト分析も無料で閲覧可能。投資助言ではなく手法検証の教育サイト。',
  });

  const STATS = [
    { value: '600+',  label: 'スキャン銘柄数'     },
    { value: '毎日',  label: '自動更新'           },
    { value: '全公開', label: 'バックテスト統計'   },
    { value: '3指数', label: 'インパクト分析'      },
  ];

  return (
    <div className="min-h-screen bg-ink overflow-hidden">
      <div className="fixed inset-0 bg-grid-pattern bg-grid opacity-40 pointer-events-none"/>
      <div className="fixed inset-0 bg-gradient-to-b from-ink via-transparent to-ink pointer-events-none"/>

      {/* ── Hero ── */}
      <section className="relative pt-32 pb-20 px-4 max-w-6xl mx-auto">
        <div className="flex justify-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                          border border-green/30 bg-green/5 text-xs font-mono text-green">
            <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse-dot"/>
            毎日自動スキャン稼働中 — 600+銘柄 · 勝率データ全公開
          </div>
        </div>

        <h1 className="text-center font-display font-800 text-bright leading-tight mb-6"
            style={{ fontSize: 'clamp(2.4rem, 6vw, 4.5rem)' }}>
          ミネルヴィニ手法を<br/>
          <span className="text-green">データで検証</span>するサイト
        </h1>

        <p className="text-center text-dim font-body max-w-xl mx-auto mb-10 leading-relaxed"
           style={{ fontSize: 'clamp(0.95rem, 2vw, 1.1rem)' }}>
          VCP × RS Rating シグナルの勝率・期待値を過去1年分で公開。<br/>
          <span className="text-text">投資助言ではなく、手法の有効性を定量検証する教育サイトです。</span>
        </p>

        <div className="flex flex-wrap justify-center gap-3 mb-16">
          <Link to="/backtest" className="btn-primary flex items-center gap-2 text-sm">
            バックテスト検証を見る <FlaskConical size={14}/>
          </Link>
          <Link to="/market" className="btn-ghost flex items-center gap-2 text-sm">
            指数インパクト分析 <Activity size={14}/>
          </Link>
        </div>

        {/* バックテスト統計カード（動的） */}
        <BacktestSummaryCard/>
      </section>

      {/* ── Stats ── */}
      <section className="border-y border-border bg-panel/50">
        <div className="max-w-6xl mx-auto px-4 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map(s => (
            <div key={s.label} className="text-center">
              <div className="font-display font-700 text-bright text-2xl">{s.value}</div>
              <div className="font-body text-xs text-dim mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="relative py-20 px-4 max-w-6xl mx-auto">
        <h2 className="font-display font-700 text-center text-bright text-3xl mb-2">コンテンツ概要</h2>
        <p className="text-center text-dim text-sm mb-12">手法検証・市場分析・銘柄スクリーニングを無料公開</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="card p-6 hover:border-muted transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-green/10 border border-green/20
                              flex items-center justify-center mb-4 group-hover:bg-green/20 transition">
                <f.icon size={18} className="text-green"/>
              </div>
              <h3 className="font-display font-600 text-bright mb-2">{f.title}</h3>
              <p className="font-body text-dim text-sm leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── コンテンツ導線 ── */}
      <section className="py-12 px-4 max-w-4xl mx-auto">
        <div className="grid md:grid-cols-3 gap-4">
          {[
            {to:'/backtest', icon:FlaskConical, title:'バックテスト',
             body:'過去1年のシグナル勝率・期待値・スコア別分布をグラフで公開'},
            {to:'/market',   icon:Activity,     title:'指数インパクト分析',
             body:'S&P500・NASDAQ・Russell2000の動きと構成銘柄の寄与をAIが毎日解説'},
            {to:'/blog',     icon:BarChart3,    title:'日次・週次レポート',
             body:'毎営業日のVCPシグナル一覧と週次の市場環境レビューを自動生成'},
          ].map(c => (
            <Link key={c.to} to={c.to}
              className="card p-5 hover:border-muted transition-colors group flex flex-col gap-3">
              <c.icon size={16} className="text-green"/>
              <div>
                <div className="font-display font-700 text-bright text-sm mb-1 group-hover:text-green transition">{c.title}</div>
                <p className="font-body text-xs text-muted leading-relaxed">{c.body}</p>
              </div>
              <div className="mt-auto flex items-center gap-1 font-mono text-xs text-green">
                見る <ChevronRight size={10}/>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-16 px-4">
        <div className="max-w-xl mx-auto card p-8 text-center border-green/20 bg-green/5">
          <div className="font-mono text-xs text-green mb-3">// 完全無料・広告収入で運営</div>
          <h2 className="font-display font-700 text-bright text-2xl mb-3">
            手法の有効性を自分の目で確認する
          </h2>
          <p className="text-dim text-sm mb-6 font-body">
            バックテスト統計・指数インパクト分析・銘柄スクリーニングレポートを<br/>
            すべて無料で公開しています。
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/backtest" className="btn-primary inline-flex items-center gap-2">
              検証データを見る <ArrowRight size={15}/>
            </Link>
            <Link to="/blog" className="btn-ghost inline-flex items-center gap-2">
              レポートを見る <ChevronRight size={15}/>
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border py-8 px-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <Shield size={14} className="text-green"/>
            <span className="font-mono text-xs text-dim">SENTINEL PRO © 2026</span>
          </div>
          <p className="font-body text-xs text-muted text-center max-w-md">
            本サービスは教育・手法検証目的です。投資助言ではありません。
          </p>
          <div className="flex gap-4 text-xs text-muted font-body">
            <Link to="/blog"      className="hover:text-dim transition">Research</Link>
            <Link to="/backtest"  className="hover:text-dim transition">Backtest</Link>
            <Link to="/market"    className="hover:text-dim transition">Market</Link>
            <Link to="/tool"      className="hover:text-dim transition">Tool</Link>
            <Link to="/privacy"   className="hover:text-dim transition">Privacy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
