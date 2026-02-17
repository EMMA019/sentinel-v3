#!/usr/bin/env python3
import os, requests, time, json

# 設定
KEY = os.environ.get("FMP_API_KEY", "")
BASE = "https://financialmodelingprep.com/stable"
SYMBOL = "AAPL"  # テスト用銘柄

print(f"=== FMP FULL DIAGNOSTICS ({SYMBOL}) ===")
print(f"Key: {KEY[:8]}...{KEY[-4:]}")

def test_endpoint(name, slug, params):
    print(f"\n--- Testing {name} ---")
    url = f"{BASE}/{slug}"
    try:
        # パラメータにAPIキーを追加
        p = {**params, "apikey": KEY}
        start = time.time()
        resp = requests.get(url, params=p, timeout=15)
        elapsed = time.time() - start
        
        print(f"URL: {resp.url.replace(KEY, '***')}")
        print(f"Status: {resp.status_code} ({elapsed:.2f}s)")

        if resp.status_code == 200:
            data = resp.json()
            
            # データ型の判定と中身のチラ見せ
            if isinstance(data, list):
                count = len(data)
                print(f"✅ Type: List (Count: {count})")
                if count > 0:
                    print(f"   Sample: {str(data[0])[:150]}...")
                else:
                    print(f"   ⚠️ Empty List returned")
            elif isinstance(data, dict):
                keys = list(data.keys())
                print(f"✅ Type: Dict (Keys: {keys})")
                print(f"   Sample: {str(data)[:150]}...")
            else:
                print(f"❓ Unknown Type: {type(data)}")
        else:
            print(f"❌ Error: {resp.text[:200]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # レートリミット配慮
    time.sleep(1)

# 1. ニュース (News)
# core_fmp.py: /stable/news/stock-latest?symbol={ticker}
test_endpoint(
    "News", 
    "news/stock-latest", 
    {"symbol": SYMBOL, "limit": 3, "page": 0}
)

# 2. 現在値 (Quote)
# core_fmp.py: /stable/quote?symbol={ticker}
test_endpoint(
    "Quote", 
    "quote", 
    {"symbol": SYMBOL}
)

# 3. 企業プロフィール (Profile)
# core_fmp.py: /stable/profile?symbol={ticker}
test_endpoint(
    "Profile", 
    "profile", 
    {"symbol": SYMBOL}
)

# 4. アナリスト評価 (Consensus)
# core_fmp.py: /stable/price-target-summary?symbol={ticker}
test_endpoint(
    "Price Target", 
    "price-target-summary", 
    {"symbol": SYMBOL}
)

# 5. 財務指標 (Key Metrics)
# core_fmp.py: /stable/key-metrics?symbol={ticker}
test_endpoint(
    "Key Metrics", 
    "key-metrics", 
    {"symbol": SYMBOL, "period": "annual", "limit": 1}
)

print("\n=== DIAGNOSTICS COMPLETE ===")

