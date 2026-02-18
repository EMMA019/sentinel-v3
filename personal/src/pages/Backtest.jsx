import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell } from 'recharts';

const fmt = (n, d=1) => n != null ? Number(n).toFixed(d) : '—';
const fmtMoney = (n) => n != null ? `¥${Math.round(n).toLocaleString('ja-JP')}` : '—';

const METHOD_LABELS = { vcp: 'VCP', canslim: 'CANSLIM', ses: 'SES', ecr: 'ECR', all: 'ALL' };
const METHOD_COLORS = { vcp: '#00FF88', canslim: '#AA66FF', ses: '#4499FF', ecr: '#FFB800', all: '#C8DCF0' };

export default function Backtest() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/content/backtest.json').then(r => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data) return (
    <div className="flex items-center justify-center h-64 font-mono text-green animate-pulse">LOADING...</div>
  );

  const methods = Object.keys(data.simulations || {});

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">

      {/* ヘッダー */}
      <div>
        <h1 className="font-mono text-bright text-xl font-bold">📈 Backtest</h1>
        <p className="text-muted font-mono text-sm">
          {data.generated_at} · 過去{data.lookback_days}日 · {data.ticker_count}銘柄
        </p>
      </div>

      {/* 全体サマリー */}
      {data.overall && (
        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="font-mono text-xs text-muted mb-4">OVERALL PERFORMANCE</div>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
            {[
              { label: 'Trades',    value: data.overall.total_trades,                  unit: '件' },
              { label: 'Win Rate',  value: `${fmt(data.overall.win_rate)}%`,            color: 'text-green' },
              { label: 'PF',        value: fmt(data.overall.profit_factor),             color: data.overall.profit_factor >= 1.5 ? 'text-green' : 'text-amber' },
              { label: 'Avg Win',   value: `+${fmt(data.overall.avg_win)}%`,            color: 'text-green' },
              { label: 'Avg Loss',  value: `${fmt(data.overall.avg_loss)}%`,            color: 'text-red' },
              { label: 'Expectancy',value: `${data.overall.expectancy >= 0 ? '+' : ''}${fmt(data.overall.expectancy)}%`, color: data.overall.expectancy >= 0 ? 'text-green' : 'text-red' },
            ].map((c, i) => (
              <div key={i}>
                <div className="text-muted font-mono text-xs">{c.label}</div>
                <div className={`font-mono text-lg font-bold ${c.color || 'text-bright'}`}>
                  {c.value}{c.unit || ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 手法別比較 */}
      {data.method_stats && (
        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="font-mono text-xs text-muted mb-4">手法別 勝率 / PF 比較</div>
          <div className="overflow-x-auto">
            <table className="w-full font-mono text-xs">
              <thead>
                <tr className="text-muted border-b border-border">
                  {['手法','Trades','Win Rate','PF','期待値','Avg Win','Avg Loss'].map(h => (
                    <th key={h} className="text-left pb-2 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.method_stats).map(([k, s]) => (
                  <tr key={k} className="border-b border-border/30">
                    <td className="py-2 pr-4 font-bold" style={{ color: METHOD_COLORS[k] }}>
                      {METHOD_LABELS[k] || k}
                    </td>
                    <td className="py-2 pr-4 text-dim">{s.total_trades}</td>
                    <td className={`py-2 pr-4 font-bold ${s.win_rate >= 45 ? 'text-green' : s.win_rate >= 35 ? 'text-amber' : 'text-red'}`}>
                      {fmt(s.win_rate)}%
                    </td>
                    <td className={`py-2 pr-4 font-bold ${s.profit_factor >= 1.5 ? 'text-green' : s.profit_factor >= 1.0 ? 'text-amber' : 'text-red'}`}>
                      {fmt(s.profit_factor)}
                    </td>
                    <td className={`py-2 pr-4 ${s.expectancy >= 0 ? 'text-green' : 'text-red'}`}>
                      {s.expectancy >= 0 ? '+' : ''}{fmt(s.expectancy)}%
                    </td>
                    <td className="py-2 pr-4 text-green">+{fmt(s.avg_win)}%</td>
                    <td className="py-2 pr-4 text-red">{fmt(s.avg_loss)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 複利シミュレーション */}
      {data.simulations && (
        <div className="space-y-4">
          <div className="bg-panel border border-border rounded-xl p-5">
            <div className="font-mono text-xs text-muted mb-4">
              💴 複利シミュレーション（¥1,000,000スタート / 残高10%投入）
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(data.simulations).map(([k, s]) => (
                <div key={k} className="bg-ink border border-border rounded-xl p-3">
                  <div className="font-mono text-xs mb-2 font-bold" style={{ color: METHOD_COLORS[k] }}>
                    {METHOD_LABELS[k] || k}
                  </div>
                  <div className="font-mono text-sm text-bright font-bold">{fmtMoney(s.final_capital)}</div>
                  <div className={`font-mono text-xs ${s.total_return >= 0 ? 'text-green' : 'text-red'}`}>
                    {s.total_return >= 0 ? '+' : ''}{fmt(s.total_return)}%
                  </div>
                  <div className="mt-2 space-y-0.5 font-mono text-xs text-muted">
                    <div>CAGR <span className="text-dim">{fmt(s.cagr)}%/yr</span></div>
                    <div>MaxDD <span className="text-red">-{fmt(s.max_drawdown)}%</span></div>
                    <div>Trades <span className="text-dim">{s.total_trades}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* エクイティカーブ（ALL） */}
          {data.simulations.all?.equity_curve?.length > 0 && (
            <div className="bg-panel border border-border rounded-xl p-5">
              <div className="font-mono text-xs text-muted mb-4">エクイティカーブ (ALL手法)</div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data.simulations.all.equity_curve.map((v, i) => ({ i, v }))}>
                  <XAxis dataKey="i" hide />
                  <YAxis
                    domain={['auto', 'auto']}
                    tickFormatter={v => `¥${(v/10000).toFixed(0)}万`}
                    width={64}
                    tick={{ fontSize: 10, fontFamily: 'monospace', fill: '#364858' }}
                  />
                  <Tooltip
                    formatter={v => [fmtMoney(v), '資産']}
                    contentStyle={{ background: '#0C1117', border: '1px solid #182030', fontFamily: 'monospace', fontSize: 11 }}
                  />
                  <ReferenceLine y={1000000} stroke="#364858" strokeDasharray="3 3" />
                  <Line type="monotone" dataKey="v" stroke="#00FF88" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* 月別損益（ALL） */}
          {data.simulations.all?.monthly?.length > 0 && (
            <div className="bg-panel border border-border rounded-xl p-5">
              <div className="font-mono text-xs text-muted mb-4">月別損益合計 (ALL)</div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={data.simulations.all.monthly} barSize={12}>
                  <XAxis dataKey="month" tick={{ fontSize: 9, fontFamily: 'monospace', fill: '#364858' }} />
                  <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fontFamily: 'monospace', fill: '#364858' }} width={40} />
                  <Tooltip
                    formatter={(v) => [`${v >= 0 ? '+' : ''}${v.toFixed(1)}%`, '損益']}
                    contentStyle={{ background: '#0C1117', border: '1px solid #182030', fontFamily: 'monospace', fontSize: 11 }}
                  />
                  <Bar dataKey="pnl_sum">
                    {data.simulations.all.monthly.map((m, i) => (
                      <Cell key={i} fill={m.pnl_sum >= 0 ? '#00FF88' : '#FF4466'} opacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* トップトレード */}
      {data.top_trades?.length > 0 && (
        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="font-mono text-xs text-muted mb-3">🏆 Best Trades</div>
          <div className="space-y-1">
            {data.top_trades.map((t, i) => (
              <div key={i} className="flex items-center justify-between font-mono text-xs py-1 border-b border-border/30">
                <span className="text-bright font-bold w-16">{t.ticker}</span>
                <span className="text-muted">{t.entry_date} → {t.exit_date}</span>
                <span className="text-green font-bold">+{t.pnl_pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 免責 */}
      <div className="text-muted font-mono text-xs border border-border/50 rounded-xl p-4 bg-panel/30">
        ⚠️ 個人用バックテスト。スリッページ・手数料・税金未考慮。過去の成績は将来を保証しない。
      </div>
    </div>
  );
}
