import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, Minus, AlertCircle, RefreshCw, ExternalLink } from 'lucide-react';

// ── ヘルパー ──────────────────────────────────────────────
const fmt  = (n, d=2) => n != null ? `$${Number(n).toFixed(d)}` : '—';
const pct  = (n)      => n != null ? `${n > 0 ? '+' : ''}${Number(n).toFixed(2)}%` : '—';
const clr  = (n)      => n > 0 ? 'text-green' : n < 0 ? 'text-red' : 'text-dim';

function ScoreBar({ value, max = 105, color = 'bg-green' }) {
  const w = Math.round((value / max) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-border rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${w}%` }} />
      </div>
      <span className="font-mono text-xs text-dim w-8 text-right">{value}</span>
    </div>
  );
}

function IndexCard({ name, data }) {
  if (!data) return null;
  const r = data.ret_1d;
  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className="text-dim font-mono text-xs mb-1">{name}</div>
      <div className={`font-mono text-xl font-bold ${clr(r)}`}>{pct(r)}</div>
      <div className="flex gap-3 mt-2 text-xs text-muted font-mono">
        <span>5d <span className={clr(data.ret_5d)}>{pct(data.ret_5d)}</span></span>
        <span>1m <span className={clr(data.ret_1m)}>{pct(data.ret_1m)}</span></span>
      </div>
    </div>
  );
}

function TickerRow({ t, idx }) {
  const rr = t._stop && t._entry
    ? ((t._target - t._entry) / (t._entry - t._stop)).toFixed(1)
    : null;

  return (
    <div className="grid grid-cols-12 gap-2 px-4 py-3 border-b border-border/50 hover:bg-panel/60 transition group">
      {/* 番号 + ティッカー */}
      <div className="col-span-3 flex items-center gap-2">
        <span className="text-muted font-mono text-xs w-5">{idx + 1}</span>
        <div>
          <Link
            to={`/realtime/${t.ticker}`}
            className="font-mono font-bold text-bright text-sm hover:text-green transition flex items-center gap-1"
          >
            {t.ticker}
            <ExternalLink size={10} className="opacity-0 group-hover:opacity-60 transition" />
          </Link>
          <div className="text-muted text-xs truncate">{t.name}</div>
        </div>
      </div>

      {/* 現在値 */}
      <div className="col-span-2 flex flex-col justify-center">
        <div className="font-mono text-sm text-bright">{fmt(t._price)}</div>
        <div className="text-muted text-xs">{t.sector?.split(' ')[0]}</div>
      </div>

      {/* エントリー / ストップ / ターゲット */}
      <div className="col-span-4 hidden md:flex flex-col gap-0.5 justify-center font-mono text-xs">
        <div className="flex gap-2">
          <span className="text-muted w-8">Entry</span>
          <span className="text-green font-bold">{fmt(t._entry)}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-muted w-8">Stop</span>
          <span className="text-red">{fmt(t._stop)}</span>
          {t._entry && t._stop && (
            <span className="text-muted">({((t._stop - t._entry) / t._entry * 100).toFixed(1)}%)</span>
          )}
        </div>
        <div className="flex gap-2">
          <span className="text-muted w-8">Tgt</span>
          <span className="text-amber">{fmt(t._target)}</span>
          {rr && <span className="text-muted">RR 1:{rr}</span>}
        </div>
      </div>

      {/* スコア */}
      <div className="col-span-3 flex flex-col gap-1 justify-center">
        <div className="flex items-center gap-1">
          <span className="text-muted font-mono text-[10px] w-5">VCP</span>
          <ScoreBar value={t.vcp} max={105} color="bg-green" />
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted font-mono text-[10px] w-5">RS</span>
          <ScoreBar value={t.rs} max={99} color="bg-blue" />
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted font-mono text-[10px] w-5">C</span>
          <ScoreBar value={t.canslim_score || 0} max={100} color="bg-purple" />
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────
export default function Dashboard() {
  const [daily,   setDaily]   = useState(null);
  const [market,  setMarket]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [showAll, setShowAll] = useState(false);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      // 最新のdailyファイルを取得
      const idx = await fetch('/content/index.json').then(r => r.json());
      const latest = idx.articles?.[0];
      if (!latest) throw new Error('No articles found');

      const [d, m] = await Promise.all([
        fetch(`/content/${latest.slug}.json`).then(r => r.json()),
        fetch('/content/market.json').then(r => r.json()),
      ]);
      setDaily(d);
      setMarket(m);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="font-mono text-green animate-pulse">LOADING...</div>
    </div>
  );

  if (error) return (
    <div className="p-6 flex items-center gap-3 text-red font-mono text-sm">
      <AlertCircle size={16} /> {error}
    </div>
  );

  const actions = daily?.data?.actions || [];
  const visible = showAll ? actions : actions.slice(0, 20);
  const idx     = market?.indices || {};

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">

      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-green text-xl font-bold glow-green">
            {daily?.date} REPORT
          </h1>
          <p className="text-muted text-sm mt-0.5">
            ACTION <span className="text-green font-bold">{daily?.data?.action_count}</span>銘柄
            &nbsp;/ WAIT <span className="text-amber">{daily?.data?.wait_count}</span>銘柄
          </p>
        </div>
        <button onClick={load} className="p-2 text-muted hover:text-text transition rounded-lg hover:bg-panel">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* 指数 */}
      <div className="grid grid-cols-3 gap-3">
        {Object.entries(idx).map(([k, v]) => (
          <IndexCard key={k} name={v.label || k} data={v.performance} />
        ))}
      </div>

      {/* セクター上位 */}
      {daily?.data?.sector?.length > 0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="text-dim font-mono text-xs mb-3">SECTOR STRENGTH</div>
          <div className="flex flex-wrap gap-2">
            {daily.data.sector.slice(0, 6).map((s, i) => (
              <div key={i} className="bg-ink border border-border rounded-lg px-3 py-1.5">
                <div className="font-mono text-xs text-bright">{s.sector}</div>
                <div className="font-mono text-xs text-green">VCP avg {s.avg_vcp}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ACTION銘柄リスト */}
      <div className="bg-panel border border-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <div className="font-mono text-sm text-bright font-bold">
            🟢 ACTION銘柄 — 価格・エントリー全表示
          </div>
          <div className="text-muted font-mono text-xs">{actions.length}銘柄</div>
        </div>

        {/* テーブルヘッダー */}
        <div className="grid grid-cols-12 gap-2 px-4 py-2 border-b border-border/50 text-muted font-mono text-xs">
          <div className="col-span-3">Ticker</div>
          <div className="col-span-2">Price</div>
          <div className="col-span-4 hidden md:block">Entry / Stop / Target</div>
          <div className="col-span-3">Score</div>
        </div>

        {visible.map((t, i) => (
          <TickerRow key={t.ticker} t={t} idx={i} />
        ))}

        {!showAll && actions.length > 20 && (
          <button
            onClick={() => setShowAll(true)}
            className="w-full py-3 text-muted font-mono text-xs hover:text-text transition hover:bg-panel/50 border-t border-border"
          >
            + {actions.length - 20}銘柄をさらに表示
          </button>
        )}
      </div>

      {/* AI分析コメント（日本語） */}
      {daily?.ja?.body && (
        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="font-mono text-xs text-muted mb-3">AI ANALYSIS</div>
          <div className="text-text text-sm leading-relaxed whitespace-pre-wrap">
            {daily.ja.body.replace(/##[^\n]*/g, '').trim()}
          </div>
        </div>
      )}

    </div>
  );
}
