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
