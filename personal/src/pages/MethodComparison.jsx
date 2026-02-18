import React, { useState, useEffect } from 'react';
import { TrendingUp, Award, BarChart3 } from 'lucide-react';

const METHOD_COLORS = {
  'VCP×RS':  '#00FF88',
  'ECR':     '#4499FF',
  'CANSLIM': '#AA66FF',
  'SES':     '#FFB800',
};

function ScoreBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted font-mono text-xs w-16">{label}</span>
      <div className="flex-1 h-6 bg-border rounded-lg overflow-hidden relative">
        <div
          className="h-full transition-all"
          style={{ width: `${value}%`, backgroundColor: color }}
        />
        <span className="absolute inset-0 flex items-center justify-center font-mono text-xs font-bold text-bright">
          {value}
        </span>
      </div>
    </div>
  );
}

function MethodCard({ data }) {
  const [expanded, setExpanded] = useState(false);
  const color = METHOD_COLORS[data.method] || '#C8DCF0';

  return (
    <div className="bg-panel border border-border rounded-xl overflow-hidden">
      <div
        onClick={() => setExpanded(v => !v)}
        className="px-5 py-4 cursor-pointer hover:bg-panel/80 transition flex items-center justify-between border-b border-border"
      >
        <div className="flex items-center gap-3">
          <Award size={16} style={{ color }} />
          <div>
            <div className="font-mono font-bold text-bright" style={{ color }}>
              {data.method}
            </div>
            <div className="text-muted font-mono text-xs mt-0.5">
              {data.top_tickers?.length || 0}銘柄
            </div>
          </div>
        </div>
        <div className="text-muted font-mono text-xs">
          {expanded ? '▼' : '▶'}
        </div>
      </div>

      {/* 平均スコア */}
      <div className="px-5 py-4 space-y-2 border-b border-border/50">
        <div className="text-muted font-mono text-xs mb-3">平均スコア</div>
        <ScoreBar label="VCP"     value={data.avg_scores?.vcp || 0}     color="#00FF88" />
        <ScoreBar label="ECR"     value={data.avg_scores?.ecr || 0}     color="#4499FF" />
        <ScoreBar label="CANSLIM" value={data.avg_scores?.canslim || 0} color="#AA66FF" />
        <ScoreBar label="SES"     value={data.avg_scores?.ses || 0}     color="#FFB800" />
      </div>

      {/* トップ銘柄リスト */}
      {expanded && (
        <div className="px-5 py-4 bg-ink/30">
          <div className="text-muted font-mono text-xs mb-3">トップ30銘柄</div>
          <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
            {(data.top_tickers || []).map((t, i) => (
              <a
                key={i}
                href={`https://finance.yahoo.com/quote/${t}`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-xs text-bright hover:text-green transition text-center py-1 px-2 bg-panel rounded border border-border/50 hover:border-green/50"
              >
                {t}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function MethodComparison() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/content/strategies.json')
      .then(r => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data?.method_comparison) return (
    <div className="flex items-center justify-center h-64 font-mono text-green animate-pulse">
      LOADING...
    </div>
  );

  const methods = data.method_comparison;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* ヘッダー */}
      <div>
        <h1 className="font-mono text-bright text-xl font-bold flex items-center gap-2">
          <BarChart3 size={20} className="text-green" /> Method Comparison
        </h1>
        <p className="text-muted font-mono text-sm mt-1">
          4手法のトップ30銘柄と平均スコア比較
        </p>
      </div>

      {/* 手法別カード */}
      <div className="space-y-4">
        {methods.map((m, i) => (
          <MethodCard key={i} data={m} />
        ))}
      </div>

      {/* 解説 */}
      <div className="bg-panel border border-border rounded-xl p-5 text-sm text-dim leading-relaxed">
        <div className="font-mono text-xs text-muted mb-2">📊 各手法の特徴</div>
        <ul className="space-y-1 list-disc list-inside">
          <li><span className="text-green font-bold">VCP×RS</span>: 
            ボラティリティ収縮 + 相対強度。テクニカル重視。</li>
          <li><span className="text-blue font-bold">ECR</span>: 
            Earnings / Capital / Risk。ファンダ + テクニカル複合。</li>
          <li><span className="text-purple font-bold">CANSLIM</span>: 
            William O'Neil手法。EPS成長・新高値・出来高重視。</li>
          <li><span className="text-amber font-bold">SES</span>: 
            Sentinel Efficiency。フラクタル効率・True Force。</li>
        </ul>
      </div>
    </div>
  );
}
