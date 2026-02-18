import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, ExternalLink, ChevronDown, ChevronUp, SlidersHorizontal } from 'lucide-react';

const fmt = (n, d=2) => n != null ? `$${Number(n).toFixed(d)}` : '—';

function ScoreChip({ label, value, max, color }) {
  const w = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-muted">{label}</span>
        <span className={`font-mono text-[10px] font-bold ${color}`}>{value}</span>
      </div>
      <div className="h-0.5 bg-border rounded-full">
        <div className={`h-full rounded-full ${color.replace('text-', 'bg-')}`} style={{ width: `${w}%` }} />
      </div>
    </div>
  );
}

function TickerRow({ t, expanded, onToggle }) {
  const rr = t._stop && t._entry
    ? ((t._target - t._entry) / (t._entry - t._stop)).toFixed(1) : null;

  return (
    <>
      <div
        className={`grid grid-cols-12 gap-2 px-4 py-3 border-b border-border/50 cursor-pointer transition ${
          expanded ? 'bg-panel' : 'hover:bg-panel/40'
        }`}
        onClick={onToggle}
      >
        {/* Ticker + status */}
        <div className="col-span-3 flex items-center gap-2">
          <span className={t.status === 'ACTION' ? 'badge-action' : 'badge-wait'}>
            {t.status}
          </span>
          <Link to={`/realtime/${t.ticker}`} onClick={(e) => e.stopPropagation()}>
            <div className="font-mono font-bold text-bright text-sm hover:text-green transition">{t.ticker}</div>
            <div className="text-muted text-xs truncate w-24">{t.name}</div>
          </Link>
        </div>

        {/* Price */}
        <div className="col-span-2 flex items-center">
          <div className="font-mono text-sm text-bright">{fmt(t._price)}</div>
        </div>

        {/* VCP / RS */}
        <div className="col-span-2 flex flex-col gap-1 justify-center">
          <div className="flex items-center gap-1 font-mono text-xs">
            <span className="text-muted w-6">VCP</span>
            <span className="text-green font-bold">{t.vcp}</span>
          </div>
          <div className="flex items-center gap-1 font-mono text-xs">
            <span className="text-muted w-6">RS</span>
            <span className="text-blue font-bold">{t.rs}</span>
          </div>
        </div>

        {/* composite */}
        <div className="col-span-2 flex items-center">
          <div className="font-mono text-lg font-bold text-bright">{t.composite?.toFixed(1)}</div>
        </div>

        {/* sector */}
        <div className="col-span-2 flex items-center">
          <span className="text-dim text-xs">{t.sector?.split(' ')[0]}</span>
        </div>

        {/* expand */}
        <div className="col-span-1 flex items-center justify-end">
          {expanded ? <ChevronUp size={14} className="text-muted" /> : <ChevronDown size={14} className="text-muted" />}
        </div>
      </div>

      {/* 展開詳細 */}
      {expanded && (
        <div className="bg-ink/60 px-4 py-4 border-b border-border grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* トレードライン */}
          <div className="col-span-2 md:col-span-1 space-y-1.5 font-mono text-sm">
            <div className="text-muted text-xs mb-2">📐 トレードライン</div>
            <div className="flex justify-between">
              <span className="text-muted text-xs">Entry</span>
              <span className="text-green font-bold">{fmt(t._entry)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted text-xs">Stop</span>
              <span className="text-red">{fmt(t._stop)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted text-xs">Target</span>
              <span className="text-amber">{fmt(t._target)}</span>
            </div>
            {rr && (
              <div className="flex justify-between">
                <span className="text-muted text-xs">RR</span>
                <span className="text-bright">1:{rr}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted text-xs">ATR%</span>
              <span className="text-dim">{t.atr_pct}%</span>
            </div>
          </div>

          {/* スコア詳細 */}
          <div className="space-y-2">
            <div className="text-muted text-xs mb-2 font-mono">📊 スコア</div>
            <ScoreChip label="VCP"      value={t.vcp}             max={105} color="text-green"  />
            <ScoreChip label="RS"       value={t.rs}              max={99}  color="text-blue"   />
            <ScoreChip label="SES"      value={t.ses}             max={100} color="text-purple" />
            <ScoreChip label="CANSLIM"  value={t.canslim_score}   max={100} color="text-amber"  />
            <ScoreChip label="ECR"      value={t.ecr_rank}        max={100} color="text-green"  />
          </div>

          {/* ECR / CANSLIM */}
          <div className="space-y-2 font-mono text-xs">
            <div className="text-muted mb-2">🔬 詳細</div>
            <div><span className="text-muted">ECR Phase:</span> <span className="text-bright">{t.ecr_phase}</span></div>
            <div><span className="text-muted">CANSLIM:</span> <span className="text-amber font-bold">{t.canslim_grade}</span></div>
            <div><span className="text-muted">PF:</span> <span className="text-dim">{t.pf}</span></div>
            <div><span className="text-muted">ma50:</span> <span className="text-dim">{t.ma50_ratio != null ? `+${t.ma50_ratio}%` : '—'}</span></div>
            <div><span className="text-muted">Pivot dist:</span> <span className="text-dim">{t.pivot_dist_pct}%</span></div>
          </div>

          {/* VCPシグナル + リンク */}
          <div className="space-y-2">
            <div className="text-muted text-xs mb-2 font-mono">⚡ VCPシグナル</div>
            <div className="space-y-1">
              {(t.vcp_detail?.signals || []).map((s, i) => (
                <div key={i} className="text-green font-mono text-xs flex items-center gap-1">
                  <span className="text-green/60">›</span> {s}
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-3">
              <a href={`https://finance.yahoo.com/quote/${t.ticker}`} target="_blank" rel="noopener noreferrer"
                className="text-muted hover:text-text font-mono text-xs transition flex items-center gap-1">
                Yahoo <ExternalLink size={9} />
              </a>
              <a href={`https://www.tradingview.com/chart/?symbol=${t.ticker}`} target="_blank" rel="noopener noreferrer"
                className="text-muted hover:text-text font-mono text-xs transition flex items-center gap-1">
                TV <ExternalLink size={9} />
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ── Scanner ───────────────────────────────────────────────
export default function Scanner() {
  const [data,     setData]     = useState(null);
  const [search,   setSearch]   = useState('');
  const [minVcp,   setMinVcp]   = useState(0);
  const [minRs,    setMinRs]    = useState(0);
  const [status,   setStatus]   = useState('ALL');
  const [sortKey,  setSortKey]  = useState('composite');
  const [expanded, setExpanded] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetch('/content/strategies.json')
      .then(r => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return (
    <div className="flex items-center justify-center h-64 font-mono text-green animate-pulse">LOADING...</div>
  );

  // strategies.json の rankings.vcp_rs と daily の actions をマージ
  // strategies.jsonにある全銘柄を表示
  const all = data.rankings?.vcp_rs || [];

  // フィルタ・ソート
  const filtered = all
    .filter(t =>
      (search === '' || t.ticker.includes(search.toUpperCase()) || t.name?.toLowerCase().includes(search.toLowerCase())) &&
      (t.scores?.vcp >= minVcp) &&
      (t.scores?.rs  >= minRs)  &&
      (status === 'ALL' || t.status === status)
    )
    .sort((a, b) => {
      if (sortKey === 'composite') return (b.scores?.composite || 0) - (a.scores?.composite || 0);
      if (sortKey === 'vcp')       return (b.scores?.vcp || 0)       - (a.scores?.vcp || 0);
      if (sortKey === 'rs')        return (b.scores?.rs  || 0)       - (a.scores?.rs  || 0);
      return 0;
    });

  // strategies.jsonの構造に合わせてデータ変換
  const toRow = (t) => ({
    ticker:       t.ticker,
    name:         t.name,
    status:       t.status,
    sector:       t.sector,
    vcp:          t.scores?.vcp,
    rs:           t.scores?.rs,
    ses:          t.scores?.ses,
    canslim_score:t.scores?.canslim,
    canslim_grade:t.canslim_grade,
    ecr_rank:     t.scores?.ecr_rank,
    ecr_phase:    t.ecr_phase,
    composite:    t.scores?.composite,
    pf:           t.scores?.pf,
    atr_pct:      t.atr_pct,
    pivot_dist_pct: t.pivot_dist_pct,
    ma50_ratio:   t.ma50_ratio,
    _price:       null,  // strategies.jsonには価格なし
    _entry:       null,
    _stop:        null,
    _target:      null,
    vcp_detail:   null,
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">

      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-bright text-xl font-bold">🔭 Scanner</h1>
          <p className="text-muted text-sm">
            {data.generated_at} · {data.ticker_count}銘柄スキャン ·
            ACTION <span className="text-green">{data.action_count}</span> /
            WAIT <span className="text-amber">{data.wait_count}</span>
          </p>
        </div>
        <button
          onClick={() => setShowFilters(v => !v)}
          className="flex items-center gap-2 text-muted hover:text-text font-mono text-xs transition px-3 py-2 border border-border rounded-lg"
        >
          <SlidersHorizontal size={14} /> フィルター
        </button>
      </div>

      {/* 検索 + フィルター */}
      <div className="space-y-3">
        <div className="flex items-center gap-3 bg-panel border border-border rounded-xl px-4 py-2.5">
          <Search size={14} className="text-muted shrink-0" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="ティッカー / 銘柄名で検索..."
            className="bg-transparent flex-1 font-mono text-sm text-bright outline-none placeholder:text-muted"
          />
        </div>

        {showFilters && (
          <div className="bg-panel border border-border rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="font-mono text-xs text-muted">ステータス</label>
              <select
                value={status}
                onChange={e => setStatus(e.target.value)}
                className="mt-1 w-full bg-ink border border-border rounded-lg px-3 py-2 font-mono text-xs text-bright focus:outline-none"
              >
                <option value="ALL">ALL</option>
                <option value="ACTION">ACTION</option>
                <option value="WAIT">WAIT</option>
              </select>
            </div>
            <div>
              <label className="font-mono text-xs text-muted">最小VCP: {minVcp}</label>
              <input type="range" min={0} max={105} value={minVcp} onChange={e => setMinVcp(+e.target.value)}
                className="mt-2 w-full accent-green" />
            </div>
            <div>
              <label className="font-mono text-xs text-muted">最小RS: {minRs}</label>
              <input type="range" min={0} max={99} value={minRs} onChange={e => setMinRs(+e.target.value)}
                className="mt-2 w-full accent-blue" />
            </div>
            <div>
              <label className="font-mono text-xs text-muted">ソート</label>
              <select
                value={sortKey}
                onChange={e => setSortKey(e.target.value)}
                className="mt-1 w-full bg-ink border border-border rounded-lg px-3 py-2 font-mono text-xs text-bright focus:outline-none"
              >
                <option value="composite">Composite</option>
                <option value="vcp">VCP Score</option>
                <option value="rs">RS Rating</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* テーブル */}
      <div className="bg-panel border border-border rounded-xl overflow-hidden">
        <div className="grid grid-cols-12 gap-2 px-4 py-2 border-b border-border text-muted font-mono text-xs">
          <div className="col-span-3">Ticker</div>
          <div className="col-span-2">Price</div>
          <div className="col-span-2">VCP / RS</div>
          <div className="col-span-2">Composite</div>
          <div className="col-span-2">Sector</div>
          <div className="col-span-1"></div>
        </div>

        <div className="text-xs text-muted font-mono px-4 py-1.5 border-b border-border/30">
          {filtered.length}件表示
        </div>

        {filtered.map(t => (
          <TickerRow
            key={t.ticker}
            t={toRow(t)}
            expanded={expanded === t.ticker}
            onToggle={() => setExpanded(expanded === t.ticker ? null : t.ticker)}
          />
        ))}
      </div>
    </div>
  );
}
