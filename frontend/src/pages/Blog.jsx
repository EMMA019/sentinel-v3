import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Calendar, Loader, TrendingUp, RefreshCw } from 'lucide-react';
import { useSEO } from '../hooks/useSEO';

const TYPE_META = {
  daily:  { label_ja:'日次レポート', label_en:'Daily',   color:'text-green border-green/30 bg-green/10'  },
  weekly: { label_ja:'週次レポート', label_en:'Weekly',  color:'text-blue  border-blue/30  bg-blue/10'   },
  stock:  { label_ja:'銘柄分析',     label_en:'Stock',   color:'text-amber border-amber/30 bg-amber/10'  },
};

function LangToggle({ lang, setLang }) {
  return (
    <div className="flex items-center gap-1 bg-panel border border-border rounded-lg p-0.5">
      {['ja','en'].map(l => (
        <button key={l} onClick={() => setLang(l)}
          className={`px-3 py-1 text-xs font-mono rounded-md transition ${
            lang===l ? 'bg-green text-ink font-700' : 'text-muted hover:text-dim'}`}>
          {l==='ja' ? '日本語' : 'English'}
        </button>
      ))}
    </div>
  );
}

function ArticleCard({ article, lang }) {
  const t    = article[lang] ?? article.ja;
  const meta = TYPE_META[article.type] ?? TYPE_META.stock;
  const data = article.data ?? {};
  const isStock = article.type === 'stock';

  return (
    <Link to={`/blog/${article.slug}`}
      className="block bg-panel border border-border rounded-xl p-5 hover:border-muted transition group">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className={`font-mono text-xs px-2 py-0.5 rounded border ${meta.color}`}>
          {lang==='ja' ? meta.label_ja : meta.label_en}
        </span>
        <span className="font-mono text-xs text-muted flex items-center gap-1">
          <Calendar size={10}/> {article.date}
        </span>
        {article.ticker && (
          <span className="font-mono text-xs text-amber font-700">{article.ticker}</span>
        )}
        {isStock && (
          <span className="font-mono text-xs text-muted flex items-center gap-1">
            <RefreshCw size={9}/> {lang==='ja' ? '毎日更新' : 'Updated daily'}
          </span>
        )}
      </div>

      <h2 className="font-display font-700 text-bright text-base leading-snug mb-2
                     group-hover:text-green transition line-clamp-2">
        {t?.title}
      </h2>
      <p className="font-body text-xs text-muted leading-relaxed line-clamp-2 mb-3">
        {t?.summary}
      </p>

      <div className="flex flex-wrap gap-2">
        {article.type==='daily' && data.action_count!=null && (<>
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-green/10 text-green">ACTION {data.action_count}</span>
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-amber/10 text-amber">WAIT {data.wait_count}</span>
        </>)}
        {article.type==='weekly' && data.action_count!=null && (
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue/10 text-blue">週次 ACTION {data.action_count}</span>
        )}
        {isStock && data.vcp!=null && (<>
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-panel border border-border text-dim">VCP {data.vcp}/105</span>
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-panel border border-border text-dim">RS {data.rs}</span>
          <span className={`font-mono text-xs px-2 py-0.5 rounded border ${
            data.status==='ACTION' ? 'bg-green/10 border-green/30 text-green' : 'bg-amber/10 border-amber/30 text-amber'}`}>
            {data.status}
          </span>
        </>)}
      </div>
    </Link>
  );
}

export default function Blog() {
  const [articles, setArticles] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [lang,     setLang]     = useState('ja');
  const [filter,   setFilter]   = useState('all');

  useSEO({
    title: lang==='ja' ? '米国株スキャンレポート — VCP×RSレーティング分析' : 'US Stock Reports — VCP×RS Rating Analysis',
    description: lang==='ja'
      ? 'VCP×RSレーティングによる米国株定量スクリーニング。日次レポート・週次レポート・銘柄個別分析を毎日自動生成。'
      : 'Daily/weekly US stock reports powered by VCP×RS screening. Auto-generated quantitative analysis.',
    type: 'website', lang,
  });

  useEffect(() => {
    fetch('/content/index.json')
      .then(r => r.ok ? r.json() : [])
      .then(d => { setArticles(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const FILTERS = [
    { id:'all',    label_ja:'すべて',       label_en:'All'    },
    { id:'daily',  label_ja:'日次レポート', label_en:'Daily'  },
    { id:'weekly', label_ja:'週次レポート', label_en:'Weekly' },
    { id:'stock',  label_ja:'銘柄分析',     label_en:'Stocks' },
  ];
  const filtered = articles.filter(a => filter==='all' || a.type===filter);

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-3xl mx-auto">

        {/* AdSense トップ */}
        <div className="mb-6 rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block',width:'100%'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
               data-ad-format="horizontal" data-full-width-responsive="true"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>

        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 size={14} className="text-green"/>
              <span className="font-mono text-xs text-green">RESEARCH</span>
            </div>
            <h1 className="font-display font-700 text-bright text-2xl">
              {lang==='ja' ? '市場分析レポート' : 'Market Analysis'}
            </h1>
            <p className="font-body text-xs text-muted mt-1">
              {lang==='ja' ? '毎日自動更新 — 日次・週次・銘柄分析' : 'Auto-updated daily — Market & Stock Analysis'}
            </p>
          </div>
          <LangToggle lang={lang} setLang={setLang}/>
        </div>

        <div className="flex gap-1 border-b border-border mb-6">
          {FILTERS.map(f => (
            <button key={f.id} onClick={() => setFilter(f.id)}
              className={`font-mono text-xs px-3 py-2.5 border-b-2 transition whitespace-nowrap ${
                filter===f.id ? 'border-green text-green' : 'border-transparent text-muted hover:text-dim'}`}>
              {lang==='ja' ? f.label_ja : f.label_en}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader size={20} className="text-muted animate-spin"/>
          </div>
        ) : filtered.length===0 ? (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <p className="font-body text-muted text-sm">
              {lang==='ja' ? '記事がありません。翌営業日に自動生成されます。' : 'No articles yet. Auto-generated on next trading day.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((a,i) => (
              <div key={a.slug}>
                <ArticleCard article={a} lang={lang}/>
                {(i+1)%5===0 && (
                  <div className="my-3 rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
                    <ins className="adsbygoogle" style={{display:'block'}}
                         data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
                         data-ad-format="fluid" data-ad-layout-key="-fb+5w+4e-db+86"/>
                    <span className="font-mono text-xs text-muted/40">Ad</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="mt-8 p-4 bg-panel border border-border rounded-xl">
          <p className="font-body text-xs text-muted leading-relaxed">
            {lang==='ja'
              ? '⚠️ 本サイトの記事はAIを活用した自動生成を含む教育目的のコンテンツです。投資助言ではありません。データはFMP APIを使用しており、遅延・誤差が含まれる場合があります。投資判断はご自身の責任で行ってください。'
              : '⚠️ Articles include AI-generated educational content. Not investment advice. Data via FMP API may contain delays. All investment decisions are your own responsibility.'}
          </p>
        </div>
      </div>
    </div>
  );
}
