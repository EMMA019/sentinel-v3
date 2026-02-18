import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { TrendingUp, TrendingDown, RefreshCw, Brain, ExternalLink, ArrowLeft } from 'lucide-react';
import TradingViewWidget from '../components/TradingViewWidget';
import VCPChart from '../components/VCPChart';
import ScoreHistoryChart from '../components/ScoreHistoryChart';
import ScoreRadarChart from '../components/ScoreRadarChart';

const fmt = (n, d=2) => n != null ? `$${Number(n).toFixed(d)}` : '—';
const pct = (n) => n != null ? `${n > 0 ? '+' : ''}${Number(n).toFixed(2)}%` : '—';
const clr = (n) => n > 0 ? 'text-green' : n < 0 ? 'text-red' : 'text-dim';

export default function RealtimePage() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [quote, setQuote] = useState(null);
  const [data, setData] = useState(null);
  const [aiJudgment, setAiJudgment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const intervalRef = useRef(null);

  // リアルタイム株価取得（10秒ごと）
  const fetchQuote = async () => {
    try {
      const resp = await fetch(`https://financialmodelingprep.com/api/v3/quote/${ticker}?apikey=${import.meta.env.VITE_FMP_API_KEY || 'demo'}`);
      const json = await resp.json();
      if (json && json[0]) {
        setQuote(json[0]);
      }
    } catch (e) {
      console.error('Quote fetch error:', e);
    }
  };

  // strategies.jsonから現在のスコア取得
  const fetchData = async () => {
    try {
      const resp = await fetch('/content/strategies.json');
      const json = await resp.json();
      
      // 全ランキングから該当ティッカーを探す
      const allRankings = Object.values(json.rankings || {}).flat();
      const found = allRankings.find(t => t.ticker === ticker);
      
      if (found) {
        setData(found);
      }
    } catch (e) {
      console.error('Data fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  // AI判断取得（事前生成済みJSON）
  const fetchAiJudgment = async () => {
    try {
      const resp = await fetch(`/content/${ticker.toLowerCase()}_judgment.json`);
      if (resp.ok) {
        const json = await resp.json();
        setAiJudgment(json);
      }
    } catch {}
  };

  // AI判断を新規生成（バックエンドapi_judge.py実行）
  const runAiJudge = async () => {
    setAiLoading(true);
    try {
      // 実際にはバックエンドAPIを叩く
      // ここではダミー（フロントエンドからPython実行は不可）
      alert('AI判断はバックエンドで `python scripts/ai_judge.py ' + ticker + '` を実行してください');
      // 実装例: fetch('/api/ai-judge', { method: 'POST', body: JSON.stringify({ ticker }) })
    } finally {
      setAiLoading(false);
    }
  };

  useEffect(() => {
    fetchQuote();
    fetchData();
    fetchAiJudgment();

    // 10秒ごとにリアルタイム更新
    intervalRef.current = setInterval(fetchQuote, 10000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [ticker]);

  const currentPrice = quote?.price || data?.price || 0;
  const change = quote?.change || 0;
  const changePercent = quote?.changesPercentage || 0;

  return (
    <div className="min-h-screen bg-ink pb-20">
      
      {/* ヘッダー */}
      <div className="border-b border-border bg-panel px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate(-1)} className="p-1 text-muted hover:text-text transition">
              <ArrowLeft size={16} />
            </button>
            <div>
              <div className="font-mono text-bright text-lg font-bold">{ticker}</div>
              {data && <div className="text-muted text-xs">{data.name}</div>}
            </div>
          </div>
          <button onClick={fetchQuote} className="p-2 text-muted hover:text-green transition rounded-lg hover:bg-panel">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">

        {/* リアルタイム価格 */}
        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-muted font-mono text-xs mb-1">現在値 (リアルタイム)</div>
              <div className="font-mono text-3xl font-bold text-bright">{fmt(currentPrice)}</div>
              <div className={`font-mono text-sm flex items-center gap-2 mt-1 ${clr(change)}`}>
                {change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {fmt(change)} ({pct(changePercent)})
              </div>
            </div>
            {quote && (
              <div className="text-right font-mono text-xs text-muted space-y-1">
                <div>Open: {fmt(quote.open)}</div>
                <div>High: <span className="text-green">{fmt(quote.dayHigh)}</span></div>
                <div>Low: <span className="text-red">{fmt(quote.dayLow)}</span></div>
                <div>Vol: {(quote.volume / 1000000).toFixed(1)}M</div>
              </div>
            )}
          </div>
        </div>

        {/* AI判断 */}
        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="font-mono text-xs text-muted flex items-center gap-2">
              <Brain size={14} className="text-green" /> AI Judgment
            </div>
            <button
              onClick={runAiJudge}
              disabled={aiLoading}
              className="flex items-center gap-2 bg-green text-ink font-mono text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-green/90 transition disabled:opacity-50"
            >
              {aiLoading ? '分析中...' : '新規判定'}
            </button>
          </div>
          
          {aiJudgment ? (
            <div className="space-y-2">
              <div className={`font-mono text-lg font-bold ${
                aiJudgment.judgment.judgment === 'BUY' ? 'text-green' :
                aiJudgment.judgment.judgment === 'WAIT' ? 'text-amber' : 'text-red'
              }`}>
                {aiJudgment.judgment.judgment} (信頼度 {aiJudgment.judgment.confidence}%)
              </div>
              <div className="text-text text-sm">{aiJudgment.judgment.reasoning}</div>
            </div>
          ) : (
            <div className="text-muted text-sm">
              AI判断データなし。`python scripts/ai_judge.py {ticker}` を実行してください。
            </div>
          )}
        </div>

        {/* スコア表示 + レーダーチャート */}
        {data && (
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-panel border border-border rounded-xl p-5">
              <ScoreRadarChart scores={data.scores} />
            </div>
            <div className="bg-panel border border-border rounded-xl p-5 space-y-3">
              <div className="text-muted font-mono text-xs">📊 Current Scores</div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ['VCP', data.scores.vcp, 105, 'text-green'],
                  ['RS', data.scores.rs, 99, 'text-blue'],
                  ['ECR', data.scores.ecr_rank, 100, 'text-amber'],
                  ['CANSLIM', data.scores.canslim, 100, 'text-purple'],
                  ['SES', data.scores.ses, 100, 'text-red'],
                  ['Composite', data.scores.composite, 100, 'text-bright'],
                ].map(([label, value, max, color]) => (
                  <div key={label} className="bg-ink rounded-lg p-3">
                    <div className="text-muted font-mono text-xs">{label}</div>
                    <div className={`font-mono text-lg font-bold ${color}`}>{value}/{max}</div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 text-xs font-mono">
                <span className={data.status === 'ACTION' ? 'badge-action' : 'badge-wait'}>
                  {data.status}
                </span>
                <span className="bg-blue-dim text-blue border border-blue/30 px-2 py-0.5 rounded">
                  {data.ecr_phase}
                </span>
                <span className="bg-purple-dim text-purple border border-purple/30 px-2 py-0.5 rounded">
                  {data.canslim_grade}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* スコア推移チャート */}
        <div className="bg-panel border border-border rounded-xl p-5">
          <ScoreHistoryChart ticker={ticker} />
        </div>

        {/* TradingViewチャート */}
        <div className="bg-panel border border-border rounded-xl overflow-hidden">
          <TradingViewWidget
            symbol={`NASDAQ:${ticker}`}
            interval="D"
            height={500}
            theme="dark"
          />
        </div>

        {/* 外部リンク */}
        <div className="flex gap-3 text-xs font-mono">
          <a href={`https://finance.yahoo.com/quote/${ticker}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 text-dim hover:text-green transition">
            Yahoo <ExternalLink size={10} />
          </a>
          <a href={`https://www.tradingview.com/chart/?symbol=${ticker}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 text-dim hover:text-green transition">
            TradingView <ExternalLink size={10} />
          </a>
          <a href={`https://seekingalpha.com/symbol/${ticker}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 text-dim hover:text-green transition">
            Seeking Alpha <ExternalLink size={10} />
          </a>
          <a href={`https://finviz.com/quote.ashx?t=${ticker}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 text-dim hover:text-green transition">
            Finviz <ExternalLink size={10} />
          </a>
        </div>

      </div>
    </div>
  );
}
