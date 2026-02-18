#!/usr/bin/env python3
"""
scripts/scrape_news.py — 複数ソースからニュース収集
====================================================
BeautifulSoup4 + requests で以下をスクレイピング:
- Seeking Alpha
- Yahoo Finance
- Benzinga
- FMP News API（既存）

使い方:
  python scripts/scrape_news.py NVDA
  → nvda_news.json を出力
"""
import os, json, sys, time
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup

sys.path.append(str(Path(__file__).parent.parent / "shared"))
from engines import core_fmp

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def scrape_seeking_alpha(ticker: str) -> list:
    """Seeking Alpha の最新記事"""
    print(f"  📰 Seeking Alpha...")
    try:
        url = f"https://seekingalpha.com/symbol/{ticker}/news"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        articles = []
        # 記事リンクを探す（サイト構造に依存）
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if '/article/' in href and not href.startswith('http'):
                href = 'https://seekingalpha.com' + href
            
            title = link.get_text(strip=True)
            if title and len(title) > 10 and href not in [a['url'] for a in articles]:
                articles.append({
                    'source': 'Seeking Alpha',
                    'title':  title,
                    'url':    href,
                    'date':   datetime.now().strftime('%Y-%m-%d'),
                })
            
            if len(articles) >= 5:
                break
        
        return articles
    except Exception as e:
        print(f"    ⚠️  Seeking Alpha エラー: {e}")
        return []


def scrape_yahoo_finance(ticker: str) -> list:
    """Yahoo Finance ニュース"""
    print(f"  📰 Yahoo Finance...")
    try:
        url = f"https://finance.yahoo.com/quote/{ticker}/news"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        articles = []
        # h3タグでニュースタイトルを探す
        for h3 in soup.find_all('h3'):
            link = h3.find('a', href=True)
            if link:
                title = link.get_text(strip=True)
                href  = link['href']
                if not href.startswith('http'):
                    href = 'https://finance.yahoo.com' + href
                
                if title and len(title) > 10:
                    articles.append({
                        'source': 'Yahoo Finance',
                        'title':  title,
                        'url':    href,
                        'date':   datetime.now().strftime('%Y-%m-%d'),
                    })
            
            if len(articles) >= 5:
                break
        
        return articles
    except Exception as e:
        print(f"    ⚠️  Yahoo Finance エラー: {e}")
        return []


def scrape_benzinga(ticker: str) -> list:
    """Benzinga ニュース（RSSまたはHTML）"""
    print(f"  📰 Benzinga...")
    try:
        # Benzingaは会員制が多いので、RSSから取得を試みる
        url = f"https://www.benzinga.com/stock/{ticker}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        articles = []
        for link in soup.find_all('a', href=True, class_=lambda c: c and 'title' in c.lower()):
            title = link.get_text(strip=True)
            href  = link['href']
            if not href.startswith('http'):
                href = 'https://www.benzinga.com' + href
            
            if title and len(title) > 10 and href not in [a['url'] for a in articles]:
                articles.append({
                    'source': 'Benzinga',
                    'title':  title,
                    'url':    href,
                    'date':   datetime.now().strftime('%Y-%m-%d'),
                })
            
            if len(articles) >= 5:
                break
        
        return articles
    except Exception as e:
        print(f"    ⚠️  Benzinga エラー: {e}")
        return []


def get_fmp_news(ticker: str) -> list:
    """FMP News API（既存）"""
    print(f"  📰 FMP API...")
    try:
        news = core_fmp.get_news(ticker, limit=10)
        return [{
            'source': 'FMP',
            'title':  n['title'],
            'url':    n['url'],
            'date':   n['published_at'][:10],
            'text':   n.get('text', '')[:200],
        } for n in (news or [])]
    except Exception as e:
        print(f"    ⚠️  FMP エラー: {e}")
        return []


def sentiment_analysis(articles: list) -> dict:
    """簡易センチメント分析"""
    positive_words = ['beat', 'upgrade', 'buy', 'strong', 'growth', 'surge', 'bullish', 'outperform']
    negative_words = ['miss', 'downgrade', 'sell', 'weak', 'decline', 'drop', 'bearish', 'underperform']
    
    pos_count = 0
    neg_count = 0
    
    for a in articles:
        text = (a.get('title', '') + ' ' + a.get('text', '')).lower()
        pos_count += sum(1 for w in positive_words if w in text)
        neg_count += sum(1 for w in negative_words if w in text)
    
    total = pos_count + neg_count
    if total == 0:
        return {'score': 0, 'label': 'Neutral'}
    
    score = (pos_count - neg_count) / total * 100
    if score > 30:
        label = 'Bullish'
    elif score < -30:
        label = 'Bearish'
    else:
        label = 'Neutral'
    
    return {
        'score': round(score, 1),
        'label': label,
        'positive_count': pos_count,
        'negative_count': neg_count,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_news.py TICKER")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    print(f"=== News Scraper: {ticker} ===")
    
    # 各ソースから収集
    all_articles = []
    all_articles.extend(get_fmp_news(ticker))
    time.sleep(1)
    all_articles.extend(scrape_seeking_alpha(ticker))
    time.sleep(1)
    all_articles.extend(scrape_yahoo_finance(ticker))
    time.sleep(1)
    all_articles.extend(scrape_benzinga(ticker))
    
    # 重複削除
    unique = []
    seen_urls = set()
    for a in all_articles:
        if a['url'] not in seen_urls:
            unique.append(a)
            seen_urls.add(a['url'])
    
    # センチメント分析
    sentiment = sentiment_analysis(unique)
    
    # 結果
    print(f"\n{'='*60}")
    print(f"収集件数: {len(unique)}件")
    print(f"センチメント: {sentiment['label']} ({sentiment['score']:+.1f})")
    print(f"  ポジティブ: {sentiment['positive_count']} / ネガティブ: {sentiment['negative_count']}")
    print(f"{'='*60}")
    
    for i, a in enumerate(unique[:10], 1):
        print(f"{i}. [{a['source']}] {a['title'][:60]}...")
    
    # JSON保存
    out = {
        "generated_at": datetime.now().isoformat(),
        "ticker":       ticker,
        "total_count":  len(unique),
        "sentiment":    sentiment,
        "articles":     unique,
    }
    
    out_file = Path(__file__).parent.parent / "frontend" / "public" / "content" / f"{ticker.lower()}_news.json"
    out_file.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n✅ Saved: {out_file}")


if __name__ == "__main__":
    main()
