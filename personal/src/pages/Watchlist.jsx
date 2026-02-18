import React, { useState, useEffect } from 'react';
import { Star, Trash2, StickyNote, ExternalLink, TrendingUp, Plus, X, Check } from 'lucide-react';

const LS_KEY = 'sentinel_watchlist';

const fmt = (n, d = 2) => n != null ? `$${Number(n).toFixed(d)}` : '—';

function loadWatchlist() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); }
  catch { return []; }
}
function saveWatchlist(list) {
  localStorage.setItem(LS_KEY, JSON.stringify(list));
}

// ACTION銘柄からウォッチリストに追加用データを取得
function useActionData() {
  const [actions, setActions] = useState([]);
  useEffect(() => {
    const load = async () => {
      try {
        const idx = await fetch('/content/index.json').then(r => r.json());
        const latest = idx.articles?.[0];
        if (!latest) return;
        const d = await fetch(`/content/${latest.slug}.json`).then(r => r.json());
        setActions(d?.data?.actions || []);
      } catch {}
    };
    load();
  }, []);
  return actions;
}

function MemoEditor({ ticker, initial, onSave }) {
  const [text, setText] = useState(initial || '');
  return (
    <div className="mt-3 space-y-2">
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="メモを入力..."
        rows={3}
        className="w-full bg-ink border border-border rounded-lg px-3 py-2 font-mono text-xs text-text resize-none focus:outline-none focus:border-green/50"
      />
      <button
        onClick={() => onSave(text)}
        className="flex items-center gap-1 text-green font-mono text-xs hover:opacity-80 transition"
      >
        <Check size={12} /> 保存
      </button>
    </div>
  );
}

function WatchCard({ item, onRemove, onMemo, actionData }) {
  const [showMemo, setShowMemo] = useState(false);
  // ACTION銘柄データと照合
  const live = actionData.find(a => a.ticker === item.ticker);

  const price  = live?._price;
  const entry  = live?._entry;
  const stop   = live?._stop;
  const target = live?._target;
  const vcp    = live?.vcp;
  const rs     = live?.rs;
  const status = live?.status;

  // 取得価格からの損益
  const pnl = item.bought_at && price
    ? ((price - item.bought_at) / item.bought_at * 100)
    : null;

  return (
    <div className="bg-panel border border-border rounded-xl overflow-hidden">
      {/* ヘッダー */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3">
          <Star size={14} className="text-amber fill-amber" />
          <div>
            <a
              href={`https://finance.yahoo.com/quote/${item.ticker}`}
              target="_blank" rel="noopener noreferrer"
              className="font-mono font-bold text-bright hover:text-green transition flex items-center gap-1"
            >
              {item.ticker} <ExternalLink size={10} className="text-muted" />
            </a>
            {item.name && <div className="text-muted text-xs">{item.name}</div>}
          </div>
          {status && (
            <span className={status === 'ACTION' ? 'badge-action' : 'badge-wait'}>
              {status}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMemo(v => !v)}
            className="p-1.5 text-muted hover:text-amber transition rounded"
          >
            <StickyNote size={14} />
          </button>
          <button
            onClick={() => onRemove(item.ticker)}
            className="p-1.5 text-muted hover:text-red transition rounded"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* 価格情報 */}
      <div className="px-4 py-3 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div className="text-muted font-mono text-xs">現在値</div>
          <div className="font-mono text-lg text-bright">{fmt(price)}</div>
          {pnl != null && (
            <div className={`font-mono text-xs ${pnl >= 0 ? 'text-green' : 'text-red'}`}>
              {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}% (取得比)
            </div>
          )}
        </div>
        <div>
          <div className="text-muted font-mono text-xs">Entry</div>
          <div className="font-mono text-green font-bold">{fmt(entry)}</div>
        </div>
        <div>
          <div className="text-muted font-mono text-xs">Stop / Target</div>
          <div className="flex gap-2 font-mono text-sm">
            <span className="text-red">{fmt(stop)}</span>
            <span className="text-muted">/</span>
            <span className="text-amber">{fmt(target)}</span>
          </div>
          {entry && stop && target && (
            <div className="text-muted font-mono text-xs">
              RR 1:{((target - entry) / (entry - stop)).toFixed(1)}
            </div>
          )}
        </div>
        <div>
          <div className="text-muted font-mono text-xs">VCP / RS</div>
          <div className="font-mono text-sm">
            <span className="text-green">{vcp ?? '—'}</span>
            <span className="text-muted"> / </span>
            <span className="text-blue">{rs ?? '—'}</span>
          </div>
        </div>
      </div>

      {/* 取得価格入力 */}
      <div className="px-4 pb-3 flex items-center gap-3">
        <span className="text-muted font-mono text-xs">取得価格:</span>
        <input
          type="number"
          step="0.01"
          defaultValue={item.bought_at || ''}
          placeholder="例: 103.50"
          onBlur={e => {
            const v = parseFloat(e.target.value);
            if (!isNaN(v)) onMemo(item.ticker, { bought_at: v });
          }}
          className="bg-ink border border-border rounded px-2 py-1 font-mono text-xs text-bright w-28 focus:outline-none focus:border-green/50"
        />
        {item.bought_at && price && (
          <span className={`font-mono text-xs ${pnl >= 0 ? 'text-green' : 'text-red'}`}>
            {pnl >= 0 ? '▲' : '▼'} {Math.abs(pnl).toFixed(2)}%
          </span>
        )}
        <div className="flex gap-2 ml-auto">
          <a href={`https://finance.yahoo.com/quote/${item.ticker}`} target="_blank" rel="noopener noreferrer"
            className="text-muted hover:text-text font-mono text-xs transition">Yahoo</a>
          <a href={`https://www.tradingview.com/chart/?symbol=${item.ticker}`} target="_blank" rel="noopener noreferrer"
            className="text-muted hover:text-text font-mono text-xs transition">TV</a>
        </div>
      </div>

      {/* メモ */}
      {item.memo && !showMemo && (
        <div className="px-4 pb-3 bg-ink/30 mx-3 mb-3 rounded-lg p-3 border border-border/50">
          <div className="text-muted font-mono text-xs mb-1">MEMO</div>
          <div className="text-dim text-xs whitespace-pre-wrap">{item.memo}</div>
        </div>
      )}
      {showMemo && (
        <div className="px-4 pb-3">
          <MemoEditor
            ticker={item.ticker}
            initial={item.memo}
            onSave={text => { onMemo(item.ticker, { memo: text }); setShowMemo(false); }}
          />
        </div>
      )}
    </div>
  );
}

// ── Watchlist ─────────────────────────────────────────────
export default function Watchlist() {
  const [list,    setList]    = useState(loadWatchlist);
  const [adding,  setAdding]  = useState(false);
  const [input,   setInput]   = useState('');
  const actionData = useActionData();

  const persist = (next) => { setList(next); saveWatchlist(next); };

  const addTicker = () => {
    const t = input.toUpperCase().trim();
    if (!t || list.find(i => i.ticker === t)) return;
    const live = actionData.find(a => a.ticker === t);
    persist([...list, {
      ticker:    t,
      name:      live?.name || '',
      added_at:  new Date().toISOString().slice(0, 10),
      bought_at: null,
      memo:      '',
    }]);
    setInput(''); setAdding(false);
  };

  // ACTION銘柄から一括追加
  const addFromActions = (ticker) => {
    if (list.find(i => i.ticker === ticker)) return;
    const live = actionData.find(a => a.ticker === ticker);
    persist([...list, {
      ticker,
      name:      live?.name || '',
      added_at:  new Date().toISOString().slice(0, 10),
      bought_at: null,
      memo:      '',
    }]);
  };

  const remove = (ticker) => persist(list.filter(i => i.ticker !== ticker));

  const update = (ticker, patch) => persist(
    list.map(i => i.ticker === ticker ? { ...i, ...patch } : i)
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">

      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-bright text-xl font-bold">⭐ Watchlist</h1>
          <p className="text-muted text-sm">{list.length}銘柄</p>
        </div>
        <button
          onClick={() => setAdding(v => !v)}
          className="flex items-center gap-2 bg-green text-ink font-mono text-sm font-bold px-4 py-2 rounded-lg hover:bg-green/90 transition"
        >
          <Plus size={14} /> 追加
        </button>
      </div>

      {/* 追加フォーム */}
      {adding && (
        <div className="bg-panel border border-border rounded-xl p-4 flex items-center gap-3">
          <input
            autoFocus
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addTicker()}
            placeholder="ティッカー（例: NVDA）"
            className="bg-ink border border-border rounded-lg px-3 py-2 font-mono text-sm text-bright flex-1 focus:outline-none focus:border-green/50"
          />
          <button onClick={addTicker} className="bg-green text-ink font-mono text-sm font-bold px-4 py-2 rounded-lg hover:bg-green/90 transition">追加</button>
          <button onClick={() => setAdding(false)} className="text-muted hover:text-text transition"><X size={16} /></button>
        </div>
      )}

      {/* ACTIONから追加 */}
      {actionData.length > 0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">本日のACTION銘柄からワンクリック追加</div>
          <div className="flex flex-wrap gap-2">
            {actionData.slice(0, 15).map(a => {
              const added = list.find(i => i.ticker === a.ticker);
              return (
                <button
                  key={a.ticker}
                  onClick={() => !added && addFromActions(a.ticker)}
                  className={`font-mono text-xs px-3 py-1.5 rounded-lg border transition ${
                    added
                      ? 'border-green/30 text-green bg-green-dim cursor-default'
                      : 'border-border text-dim hover:border-green/50 hover:text-text'
                  }`}
                >
                  {a.ticker} {added ? '✓' : '+'}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* カードリスト */}
      {list.length === 0 ? (
        <div className="text-center text-muted font-mono py-16">
          <Star size={32} className="mx-auto mb-4 opacity-30" />
          <p>ウォッチリストは空です</p>
        </div>
      ) : (
        <div className="space-y-4">
          {list.map(item => (
            <WatchCard
              key={item.ticker}
              item={item}
              onRemove={remove}
              onMemo={update}
              actionData={actionData}
            />
          ))}
        </div>
      )}
    </div>
  );
}
