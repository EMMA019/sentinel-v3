# Project Code Summary

Generated on: 2026-02-16 07:18:51

## File: `README.md`

md
# SENTINEL PRO

米国株VCP×RSスクリーニング — ブログ自動生成サービス

## 構成

```
sentinel-pro/
├── shared/engines/     # 分析エンジン（VCP・RS・FMP API）
├── scripts/            # 毎日の記事生成スクリプト
├── api/stock/          # Vercel Serverless Function
├── frontend/           # React + Vite フロントエンド
└── .github/workflows/  # GitHub Actions（毎日JST15時実行）
```

## セットアップ

```bash
# 1. フロントエンド
cd frontend && npm install && npm run dev

# 2. 記事生成テスト
export FMP_API_KEY=your_key
export OPENAI_API_KEY=your_key
python scripts/generate_articles.py
```

## GitHub Secrets

| Secret | 内容 |
|--------|------|
| `FMP_API_KEY` | Financial Modeling Prep APIキー |
| `OPENAI_API_KEY` | DeepSeek or OpenAI APIキー |
| `OPENAI_BASE_URL` | `https://api.deepseek.com` |
| `OPENAI_MODEL` | `deepseek-chat` |
| `VERCEL_DEPLOY_HOOK` | Vercel Deploy Hook URL（任意）|

## デプロイ

Vercel に GitHub リポジトリを連携するだけ。
`vercel.json` が自動で設定します。



## File: `vercel.json`

json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" },
    { "source": "/(.*)",     "destination": "/index.html" }
  ],
  "functions": {
    "api/stock/[ticker].py": {
      "runtime": "python3.9"
    }
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options",        "value": "DENY" }
      ]
    }
  ]
}



## File: `.github\workflows\daily-articles.yml`

yaml
name: Daily & Weekly Article Generation

on:
  schedule:
    - cron: '0 6 * * 1-5'   # 平日 UTC06:00 = JST15:00
    - cron: '0 0 * * 6'     # 土曜 UTC00:00 = JST09:00
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r shared/requirements-shared.txt
          pip install -r scripts/requirements-scripts.txt

      - name: Generate articles
        env:
          FMP_API_KEY:     ${{ secrets.FMP_API_KEY }}
          OPENAI_API_KEY:  ${{ secrets.OPENAI_API_KEY }}
          OPENAI_BASE_URL: ${{ secrets.OPENAI_BASE_URL }}
          OPENAI_MODEL:    ${{ secrets.OPENAI_MODEL }}
        run: python scripts/generate_articles.py

      - name: Generate sitemap & robots.txt
        run: python scripts/generate_sitemap.py

      - name: Commit and push
        run: |
          git config user.name  "sentinel-bot"
          git config user.email "bot@sentinel-pro.app"
          git add frontend/public/content/ \
                  frontend/public/sitemap.xml \
                  frontend/public/robots.txt
          git diff --staged --quiet && echo "No changes" || \
            git commit -m "📊 $(date +'%Y-%m-%d') update" && git push

      - name: Trigger Vercel redeploy
        if: success()
        run: |
          [ -n "${{ secrets.VERCEL_DEPLOY_HOOK }}" ] && \
            curl -X POST "${{ secrets.VERCEL_DEPLOY_HOOK }}" && \
            echo "✅ Vercel redeploy triggered" || true



## File: `api\stock\[ticker].py`

py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / 'shared'))

from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer
from engines.config import CONFIG
import pandas as pd


def handler(request):
    ticker = request.path_params.get('ticker', '').upper().strip()
    if not ticker:
        return {"error": "ticker is required"}, 400

    df = core_fmp.get_historical_data(ticker, days=700)
    if df is None or len(df) < 200:
        return {"error": f"Insufficient data for {ticker}"}, 404

    vcp      = VCPAnalyzer.calculate(df)
    rs_raw   = RSAnalyzer.get_raw_score(df)
    rs_rating = min(99, max(1, int((rs_raw + 1) * 50)))

    # 最新クォート（リアルタイム価格優先）
    quote = core_fmp.get_quote(ticker)
    price = float(quote.get('price', 0)) if quote else float(df['Close'].iloc[-1])
    if not price:
        price = float(df['Close'].iloc[-1])

    # トレードレベル計算
    pivot  = float(df['High'].iloc[-20:].max())
    entry  = round(pivot * 1.002, 2)
    stop   = round(entry - vcp['atr'] * CONFIG['STOP_LOSS_ATR'], 2)
    target = round(entry + (entry - stop) * CONFIG['TARGET_R_MULTIPLE'], 2)
    dist   = (price - pivot) / pivot * 100
    status = "ACTION" if -5 <= dist <= 3 else ("WAIT" if dist < -5 else "EXTENDED")

    # ローソク足データ（直近180日）
    cutoff  = df.index[-1] - pd.DateOffset(days=180)
    df_plot = df[df.index >= cutoff]
    candles = [
        {
            "date":   d.strftime("%Y-%m-%d"),
            "open":   round(float(r["Open"]),  2),
            "high":   round(float(r["High"]),  2),
            "low":    round(float(r["Low"]),   2),
            "close":  round(float(r["Close"]), 2),
            "volume": int(r["Volume"]),
        }
        for d, r in df_plot.iterrows()
    ]

    # 会社プロフィール
    profile = core_fmp.get_company_profile(ticker) or {}

    return {
        "ticker":   ticker,
        "status":   status,
        "price":    round(price, 2),
        "dist_pct": round(dist, 2),
        "vcp":      vcp,
        "rs":       rs_rating,
        "trade": {
            "entry":  entry,
            "stop":   stop,
            "target": target,
        },
        "profile": {
            "sector":      profile.get("sector", "N/A"),
            "industry":    profile.get("industry", "N/A"),
            "description": profile.get("description", ""),
            "exchange":    profile.get("exchangeShortName", ""),
        },
        "candles": candles,
    }



## File: `frontend\index.html`

html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />

    <!-- ── デフォルトSEO（useSEO.js が上書きする）──────── -->
    <title>SENTINEL PRO — 米国株VCP×RSスクリーニング</title>
    <meta name="description"
          content="VCP（ボラティリティ収縮パターン）とRSレーティングによる米国株定量スクリーニング。毎日自動生成の分析レポートを日英で提供。" />
    <meta name="robots" content="index, follow" />
    <meta name="author"  content="SENTINEL PRO" />
    <link rel="canonical" href="https://sentinel-pro.vercel.app/" />

    <!-- ── OGP デフォルト ──────────────────────────────── -->
    <meta property="og:type"        content="website" />
    <meta property="og:site_name"   content="SENTINEL PRO" />
    <meta property="og:title"       content="SENTINEL PRO — 米国株VCP×RSスクリーニング" />
    <meta property="og:description" content="VCPとRSレーティングで優良セットアップを自動検出。毎日の分析レポートを日英で配信。" />
    <meta property="og:url"         content="https://sentinel-pro.vercel.app/" />
    <meta property="og:image"       content="https://sentinel-pro.vercel.app/og-default.png" />
    <meta property="og:locale"      content="ja_JP" />
    <meta property="og:locale:alternate" content="en_US" />

    <!-- ── Twitter Card ───────────────────────────────── -->
    <meta name="twitter:card"        content="summary_large_image" />
    <meta name="twitter:title"       content="SENTINEL PRO — 米国株VCP×RSスクリーニング" />
    <meta name="twitter:description" content="VCPとRSレーティングで優良セットアップを自動検出。" />
    <meta name="twitter:image"       content="https://sentinel-pro.vercel.app/og-default.png" />

    <!-- ── Favicon ────────────────────────────────────── -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />

    <!-- ── Google AdSense ─────────────────────────────── -->
    <!-- 審査通過後に ca-pub-XXXXXXXXXX を自分のIDに変更 -->
    <script async
      src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXX"
      crossorigin="anonymous">
    </script>

    <!-- ── Google Search Console 確認用 ──────────────── -->
    <!-- 取得後にコメントアウトを外す -->
    <!-- <meta name="google-site-verification" content="XXXXXXXXXX" /> -->

    <!-- ── JSON-LD WebSite スキーマ（デフォルト）─────── -->
    <script type="application/ld+json" id="json-ld">
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "SENTINEL PRO",
      "url": "https://sentinel-pro.vercel.app",
      "description": "VCP×RSレーティングによる米国株定量スクリーニングサービス",
      "inLanguage": ["ja-JP", "en-US"],
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://sentinel-pro.vercel.app/blog?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    }
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>



## File: `frontend\package.json`

json
{
  "name": "sentinel-pro-frontend",
  "private": true,
  "version": "3.0.0",
  "type": "module",
  "scripts": {
    "dev":     "vite",
    "build":   "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react":            "^18.3.1",
    "react-dom":        "^18.3.1",
    "react-router-dom": "^6.26.0",
    "react-markdown":   "^9.0.1",
    "recharts":         "^2.12.7",
    "lucide-react":     "^0.447.0",
    "date-fns":         "^3.6.0",
    "clsx":             "^2.1.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite":                 "^5.4.1",
    "tailwindcss":          "^3.4.10",
    "autoprefixer":         "^10.4.20",
    "postcss":              "^8.4.45"
  }
}



## File: `frontend\postcss.config.js`

js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}



## File: `frontend\tailwind.config.js`

js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Syne"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
        body:    ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        ink:    '#080C10',
        panel:  '#0E1318',
        border: '#1C2530',
        muted:  '#3D4F63',
        dim:    '#7A90A8',
        text:   '#D4E2F0',
        bright: '#EBF4FF',
        green:  { DEFAULT: '#22C55E', dim: '#16532A', glow: '#22C55E40' },
        amber:  { DEFAULT: '#F59E0B', dim: '#78350F' },
        red:    { DEFAULT: '#EF4444', dim: '#7F1D1D' },
        blue:   { DEFAULT: '#3B82F6', dim: '#1E3A5F' },
      },
      backgroundImage: {
        'grid-pattern': `
          linear-gradient(rgba(28,37,48,0.6) 1px, transparent 1px),
          linear-gradient(90deg, rgba(28,37,48,0.6) 1px, transparent 1px)
        `,
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'fade-up':   'fadeUp 0.5s ease forwards',
        'pulse-dot': 'pulseDot 2s ease-in-out infinite',
        'scan-line': 'scanLine 3s linear infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: 0, transform: 'translateY(16px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%,100%': { opacity: 1, transform: 'scale(1)' },
          '50%':     { opacity: 0.4, transform: 'scale(0.8)' },
        },
        scanLine: {
          from: { transform: 'translateY(-100%)' },
          to:   { transform: 'translateY(400%)' },
        },
      },
    },
  },
  plugins: [],
}



## File: `frontend\vite.config.js`

js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          icons:  ['lucide-react'],
        },
      },
    },
  },
});



## File: `frontend\public\content\index.json`

json
[]



## File: `frontend\src\App.jsx`

javascript
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Navbar        from './components/layout/Navbar';
import Landing       from './pages/Landing';
import Blog          from './pages/Blog';
import ArticleDetail from './pages/ArticleDetail';
import ToolPage      from './pages/ToolPage';
import Privacy       from './pages/Privacy';

function Footer() {
  return (
    <footer className="border-t border-border bg-panel py-6 px-4 mt-auto">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="font-mono text-xs text-muted">
          © 2026 SENTINEL PRO — For educational purposes only. Not investment advice.
        </div>
        <div className="flex items-center gap-4">
          <Link to="/blog"    className="font-mono text-xs text-muted hover:text-dim transition">Blog</Link>
          <Link to="/tool"    className="font-mono text-xs text-muted hover:text-dim transition">Tool</Link>
          <Link to="/privacy" className="font-mono text-xs text-muted hover:text-dim transition">Privacy</Link>
        </div>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/"           element={<Landing />} />
            <Route path="/blog"       element={<Blog />} />
            <Route path="/blog/:slug" element={<ArticleDetail />} />
            <Route path="/tool"       element={<ToolPage />} />
            <Route path="/privacy"    element={<Privacy />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}



## File: `frontend\src\index.css`

css
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    background-color: #080C10;
    color: #D4E2F0;
    font-family: 'DM Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  ::selection { background: #22C55E30; color: #EBF4FF; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #080C10; }
  ::-webkit-scrollbar-thumb { background: #1C2530; border-radius: 3px; }
}

@layer components {
  .btn-primary {
    @apply px-5 py-2.5 bg-green rounded-lg font-body font-medium text-ink
    hover:brightness-110 active:scale-95 transition-all duration-150;
  }
  .btn-ghost {
    @apply px-5 py-2.5 border border-border rounded-lg font-body font-medium text-dim
    hover:border-muted hover:text-text transition-all duration-150;
  }
  .card {
    @apply bg-panel border border-border rounded-xl;
  }
  .tag-action { @apply text-xs font-mono px-2 py-0.5 rounded bg-green-dim text-green; }
  .tag-wait   { @apply text-xs font-mono px-2 py-0.5 rounded bg-amber-dim text-amber; }
  .tag-ext    { @apply text-xs font-mono px-2 py-0.5 rounded bg-muted/20 text-dim; }
}



## File: `frontend\src\main.jsx`

javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);



## File: `frontend\src\components\layout\Navbar.jsx`

javascript
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, Menu, X } from 'lucide-react';

const NAV_LINKS = [
  { to: '/blog',    label: 'Research' },
  { to: '/tool',    label: 'Tool'     },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-ink/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-7 h-7 rounded-md bg-green/10 border border-green/30
                          flex items-center justify-center group-hover:bg-green/20 transition">
            <Shield size={14} className="text-green" />
          </div>
          <span className="font-display font-700 text-bright text-sm tracking-wide">SENTINEL</span>
          <span className="font-mono text-xs text-green px-1.5 py-0.5 bg-green/10 rounded border border-green/20">PRO</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(l => (
            <Link key={l.to} to={l.to}
              className={`px-3 py-1.5 text-sm rounded-md transition font-body ${
                loc.pathname.startsWith(l.to)
                  ? 'text-bright bg-border'
                  : 'text-dim hover:text-text hover:bg-border/50'
              }`}>{l.label}</Link>
          ))}
        </div>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-2">
          <Link to="/tool#contact"
            className="px-4 py-1.5 rounded-lg bg-green/10 border border-green/20
                       font-mono text-xs text-green hover:bg-green/20 transition">
            利用問い合わせ
          </Link>
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden text-dim" onClick={() => setOpen(!open)}>
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-border bg-panel px-4 py-4 space-y-1">
          {NAV_LINKS.map(l => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)}
              className="block px-3 py-2 text-sm text-dim hover:text-text rounded-md
                         hover:bg-border/50 transition">
              {l.label}
            </Link>
          ))}
          <div className="pt-2 border-t border-border mt-2">
            <Link to="/tool#contact" onClick={() => setOpen(false)}
              className="block text-center px-3 py-2 rounded-lg bg-green/10 border border-green/20
                         font-mono text-xs text-green">
              利用問い合わせ
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}



## File: `frontend\src\hooks\useSEO.js`

js
import { useEffect } from 'react';

const SITE_NAME = 'SENTINEL PRO';
const BASE_URL  = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_SITE_URL)
                    || 'https://sentinel-pro.vercel.app';
const DEFAULT_OG_IMAGE = `${BASE_URL}/og-default.png`;

export function useSEO({
  title,
  description,
  url,
  image,
  type    = 'website',
  lang    = 'ja',
  article = null,
} = {}) {
  useEffect(() => {
    const fullTitle = title ? `${title} | ${SITE_NAME}` : SITE_NAME;
    const ogImage   = image || DEFAULT_OG_IMAGE;
    // canonical は effect 内で取得 → SPA ナビゲーション後も正確なパスになる
    const canonical = url || (BASE_URL + window.location.pathname);

    // ── <title> ──────────────────────────────────────────
    document.title = fullTitle;

    // ── <html lang> ──────────────────────────────────────
    document.documentElement.lang = lang === 'en' ? 'en' : 'ja';

    // ── helpers ───────────────────────────────────────────
    const setMeta = (attr, attrVal, content) => {
      if (!content) return;
      let el = document.querySelector(`meta[${attr}="${attrVal}"]`);
      if (!el) {
        el = document.createElement('meta');
        el.setAttribute(attr, attrVal);
        document.head.appendChild(el);
      }
      el.setAttribute('content', content);
    };
    const setLink = (rel, href) => {
      let el = document.querySelector(`link[rel="${rel}"]`);
      if (!el) {
        el = document.createElement('link');
        el.setAttribute('rel', rel);
        document.head.appendChild(el);
      }
      el.setAttribute('href', href);
    };

    // ── Basic meta ────────────────────────────────────────
    setMeta('name', 'description', description);
    setMeta('name', 'robots',      'index, follow');
    setMeta('name', 'author',      SITE_NAME);
    setLink('canonical', canonical);

    // ── OGP ───────────────────────────────────────────────
    setMeta('property', 'og:title',       fullTitle);
    setMeta('property', 'og:description', description);
    setMeta('property', 'og:url',         canonical);
    setMeta('property', 'og:image',       ogImage);
    setMeta('property', 'og:type',        type);
    setMeta('property', 'og:site_name',   SITE_NAME);
    setMeta('property', 'og:locale',      lang === 'en' ? 'en_US' : 'ja_JP');

    // ── Twitter Card ──────────────────────────────────────
    setMeta('name', 'twitter:card',        'summary_large_image');
    setMeta('name', 'twitter:title',       fullTitle);
    setMeta('name', 'twitter:description', description);
    setMeta('name', 'twitter:image',       ogImage);

    // ── JSON-LD ───────────────────────────────────────────
    const existingLD = document.getElementById('json-ld');
    if (existingLD) existingLD.remove();

    const schema = (type === 'article' && article) ? {
      '@context':    'https://schema.org',
      '@type':       'Article',
      headline:      fullTitle,
      description,
      url:           canonical,
      image:         ogImage,
      datePublished: article.published_at,
      dateModified:  article.published_at,
      author:     { '@type': 'Organization', name: SITE_NAME, url: BASE_URL },
      publisher:  {
        '@type': 'Organization', name: SITE_NAME,
        logo: { '@type': 'ImageObject', url: `${BASE_URL}/logo.png` },
      },
      inLanguage: lang === 'en' ? 'en-US' : 'ja-JP',
      ...(article.ticker ? {
        about: { '@type': 'Corporation', tickerSymbol: article.ticker, exchange: 'NASDAQ' },
      } : {}),
    } : {
      '@context':  'https://schema.org',
      '@type':     'WebSite',
      name:        SITE_NAME,
      url:         BASE_URL,
      description: 'VCP×RSレーティングによる米国株定量スクリーニングサービス',
      inLanguage:  ['ja-JP', 'en-US'],
      potentialAction: {
        '@type':       'SearchAction',
        target:        `${BASE_URL}/blog?q={search_term_string}`,
        'query-input': 'required name=search_term_string',
      },
    };

    const script  = document.createElement('script');
    script.id     = 'json-ld';
    script.type   = 'application/ld+json';
    script.text   = JSON.stringify(schema);
    document.head.appendChild(script);

    return () => { document.title = SITE_NAME; };
  }, [title, description, url, image, type, lang, JSON.stringify(article)]);
}



## File: `frontend\src\pages\ArticleDetail.jsx`

javascript
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { Calendar, ChevronLeft, Loader, RefreshCw, TrendingUp,
         ExternalLink, Newspaper, Users, BarChart2, TrendingDown } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useSEO } from '../hooks/useSEO';

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

// ── チャート画像（Base64） ───────────────────────────────
function CandleChart({ chart_b64, ticker }) {
  if (!chart_b64) return null;
  return (
    <div className="my-6 not-prose rounded-xl overflow-hidden border border-border">
      <img src={`data:image/png;base64,${chart_b64}`}
           alt={`${ticker} candlestick chart`}
           className="w-full" loading="lazy"/>
    </div>
  );
}

// ── VCPスコア推移グラフ ──────────────────────────────────
function StockHistoryChart({ history, lang }) {
  if (!history?.length) return null;
  const data = [...history].reverse().slice(-30).map(h => ({
    date: h.date?.slice(5), vcp: h.vcp??0, rs: h.rs??0,
  }));
  return (
    <div className="my-4 bg-ink border border-border rounded-xl p-4 not-prose">
      <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
        <TrendingUp size={11}/> {lang==='ja'?'スコア推移（直近30日）':'Score History (30d)'}
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[{key:'vcp',color:'#22C55E',max:105,label:'VCP'},
          {key:'rs', color:'#3B82F6',max:99, label:'RS'}].map(c => (
          <div key={c.key}>
            <div className="font-mono text-xs mb-1" style={{color:c.color}}>{c.label}</div>
            <ResponsiveContainer width="100%" height={70}>
              <LineChart data={data}>
                <XAxis dataKey="date" tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false} axisLine={false} interval="preserveStartEnd"/>
                <YAxis domain={[0,c.max]} tick={{fontSize:8,fill:'#3D4F63'}} tickLine={false} axisLine={false} width={18}/>
                <Tooltip contentStyle={{background:'#0E1318',border:'1px solid #1C2530',borderRadius:'6px',fontSize:'10px'}} labelStyle={{color:'#7A90A8'}}/>
                <ReferenceLine y={c.key==='vcp'?70:80} stroke={c.color} strokeDasharray="3 3" strokeOpacity={0.3}/>
                <Line type="monotone" dataKey={c.key} stroke={c.color} strokeWidth={1.5} dot={false}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 銘柄スコアパネル ─────────────────────────────────────
function StockDataPanel({ data, lang }) {
  if (!data?.ticker) return null;
  const bd     = data.vcp_breakdown ?? {};
  const an     = data.analyst       ?? {};
  const fund   = data.fundamentals  ?? {};
  const own    = data.ownership     ?? {};
  const news   = data.news          ?? [];

  const rr = data.entry && data.stop && data.target
    ? ((data.target - data.entry) / (data.entry - data.stop)).toFixed(1) : null;

  return (
    <div className="my-6 not-prose space-y-3">

      {/* ① スコアカード */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {[
          {label:'VCP Score', val:`${data.vcp}/105`, hi:data.vcp>=70,  color:'text-green'},
          {label:'RS Rating', val:`${data.rs}/99`,   hi:data.rs>=80,   color:'text-blue'},
          {label:'Status',    val:data.status,       hi:data.status==='ACTION', color:data.status==='ACTION'?'text-green':'text-amber'},
          {label:'Price',     val:`$${data.price}`,  hi:false, color:'text-bright'},
        ].map(c => (
          <div key={c.label} className="bg-panel border border-border rounded-xl p-3">
            <div className="font-mono text-xs text-muted mb-1">{c.label}</div>
            <div className={`font-display text-xl font-700 ${c.hi ? c.color : 'text-bright'}`}>{c.val}</div>
          </div>
        ))}
      </div>

      {/* ② トレードパラメータ */}
      {data.entry && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">
            {lang==='ja'?'参考トレードパラメータ（教育目的）':'Reference Trade Parameters (Educational)'}
          </div>
          <div className="grid grid-cols-3 gap-3 mb-2">
            {[{l:lang==='ja'?'エントリー目安':'Entry Ref',v:`$${data.entry}`,c:'text-bright'},
              {l:lang==='ja'?'ストップロス':'Stop Loss',v:`$${data.stop}`,c:'text-red'},
              {l:lang==='ja'?'ターゲット':'Target',v:`$${data.target}`,c:'text-green'}].map(p => (
              <div key={p.l} className="text-center">
                <div className="font-mono text-xs text-muted">{p.l}</div>
                <div className={`font-mono text-sm font-700 mt-0.5 ${p.c}`}>{p.v}</div>
              </div>
            ))}
          </div>
          {rr && <div className="text-center pt-2 border-t border-border font-mono text-xs text-muted">
            RR: <span className="text-bright font-700">1 : {rr}</span>
          </div>}
        </div>
      )}

      {/* ③ VCPブレイクダウン */}
      <div className="bg-panel border border-border rounded-xl p-4">
        <div className="font-mono text-xs text-muted mb-3">
          {lang==='ja'?'VCPスコア内訳':'VCP Breakdown'}
        </div>
        <div className="space-y-2.5">
          {[{l:'Tightness',d:lang==='ja'?'値動き収縮':'Price tightness',v:bd.tight??0,max:40},
            {l:'Volume',   d:lang==='ja'?'出来高収縮':'Volume dry-up',  v:bd.vol??0,  max:30},
            {l:'MA Align', d:lang==='ja'?'移動平均の並び':'MA alignment', v:bd.ma??0,   max:30},
            {l:'Pivot',    d:lang==='ja'?'ピボット近接':'Pivot proximity',v:bd.pivot??0,max:5},
          ].map(b => (
            <div key={b.l}>
              <div className="flex justify-between mb-0.5">
                <span className="font-mono text-xs text-dim">{b.l} <span className="text-muted/60">{b.d}</span></span>
                <span className={`font-mono text-xs font-700 ${b.v/b.max>=0.8?'text-green':b.v/b.max>=0.5?'text-amber':'text-dim'}`}>{b.v}/{b.max}</span>
              </div>
              <div className="h-1.5 bg-border rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{
                  width:`${Math.min(100,(b.v/b.max)*100)}%`,
                  background:b.v/b.max>=0.8?'#22C55E':b.v/b.max>=0.5?'#F59E0B':'#3D4F63'
                }}/>
              </div>
            </div>
          ))}
          <div className="flex justify-between pt-2 border-t border-border font-mono text-xs">
            <span className="text-muted">{lang==='ja'?'合計':'Total'}</span>
            <span className={`font-700 ${data.vcp>=70?'text-green':data.vcp>=50?'text-amber':'text-muted'}`}>
              {data.vcp}/105
            </span>
          </div>
        </div>
        {data.signals?.length>0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border">
            {data.signals.map(s => (
              <span key={s} className="font-mono text-xs px-2 py-0.5 rounded bg-green/10 border border-green/20 text-green">{s}</span>
            ))}
          </div>
        )}
      </div>

      {/* ④ ファンダメンタル */}
      {Object.keys(fund).length>0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <BarChart2 size={11}/> {lang==='ja'?'ファンダメンタル':'Fundamentals'}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {[
              {l:lang==='ja'?'予想PER':'Fwd P/E',          v:fund.pe_forward,     fmt:(v)=>`${v}x`},
              {l:lang==='ja'?'売上成長率(YoY)':'Rev Growth', v:fund.revenue_growth_yoy, fmt:(v)=>{
                const n=parseFloat(v); return <span className={n>=0?'text-green':'text-red'}>{n>=0?'+':''}{v}%</span>;
              }},
              {l:lang==='ja'?'利益成長率(YoY)':'EPS Growth', v:fund.earnings_growth_yoy, fmt:(v)=>{
                const n=parseFloat(v); return <span className={n>=0?'text-green':'text-red'}>{n>=0?'+':''}{v}%</span>;
              }},
              {l:'ROE',     v:fund.roe,          fmt:(v)=>`${v}%`},
              {l:lang==='ja'?'粗利率':'Gross Margin', v:fund.gross_margin, fmt:(v)=>`${v}%`},
              {l:lang==='ja'?'時価総額':'Mkt Cap',    v:fund.market_cap_b, fmt:(v)=>`$${v}B`},
            ].map(f => f.v!=null && (
              <div key={f.l} className="bg-ink rounded-lg p-2.5">
                <div className="font-mono text-xs text-muted">{f.l}</div>
                <div className="font-mono text-sm font-700 text-bright mt-0.5">
                  {typeof f.fmt(f.v) === 'object' ? f.fmt(f.v) : f.fmt(f.v)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ⑤ アナリスト評価 */}
      {Object.keys(an).length>0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <Users size={11}/> {lang==='ja'?`アナリスト評価（${an.analyst_count||0}名）`:`Analyst Consensus (${an.analyst_count||0})`}
          </div>
          <div className="flex items-center gap-4 mb-3">
            <span className={`font-display text-2xl font-700 ${
              an.consensus==='Buy'?'text-green':an.consensus==='Sell'?'text-red':'text-amber'}`}>
              {an.consensus}
            </span>
            {an.target_mean && (
              <div>
                <div className="font-mono text-xs text-muted">{lang==='ja'?'目標株価（平均）':'Price Target (Mean)'}</div>
                <div className="font-mono text-sm font-700 text-bright">
                  ${an.target_mean}
                  {an.target_pct != null && (
                    <span className={`ml-2 text-xs ${an.target_pct>=0?'text-green':'text-red'}`}>
                      {an.target_pct>=0?'+':''}{an.target_pct}%
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
          {/* Buy/Hold/Sell バー */}
          {(an.buy||an.hold||an.sell) && (() => {
            const total = (an.buy||0)+(an.hold||0)+(an.sell||0);
            return (
              <div>
                <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
                  <div className="bg-green"    style={{width:`${((an.buy||0)/total)*100}%`}}/>
                  <div className="bg-amber"    style={{width:`${((an.hold||0)/total)*100}%`}}/>
                  <div className="bg-red"      style={{width:`${((an.sell||0)/total)*100}%`}}/>
                </div>
                <div className="flex justify-between mt-1 font-mono text-xs text-muted">
                  <span className="text-green">Buy {an.buy||0}</span>
                  <span className="text-amber">Hold {an.hold||0}</span>
                  <span className="text-red">Sell {an.sell||0}</span>
                </div>
              </div>
            );
          })()}
          {an.target_high && an.target_low && (
            <div className="mt-2 pt-2 border-t border-border font-mono text-xs text-muted">
              {lang==='ja'?'目標株価レンジ':'Target Range'}: <span className="text-bright">${an.target_low} — ${an.target_high}</span>
            </div>
          )}
        </div>
      )}

      {/* ⑥ 投資家動向（機関・空売り） */}
      {Object.keys(own).some(k=>own[k]!=null) && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <TrendingDown size={11}/> {lang==='ja'?'投資家動向':'Investor Activity'}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {[
              {l:lang==='ja'?'機関投資家保有率':'Inst. Ownership', v:own.institutional_pct,   fmt:(v)=>`${v}%`},
              {l:lang==='ja'?'インサイダー保有率':'Insider Own.',   v:own.insider_pct,         fmt:(v)=>`${v}%`},
              {l:lang==='ja'?'空売り比率':'Short Float',           v:own.short_float_pct,     fmt:(v)=><span className={parseFloat(v)>15?'text-red':parseFloat(v)>8?'text-amber':'text-green'}>{v}%</span>},
              {l:lang==='ja'?'空売り日数':'Days to Cover',         v:own.short_days_to_cover, fmt:(v)=>`${v}d`},
            ].map(f => f.v!=null && (
              <div key={f.l} className="bg-ink rounded-lg p-2.5">
                <div className="font-mono text-xs text-muted">{f.l}</div>
                <div className="font-mono text-sm font-700 text-bright mt-0.5">
                  {typeof f.fmt(f.v)==='object' ? f.fmt(f.v) : f.fmt(f.v)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ⑦ 直近ニュース */}
      {news.length>0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3 flex items-center gap-2">
            <Newspaper size={11}/> {lang==='ja'?'直近ニュース':'Recent News'}
          </div>
          <div className="space-y-2">
            {news.slice(0,4).map((n,i) => (
              <a key={i} href={n.url} target="_blank" rel="noopener noreferrer"
                 className="block group">
                <div className="flex items-start gap-2">
                  <ExternalLink size={10} className="text-muted mt-1 shrink-0 group-hover:text-green transition"/>
                  <div>
                    <p className="font-body text-xs text-dim group-hover:text-text transition leading-snug">{n.title}</p>
                    <p className="font-mono text-xs text-muted mt-0.5">{n.source} · {n.published_at?.slice(0,10)}</p>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── VCPランキングテーブル ────────────────────────────────
function VCPRankingTable({ ranking, lang }) {
  if (!ranking?.length) return null;
  return (
    <div className="my-6 not-prose">
      <div className="bg-ink border border-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <span className="font-mono text-xs text-muted">{lang==='ja'?'VCPスコアランキング':'VCP Ranking'}</span>
          <span className="font-mono text-xs text-muted">{lang==='ja'?'↑ ティッカーで個別ページへ':'↑ Click ticker for details'}</span>
        </div>
        <div className="grid grid-cols-[28px_64px_1fr_56px_56px_72px_64px] gap-2 px-4 py-2 border-b border-border/50">
          {['#','Ticker','Name','VCP','RS','Status','Price'].map(h=>(
            <span key={h} className="font-mono text-xs text-muted">{h}</span>
          ))}
        </div>
        <div className="divide-y divide-border/30">
          {ranking.slice(0,20).map(r => (
            <Link key={r.ticker} to={`/blog/stock-${r.ticker.toLowerCase()}`}
              className="grid grid-cols-[28px_64px_1fr_56px_56px_72px_64px] gap-2 px-4 py-2.5
                         hover:bg-panel/60 transition group items-center">
              <span className="font-mono text-xs text-muted">{r.rank}</span>
              <span className="font-mono text-xs text-bright font-700 group-hover:text-green transition flex items-center gap-1">
                {r.ticker}<ExternalLink size={9} className="opacity-0 group-hover:opacity-60 transition"/>
              </span>
              <span className="font-body text-xs text-muted truncate">{r.name||r.ticker}</span>
              <div className="flex items-center gap-1">
                <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{
                    width:`${(r.vcp/105)*100}%`,
                    background:r.vcp>=80?'#22C55E':r.vcp>=60?'#F59E0B':'#3D4F63'
                  }}/>
                </div>
                <span className={`font-mono text-xs font-700 w-6 text-right ${r.vcp>=80?'text-green':r.vcp>=60?'text-amber':'text-dim'}`}>{r.vcp}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                  <div className="h-full bg-blue rounded-full" style={{width:`${(r.rs/99)*100}%`}}/>
                </div>
                <span className="font-mono text-xs font-700 text-blue w-6 text-right">{r.rs}</span>
              </div>
              <span className={`font-mono text-xs px-1.5 py-0.5 rounded text-center border ${
                r.status==='ACTION'?'bg-green/10 border-green/20 text-green':'bg-amber/10 border-amber/20 text-amber'}`}>
                {r.status}
              </span>
              <span className="font-mono text-xs text-dim text-right">${r.price}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 日次データパネル ─────────────────────────────────────
function DailyDataPanel({ data, lang }) {
  if (!data) return null;
  const { index={}, sector=[], vcp_ranking=[] } = data;
  return (
    <div className="my-6 space-y-4 not-prose">
      {Object.keys(index).length>0 && (
        <div className="bg-ink border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'本日の指数パフォーマンス':'Index Performance Today'}</div>
          <div className="grid grid-cols-3 gap-3">
            {Object.values(index).map(d => (
              <div key={d.name} className="text-center">
                <div className="font-mono text-xs text-muted">{d.name}</div>
                <div className={`font-mono text-base font-700 ${d.chg_1d>=0?'text-green':'text-red'}`}>
                  {d.chg_1d>=0?'+':''}{d.chg_1d}%
                </div>
                <div className="font-mono text-xs text-muted">${d.price}</div>
                <div className="font-mono text-xs text-muted">5d: {d.chg_5d>=0?'+':''}{d.chg_5d}%</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {sector.length>0 && (
        <div className="bg-ink border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'セクター強度（平均RS）':'Sector Strength (Avg RS)'}</div>
          <div className="space-y-2">
            {sector.slice(0,8).map(s => (
              <div key={s.sector} className="flex items-center gap-3">
                <span className="font-mono text-xs text-dim w-28 truncate">{s.sector}</span>
                <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{
                    width:`${Math.min(100,(s.avg_rs/99)*100)}%`,
                    background:s.avg_rs>=85?'#22C55E':s.avg_rs>=70?'#F59E0B':'#3D4F63'
                  }}/>
                </div>
                <span className="font-mono text-xs text-bright w-7 text-right font-700">{s.avg_rs}</span>
                {s.action_count>0 && <span className="font-mono text-xs text-green w-10">▲{s.action_count}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
      {vcp_ranking.length>0 && <VCPRankingTable ranking={vcp_ranking} lang={lang}/>}
    </div>
  );
}

// ── 週次データパネル ─────────────────────────────────────
function WeeklyDataPanel({ data, lang }) {
  if (!data) return null;
  const { index={}, sector=[], vcp_ranking=[] } = data;
  return (
    <div className="my-6 space-y-4 not-prose">
      {Object.keys(index).length>0 && (
        <div className="bg-ink border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'週次パフォーマンス（5d）':'Weekly Performance (5d)'}</div>
          <div className="grid grid-cols-3 gap-3">
            {Object.values(index).map(d => (
              <div key={d.name} className="text-center">
                <div className="font-mono text-xs text-muted">{d.name}</div>
                <div className={`font-mono text-base font-700 ${(d.chg_5d??0)>=0?'text-green':'text-red'}`}>
                  {(d.chg_5d??0)>=0?'+':''}{d.chg_5d}%
                </div>
                <div className="font-mono text-xs text-muted">5d</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {sector.length>0 && (
        <div className="bg-ink border border-border rounded-xl p-4">
          <div className="font-mono text-xs text-muted mb-3">{lang==='ja'?'セクター週間強度':'Sector Weekly Strength'}</div>
          <div className="space-y-2">
            {sector.slice(0,6).map(s => (
              <div key={s.sector} className="flex items-center gap-3">
                <span className="font-mono text-xs text-dim w-28 truncate">{s.sector}</span>
                <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{
                    width:`${Math.min(100,(s.avg_rs/99)*100)}%`,
                    background:s.avg_rs>=85?'#22C55E':s.avg_rs>=70?'#F59E0B':'#3D4F63'
                  }}/>
                </div>
                <span className="font-mono text-xs text-bright w-7 text-right">{s.avg_rs}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {vcp_ranking.length>0 && <VCPRankingTable ranking={vcp_ranking} lang={lang}/>}
    </div>
  );
}

// ── メインページ ─────────────────────────────────────────
export default function ArticleDetail() {
  const { slug }  = useParams();
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lang,    setLang]    = useState('ja');

  useEffect(() => {
    let url = '';
    if      (slug.startsWith('daily-'))  url = `/content/daily/${slug.replace('daily-','')}.json`;
    else if (slug.startsWith('weekly-')) url = `/content/weekly/${slug.replace('weekly-','')}.json`;
    else if (slug.startsWith('stock-'))  url = `/content/stocks/${slug.replace('stock-','').toUpperCase()}.json`;
    if (!url) { setLoading(false); return; }
    fetch(url).then(r=>r.ok?r.json():null).then(d=>{setArticle(d);setLoading(false);}).catch(()=>setLoading(false));
  }, [slug]);

  const t = article?.[lang] ?? article?.ja;
  useSEO({ title:t?.title, description:t?.summary,
           type:article?'article':'website', lang,
           article:article?{published_at:article.published_at,ticker:article.ticker}:null });

  if (loading) return <div className="min-h-screen bg-ink pt-24 flex items-center justify-center"><Loader size={24} className="text-muted animate-spin"/></div>;
  if (!article) return (
    <div className="min-h-screen bg-ink pt-24 px-4">
      <div className="max-w-3xl mx-auto text-center mt-20">
        <p className="font-body text-muted">記事が見つかりません</p>
        <Link to="/blog" className="text-green font-mono text-xs hover:underline mt-2 block">← Back to Blog</Link>
      </div>
    </div>
  );

  const TYPE_LABEL = {
    daily:  {ja:'日次レポート',en:'Daily Report',  color:'text-green border-green/30 bg-green/10'},
    weekly: {ja:'週次レポート',en:'Weekly Report', color:'text-blue  border-blue/30  bg-blue/10'},
    stock:  {ja:'銘柄分析',    en:'Stock Analysis',color:'text-amber border-amber/30 bg-amber/10'},
  };
  const tm = TYPE_LABEL[article.type] ?? TYPE_LABEL.stock;

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-3xl mx-auto mb-4">
        <div className="rounded-xl overflow-hidden bg-panel border border-border min-h-[90px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block',width:'100%'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX"
               data-ad-format="horizontal" data-full-width-responsive="true"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto">
        <Link to="/blog" className="inline-flex items-center gap-1 font-mono text-xs text-muted hover:text-dim mb-6">
          <ChevronLeft size={12}/> {lang==='ja'?'レポート一覧':'All Reports'}
        </Link>

        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`font-mono text-xs px-2 py-0.5 rounded border ${tm.color}`}>
              {lang==='ja'?tm.ja:tm.en}
            </span>
            <span className="font-mono text-xs text-muted flex items-center gap-1">
              <Calendar size={10}/> {article.date}
            </span>
            {article.ticker && <span className="font-mono text-xs text-amber font-700">{article.ticker}</span>}
            {article.name   && <span className="font-body text-xs text-muted">{article.name}</span>}
            {article.type==='stock' && (
              <span className="font-mono text-xs text-green/60 flex items-center gap-1">
                <RefreshCw size={9}/> {lang==='ja'?'毎日更新':'Daily update'}
              </span>
            )}
          </div>
          <LangToggle lang={lang} setLang={setLang}/>
        </div>

        <h1 className="font-display font-700 text-bright text-2xl md:text-3xl leading-tight mb-3">{t?.title}</h1>
        <p className="font-body text-dim text-sm leading-relaxed mb-6 border-l-2 border-green/40 pl-4">{t?.summary}</p>

        {/* チャート（銘柄ページのみ） */}
        {article.type==='stock' && <CandleChart chart_b64={article.chart_b64} ticker={article.ticker}/>}

        {/* データビジュアル */}
        {article.type==='stock'  && <StockDataPanel data={article.data} lang={lang}/>}
        {article.type==='stock'  && <StockHistoryChart history={article.history} lang={lang}/>}
        {article.type==='daily'  && <DailyDataPanel  data={article.data} lang={lang}/>}
        {article.type==='weekly' && <WeeklyDataPanel data={article.data} lang={lang}/>}

        <div className="my-6 rounded-xl overflow-hidden bg-panel border border-border min-h-[250px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>

        <div className="prose prose-invert prose-sm max-w-none
          prose-headings:font-display prose-headings:text-bright prose-headings:font-700
          prose-p:font-body prose-p:text-dim prose-p:leading-relaxed
          prose-strong:text-text prose-code:font-mono prose-code:text-green
          prose-code:bg-panel prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
          prose-blockquote:border-green/40 prose-blockquote:text-muted
          prose-a:text-green prose-a:no-underline hover:prose-a:underline">
          <ReactMarkdown>{t?.body??''}</ReactMarkdown>
        </div>

        <div className="mt-8 rounded-xl overflow-hidden bg-panel border border-border min-h-[250px] flex items-center justify-center">
          <ins className="adsbygoogle" style={{display:'block'}}
               data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"/>
          <span className="font-mono text-xs text-muted/40">Ad</span>
        </div>

        <div className="mt-6 p-4 bg-panel border border-border rounded-xl">
          <p className="font-body text-xs text-muted leading-relaxed">
            {lang==='ja'
              ? '⚠️ 本記事はAIを活用した自動生成を含む教育目的のコンテンツです。投資助言ではありません。データはFMP APIを使用しており、遅延・誤差が含まれる場合があります。投資判断はご自身の責任で行ってください。'
              : '⚠️ AI-generated educational content. Not investment advice. Data via FMP API may contain delays. All investment decisions are your own responsibility.'}
          </p>
        </div>
      </div>
    </div>
  );
}



## File: `frontend\src\pages\Blog.jsx`

javascript
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



## File: `frontend\src\pages\Landing.jsx`

javascript
import { Link } from 'react-router-dom';
import { Shield, TrendingUp, Zap, BarChart3, ArrowRight, ChevronRight } from 'lucide-react';
import { useSEO } from '../hooks/useSEO';

const PROOF_TRADE = {
  ticker: 'GLW', company: 'Corning Inc.',
  entry: 116.00, exit: 130.30, gain: '+12.3%', days: 4, date: '2026年2月',
};

const FEATURES = [
  { icon: BarChart3,  title: 'RS Rating',         body: '全銘柄を相対強度でランク付け。市場の上位銘柄だけをスキャン対象に絞り込む。' },
  { icon: TrendingUp, title: 'VCP スコアリング',   body: 'Mark Minerviniのボラティリティ収縮パターンを定量化。最大105点のスコアで可視化。' },
  { icon: Zap,        title: '毎日自動スキャン',   body: 'GitHub Actionsが600+銘柄を毎日スキャン。翌朝には結果とAI解説記事が更新される。' },
  { icon: Shield,     title: 'リスク管理',         body: 'ATRベースのストップロス、ポジションサイジング、セクター分散を自動計算。' },
];

const STATS = [
  { value: '600+',    label: 'スキャン銘柄数' },
  { value: '毎日',    label: '自動更新'       },
  { value: '105pt',   label: 'VCPスコア最大値'},
  { value: '3種類',   label: 'レポート形式'   },
];

export default function Landing() {
  useSEO({
    title: 'SENTINEL PRO — ミネルヴィニ手法を自動化した米国株スキャナー',
    description: 'VCP×RSレーティングで600+銘柄を毎日自動スキャン。日次・週次レポートと銘柄個別分析をAIが自動生成。教育目的の定量スクリーニングツール。',
  });

  return (
    <div className="min-h-screen bg-ink overflow-hidden">
      <div className="fixed inset-0 bg-grid-pattern bg-grid opacity-40 pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-b from-ink via-transparent to-ink pointer-events-none" />

      {/* ── Hero ── */}
      <section className="relative pt-32 pb-20 px-4 max-w-6xl mx-auto">
        <div className="flex justify-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                          border border-green/30 bg-green/5 text-xs font-mono text-green">
            <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse-dot" />
            毎日自動スキャン稼働中 — 600+銘柄
          </div>
        </div>

        <h1 className="text-center font-display font-800 text-bright leading-tight mb-6"
            style={{ fontSize: 'clamp(2.4rem, 6vw, 4.5rem)' }}>
          ミネルヴィニ手法を<br />
          <span className="text-green">自動化</span>したスキャナー
        </h1>

        <p className="text-center text-dim font-body max-w-xl mx-auto mb-10 leading-relaxed"
           style={{ fontSize: 'clamp(0.95rem, 2vw, 1.1rem)' }}>
          RS Rating × VCP スコアで、600+銘柄から高確率セットアップを毎日自動抽出。<br />
          <span className="text-text">投資助言ではなく、データ教育ツールです。</span>
        </p>

        <div className="flex flex-wrap justify-center gap-3 mb-16">
          <Link to="/blog" className="btn-primary flex items-center gap-2 text-sm">
            今日のレポートを見る <ArrowRight size={15} />
          </Link>
          <Link to="/tool" className="btn-ghost flex items-center gap-2 text-sm">
            ツールについて <ChevronRight size={15} />
          </Link>
        </div>

        {/* Proof card */}
        <div className="max-w-lg mx-auto">
          <div className="card p-1 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-border/40 rounded-t-lg border-b border-border">
              <span className="font-mono text-xs text-dim">実際のトレード実績 — {PROOF_TRADE.date}</span>
              <span className="font-mono text-xs text-green flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green" />VERIFIED
              </span>
            </div>
            <div className="p-5 grid grid-cols-2 gap-4">
              <div>
                <div className="font-display font-700 text-bright text-3xl">{PROOF_TRADE.ticker}</div>
                <div className="font-body text-xs text-dim mt-0.5">{PROOF_TRADE.company}</div>
                <div className="mt-4 space-y-1.5">
                  {[['ENTRY', `$${PROOF_TRADE.entry.toFixed(2)}`],
                    ['EXIT',  `$${PROOF_TRADE.exit.toFixed(2)}`],
                    ['DAYS',  `${PROOF_TRADE.days} 営業日`]].map(([k,v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-muted font-mono">{k}</span>
                      <span className="text-text font-mono">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex flex-col items-end justify-between">
                <div className="text-right">
                  <div className="font-display font-800 text-green text-4xl">{PROOF_TRADE.gain}</div>
                  <div className="font-mono text-xs text-green/60 mt-1">{PROOF_TRADE.days}営業日</div>
                </div>
                <svg viewBox="0 0 80 32" className="w-full opacity-60">
                  <polyline points="0,28 14,24 28,20 42,15 56,10 70,5 80,2"
                    fill="none" stroke="#22C55E" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
            <div className="px-4 pb-3">
              <p className="text-xs text-muted font-body">
                ⚠️ 過去の実績は将来の結果を保証しません。データは教育目的です。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="border-y border-border bg-panel/50">
        <div className="max-w-6xl mx-auto px-4 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map(s => (
            <div key={s.label} className="text-center">
              <div className="font-display font-700 text-bright text-2xl">{s.value}</div>
              <div className="font-body text-xs text-dim mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="relative py-20 px-4 max-w-6xl mx-auto">
        <h2 className="font-display font-700 text-center text-bright text-3xl mb-2">機能概要</h2>
        <p className="text-center text-dim text-sm mb-12">プロのトレーダーが使う手法を、誰でも使えるツールに</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="card p-6 hover:border-muted transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-green/10 border border-green/20
                              flex items-center justify-center mb-4 group-hover:bg-green/20 transition">
                <f.icon size={18} className="text-green" />
              </div>
              <h3 className="font-display font-600 text-bright mb-2">{f.title}</h3>
              <p className="font-body text-dim text-sm leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-20 px-4">
        <div className="max-w-xl mx-auto card p-8 text-center border-green/20 bg-green/5">
          <div className="font-mono text-xs text-green mb-3">// 無料で今すぐ</div>
          <h2 className="font-display font-700 text-bright text-2xl mb-3">
            毎日のスキャン結果を見る
          </h2>
          <p className="text-dim text-sm mb-6 font-body">
            ブログで毎日更新されるレポートを無料でチェック。<br />
            ツール利用を希望する方はお問い合わせください。
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/blog" className="btn-primary inline-flex items-center gap-2">
              レポートを見る <ArrowRight size={15} />
            </Link>
            <Link to="/tool#contact" className="btn-ghost inline-flex items-center gap-2">
              ツールの利用問い合わせ
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border py-8 px-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <Shield size={14} className="text-green" />
            <span className="font-mono text-xs text-dim">SENTINEL PRO © 2026</span>
          </div>
          <p className="font-body text-xs text-muted text-center max-w-md">
            本サービスは教育・情報提供目的です。投資助言ではありません。
          </p>
          <div className="flex gap-4 text-xs text-muted font-body">
            <Link to="/blog"    className="hover:text-dim transition">Research</Link>
            <Link to="/tool"    className="hover:text-dim transition">Tool</Link>
            <Link to="/privacy" className="hover:text-dim transition">Privacy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}



## File: `frontend\src\pages\Privacy.jsx`

javascript
import { useSEO } from '../hooks/useSEO';

export default function Privacy() {
  useSEO({
    title:       'プライバシーポリシー / Privacy Policy',
    description: 'SENTINEL PROのプライバシーポリシーおよびGoogle AdSense、Cookieの使用に関する説明。',
  });

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="font-display font-700 text-bright text-2xl mb-8">
          プライバシーポリシー / Privacy Policy
        </h1>

        {/* 日本語 */}
        <section className="mb-10 space-y-4">
          <h2 className="font-display font-700 text-bright text-lg border-b border-border pb-2">
            日本語
          </h2>

          <div className="space-y-3 font-body text-sm text-dim leading-relaxed">
            <p>
              本サイト（SENTINEL PRO）は、Google AdSenseを利用した広告を掲載しています。
              Googleはユーザーのウェブサイト閲覧情報を元に、関連性の高い広告を表示するためにCookieを使用することがあります。
            </p>
            <h3 className="font-700 text-text">Cookieについて</h3>
            <p>
              本サイトはCookieを使用しています。Cookieはブラウザの設定から無効にすることができますが、
              一部のサービスが正常に動作しなくなる場合があります。
            </p>
            <h3 className="font-700 text-text">Google AdSenseについて</h3>
            <p>
              本サイトはGoogle AdSenseを使用しています。Google AdSenseはユーザーの興味・関心に基づいた
              パーソナライズド広告を配信するためにDoubleClickのCookieを使用することがあります。
              詳細はGoogleの
              <a href="https://policies.google.com/technologies/ads"
                 className="text-green hover:underline mx-1" target="_blank" rel="noreferrer">
                広告ポリシー
              </a>
              をご参照ください。
            </p>
            <h3 className="font-700 text-text">アクセス解析について</h3>
            <p>
              本サイトは、サービス改善のためにGoogle Analytics等のアクセス解析ツールを使用する場合があります。
              収集されるデータは匿名化されており、個人を特定するものではありません。
            </p>
            <h3 className="font-700 text-text">免責事項</h3>
            <p>
              本サイトに掲載されているコンテンツは、教育目的で提供されるものであり、投資助言ではありません。
              投資に関する最終的な判断はご自身の責任において行ってください。
            </p>
            <p className="text-xs text-muted">最終更新: 2026年2月</p>
          </div>
        </section>

        {/* English */}
        <section className="space-y-4">
          <h2 className="font-display font-700 text-bright text-lg border-b border-border pb-2">
            English
          </h2>

          <div className="space-y-3 font-body text-sm text-dim leading-relaxed">
            <p>
              This website (SENTINEL PRO) displays advertisements through Google AdSense.
              Google may use cookies to show relevant ads based on your browsing history.
            </p>
            <h3 className="font-700 text-text">About Cookies</h3>
            <p>
              This site uses cookies. You can disable cookies through your browser settings,
              though some features may not function properly as a result.
            </p>
            <h3 className="font-700 text-text">Google AdSense</h3>
            <p>
              This site uses Google AdSense, which may use the DoubleClick cookie to serve
              personalized ads based on your interests. For details, please see Google's
              <a href="https://policies.google.com/technologies/ads"
                 className="text-green hover:underline mx-1" target="_blank" rel="noreferrer">
                Advertising Policies
              </a>.
            </p>
            <h3 className="font-700 text-text">Analytics</h3>
            <p>
              This site may use Google Analytics or similar tools for service improvement.
              All data collected is anonymized and cannot identify individuals.
            </p>
            <h3 className="font-700 text-text">Disclaimer</h3>
            <p>
              All content on this site is provided for educational purposes only and does
              not constitute investment advice. All investment decisions are made at your
              own risk and responsibility.
            </p>
            <p className="text-xs text-muted">Last updated: February 2026</p>
          </div>
        </section>
      </div>
    </div>
  );
}



## File: `frontend\src\pages\ToolPage.jsx`

javascript
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, TrendingUp, Zap, BarChart3, Mail,
  ChevronRight, Check, AlertTriangle, Clock, Globe,
} from 'lucide-react';
import { useSEO } from '../hooks/useSEO';

/* ── 機能リスト ───────────────────────────────────────── */
const FEATURES = [
  {
    icon:  BarChart3,
    title: 'RSレーティング自動計算',
    body:  '600+銘柄を1年・半年・3ヶ月・1ヶ月の相対強度で重み付けランク付け。市場上位の銘柄だけに絞り込む。',
  },
  {
    icon:  TrendingUp,
    title: 'VCPスコアリング（最大105点）',
    body:  'ボラティリティ収縮・出来高ドライアップ・移動平均アライメント・ピボット距離を定量化。Minervini流のセットアップを自動検出。',
  },
  {
    icon:  Zap,
    title: '毎日自動スキャン',
    body:  '米国市場クローズ後にGitHub Actionsが自動実行。翌朝にはACTION/WAITシグナル一覧とAI解説記事が更新済み。',
  },
  {
    icon:  Shield,
    title: 'ATRベースのリスク管理',
    body:  'ストップロス・エントリー・ターゲットを自動計算。口座リスク1.5%ルールに基づくポジションサイジング付き。',
  },
  {
    icon:  Globe,
    title: 'ファンダメンタル＋インサイダー',
    body:  'アナリスト目標株価・フォワードPE・売上成長率・インサイダー売買アラートを一画面で確認。',
  },
  {
    icon:  Clock,
    title: 'ポートフォリオ追跡',
    body:  '保有銘柄のリアルタイムP&L・Rマルチプル・動的ATRストップを自動更新。出口判断をデータで裏付け。',
  },
];

/* ── 実績 ─────────────────────────────────────────────── */
const PROOF = {
  ticker:  'GLW',
  company: 'Corning Inc.',
  gain:    '+12.3%',
  days:    4,
  date:    '2026年2月',
};

/* ── スペック ─────────────────────────────────────────── */
const SPECS = [
  { label: 'スキャン銘柄数',   value: '600+' },
  { label: '対象市場',         value: 'NYSE / NASDAQ' },
  { label: 'スキャン頻度',     value: '毎営業日' },
  { label: '言語',             value: '日本語 / English' },
  { label: 'データソース',     value: 'FMP API' },
  { label: 'インフラ',         value: 'GitHub Actions + Vercel' },
];

/* ── FAQ ──────────────────────────────────────────────── */
const FAQS = [
  {
    q: 'どんな人に向いていますか？',
    a: 'VCP・RSレーティングによるモメンタム投資に興味がある個人投資家の方、または投資コミュニティ・スクールを運営されている方に向いています。',
  },
  {
    q: '提供形式はどうなりますか？',
    a: 'ご要望に応じて個別にご相談します。ツールへのアクセス権付与、カスタマイズ対応、データフィードの提供など、柔軟に対応可能です。',
  },
  {
    q: '投資助言になりますか？',
    a: 'なりません。本ツールは定量的なスクリーニング結果を提示するものであり、売買推奨は行いません。最終的な投資判断はご自身の責任で行ってください。',
  },
  {
    q: 'スマートフォンでも使えますか？',
    a: 'はい。レスポンシブデザインに対応しており、スマートフォン・タブレット・PCから利用可能です。',
  },
];

export default function ToolPage() {
  const [openFaq, setOpenFaq] = useState(null);
  const [copied,  setCopied]  = useState(false);

  const CONTACT_EMAIL = 'contact@sentinel-pro.app'; // ← 実際のメアドに変更

  useSEO({
    title:       'SENTINEL PRO — 米国株VCP×RSスクリーニングツール',
    description: 'VCPパターンとRSレーティングで600+銘柄を毎日自動スキャン。ポートフォリオ追跡・リスク管理・AI解説記事が一体化した米国株分析ツール。利用希望はお問い合わせください。',
    type:        'website',
  });

  const handleCopy = () => {
    navigator.clipboard.writeText(CONTACT_EMAIL);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-ink overflow-hidden">

      {/* Grid背景 */}
      <div className="fixed inset-0 bg-grid-pattern bg-grid opacity-40 pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-b from-ink via-transparent to-ink pointer-events-none" />

      {/* ── Hero ────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 px-4 max-w-4xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                        border border-green/30 bg-green/5 text-xs font-mono text-green mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse-dot" />
          稼働中 — 毎営業日 JST 15:00 自動スキャン
        </div>

        <h1 className="font-display font-800 text-bright leading-tight mb-6"
            style={{ fontSize: 'clamp(2.2rem, 5vw, 3.8rem)' }}>
          米国株を毎日<br />
          <span className="text-green">定量的に</span>スクリーニング
        </h1>

        <p className="font-body text-dim text-lg leading-relaxed max-w-2xl mx-auto mb-10">
          VCP（ボラティリティ収縮パターン）× RSレーティングで600+銘柄を自動分析。<br />
          エントリー・ストップ・ターゲットまで一括計算し、毎日更新します。
        </p>

        {/* 実績バッジ */}
        <div className="inline-flex items-center gap-3 px-4 py-3 rounded-xl
                        bg-green/10 border border-green/30 mb-10">
          <div className="text-left">
            <div className="font-mono text-xs text-muted">直近シグナル実績</div>
            <div className="font-mono text-sm font-700 text-bright">
              {PROOF.ticker} {PROOF.gain} <span className="text-muted font-400">/ {PROOF.days}営業日</span>
            </div>
            <div className="font-mono text-xs text-muted">{PROOF.company} · {PROOF.date}</div>
          </div>
        </div>

        {/* CTAボタン */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <a href="#contact"
             className="flex items-center gap-2 px-6 py-3 rounded-xl bg-green text-ink
                        font-display font-700 text-sm hover:bg-green/90 transition">
            利用を検討している <ChevronRight size={14} />
          </a>
          <Link to="/blog"
             className="flex items-center gap-2 px-6 py-3 rounded-xl border border-border
                        text-dim font-display font-600 text-sm hover:border-muted hover:text-bright transition">
            分析レポートを見る
          </Link>
        </div>
      </section>

      {/* ── スペック ─────────────────────────────────────── */}
      <section className="relative px-4 max-w-4xl mx-auto mb-20">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {SPECS.map(s => (
            <div key={s.label} className="bg-panel border border-border rounded-xl p-4">
              <div className="font-mono text-xs text-muted mb-1">{s.label}</div>
              <div className="font-display font-700 text-bright text-sm">{s.value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 機能詳細 ─────────────────────────────────────── */}
      <section className="relative px-4 max-w-4xl mx-auto mb-24">
        <div className="text-center mb-10">
          <div className="font-mono text-xs text-green mb-2">FEATURES</div>
          <h2 className="font-display font-700 text-bright text-2xl">主な機能</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {FEATURES.map(f => (
            <div key={f.title}
                 className="bg-panel border border-border rounded-xl p-5 flex gap-4">
              <div className="w-9 h-9 rounded-lg bg-green/10 border border-green/20
                              flex items-center justify-center shrink-0">
                <f.icon size={16} className="text-green" />
              </div>
              <div>
                <div className="font-display font-700 text-bright text-sm mb-1">{f.title}</div>
                <div className="font-body text-xs text-muted leading-relaxed">{f.body}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── スクリーンショットイメージ ────────────────────── */}
      <section className="relative px-4 max-w-4xl mx-auto mb-24">
        <div className="bg-panel border border-border rounded-2xl p-6 md:p-8">
          <div className="font-mono text-xs text-green mb-4">LIVE DEMO</div>
          <div className="grid md:grid-cols-2 gap-6">

            {/* スキャン結果イメージ */}
            <div className="bg-ink rounded-xl border border-border p-4">
              <div className="font-mono text-xs text-muted mb-3">スキャン結果（イメージ）</div>
              {[
                { t: 'NVDA', vcp: 92, rs: 97, status: 'ACTION', price: 142.50 },
                { t: 'AMD',  vcp: 81, rs: 89, status: 'ACTION', price: 118.30 },
                { t: 'AVGO', vcp: 76, rs: 94, status: 'WAIT',   price: 231.10 },
                { t: 'TSM',  vcp: 71, rs: 88, status: 'WAIT',   price: 198.40 },
              ].map(row => (
                <div key={row.t}
                     className="flex items-center justify-between py-2
                                border-b border-border/50 last:border-0 text-xs font-mono">
                  <span className="text-bright font-700 w-12">{row.t}</span>
                  <span className="text-muted">VCP {row.vcp}</span>
                  <span className="text-muted">RS {row.rs}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${
                    row.status === 'ACTION'
                      ? 'bg-green/10 text-green border border-green/20'
                      : 'bg-amber/10 text-amber border border-amber/20'
                  }`}>{row.status}</span>
                  <span className="text-dim">${row.price}</span>
                </div>
              ))}
            </div>

            {/* VCPブレイクダウンイメージ */}
            <div className="bg-ink rounded-xl border border-border p-4">
              <div className="font-mono text-xs text-muted mb-3">VCPスコア内訳（NVDA）</div>
              {[
                { label: 'Tightness', val: 40, max: 40 },
                { label: 'Volume',    val: 25, max: 30 },
                { label: 'MA Align',  val: 22, max: 30 },
                { label: 'Pivot',     val: 5,  max: 5  },
              ].map(b => (
                <div key={b.label} className="mb-3">
                  <div className="flex justify-between text-xs font-mono text-muted mb-1">
                    <span>{b.label}</span>
                    <span className="text-dim">{b.val}/{b.max}</span>
                  </div>
                  <div className="h-1.5 bg-border rounded-full overflow-hidden">
                    <div className="h-full bg-green rounded-full"
                         style={{ width: `${(b.val / b.max) * 100}%` }} />
                  </div>
                </div>
              ))}
              <div className="mt-3 pt-3 border-t border-border flex justify-between font-mono text-xs">
                <span className="text-muted">Total</span>
                <span className="text-green font-700">92/105</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────── */}
      <section className="relative px-4 max-w-2xl mx-auto mb-24">
        <div className="text-center mb-8">
          <div className="font-mono text-xs text-green mb-2">FAQ</div>
          <h2 className="font-display font-700 text-bright text-2xl">よくある質問</h2>
        </div>
        <div className="space-y-2">
          {FAQS.map((faq, i) => (
            <div key={i} className="bg-panel border border-border rounded-xl overflow-hidden">
              <button
                className="w-full text-left px-5 py-4 flex items-center justify-between gap-3"
                onClick={() => setOpenFaq(openFaq === i ? null : i)}>
                <span className="font-display font-600 text-bright text-sm">{faq.q}</span>
                <ChevronRight size={14} className={`text-muted shrink-0 transition-transform ${
                  openFaq === i ? 'rotate-90' : ''
                }`} />
              </button>
              {openFaq === i && (
                <div className="px-5 pb-4">
                  <p className="font-body text-sm text-muted leading-relaxed">{faq.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── お問い合わせ ─────────────────────────────────── */}
      <section id="contact" className="relative px-4 max-w-2xl mx-auto mb-24">
        <div className="bg-panel border border-green/30 rounded-2xl p-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-green/10 border border-green/20
                          flex items-center justify-center mx-auto mb-4">
            <Mail size={20} className="text-green" />
          </div>
          <h2 className="font-display font-700 text-bright text-xl mb-2">
            ツールの利用を検討している方へ
          </h2>
          <p className="font-body text-sm text-muted leading-relaxed mb-6 max-w-md mx-auto">
            個人投資家・コミュニティ運営者・投資スクール向けに個別対応しています。
            ご要望・用途を教えていただければ、最適な形をご提案します。
          </p>

          {/* メールアドレス表示 */}
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                            bg-ink border border-border font-mono text-sm text-bright">
              <Mail size={13} className="text-muted" />
              {CONTACT_EMAIL}
            </div>
            <button onClick={handleCopy}
                    className="px-3 py-2.5 rounded-xl bg-green/10 border border-green/20
                               font-mono text-xs text-green hover:bg-green/20 transition">
              {copied ? '✓ コピー済み' : 'コピー'}
            </button>
          </div>

          <a href={`mailto:${CONTACT_EMAIL}?subject=SENTINEL PRO 利用問い合わせ&body=【用途】%0A%0A【希望する機能】%0A%0A【その他】`}
             className="inline-flex items-center gap-2 px-6 py-3 rounded-xl
                        bg-green text-ink font-display font-700 text-sm
                        hover:bg-green/90 transition">
            メールで問い合わせる <ChevronRight size={14} />
          </a>

          <p className="font-mono text-xs text-muted mt-4">
            ※ 投資助言サービスではありません
          </p>
        </div>
      </section>

      {/* ── 免責 ─────────────────────────────────────────── */}
      <section className="relative px-4 max-w-2xl mx-auto pb-16">
        <div className="flex gap-2 p-4 bg-panel border border-border rounded-xl">
          <AlertTriangle size={14} className="text-amber shrink-0 mt-0.5" />
          <p className="font-body text-xs text-muted leading-relaxed">
            本ツールは定量的な銘柄スクリーニングを提供するものであり、投資助言・売買推奨ではありません。
            表示されるシグナル・スコアはあくまで参考情報です。投資判断はご自身の責任において行ってください。
            データはFMP APIを使用しており、遅延・誤差が含まれる場合があります。
          </p>
        </div>
      </section>

    </div>
  );
}



## File: `scripts\generate_articles.py`

py
#!/usr/bin/env python3
"""
scripts/generate_articles.py
============================
【平日】スキャン → 日次レポート（指数+セクター+VCPランキング）
         + 銘柄ページ累積更新（TICKER.json を上書き）
【土曜】週次レポート（先週振り返り + 翌週展望）
"""
import sys, json, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent.parent / "shared"))
sys.path.append(str(Path(__file__).parent))
from engines import core_fmp
from engines.analysis import VCPAnalyzer, RSAnalyzer, StrategyValidator
from engines.config import CONFIG, TICKERS
try:
    from generate_chart import generate_candle_chart
    CHART_ENABLED = True
except ImportError:
    CHART_ENABLED = False
    print("Chart generation disabled (mplfinance not installed)")

JST   = timezone(timedelta(hours=9))
NOW   = datetime.now(JST)
TODAY = NOW.strftime("%Y-%m-%d")
IS_SATURDAY = NOW.weekday() == 5

CONTENT_DIR = Path(__file__).parent.parent / "frontend" / "public" / "content"
DAILY_DIR   = CONTENT_DIR / "daily"
STOCKS_DIR  = CONTENT_DIR / "stocks"
WEEKLY_DIR  = CONTENT_DIR / "weekly"
INDEX_FILE  = CONTENT_DIR / "index.json"
for d in [DAILY_DIR, STOCKS_DIR, WEEKLY_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def call_ai(prompt, max_tokens=1500, system=""):
    api_key  = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    model    = os.environ.get("OPENAI_MODEL", "deepseek-chat")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client   = OpenAI(api_key=api_key, base_url=base_url)
        messages = ([{"role":"system","content":system}] if system else [])
        messages.append({"role":"user","content":prompt})
        res = client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=messages, temperature=0.7)
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI error: {e}"); return ""


def run_scan():
    print(f"Scanning {len(TICKERS)} tickers...")
    raw_list = []
    for t in TICKERS:
        df = core_fmp.get_historical_data(t, days=700)
        if df is None or len(df) < 200:
            continue
        rs_raw = RSAnalyzer.get_raw_score(df)
        if rs_raw != -999.0:
            raw_list.append({"ticker": t, "df": df, "raw_rs": rs_raw})
    if not raw_list:
        return {"qualified":[], "actions":[], "waits":[], "all_scored":[]}

    scored = RSAnalyzer.assign_percentiles(raw_list)
    qualified, all_scored = [], []
    for item in scored:
        vcp   = VCPAnalyzer.calculate(item["df"])
        pf    = StrategyValidator.run(item["df"])
        price = float(item["df"]["Close"].iloc[-1])
        pivot = float(item["df"]["High"].iloc[-20:].max())
        entry = round(pivot * 1.002, 2)
        stop  = round(entry - vcp["atr"] * CONFIG["STOP_LOSS_ATR"], 2)
        target= round(entry + (entry - stop) * CONFIG["TARGET_R_MULTIPLE"], 2)
        dist  = (price - pivot) / pivot
        status= "ACTION" if -0.05<=dist<=0.03 else ("WAIT" if dist<-0.05 else "EXTENDED")
        profile = core_fmp.get_company_profile(item["ticker"]) or {}
        row = {
            "ticker":item["ticker"], "status":status, "rs":item["rs_rating"],
            "vcp":vcp["score"], "pf":round(pf,2), "price":round(price,2),
            "entry":entry, "stop":stop, "target":target,
            "sector":profile.get("sector","N/A"), "industry":profile.get("industry","N/A"),
            "name":profile.get("companyName",item["ticker"]),
            "vcp_detail":vcp, "df":item["df"],
        }
        all_scored.append(row)
        if (item["rs_rating"]>=CONFIG["MIN_RS_RATING"] and
                vcp["score"]>=CONFIG["MIN_VCP_SCORE"] and pf>=CONFIG["MIN_PROFIT_FACTOR"]):
            qualified.append(row)

    qualified.sort(key=lambda x:(x["status"]=="ACTION", x["vcp"]+x["rs"]), reverse=True)
    all_scored.sort(key=lambda x: x["vcp"]+x["rs"]*0.5, reverse=True)
    actions = [q for q in qualified if q["status"]=="ACTION"]
    waits   = [q for q in qualified if q["status"]=="WAIT"]
    print(f"ACTION:{len(actions)} WAIT:{len(waits)} Scored:{len(all_scored)}")
    return {"qualified":qualified, "actions":actions, "waits":waits, "all_scored":all_scored}


def get_index_data():
    result = {}
    for ticker, name in {"SPY":"S&P500","QQQ":"NASDAQ100","IWM":"Russell2000"}.items():
        try:
            df = core_fmp.get_historical_data(ticker, days=30)
            if df is None or len(df)<6: continue
            c = df["Close"]
            result[ticker] = {
                "name":name, "price":round(float(c.iloc[-1]),2),
                "chg_1d": round((float(c.iloc[-1])/float(c.iloc[-2])-1)*100,2),
                "chg_5d": round((float(c.iloc[-1])/float(c.iloc[-6])-1)*100,2),
                "chg_20d":round((float(c.iloc[-1])/float(c.iloc[-21])-1)*100,2) if len(c)>=21 else None,
            }
        except Exception as e:
            print(f"Index error {ticker}: {e}")
    return result


def calc_sector_summary(all_scored):
    sectors = {}
    for item in all_scored:
        s = item.get("sector","N/A")
        if s=="N/A": continue
        if s not in sectors:
            sectors[s] = {"rs_sum":0,"vcp_sum":0,"count":0,"actions":0}
        sectors[s]["rs_sum"]  += item["rs"]
        sectors[s]["vcp_sum"] += item["vcp"]
        sectors[s]["count"]   += 1
        if item["status"]=="ACTION": sectors[s]["actions"]+=1
    result = []
    for s,v in sectors.items():
        n=v["count"]
        result.append({"sector":s,"avg_rs":round(v["rs_sum"]/n,1),
                        "avg_vcp":round(v["vcp_sum"]/n,1),"count":n,"action_count":v["actions"]})
    return sorted(result, key=lambda x:x["avg_rs"], reverse=True)


def build_vcp_ranking(all_scored, top_n=30):
    return [{"rank":i+1,"ticker":r["ticker"],"name":r["name"],"vcp":r["vcp"],
             "rs":r["rs"],"status":r["status"],"price":r["price"],"sector":r["sector"]}
            for i,r in enumerate(all_scored[:top_n])]


def generate_daily_report(scan, index_data, sector_data):
    actions = scan["actions"]; waits = scan["waits"]
    ranking = build_vcp_ranking(scan["all_scored"])
    at = ", ".join(q["ticker"] for q in actions[:10]) or "なし"
    wt = ", ".join(q["ticker"] for q in waits[:8])   or "なし"
    top_sectors = " / ".join(s["sector"] for s in sector_data[:3])

    idx_ja = "\n".join(
        f"{d['name']}: {'+' if d['chg_1d']>=0 else ''}{d['chg_1d']}% (5日:{'+' if d['chg_5d']>=0 else ''}{d['chg_5d']}%)"
        for d in index_data.values())
    idx_en = "\n".join(
        f"{d['name']}: {'+' if d['chg_1d']>=0 else ''}{d['chg_1d']}% (5d:{'+' if d['chg_5d']>=0 else ''}{d['chg_5d']}%)"
        for d in index_data.values())

    sys_msg = "あなたは米国株の定量アナリストです。データを正確に解釈し、教育的かつ読みやすい文章を書いてください。投資助言は絶対にしないでください。"
    p_ja = f"""本日（{TODAY}）の米国株市場レポートを作成してください。

【指数動向】
{idx_ja}

【スキャン結果】ACTIONシグナル:{len(actions)}銘柄({at}) / WAIT:{len(waits)}銘柄({wt})
【強いセクター上位3】{top_sectors}

700〜900文字。見出し3つ(## ①指数動向 ②VCP×RSシグナル ③セクター分析)。
VCPとRSの意味を自然に説明。断定表現禁止。末尾に1行免責事項。Markdown出力。"""

    p_en = f"""Write today's ({TODAY}) US stock market report.
【Index】{idx_en}
【Signals】ACTION:{len(actions)}({at}) WAIT:{len(waits)}({wt})
【Top Sectors】{top_sectors}
350-450 words, 3 headings (##①Index ②Signals ③Sectors), explain VCP/RS,
no recommendations, 1-line disclaimer. Markdown."""

    print("Generating daily report...")
    body_ja = call_ai(p_ja, 1400, sys_msg) or f"""## {TODAY} 指数動向\n{idx_ja}\n## VCP×RSシグナル\nACTION **{len(actions)}銘柄**: {at}\n## セクター分析\n強いセクター: {top_sectors}\n⚠️ 教育目的であり、投資助言ではありません。"""
    body_en = call_ai(p_en, 900) or f"""## Index {TODAY}\n{idx_en}\n## Signals\nACTION:{len(actions)} {at}\n## Sectors\nLeading: {top_sectors}\n⚠️ Not investment advice."""

    spx = index_data.get("SPY",{}).get("chg_1d","?")
    slug = f"daily-{TODAY}"
    return {
        "slug":slug,"type":"daily","date":TODAY,"published_at":NOW.isoformat(),
        "ja":{"title":f"{TODAY} 米国株レポート — SPY {spx}% / ACTION {len(actions)}銘柄",
              "summary":f"S&P500 {spx}%、強いセクター:{top_sectors}。VCPシグナルACTION {len(actions)}銘柄。","body":body_ja},
        "en":{"title":f"US Market {TODAY} — SPY {spx}% / {len(actions)} ACTION",
              "summary":f"S&P500 {spx}%, top sectors:{top_sectors}. {len(actions)} ACTION signals.","body":body_en},
        "data":{"action_count":len(actions),"wait_count":len(waits),
                "actions":[{k:v for k,v in a.items() if k not in("vcp_detail","df")} for a in actions[:10]],
                "index":index_data,"sector":sector_data,"vcp_ranking":ranking},
    }


def update_stock_page(item):
    ticker = item["ticker"]
    vcp    = item["vcp_detail"]
    bd     = vcp.get("breakdown",{})
    sig_ja = " / ".join(vcp.get("signals",[])) or "なし"
    sig_en = " / ".join(vcp.get("signals",[])) or "none"
    stock_file = STOCKS_DIR / f"{ticker}.json"

    # 履歴保持
    history = []
    if stock_file.exists():
        try:
            ex = json.loads(stock_file.read_text(encoding="utf-8"))
            history = ex.get("history",[])
            if ex.get("date") and ex["date"] != TODAY:
                snap = {"date":ex["date"],"vcp":ex.get("data",{}).get("vcp"),
                        "rs":ex.get("data",{}).get("rs"),"price":ex.get("data",{}).get("price"),
                        "status":ex.get("data",{}).get("status")}
                history = ([snap]+history)[:90]
        except Exception:
            pass

    print(f"  Updating: {ticker} (fetching rich data)...")

    # ── リッチデータ取得（FMP Starter） ──────────────────
    analyst   = core_fmp.get_analyst_consensus(ticker) or {}
    fund      = core_fmp.get_fundamentals(ticker)      or {}
    ownership = core_fmp.get_ownership(ticker)         or {}
    news      = core_fmp.get_news(ticker, limit=5)

    # ── チャート画像生成 ──────────────────────────────────
    chart_b64 = ""
    if CHART_ENABLED:
        try:
            chart_b64 = generate_candle_chart(
                item["df"], ticker, item["vcp"],
                entry=item["entry"], stop=item["stop"], target=item["target"],
                days=90
            )
        except Exception as e:
            print(f"  Chart error {ticker}: {e}")

    # ── AI記事生成（リッチデータを含めたプロンプト）──────
    analyst_str = ""
    if analyst:
        analyst_str = f"アナリスト評価:{analyst.get('consensus','N/A')}({analyst.get('analyst_count',0)}名) 目標株価平均:${analyst.get('target_mean','N/A')} 乖離:{analyst.get('target_pct','N/A')}%"

    fund_str = ""
    if fund:
        fund_str = (f"予想PER:{fund.get('pe_forward','N/A')} 売上成長率:{fund.get('revenue_growth_yoy','N/A')}% "
                    f"利益成長率:{fund.get('earnings_growth_yoy','N/A')}% ROE:{fund.get('roe','N/A')}% "
                    f"粗利率:{fund.get('gross_margin','N/A')}% 時価総額:${fund.get('market_cap_b','N/A')}B")

    own_str = ""
    if ownership:
        own_str = (f"機関投資家保有率:{ownership.get('institutional_pct','N/A')}% "
                   f"空売り比率:{ownership.get('short_float_pct','N/A')}% "
                   f"空売り日数:{ownership.get('short_days_to_cover','N/A')}日")

    news_str = "\n".join(f"- {n['title']} ({n['source']})" for n in news[:3]) or "なし"

    sys_msg = "あなたは米国株のテクニカル・ファンダメンタルアナリストです。定量データを正確に解説し、初心者にも分かりやすい教育的コンテンツを書いてください。投資助言は絶対にしないでください。"

    p_ja = f"""{item['name']}（{ticker}）の総合分析レポート（1200〜1500文字）を書いてください。

【テクニカル】
VCPスコア:{item['vcp']}/105(T:{bd.get('tight',0)} V:{bd.get('vol',0)} MA:{bd.get('ma',0)} P:{bd.get('pivot',0)})
RS:{item['rs']}/99 PF:{item['pf']}x 現在値:${item['price']} 状態:{item['status']}
エントリー目安:${item['entry']} ストップ:${item['stop']} ターゲット:${item['target']}
シグナル:{sig_ja} セクター:{item['sector']}/{item['industry']}

【ファンダメンタル】
{fund_str if fund_str else "データなし"}

【アナリスト評価】
{analyst_str if analyst_str else "データなし"}

【投資家動向】
{own_str if own_str else "データなし"}

【直近ニュース】
{news_str}

見出し5つ(##①企業・セクター概要 ②テクニカル分析（VCP詳細） ③ファンダメンタル ④アナリスト・投資家動向 ⑤注意点)。
断定的売買推奨は禁止。末尾に免責事項。Markdown出力。"""

    p_en = f"""Write a comprehensive analysis report (600-700 words) for {item['name']} ({ticker}).

[Technical] VCP:{item['vcp']}/105 RS:{item['rs']}/99 PF:{item['pf']}x Price:${item['price']} Status:{item['status']}
Entry:${item['entry']} Stop:${item['stop']} Target:${item['target']} Signals:{sig_en}

[Fundamentals] {fund_str or "N/A"}
[Analyst] {analyst_str or "N/A"}
[Ownership] {own_str or "N/A"}

5 headings(##①Overview ②Technical/VCP ③Fundamentals ④Analyst/Ownership ⑤Caution).
No buy/sell recommendations. 1-line disclaimer. Markdown."""

    body_ja = call_ai(p_ja, 2200, sys_msg) or f"""## {item['name']}（{ticker}）\n## テクニカル分析\nVCP:{item['vcp']}/105 RS:{item['rs']}/99 状態:{item['status']}\n## ファンダメンタル\n{fund_str}\n## アナリスト\n{analyst_str}\n## 注意点\n⚠️ 投資助言ではありません。"""
    body_en = call_ai(p_en, 1400) or f"""## {ticker}\n## Technical\nVCP:{item['vcp']}/105 RS:{item['rs']}\n## Fundamentals\n{fund_str}\n## Analyst\n{analyst_str}\n## Caution\n⚠️ Not investment advice."""
    time.sleep(1.5)

    slug = f"stock-{ticker.lower()}"
    doc = {
        "slug":slug,"type":"stock","ticker":ticker,"name":item["name"],
        "date":TODAY,"published_at":NOW.isoformat(),
        "ja":{"title":f"{item['name']}（{ticker}）株価分析 VCP{item['vcp']}点・RS{item['rs']}【{TODAY}更新】",
              "summary":f"{ticker} VCP:{item['vcp']}/105 RS:{item['rs']} {item['status']}。{analyst_str[:60] if analyst_str else ''}。{TODAY}更新。",
              "body":body_ja},
        "en":{"title":f"{item['name']} ({ticker}) Analysis VCP{item['vcp']} RS{item['rs']} [{TODAY}]",
              "summary":f"{ticker} VCP:{item['vcp']}/105 RS:{item['rs']} {item['status']}. {TODAY}.",
              "body":body_en},
        "data":{
            "ticker":ticker,"name":item["name"],"status":item["status"],"rs":item["rs"],
            "vcp":item["vcp"],"pf":item["pf"],"price":item["price"],"entry":item["entry"],
            "stop":item["stop"],"target":item["target"],"sector":item["sector"],
            "industry":item["industry"],"vcp_breakdown":bd,"signals":vcp.get("signals",[]),
            # リッチデータ
            "analyst":   analyst,
            "fundamentals": fund,
            "ownership": ownership,
            "news":      news,
        },
        "chart_b64": chart_b64,  # Base64 PNG（空文字の場合は表示しない）
        "history":history,
    }
    stock_file.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    return doc


def generate_weekly_report(scan, index_data, sector_data):
    actions = scan["actions"]
    ranking = build_vcp_ranking(scan["all_scored"], top_n=20)
    week_str = f"{(NOW-timedelta(days=6)).strftime('%m/%d')}〜{NOW.strftime('%m/%d')}"
    top_rank = "\n".join(f"{r['rank']}. {r['ticker']} VCP:{r['vcp']} RS:{r['rs']} [{r['status']}]" for r in ranking[:10])
    top_sectors = " / ".join(s["sector"] for s in sector_data[:3])
    spx5 = index_data.get("SPY",{}).get("chg_5d","N/A")
    qqq5 = index_data.get("QQQ",{}).get("chg_5d","N/A")
    iwm5 = index_data.get("IWM",{}).get("chg_5d","N/A")

    sys_msg = "あなたは米国株市場の週次レポートを作成するアナリストです。投資助言は厳禁です。"
    p_ja = f"""先週（{week_str}）の米国株振り返りと翌週展望レポート（1000〜1300文字）を作成してください。
指数: S&P500 {spx5}% / NASDAQ100 {qqq5}% / Russell2000 {iwm5}%
VCPランキング上位10:\n{top_rank}
強いセクター:{top_sectors}
見出し4つ(##①先週の振り返り ②注目銘柄 ③セクター動向 ④翌週の注目ポイント)。
翌週の市場環境も解説。断定表現禁止。末尾に免責事項。Markdown出力。"""

    p_en = f"""Weekly US stock review & outlook for {week_str} (500-650 words).
SPY:{spx5}% QQQ:{qqq5}% IWM:{iwm5}%
Top VCP:\n{top_rank}
Top sectors:{top_sectors}
4 headings(##①Review ②Stocks ③Sectors ④Outlook). No recommendations. Disclaimer. Markdown."""

    print("Generating weekly report...")
    body_ja = call_ai(p_ja, 2000, sys_msg) or f"""## 先週({week_str})の振り返り\nS&P500:{spx5}% NASDAQ:{qqq5}%\n## 注目銘柄\n{top_rank}\n## セクター動向\n{top_sectors}\n## 翌週の注目ポイント\nACTION:{len(actions)}銘柄\n⚠️ 投資助言ではありません。"""
    body_en = call_ai(p_en, 1200) or f"""## Week in Review ({week_str})\nSPY:{spx5}% QQQ:{qqq5}%\n## Top Stocks\n{top_rank}\n## Sectors\n{top_sectors}\n## Outlook\nACTION:{len(actions)}\n⚠️ Not investment advice."""

    slug = f"weekly-{TODAY}"
    return {
        "slug":slug,"type":"weekly","date":TODAY,"week":week_str,"published_at":NOW.isoformat(),
        "ja":{"title":f"週次レポート {week_str} — 振り返りと翌週展望",
              "summary":f"S&P500先週{spx5}%。強いセクター:{top_sectors}。翌週のVCP注目銘柄を解説。","body":body_ja},
        "en":{"title":f"Weekly Report {week_str} — Review & Outlook",
              "summary":f"S&P500 weekly {spx5}%. Top sectors:{top_sectors}. VCP outlook for next week.","body":body_en},
        "data":{"week":week_str,"index":index_data,"sector":sector_data,
                "vcp_ranking":ranking,"action_count":len(actions)},
    }


def update_index(new_articles):
    existing = []
    if INDEX_FILE.exists():
        try: existing = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception: pass
    ex_map = {a["slug"]:i for i,a in enumerate(existing)}
    for a in new_articles:
        entry = {k:v for k,v in a.items() if k not in ("ja","en","history","data")}
        if "ja" in a: entry["ja"] = {k:v for k,v in a["ja"].items() if k!="body"}
        if "en" in a: entry["en"] = {k:v for k,v in a["en"].items() if k!="body"}
        if "data" in a:
            entry["data"] = {k:v for k,v in a["data"].items()
                             if k not in ("actions","vcp_ranking") and not isinstance(v,list)}
            entry["data"]["action_count"] = a["data"].get("action_count",0)
        if a["slug"] in ex_map: existing[ex_map[a["slug"]]] = entry
        else: existing.insert(0, entry)
    existing.sort(key=lambda x: x.get("published_at",""), reverse=True)
    INDEX_FILE.write_text(json.dumps(existing[:300], ensure_ascii=False, indent=2))
    print(f"index.json: {len(existing)} entries")


def main():
    print(f"===== SENTINEL {'WEEKLY' if IS_SATURDAY else 'DAILY'} {TODAY} =====")
    new_articles = []
    scan        = run_scan()
    index_data  = get_index_data()
    sector_data = calc_sector_summary(scan["all_scored"])

    if IS_SATURDAY:
        weekly = generate_weekly_report(scan, index_data, sector_data)
        (WEEKLY_DIR / f"{TODAY}.json").write_text(json.dumps(weekly, ensure_ascii=False, indent=2))
        new_articles.append(weekly)
        print("✅ Weekly report saved")
    else:
        daily = generate_daily_report(scan, index_data, sector_data)
        (DAILY_DIR / f"{TODAY}.json").write_text(json.dumps(daily, ensure_ascii=False, indent=2))
        new_articles.append(daily)
        print("✅ Daily report saved")

        # ACTION上位5 + WAIT上位3 を累積更新
        for item in (scan["actions"][:5] + scan["waits"][:3]):
            try:
                doc = update_stock_page(item)
                new_articles.append(doc)
            except Exception as e:
                print(f"❌ {item['ticker']}: {e}")

    update_index(new_articles)
    print(f"===== Done: {len(new_articles)} articles =====")

if __name__ == "__main__":
    main()



## File: `scripts\generate_chart.py`

py
"""
generate_chart.py
OHLCVデータからローソク足チャート画像を生成してBase64で返す
matplotlib + mplfinance 使用
"""
import base64, io
import pandas as pd
import numpy as np
from pathlib import Path


def generate_candle_chart(df: pd.DataFrame, ticker: str, vcp_score: int,
                          entry: float = None, stop: float = None,
                          target: float = None, days: int = 90) -> str:
    """
    ローソク足チャートをPNG Base64で返す
    - ダークテーマ (ink background)
    - 20MA / 50MA / 200MA
    - 出来高バー
    - エントリー/ストップ/ターゲットライン（任意）
    Returns: base64 encoded PNG string
    """
    try:
        import mplfinance as mpf
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("mplfinance not installed, skipping chart")
        return ""

    # 直近N日
    df_plot = df.iloc[-days:].copy()
    if len(df_plot) < 20:
        return ""

    # 移動平均
    df_plot["MA20"]  = df_plot["Close"].rolling(20).mean()
    df_plot["MA50"]  = df_plot["Close"].rolling(50).mean()
    df_plot["MA200"] = df_plot["Close"].rolling(200).mean()

    # スタイル設定（ダークテーマ）
    mc = mpf.make_marketcolors(
        up="#22C55E", down="#EF4444",
        edge={"up":"#22C55E","down":"#EF4444"},
        wick={"up":"#22C55E","down":"#EF4444"},
        volume={"up":"#22C55E40","down":"#EF444440"},
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor="#0E1318",
        edgecolor="#1C2530",
        figcolor="#080C10",
        gridcolor="#1C2530",
        gridstyle="--",
        gridaxis="both",
        y_on_right=True,
        rc={
            "axes.labelcolor":  "#7A90A8",
            "xtick.color":      "#3D4F63",
            "ytick.color":      "#3D4F63",
            "font.family":      "monospace",
            "font.size":        8,
        }
    )

    # 追加プロット（MA線）
    add_plots = [
        mpf.make_addplot(df_plot["MA20"],  color="#3B82F6", width=1.0, linestyle="-"),
        mpf.make_addplot(df_plot["MA50"],  color="#F59E0B", width=1.0, linestyle="-"),
        mpf.make_addplot(df_plot["MA200"], color="#EF4444", width=0.8, linestyle="--"),
    ]

    # チャート描画
    fig, axes = mpf.plot(
        df_plot,
        type="candle",
        style=s,
        volume=True,
        addplot=add_plots,
        figratio=(12, 7),
        figscale=1.0,
        tight_layout=True,
        returnfig=True,
        datetime_format="%m/%d",
        xrotation=0,
    )

    ax_main = axes[0]

    # タイトル
    price = float(df_plot["Close"].iloc[-1])
    chg   = (price / float(df_plot["Close"].iloc[0]) - 1) * 100
    sign  = "+" if chg >= 0 else ""
    color = "#22C55E" if chg >= 0 else "#EF4444"
    ax_main.set_title(
        f"{ticker}  ${price:.2f}  {sign}{chg:.1f}%  VCP {vcp_score}/105",
        color="#EBF4FF", fontsize=10, fontweight="bold", loc="left", pad=8
    )

    # エントリー / ストップ / ターゲットライン
    xlim = ax_main.get_xlim()
    if entry:
        ax_main.axhline(y=entry, color="#22C55E", linewidth=1.0,
                        linestyle="--", alpha=0.8, xmin=0.8)
        ax_main.text(xlim[1]*0.99, entry, f" E ${entry:.2f}",
                     color="#22C55E", fontsize=7, va="center", ha="right")
    if stop:
        ax_main.axhline(y=stop, color="#EF4444", linewidth=1.0,
                        linestyle="--", alpha=0.8, xmin=0.8)
        ax_main.text(xlim[1]*0.99, stop, f" S ${stop:.2f}",
                     color="#EF4444", fontsize=7, va="center", ha="right")
    if target:
        ax_main.axhline(y=target, color="#F59E0B", linewidth=1.0,
                        linestyle="--", alpha=0.8, xmin=0.8)
        ax_main.text(xlim[1]*0.99, target, f" T ${target:.2f}",
                     color="#F59E0B", fontsize=7, va="center", ha="right")

    # 凡例
    legend_handles = [
        mpatches.Patch(color="#3B82F6", label="MA20"),
        mpatches.Patch(color="#F59E0B", label="MA50"),
        mpatches.Patch(color="#EF4444", label="MA200"),
    ]
    ax_main.legend(handles=legend_handles, loc="upper left",
                   framealpha=0.0, fontsize=7,
                   labelcolor=["#3B82F6","#F59E0B","#EF4444"])

    # PNG → Base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="#080C10", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")



## File: `scripts\generate_sitemap.py`

py
#!/usr/bin/env python3
"""generate_sitemap.py — 銘柄ページ(累積)・週次レポートも含めて生成"""
import json
from datetime import datetime
from pathlib import Path

SITE_URL    = "https://your-site.vercel.app"   # ← デプロイ後に変更
ROOT        = Path(__file__).parent.parent
CONTENT_DIR = ROOT / "frontend" / "public" / "content"
INDEX_FILE  = CONTENT_DIR / "index.json"
SITEMAP_OUT = ROOT / "frontend" / "public" / "sitemap.xml"
ROBOTS_OUT  = ROOT / "frontend" / "public" / "robots.txt"
TODAY       = datetime.now().strftime("%Y-%m-%d")

STATIC = [
    {"url":"/",        "changefreq":"daily",   "priority":"1.0"},
    {"url":"/blog",    "changefreq":"daily",   "priority":"0.9"},
    {"url":"/tool",    "changefreq":"monthly", "priority":"0.7"},
    {"url":"/privacy", "changefreq":"monthly", "priority":"0.3"},
]

def build_sitemap():
    articles = []
    if INDEX_FILE.exists():
        try: articles = json.loads(INDEX_FILE.read_text())
        except Exception: pass

    urls = []
    for p in STATIC:
        urls.append(f"""  <url>
    <loc>{SITE_URL}{p['url']}</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>{p['changefreq']}</changefreq>
    <priority>{p['priority']}</priority>
  </url>""")

    for a in articles:
        slug  = a.get("slug","")
        date  = a.get("date", TODAY)
        atype = a.get("type","stock")
        # 銘柄ページ(stock-xxx)はchangefreq=daily、高priority
        if atype == "stock":
            changefreq, priority = "daily", "0.85"
        elif atype == "weekly":
            changefreq, priority = "weekly", "0.80"
        else:
            changefreq, priority = "monthly", "0.75"

        urls.append(f"""  <url>
    <loc>{SITE_URL}/blog/{slug}</loc>
    <lastmod>{date}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
    <xhtml:link rel="alternate" hreflang="ja" href="{SITE_URL}/blog/{slug}?lang=ja"/>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE_URL}/blog/{slug}?lang=en"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_URL}/blog/{slug}"/>
  </url>""")

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
{chr(10).join(urls)}
</urlset>"""
    SITEMAP_OUT.write_text(sitemap)
    print(f"✅ sitemap.xml: {len(urls)} URLs")

def build_robots():
    ROBOTS_OUT.write_text(f"""User-agent: *
Allow: /
Sitemap: {SITE_URL}/sitemap.xml
Disallow: /dashboard
Disallow: /settings
""")
    print("✅ robots.txt generated")

if __name__ == "__main__":
    build_sitemap()
    build_robots()



## File: `scripts\requirements-scripts.txt`

txt
-r ../shared/requirements-shared.txt
openai
feedparser
beautifulsoup4
lxml
mplfinance
matplotlib



## File: `shared\requirements-shared.txt`

txt
pandas
numpy
scipy
requests



## File: `shared\engines\__init__.py`

py



## File: `shared\engines\analysis.py`

py
import pandas as pd
import numpy as np
from config import CONFIG


class VCPAnalyzer:
    @staticmethod
    def calculate(df: pd.DataFrame) -> dict:
        try:
            if df is None or len(df) < 130:
                return VCPAnalyzer._empty()
            close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low  - close.shift()).abs()
            ], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])

            periods = [20, 30, 40, 60]
            ranges  = []
            for p in periods:
                h, l = float(high.iloc[-p:].max()), float(low.iloc[-p:].min())
                ranges.append((h - l) / h)

            avg_range      = float(np.mean(ranges[:3]))
            is_contracting = ranges[0] < ranges[1] < ranges[2]

            tight_score = (
                40 if avg_range < 0.10 else
                30 if avg_range < 0.15 else
                20 if avg_range < 0.20 else
                10 if avg_range < 0.28 else 0
            )
            if is_contracting:
                tight_score += 5
            tight_score = min(40, tight_score)

            v20_avg = float(volume.iloc[-20:].mean())
            v60_avg = float(volume.iloc[-60:-40].mean())
            v_ratio = v20_avg / v60_avg if v60_avg > 0 else 1.0
            vol_score = (
                30 if v_ratio < 0.45 else
                25 if v_ratio < 0.60 else
                15 if v_ratio < 0.75 else 0
            )

            ma50  = float(close.rolling(50).mean().iloc[-1])
            ma150 = float(close.rolling(150).mean().iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1])
            price = float(close.iloc[-1])
            ma_score = (
                (10 if price > ma50  else 0) +
                (10 if ma50  > ma150 else 0) +
                (10 if ma150 > ma200 else 0)
            )

            pivot    = float(high.iloc[-50:].max())
            distance = (pivot - price) / pivot
            pivot_bonus = (
                5 if 0    <= distance <= 0.04 else
                3 if 0.04 <  distance <= 0.08 else 0
            )

            signals = []
            if tight_score >= 35:  signals.append("Tight Base (VCP)")
            if is_contracting:     signals.append("V-Contraction Detected")
            if v_ratio < 0.75:     signals.append("Volume Dry-up Detected")
            if ma_score >= 20:     signals.append("Trend Alignment OK")
            if pivot_bonus > 0:    signals.append("Near Pivot Point")

            return {
                "score":     int(min(105, tight_score + vol_score + ma_score + pivot_bonus)),
                "atr":       atr,
                "signals":   signals,
                "is_dryup":  v_ratio < 0.75,
                "range_pct": round(ranges[0], 4),
                "vol_ratio": round(v_ratio, 2),
                "breakdown": {
                    "tight": tight_score,
                    "vol":   vol_score,
                    "ma":    ma_score,
                    "pivot": pivot_bonus,
                },
            }
        except Exception:
            return VCPAnalyzer._empty()

    @staticmethod
    def _empty() -> dict:
        return {
            "score": 0, "atr": 0.0, "signals": [],
            "is_dryup": False, "range_pct": 0.0, "vol_ratio": 1.0,
            "breakdown": {"tight": 0, "vol": 0, "ma": 0, "pivot": 0},
        }


class RSAnalyzer:
    @staticmethod
    def get_raw_score(df: pd.DataFrame) -> float:
        try:
            c = df["Close"]
            if len(c) < 21:
                return -999.0
            r = lambda n: (c.iloc[-1] / c.iloc[-n] - 1) if len(c) >= n else (c.iloc[-1] / c.iloc[0] - 1)
            return (r(252) * 0.4) + (r(126) * 0.2) + (r(63) * 0.2) + (r(21) * 0.2)
        except Exception:
            return -999.0

    @staticmethod
    def assign_percentiles(raw_list: list) -> list:
        if not raw_list:
            return []
        raw_list.sort(key=lambda x: x["raw_rs"])
        total = len(raw_list)
        for i, item in enumerate(raw_list):
            item["rs_rating"] = int(((i + 1) / total) * 99) + 1
        return raw_list


class StrategyValidator:
    @staticmethod
    def run(df: pd.DataFrame) -> float:
        try:
            if len(df) < 200:
                return 1.0
            close, high, low = df["Close"], df["High"], df["Low"]
            tr  = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low  - close.shift()).abs()
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()

            trades, in_pos, entry_p, stop_p = [], False, 0.0, 0.0
            for i in range(max(50, len(df) - 250), len(df)):
                if in_pos:
                    if low.iloc[i] <= stop_p:
                        trades.append(-1.0); in_pos = False
                    elif high.iloc[i] >= entry_p + (entry_p - stop_p) * CONFIG["TARGET_R_MULTIPLE"]:
                        trades.append(CONFIG["TARGET_R_MULTIPLE"]); in_pos = False
                    elif i == len(df) - 1:
                        trades.append(
                            (close.iloc[i] - entry_p) / (entry_p - stop_p)
                            if entry_p > stop_p else 0
                        ); in_pos = False
                else:
                    pivot = high.iloc[i - 20:i].max()
                    if close.iloc[i] > pivot and close.iloc[i] > close.rolling(50).mean().iloc[i]:
                        in_pos  = True
                        entry_p = float(close.iloc[i])
                        stop_p  = entry_p - float(atr.iloc[i]) * CONFIG["STOP_LOSS_ATR"]

            if not trades:
                return 1.0
            pos = sum(t for t in trades if t > 0)
            neg = abs(sum(t for t in trades if t < 0))
            return round(min(10.0, pos / neg if neg > 0 else (5.0 if pos > 0 else 1.0)), 2)
        except Exception:
            return 1.0



## File: `shared\engines\config.py`

py
import os

def _ei(key, default):
    v = os.getenv(key, "").strip()
    return int(v) if v else default

def _ef(key, default):
    v = os.getenv(key, "").strip()
    return float(v) if v else default

CONFIG = {
    "CAPITAL_JPY":       _ei("CAPITAL_JPY",       1_000_000),
    "MAX_POSITIONS":     _ei("MAX_POSITIONS",      20),
    "ACCOUNT_RISK_PCT":  _ef("ACCOUNT_RISK_PCT",   0.015),
    "MAX_SAME_SECTOR":   _ei("MAX_SAME_SECTOR",    2),
    "MIN_RS_RATING":     _ei("MIN_RS_RATING",      70),
    "MIN_VCP_SCORE":     _ei("MIN_VCP_SCORE",      55),
    "MIN_PROFIT_FACTOR": _ef("MIN_PROFIT_FACTOR",  1.1),
    "STOP_LOSS_ATR":     _ef("STOP_LOSS_ATR",      2.0),
    "TARGET_R_MULTIPLE": _ef("TARGET_R_MULTIPLE",  2.5),
    "CACHE_EXPIRY":      12 * 3600,
}

# NASDAQ 100
_NASDAQ100 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","COST",
    "NFLX","TMUS","AMD","PEP","LIN","CSCO","ADBE","INTU","TXN","QCOM",
    "AMAT","ISRG","BKNG","HON","VRTX","PANW","ADP","MU","SBUX","GILD",
    "LRCX","MRVL","REGN","KLAC","MDLZ","SNPS","CDNS","ADI","MELI","CRWD",
    "CEG","CTAS","ORLY","CSX","ASML","FTNT","MAR","PCAR","KDP","DASH",
    "MNST","WDAY","FAST","ROST","PAYX","DXCM","AEP","EA","CTSH","GEHC",
    "IDXX","ODFL","LULU","XEL","BKR","ON","KHC","EXC","VRSK","FANG",
    "BIIB","TTWO","GFS","ARM","TTD","ANSS","DLTR","WBD","NXPI","ROP",
    "CPRT","CSGP","CHTR","ILMN","MDB","ZS","TEAM","DDOG","NET","ZM",
    "OKTA","DOCU","RIVN","LCID","SMCI","MSTR","PLTR","APP","SIRI","PARA",
]

# ダウ 30
_DOW30 = [
    "AAPL","AMGN","AXP","BA","CAT","CRM","CSCO","CVX","DIS","DOW",
    "GS","HD","HON","IBM","INTC","JNJ","JPM","KO","MCD","MMM",
    "MRK","MSFT","NKE","PG","SHW","TRV","UNH","V","VZ","WMT",
]

# ラッセル2000 注目銘柄（流動性・成長性重視）
_RUSSELL2000 = [
    # ヘルスケア・バイオ
    "ACAD","ACHC","AGIO","ALKS","ALNY","AMPH","ARDX","ARWR","AXSM",
    "BMRN","BPMC","CERE","CHRS","CMPS","CNMD","COHU","DVAX","EOLS",
    "FIXX","FOLD","GKOS","HALO","HIMS","IMCR","INVA","IONS","IOVA",
    "ITCI","JANX","JAZZ","KROS","KURA","KYMR","LNTH","MGNX","MNKD",
    "MRUS","MYGN","NKTR","NVCR","OCGN","ORIC","PRCT","PRGO","PRTA",
    "PTCT","PTGX","RCUS","RLAY","ROIV","RPRX","RYTM","SAGE","SANA",
    "SEER","SMMT","VKTX","RARE","UTHR","HOLX","RXRX","TMDX","INSP",
    "IRTC","LIVN","NARI","SWAV","ACMR","NTRA","EXAS","NEOG","INCY",
    # テクノロジー・SaaS
    "ACLS","AGYS","AMBA","APPN","AVAV","BAND","BIGC","BRZE","CDAY",
    "CLFD","DAVE","DCBO","DLB","DOMO","EGAN","EGHT","ENVX","EXPI",
    "EXTR","FARO","FLNC","FROG","GBTG","GDRX","GLBE","GTLB","HCAT",
    "HEAR","SOUN","IONQ","OKLO","PATH","MNDY","IOT","DUOL","CFLT",
    "BBAI","CIEN","VIAV","IPGP","RXRX","IIVI","SAIL","VRNS","QLYS",
    # 消費・小売
    "BKE","BJRI","BLMN","BOOT","BRCC","BYND","CAKE","CALM","CATO",
    "CBRL","CENT","CENTA","CONN","CRSR","CSTE","CSWI","DRVN","EVTC",
    "WING","CAVA","CART","ONON","DECK","LULU","CROX","CELH","ELF",
    "SKIN","XPOF","BIRK","BOOT","BKE","PLNT","MODG","OXM","GFF",
    # 産業・エネルギー・素材
    "AEIS","AEHR","ALEX","ALG","ALGT","AMRC","AMSC","AMPS","AMTX",
    "AMWD","APOG","APPF","APYX","AQMS","ARLO","AROC","ARRY","ARVN",
    "ATKR","ATRC","ATSG","AZTA","BCC","BCPC","BLBD","BRC","BTG","BW",
    "CALM","CANO","CCJ","CDMO","CDNA","CEVA","CLPS","CMCO","CODA",
    "COLB","COOK","CPRX","CRAI","CRAW","CRIS","CTBI","CTRE","DQ",
    "DUOS","EKSO","ELVN","EMBC","EMKR","ENVB","EPRT","FCNCA","FORM",
    "GIGA","GLNG","GLPI","GOOS","GORV","GPCR","GREE","GRND","GURE",
    "HLNE","HMST","HNNA","HNRG","HIPO","MDXG","MGTX","NRIX","NTST",
    "NVET","ONEM","OPCH","PHAT","RPID","RDUS","RNST","UEC","URA",
    "UUUU","DNN","NXE","SCCO","AA","NUE","STLD","CLF","MP","ALTM",
    # フィンテック・暗号資産
    "AFRM","UPST","SOFI","DKNG","HOOD","MARA","RIOT","BITF","HUT",
    "IREN","WULF","CORZ","CIFR","CLSK","APLD","NBIS","ALAB","CLS",
    "FUTU","TIGR","NRDS","PFSI","GHLD","RCKT","LDI","UWMC","ESNT",
]

# コア（S&P500主要・高流動性）
_CORE = [
    # 半導体
    "NVDA","AMD","AVGO","TSM","ASML","MU","QCOM","MRVL","LRCX","AMAT","KLAC",
    "ADI","ON","SMCI","ARM","MPWR","TER","COHR","APH","TXN","GLW","INTC",
    "STM","WOLF","SWKS","QRVO","MCHP","ENTG","ONTO","AMKR","CAMT",
    # ビッグテック・クラウド・サイバー
    "MSFT","GOOGL","META","AAPL","AMZN","NFLX","CRM","NOW","SNOW","ADBE",
    "INTU","ORCL","IBM","CSCO","ANET","NET","PANW","CRWD","PLTR","ACN",
    "ZS","OKTA","FTNT","CYBR","S","TENB","VRNS","QLYS","SAIL",
    # AI・インフラ
    "APLD","VRT","ALAB","NBIS","CLS","IONQ","OKLO","DDOG","MDB","HUBS",
    "TTD","APP","GTLB","IOT","DUOL","CFLT","AI","PATH","MNDY","RXRX",
    "SOUN","BBAI","CIEN","LITE","IPGP","VIAV",
    # 金融・保険・決済
    "BRK-B","JPM","GS","MS","BAC","WFC","C","AXP","V","MA","COIN","MSTR",
    "HOOD","PYPL","SOFI","AFRM","UPST","SCHW","BX","BLK","SPGI","MCO",
    "CB","TRV","PGR","AIG","AFL","MET","PRU","CINF",
    "ICE","CME","NDAQ","CBOE","FIS","FI","GPN","JKHY","WEX",
    # ヘルスケア・バイオ・医療機器
    "UNH","LLY","ABBV","REGN","VRTX","NVO","BSX","ISRG","TMO","ABT",
    "MRNA","BNTX","MDT","CI","ELV","HCA","HOLX","DVAX","SMMT","VKTX",
    "CRSP","NTLA","BEAM","UTHR","RARE","OMER","GILD","AMGN","BIIB",
    "INCY","EXAS","NTRA","NEOG","TMDX","INSP","IRTC","LIVN","NARI","SWAV",
    "HIMS","ACAD","ALNY","IONS","ARWR","PTCT","RXRX","KYMR","JANX","BPMC",
    # 消費・小売・外食・ブランド
    "COST","WMT","HD","MCD","SBUX","NKE","MELI","BABA","TSLA","CVNA",
    "LULU","ONON","DECK","CROX","WING","CMG","DPZ","YUM","CELH","MNST",
    "CART","CAVA","ROST","TJX","LOW","TGT","ORLY","AZO","EBAY","ETSY",
    "W","CHWY","ELF","SKIN","BIRK","TPR","CPRI","BOOT","BKE","PLNT",
    # エネルギー
    "XOM","CVX","COP","EOG","SLB","OXY","VLO","PSX","MPC","FCX","CCJ",
    "URA","UUUU","DNN","NXE","UEC","AM","TRGP","OKE","WMB","KMI","ET",
    "CTRA","DVN","FANG","MRO","APA","HAL","BKR","NOV","WHD",
    # 産業・防衛・航空宇宙
    "GE","GEV","ETN","CAT","HON","DE","LMT","RTX","BA","GD","HII","AXON",
    "LHX","NOC","TDG","ROP","URI","PCAR","CMI","NSC","UNP","CSX","FDX",
    "RKLB","ASTS","BE","LUNR","RCL","DAL","UAL","ALK","AAL",
    "TT","CARR","OTIS","AME","RRX","GWW","FAST","MLI",
    # 不動産・公共・インフラ
    "NEE","DUK","SO","AEP","EXC","XEL","ED","D","PCG","EIX","WEC","AWK",
    "AMT","EQIX","PLD","CCI","DLR","O","PSA","WELL","IRM","VICI","GLPI",
    "SPG","EQR","AVB","MAA","NNN","STAG",
    # テレコム・メディア・エンタメ
    "TMUS","VZ","CMCSA","DIS","SPOT","RDDT","RBLX","UBER","ABNB","BKNG",
    "MAR","HLT","DKNG","SOUN","GME","PARA","WBD","AMCX","PINS",
    "YELP","Z","EXPE","LMND","FUBO",
    # 素材・鉱業・化学
    "NUE","STLD","AA","SCCO","FCX","NEM","AEM","WPM","RGLD","CLF",
    "MP","ALTM","OLN","CE","EMN","LYB","DOW","LIN","APD","SHW",
    # ETF
    "SPY","QQQ","IWM","SMH","XLF","XLV","XLE","XLI","XLK","XLC","XLY",
    "XLRE","XLP","XLB","XLU","GLD","SLV","USO","TLT","HYG","ARKK",
    "SOXX","IBB","XBI","KRE","HACK","BOTZ","CIBR","CLOU","WCLD",
]

TICKERS = sorted(list(set(_NASDAQ100 + _DOW30 + _RUSSELL2000 + _CORE)))



## File: `shared\engines\core_fmp.py`

py
"""
core_fmp.py — Financial Modeling Prep API クライアント
Starter プラン（$19/mo）: 300 req/min, 5年履歴, 米国株
"""
import os, time, requests, pickle, pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

FMP_API_KEY  = os.environ.get("FMP_API_KEY", "")
BASE_URL     = "https://financialmodelingprep.com/api/v3"
BASE_URL_V4  = "https://financialmodelingprep.com/api/v4"
CACHE_DIR    = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)

# 300 req/min → 250ms間隔
_last_call   = 0.0
_MIN_INTERVAL = 0.25

def _throttle():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.time()

def _get(url: str, params: dict = {}, cache_key: str = "", ttl: int = 0) -> dict | list | None:
    """汎用GETリクエスト（キャッシュ対応）"""
    if cache_key:
        cf = CACHE_DIR / f"{cache_key}.pkl"
        if cf.exists() and (time.time() - cf.stat().st_mtime < ttl):
            try:
                with open(cf, "rb") as f: return pickle.load(f)
            except Exception: pass
    try:
        _throttle()
        resp = requests.get(url, params={**params, "apikey": FMP_API_KEY}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if cache_key and data:
            with open(CACHE_DIR / f"{cache_key}.pkl", "wb") as f: pickle.dump(data, f)
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print(f"Rate limit hit, sleeping 60s...")
            time.sleep(60)
        else:
            print(f"HTTP {e.response.status_code}: {url}")
        return None
    except Exception as e:
        print(f"FMP error: {e}")
        return None


# ── OHLCVデータ（12時間キャッシュ）──────────────────────
def get_historical_data(ticker: str, days: int = 700) -> pd.DataFrame | None:
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date   = datetime.now().strftime("%Y-%m-%d")
    data = _get(f"{BASE_URL}/historical-price-full/{ticker}",
                {"from": from_date, "to": to_date},
                cache_key=f"hist_{ticker}", ttl=12*3600)
    if not data or "historical" not in data or not data["historical"]:
        return None
    df = pd.DataFrame(data["historical"])
    df = df.rename(columns={"date":"Date","open":"Open","high":"High",
                             "low":"Low","close":"Close","volume":"Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df[["Open","High","Low","Close","Volume"]].copy()


# ── リアルタイムクォート ──────────────────────────────────
def get_quote(ticker: str) -> dict | None:
    data = _get(f"{BASE_URL}/quote/{ticker}")
    return data[0] if isinstance(data, list) and data else None


# ── 会社プロフィール（24時間キャッシュ）─────────────────
def get_company_profile(ticker: str) -> dict | None:
    data = _get(f"{BASE_URL}/profile/{ticker}",
                cache_key=f"profile_{ticker}", ttl=24*3600)
    return data[0] if isinstance(data, list) and data else None


# ── アナリスト評価・目標株価（24時間キャッシュ）──────────
def get_analyst_consensus(ticker: str) -> dict | None:
    """
    Returns: {
      consensus: 'Buy'|'Sell'|'Hold',
      analyst_count: int,
      target_high: float, target_low: float, target_mean: float,
      target_pct: float  (目標株価と現在値の乖離%)
    }
    """
    data = _get(f"{BASE_URL}/analyst-stock-recommendations/{ticker}",
                cache_key=f"analyst_{ticker}", ttl=24*3600)
    if not isinstance(data, list) or not data:
        return None
    # 直近3ヶ月の集計
    buy = sell = hold = 0
    for r in data[:6]:  # 直近6レコード（月次）
        buy  += r.get("analystRatingsbuy", 0) + r.get("analystRatingsStrongBuy", 0)
        hold += r.get("analystRatingsHold", 0)
        sell += r.get("analystRatingsSell", 0) + r.get("analystRatingsStrongSell", 0)
    total = buy + hold + sell
    if total == 0: return None

    # 目標株価
    tp = _get(f"{BASE_URL}/price-target-consensus/{ticker}",
              cache_key=f"pricetarget_{ticker}", ttl=24*3600)
    target_mean = tp[0].get("targetConsensus") if isinstance(tp, list) and tp else None
    target_high = tp[0].get("targetHigh")      if isinstance(tp, list) and tp else None
    target_low  = tp[0].get("targetLow")       if isinstance(tp, list) and tp else None

    # 現在値取得して乖離%計算
    quote = get_quote(ticker)
    price = float(quote.get("price", 0)) if quote else 0
    target_pct = round((target_mean - price) / price * 100, 1) if target_mean and price else None

    consensus = "Buy" if buy > sell and buy > hold else \
                "Sell" if sell > buy and sell > hold else "Hold"

    return {
        "consensus":     consensus,
        "analyst_count": total,
        "buy":  buy, "hold": hold, "sell": sell,
        "target_mean": round(target_mean, 2) if target_mean else None,
        "target_high": round(target_high, 2) if target_high else None,
        "target_low":  round(target_low,  2) if target_low  else None,
        "target_pct":  target_pct,
    }


# ── ファンダメンタルズ（TTM）────────────────────────────
def get_fundamentals(ticker: str) -> dict | None:
    """
    Returns: {
      pe_forward, pe_ttm, eps_ttm,
      revenue_growth_yoy, earnings_growth_yoy,
      gross_margin, profit_margin,
      debt_to_equity, current_ratio,
      market_cap_b (10億ドル単位)
    }
    """
    # Key Metrics TTM
    km = _get(f"{BASE_URL}/key-metrics-ttm/{ticker}",
              cache_key=f"keymetrics_{ticker}", ttl=24*3600)
    km = km[0] if isinstance(km, list) and km else {}

    # Income statement growth
    ig = _get(f"{BASE_URL}/income-statement-growth/{ticker}",
              {"limit": 2},
              cache_key=f"incgrowth_{ticker}", ttl=24*3600)
    ig = ig[0] if isinstance(ig, list) and ig else {}

    # Financial ratios TTM
    fr = _get(f"{BASE_URL}/ratios-ttm/{ticker}",
              cache_key=f"ratios_{ticker}", ttl=24*3600)
    fr = fr[0] if isinstance(fr, list) and fr else {}

    def _pct(v):
        return round(float(v)*100, 1) if v is not None else None
    def _rnd(v, n=2):
        return round(float(v), n) if v is not None else None

    return {
        "pe_forward":          _rnd(km.get("peRatioTTM")),
        "pe_ttm":              _rnd(fr.get("priceEarningsRatioTTM")),
        "eps_ttm":             _rnd(km.get("epsTTM")),
        "revenue_growth_yoy":  _pct(ig.get("growthRevenue")),
        "earnings_growth_yoy": _pct(ig.get("growthNetIncome")),
        "gross_margin":        _pct(fr.get("grossProfitMarginTTM")),
        "profit_margin":       _pct(fr.get("netProfitMarginTTM")),
        "debt_to_equity":      _rnd(fr.get("debtEquityRatioTTM")),
        "current_ratio":       _rnd(fr.get("currentRatioTTM")),
        "market_cap_b":        _rnd(km.get("marketCapTTM", 0) / 1e9, 1) if km.get("marketCapTTM") else None,
        "revenue_per_share":   _rnd(km.get("revenuePerShareTTM")),
        "roe":                 _pct(fr.get("returnOnEquityTTM")),
        "roa":                 _pct(fr.get("returnOnAssetsTTM")),
    }


# ── 機関投資家・インサイダー保有（24時間キャッシュ）──────
def get_ownership(ticker: str) -> dict | None:
    """
    Returns: {
      institutional_pct: float,   # 機関投資家保有率%
      insider_pct: float,         # インサイダー保有率%
      short_float_pct: float,     # 空売り比率%
      short_days_to_cover: float, # 空売り日数
    }
    """
    # 機関投資家保有率
    inst = _get(f"{BASE_URL}/institutional-holder/{ticker}",
                cache_key=f"inst_{ticker}", ttl=24*3600)

    # 空売りデータ
    short = _get(f"{BASE_URL}/short-float/{ticker}",
                 cache_key=f"short_{ticker}", ttl=24*3600)
    short = short[0] if isinstance(short, list) and short else {}

    # プロフィールから保有率取得（最も確実）
    profile = get_company_profile(ticker) or {}

    inst_pct   = None
    insider_pct = None
    # 機関保有率はプロフィールに含まれる場合がある
    if profile.get("institutionalOwnershipPercentage"):
        inst_pct = round(float(profile["institutionalOwnershipPercentage"]) * 100, 1)

    # 空売り
    short_float = None
    short_days  = None
    if short.get("shortFloatPercent"):
        short_float = round(float(short["shortFloatPercent"]), 1)
    if short.get("shortDaysToCover"):
        short_days = round(float(short["shortDaysToCover"]), 1)

    return {
        "institutional_pct":   inst_pct,
        "insider_pct":         insider_pct,
        "short_float_pct":     short_float,
        "short_days_to_cover": short_days,
    }


# ── 直近ニュース（6時間キャッシュ）──────────────────────
def get_news(ticker: str, limit: int = 5) -> list:
    """
    Returns: [{"title", "publishedDate", "source", "url", "summary"}, ...]
    """
    data = _get(f"{BASE_URL}/stock_news",
                {"tickers": ticker, "limit": limit},
                cache_key=f"news_{ticker}", ttl=6*3600)
    if not isinstance(data, list):
        return []
    return [{
        "title":         d.get("title", ""),
        "published_at":  d.get("publishedDate", ""),
        "source":        d.get("site", ""),
        "url":           d.get("url", ""),
        "summary":       d.get("text", "")[:200] if d.get("text") else "",
    } for d in data[:limit]]


# ── チャート用ローソク足データ（直近90日）────────────────
def get_candles_for_chart(ticker: str, days: int = 120) -> list:
    df = get_historical_data(ticker, days=days)
    if df is None: return []
    return [{
        "date":   d.strftime("%Y-%m-%d"),
        "open":   round(float(r["Open"]),  2),
        "high":   round(float(r["High"]),  2),
        "low":    round(float(r["Low"]),   2),
        "close":  round(float(r["Close"]), 2),
        "volume": int(r["Volume"]),
    } for d, r in df.iterrows()]



