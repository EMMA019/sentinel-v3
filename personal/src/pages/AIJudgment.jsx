import React, { useState } from 'react';
import { Brain, Search, TrendingUp, AlertTriangle, Target, Shield } from 'lucide-react';

export default function AIJudgment() {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const analyze = async () => {
    if (!ticker) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // JSONファイルを読み込む（事前にai_judge.pyで生成済み）
      const resp = await fetch(`/content/${ticker.toLowerCase()}_judgment.json`);
      if (!resp.ok) throw new Error('分析データが見つかりません。先にai_judge.pyを実行してください。');
      const json = await resp.json();
      setData(json);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const judgmentColor = {
    'BUY':  'text-green',
    'WAIT': 'text-amber',
    'SELL': 'text-red',
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      
      {/* ヘッダー */}
      <div>
        <h1 className="font-mono text-bright text-xl font-bold flex items-center gap-2">
          <Brain size={20} className="text-green" /> AI Judgment Engine
        </h1>
        <p className="text-muted font-mono text-sm mt-1">
          VCP/CANSLIM/ECR全ルール + ニュースセンチメント → OpenAI判定
        </p>
      </div>

      {/* 検索 */}
      <div className="flex items-center gap-3">
        <div className="flex-1 flex items-center gap-3 bg-panel border border-border rounded-xl px-4 py-3">
          <Search size={14} className="text-muted shrink-0" />
          <input
            value={ticker}
            onChange={e => setTicker(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && analyze()}
            placeholder="TICKER (例: NVDA)"
            className="bg-transparent flex-1 font-mono text-sm text-bright outline-none placeholder:text-muted"
          />
        </div>
        <button
          onClick={analyze}
          disabled={loading || !ticker}
          className="flex items-center gap-2 bg-green text-ink font-mono text-sm font-bold px-6 py-3 rounded-xl hover:bg-green/90 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? '分析中...' : '判定実行'}
        </button>
      </div>

      {/* エラー */}
      {error && (
        <div className="bg-red-dim border border-red/30 rounded-xl p-4 text-red font-mono text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* 結果 */}
      {data && (
        <div className="space-y-4">
          
          {/* 判定結果 */}
          <div className={`bg-panel border rounded-xl p-6 ${
            data.judgment.judgment === 'BUY' ? 'border-green' :
            data.judgment.judgment === 'WAIT' ? 'border-amber' : 'border-red'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-muted font-mono text-xs">AI判定</div>
                <div className={`font-mono text-3xl font-bold ${judgmentColor[data.judgment.judgment]}`}>
                  {data.judgment.judgment}
                </div>
              </div>
              <div className="text-right">
                <div className="text-muted font-mono text-xs">信頼度</div>
                <div className="font-mono text-2xl font-bold text-bright">
                  {data.judgment.confidence}%
                </div>
              </div>
            </div>
            <div className="text-text text-sm leading-relaxed">
              {data.judgment.reasoning}
            </div>
          </div>

          {/* テクニカルスコア */}
          <div className="bg-panel border border-border rounded-xl p-5">
            <div className="font-mono text-xs text-muted mb-3">📊 テクニカルスコア</div>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(data.context.scores).map(([k, v]) => (
                <div key={k}>
                  <div className="text-muted font-mono text-xs">{k.toUpperCase()}</div>
                  <div className="font-mono text-lg font-bold text-bright">{v}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 space-y-1">
              {data.context.vcp_signals.map((s, i) => (
                <div key={i} className="text-green font-mono text-xs">✓ {s}</div>
              ))}
            </div>
          </div>

          {/* エントリープラン */}
          {data.judgment.entry_plan && (
            <div className="bg-panel border border-green/30 rounded-xl p-5">
              <div className="font-mono text-xs text-green mb-2 flex items-center gap-2">
                <Target size={12} /> エントリープラン
              </div>
              <div className="text-text text-sm">{data.judgment.entry_plan}</div>
            </div>
          )}

          {/* リスク */}
          {data.judgment.risks?.length > 0 && (
            <div className="bg-panel border border-red/30 rounded-xl p-5">
              <div className="font-mono text-xs text-red mb-2 flex items-center gap-2">
                <AlertTriangle size={12} /> リスク
              </div>
              <ul className="space-y-1">
                {data.judgment.risks.map((r, i) => (
                  <li key={i} className="text-text text-sm">• {r}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 材料 */}
          {data.judgment.catalysts?.length > 0 && (
            <div className="bg-panel border border-blue/30 rounded-xl p-5">
              <div className="font-mono text-xs text-blue mb-2 flex items-center gap-2">
                <TrendingUp size={12} /> 材料・カタリスト
              </div>
              <ul className="space-y-1">
                {data.judgment.catalysts.map((c, i) => (
                  <li key={i} className="text-text text-sm">• {c}</li>
                ))}
              </ul>
            </div>
          )}

          {/* ニュース */}
          <div className="bg-panel border border-border rounded-xl p-5">
            <div className="font-mono text-xs text-muted mb-3">📰 最新ニュース</div>
            <div className="text-xs text-dim whitespace-pre-wrap font-mono leading-relaxed">
              {data.context.news.fmp}
            </div>
          </div>

          {/* 免責 */}
          <div className="text-muted font-mono text-xs border border-border/50 rounded-xl p-4 bg-panel/30">
            ⚠️ AI判定は参考情報です。投資判断は自己責任で行ってください。
          </div>
        </div>
      )}

      {/* 使い方 */}
      {!data && !loading && (
        <div className="bg-panel border border-border rounded-xl p-5 text-sm text-dim space-y-2">
          <div className="font-mono text-xs text-muted mb-2">💡 使い方</div>
          <p>1. ティッカーを入力して「判定実行」をクリック</p>
          <p>2. 初回は <code className="bg-ink px-1 py-0.5 rounded text-xs">python scripts/ai_judge.py TICKER</code> を実行してJSON生成</p>
          <p>3. OpenAI APIキーを環境変数 <code className="bg-ink px-1 py-0.5 rounded text-xs">OPENAI_API_KEY</code> に設定</p>
        </div>
      )}
    </div>
  );
}
