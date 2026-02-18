import React, { useState, useEffect } from 'react';
import { TrendingUp, Plus, X, Search } from 'lucide-react';
import TradingViewWidget from '../components/TradingViewWidget';

const LS_KEY = 'sentinel_chart_tabs';

function loadTabs() {
  try {
    const saved = localStorage.getItem(LS_KEY);
    return saved ? JSON.parse(saved) : ['NVDA', 'AAPL', 'MSFT'];
  } catch {
    return ['NVDA', 'AAPL', 'MSFT'];
  }
}

function saveTabs(tabs) {
  localStorage.setItem(LS_KEY, JSON.stringify(tabs));
}

export default function ChartPage() {
  const [tabs, setTabs] = useState(loadTabs);
  const [active, setActive] = useState(0);
  const [adding, setAdding] = useState(false);
  const [input, setInput] = useState('');
  const [interval, setInterval] = useState('D');

  const persist = (newTabs) => {
    setTabs(newTabs);
    saveTabs(newTabs);
  };

  const addTab = () => {
    const ticker = input.toUpperCase().trim();
    if (!ticker || tabs.includes(ticker)) return;
    const updated = [...tabs, ticker];
    persist(updated);
    setActive(updated.length - 1);
    setInput('');
    setAdding(false);
  };

  const removeTab = (idx) => {
    if (tabs.length === 1) return; // 最低1つは残す
    const updated = tabs.filter((_, i) => i !== idx);
    persist(updated);
    if (active >= updated.length) setActive(updated.length - 1);
  };

  const currentSymbol = tabs[active];

  return (
    <div className="h-screen flex flex-col bg-ink">
      
      {/* タブバー */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-panel overflow-x-auto">
        <TrendingUp size={16} className="text-green shrink-0" />
        
        {tabs.map((t, i) => (
          <div
            key={i}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg font-mono text-sm transition cursor-pointer group ${
              active === i
                ? 'bg-green text-ink font-bold'
                : 'bg-ink border border-border text-dim hover:text-text'
            }`}
          >
            <span onClick={() => setActive(i)}>{t}</span>
            {tabs.length > 1 && (
              <button
                onClick={(e) => { e.stopPropagation(); removeTab(i); }}
                className="opacity-0 group-hover:opacity-100 hover:text-red transition"
              >
                <X size={12} />
              </button>
            )}
          </div>
        ))}

        {adding ? (
          <div className="flex items-center gap-2 bg-ink border border-border rounded-lg px-2 py-1">
            <input
              autoFocus
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addTab()}
              placeholder="TICKER"
              className="bg-transparent font-mono text-xs text-bright w-16 outline-none"
            />
            <button onClick={addTab} className="text-green hover:opacity-80">✓</button>
            <button onClick={() => setAdding(false)} className="text-muted hover:text-text">✕</button>
          </div>
        ) : (
          <button
            onClick={() => setAdding(true)}
            className="p-1 text-muted hover:text-green transition rounded"
          >
            <Plus size={14} />
          </button>
        )}

        {/* 時間軸切り替え */}
        <div className="ml-auto flex gap-1 shrink-0">
          {[
            ['1', '1分'],
            ['5', '5分'],
            ['15', '15分'],
            ['60', '1時間'],
            ['D', '日足'],
            ['W', '週足'],
          ].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setInterval(val)}
              className={`font-mono text-xs px-2 py-1 rounded transition ${
                interval === val
                  ? 'bg-green text-ink font-bold'
                  : 'text-muted hover:text-text'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* チャート本体 */}
      <div className="flex-1 px-4 py-4">
        <div className="h-full bg-panel border border-border rounded-xl overflow-hidden">
          <TradingViewWidget
            symbol={`NASDAQ:${currentSymbol}`}
            interval={interval}
            height="100%"
            theme="dark"
            showToolbar={true}
          />
        </div>
      </div>

      {/* クイックリンク */}
      <div className="px-4 py-3 border-t border-border bg-panel flex items-center gap-3 text-xs font-mono">
        <span className="text-muted">外部リンク:</span>
        <a href={`https://finance.yahoo.com/quote/${currentSymbol}`} target="_blank" rel="noopener noreferrer"
          className="text-dim hover:text-green transition">Yahoo</a>
        <a href={`https://www.tradingview.com/chart/?symbol=${currentSymbol}`} target="_blank" rel="noopener noreferrer"
          className="text-dim hover:text-green transition">TradingView</a>
        <a href={`https://seekingalpha.com/symbol/${currentSymbol}`} target="_blank" rel="noopener noreferrer"
          className="text-dim hover:text-green transition">Seeking Alpha</a>
        <a href={`https://finviz.com/quote.ashx?t=${currentSymbol}`} target="_blank" rel="noopener noreferrer"
          className="text-dim hover:text-green transition">Finviz</a>
      </div>
    </div>
  );
}
