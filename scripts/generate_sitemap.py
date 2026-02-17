#!/usr/bin/env python3
"""
generate_sitemap.py — サイトマップとrobots.txtの生成
================================================
index.json を読み込んで、SEO用のファイルを作成します。
修正点: 壊れたデータ（文字列のみなど）が含まれていてもスキップして続行するように修正
"""
import json
from datetime import datetime
from pathlib import Path

# ▼▼▼【重要】デプロイ先のURLに変更してください ▼▼▼
SITE_URL    = "https://your-site.vercel.app"
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

ROOT        = Path(__file__).parent.parent
CONTENT_DIR = ROOT / "frontend" / "public" / "content"
INDEX_FILE  = CONTENT_DIR / "index.json"
SITEMAP_OUT = ROOT / "frontend" / "public" / "sitemap.xml"
ROBOTS_OUT  = ROOT / "frontend" / "public" / "robots.txt"
TODAY       = datetime.now().strftime("%Y-%m-%d")

# 静的ページの定義
STATIC = [
    {"url":"",         "changefreq":"daily",   "priority":"1.0"}, # トップページ
    {"url":"/blog",    "changefreq":"daily",   "priority":"0.9"},
    {"url":"/tool",    "changefreq":"monthly", "priority":"0.7"},
    {"url":"/privacy", "changefreq":"monthly", "priority":"0.3"},
]

def build_sitemap():
    articles = []
    
    # index.json の読み込み
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text())
            articles = data.get("articles", [])
        except Exception as e:
            print(f"⚠️ Error reading index.json: {e}")
            pass

    urls = []
    
    # 1. 静的ページの追加
    for p in STATIC:
        loc = f"{SITE_URL}{p['url']}"
        urls.append(f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>{p['changefreq']}</changefreq>
    <priority>{p['priority']}</priority>
  </url>""")

    # 2. 記事ページの追加
    for a in articles:
        # 【修正】ここがエラーの原因でした。
        # a が辞書(dict)ではなく文字列(str)になってしまっているデータがある場合、スキップします。
        if not isinstance(a, dict):
            continue

        slug  = a.get("slug", "")
        if not slug: continue
        
        date  = a.get("date", TODAY)
        atype = a.get("type", "daily")
        
        if atype == "daily":
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
  </url>""")

    # XMLの組み立て
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    SITEMAP_OUT.write_text(sitemap_content)
    print(f"✅ sitemap.xml: Generated {len(urls)} URLs")


def build_robots():
    robots_content = f"""User-agent: *
Allow: /
Sitemap: {SITE_URL}/sitemap.xml
Disallow: /api/
Disallow: /_next/
"""
    ROBOTS_OUT.write_text(robots_content)
    print("✅ robots.txt: Generated")


if __name__ == "__main__":
    print(f"=== Generating Sitemap & Robots for {SITE_URL} ===")
    build_sitemap()
    build_robots()
    print("=== Done ===")

