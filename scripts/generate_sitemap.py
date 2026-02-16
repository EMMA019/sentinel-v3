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
