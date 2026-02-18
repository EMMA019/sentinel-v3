import React, { useState, useEffect } from 'react';
import { Plus, Trash2, TrendingUp, TrendingDown, DollarSign, X } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const LS_KEY = 'sentinel_portfolio';
const fmt    = (n, d=2) => n != null ? `$${Number(n).toLocaleString('en-US', {minimumFractionDigits:d,maximumFractionDigits:d})}` : '—';
const fmtJPY = (n) => n != null ? `¥${Math.round(n).toLocaleString('ja-JP')}` : '—';

function load()  { try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); } catch { return []; } }
function save(d) { localStorage.setItem(LS_KEY, JSON.stringify(d)); }

// 現在値取得（daily JSONから照合）
function useCurrentPrices() {
  const [prices, setPrices] = useState({});
  useEffect(() => {
    const f = async () => {
      try {
        const idx = await fetch('/content/index.json').then(r=>r.json());
        const slug = idx.articles?.[0]?.slug;
        if (!slug) return;
        const d = await fetch(`/content/${slug}.json`).then(r=>r.json());
        const map = {};
        (d?.data?.actions || []).forEach(a => { map[a.ticker] = a._price; });
        (d?.data?.waits   || []).forEach(a => { map[a.ticker] = a._price; });
        setPrices(map);
      } catch {}
    };
    f();
  }, []);
  return prices;
}

const COLORS = ['#00FF88','#4499FF','#FFB800','#FF4466','#AA66FF','#00CCFF','#FF8844'];

function AddTradeModal({ onAdd, onClose }) {
  const [form, setForm] = useState({
    ticker: '', shares: '', bought_at: '', date: new Date().toISOString().slice(0,10),
    stop: '', target: '', note: ''
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = () => {
    if (!form.ticker || !form.shares || !form.bought_at) return;
    onAdd({
      id:        Date.now(),
      ticker:    form.ticker.toUpperCase().trim(),
      shares:    parseFloat(form.shares),
      bought_at: parseFloat(form.bought_at),
      stop:      form.stop    ? parseFloat(form.stop)   : null,
      target:    form.target  ? parseFloat(form.target) : null,
      date:      form.date,
      note:      form.note,
      status:    'open',
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-ink/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-panel border border-border rounded-2xl w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-mono font-bold text-bright">新規エントリー記録</h2>
          <button onClick={onClose} className="text-muted hover:text-text"><X size={16}/></button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            ['ticker',    'Ticker',    'text',   'NVDA'],
            ['shares',    '株数',      'number', '10'],
            ['bought_at', '取得価格',  'number', '450.00'],
            ['date',      '取得日',    'date',   ''],
            ['stop',      'ストップ',  'number', '430.00'],
            ['target',    'ターゲット','number', '500.00'],
          ].map(([k, label, type, ph]) => (
            <div key={k}>
              <label className="text-muted font-mono text-xs">{label}</label>
              <input
                type={type}
                step={type==='number' ? '0.01' : undefined}
                value={form[k]}
                onChange={e => set(k, e.target.value)}
                placeholder={ph}
                className="mt-1 w-full bg-ink border border-border rounded-lg px-3 py-2 font-mono text-sm text-bright focus:outline-none focus:border-green/50"
              />
            </div>
          ))}
        </div>

        <div>
          <label className="text-muted font-mono text-xs">メモ</label>
          <input
            value={form.note}
            onChange={e => set('note', e.target.value)}
            className="mt-1 w-full bg-ink border border-border rounded-lg px-3 py-2 font-mono text-sm text-bright focus:outline-none focus:border-green/50"
          />
        </div>

        <button
          onClick={submit}
          className="w-full bg-green text-ink font-mono font-bold py-3 rounded-xl hover:bg-green/90 transition"
        >
          追加
        </button>
      </div>
    </div>
  );
}

function TradeRow({ t, price, onClose, onRemove }) {
  const currentPrice = price || t.bought_at;
  const pnlPct = ((currentPrice - t.bought_at) / t.bought_at * 100);
  const pnlAmt = (currentPrice - t.bought_at) * t.shares;
  const cost   = t.bought_at * t.shares;

  // ストップ・ターゲットまでの距離
  const toStop   = t.stop   ? ((t.stop   - currentPrice) / currentPrice * 100) : null;
  const toTarget = t.target ? ((t.target - currentPrice) / currentPrice * 100) : null;

  return (
    <div className="px-4 py-3 border-b border-border/50 hover:bg-panel/40 transition">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div>
            <div className="font-mono font-bold text-bright text-sm">{t.ticker}</div>
            <div className="text-muted font-mono text-xs">{t.date} · {t.shares}株 · 取得{fmt(t.bought_at)}</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* 現在値と損益 */}
          <div className="text-right">
            <div className="font-mono text-sm text-bright">{fmt(currentPrice)}</div>
            <div className={`font-mono text-xs ${pnlPct >= 0 ? 'text-green' : 'text-red'}`}>
              {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}% ({pnlPct >= 0 ? '+' : ''}{fmt(pnlAmt)})
            </div>
          </div>

          {/* ストップ・ターゲット */}
          <div className="hidden md:block text-right">
            {t.stop && <div className="font-mono text-xs text-red">Stop {fmt(t.stop)} ({toStop?.toFixed(1)}%)</div>}
            {t.target && <div className="font-mono text-xs text-amber">Tgt {fmt(t.target)} ({toTarget?.toFixed(1) > 0 ? '+' : ''}{toTarget?.toFixed(1)}%)</div>}
          </div>

          {/* 操作 */}
          <div className="flex gap-1">
            <button
              onClick={() => onClose(t.id, currentPrice)}
              className="font-mono text-xs text-amber hover:text-amber/80 transition px-2 py-1 border border-amber/30 rounded"
            >
              決済
            </button>
            <button onClick={() => onRemove(t.id)} className="p-1 text-muted hover:text-red transition">
              <Trash2 size={12} />
            </button>
          </div>
        </div>
      </div>
      {t.note && <div className="mt-1 text-muted font-mono text-xs pl-0">{t.note}</div>}
    </div>
  );
}

// ── Portfolio ─────────────────────────────────────────────
export default function Portfolio() {
  const [trades,  setTrades]  = useState(load);
  const [showAdd, setShowAdd] = useState(false);
  const prices = useCurrentPrices();

  const persist = (next) => { setTrades(next); save(next); };

  const addTrade  = (t) => persist([...trades, t]);
  const removeTrade = (id) => persist(trades.filter(t => t.id !== id));
  const closeTrade = (id, closePrice) => {
    persist(trades.map(t => t.id === id
      ? { ...t, status: 'closed', closed_at: closePrice, close_date: new Date().toISOString().slice(0,10) }
      : t
    ));
  };

  const open   = trades.filter(t => t.status === 'open');
  const closed = trades.filter(t => t.status === 'closed');

  // サマリー計算
  const totalCost = open.reduce((s, t) => s + t.bought_at * t.shares, 0);
  const totalValue = open.reduce((s, t) => s + (prices[t.ticker] || t.bought_at) * t.shares, 0);
  const totalPnL   = totalValue - totalCost;
  const totalPnLPct = totalCost > 0 ? totalPnL / totalCost * 100 : 0;

  const closedPnL = closed.reduce((s, t) => {
    if (!t.closed_at) return s;
    return s + (t.closed_at - t.bought_at) * t.shares;
  }, 0);

  // セクター配分（セクター情報がある場合）
  const allocationData = open.reduce((acc, t) => {
    const val = (prices[t.ticker] || t.bought_at) * t.shares;
    const key = t.ticker;
    const existing = acc.find(a => a.name === key);
    if (existing) existing.value += val;
    else acc.push({ name: key, value: val });
    return acc;
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">

      {showAdd && <AddTradeModal onAdd={addTrade} onClose={() => setShowAdd(false)} />}

      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-bright text-xl font-bold">💼 Portfolio</h1>
          <p className="text-muted text-sm">保有{open.length}銘柄 / 決済済{closed.length}件</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-green text-ink font-mono text-sm font-bold px-4 py-2 rounded-lg hover:bg-green/90 transition"
        >
          <Plus size={14} /> エントリー記録
        </button>
      </div>

      {/* サマリーカード */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: '評価額合計',    value: fmt(totalValue, 0),  sub: `元本 ${fmt(totalCost, 0)}` },
          { label: '含み損益',      value: fmt(totalPnL, 0),    sub: `${totalPnLPct >= 0 ? '+' : ''}${totalPnLPct.toFixed(2)}%`, color: totalPnL >= 0 ? 'text-green' : 'text-red' },
          { label: '確定損益',      value: fmt(closedPnL, 0),   sub: `${closed.length}件決済済`, color: closedPnL >= 0 ? 'text-green' : 'text-red' },
          { label: '保有銘柄数',    value: `${open.length}銘柄`, sub: '現在' },
        ].map((c, i) => (
          <div key={i} className="bg-panel border border-border rounded-xl p-4">
            <div className="text-muted font-mono text-xs mb-1">{c.label}</div>
            <div className={`font-mono text-lg font-bold ${c.color || 'text-bright'}`}>{c.value}</div>
            <div className="text-muted font-mono text-xs">{c.sub}</div>
          </div>
        ))}
      </div>

      {/* 配分チャート + 保有リスト */}
      <div className="grid md:grid-cols-3 gap-6">
        {allocationData.length > 1 && (
          <div className="bg-panel border border-border rounded-xl p-4">
            <div className="font-mono text-xs text-muted mb-3">配分</div>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={allocationData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                  {allocationData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#0C1117', border: '1px solid #182030', fontFamily: 'monospace', fontSize: 11 }}
                  formatter={(v) => [fmt(v, 0), '']}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1 mt-2">
              {allocationData.map((d, i) => (
                <div key={i} className="flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="text-dim">{d.name}</span>
                  </div>
                  <span className="text-text">{totalValue > 0 ? (d.value / totalValue * 100).toFixed(1) : 0}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className={`${allocationData.length > 1 ? 'md:col-span-2' : 'md:col-span-3'} bg-panel border border-border rounded-xl overflow-hidden`}>
          <div className="px-4 py-3 border-b border-border font-mono text-sm text-bright font-bold">
            保有中 ({open.length})
          </div>
          {open.length === 0 ? (
            <div className="text-center text-muted font-mono py-12 text-sm">保有銘柄なし</div>
          ) : (
            open.map(t => (
              <TradeRow
                key={t.id}
                t={t}
                price={prices[t.ticker]}
                onClose={closeTrade}
                onRemove={removeTrade}
              />
            ))
          )}
        </div>
      </div>

      {/* 決済済みトレード */}
      {closed.length > 0 && (
        <div className="bg-panel border border-border rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-border font-mono text-sm text-bright font-bold">
            決済済み ({closed.length})
          </div>
          {closed.map(t => {
            const pnlPct = t.closed_at ? (t.closed_at - t.bought_at) / t.bought_at * 100 : 0;
            const pnlAmt = t.closed_at ? (t.closed_at - t.bought_at) * t.shares : 0;
            return (
              <div key={t.id} className="px-4 py-3 border-b border-border/50 flex items-center justify-between">
                <div>
                  <span className="font-mono font-bold text-dim">{t.ticker}</span>
                  <span className="text-muted font-mono text-xs ml-3">{t.date} → {t.close_date}</span>
                  <span className="text-muted font-mono text-xs ml-3">{t.shares}株</span>
                </div>
                <div className="text-right">
                  <div className={`font-mono text-sm font-bold ${pnlPct >= 0 ? 'text-green' : 'text-red'}`}>
                    {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                  </div>
                  <div className={`font-mono text-xs ${pnlPct >= 0 ? 'text-green' : 'text-red'}`}>
                    {pnlAmt >= 0 ? '+' : ''}{fmt(pnlAmt)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
