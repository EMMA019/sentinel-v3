#!/usr/bin/env python3
"""
scripts/test_fundamentals.py — ファンダメンタルズ取得テスト
"""
import os, requests, json

KEY  = os.environ.get("FMP_API_KEY", "")
BASE = "https://financialmodelingprep.com/stable"
TICKER = "AAPL"

def test(name, url, params={}):
    print(f"\n[{name}]")
    print(f"  URL: {url}")
    resp = requests.get(url, params={**params, "apikey": KEY}, timeout=15)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        item = data[0] if isinstance(data, list) and data else data
        if item:
            # 最初の5キーだけ表示
            keys = list(item.keys())[:5]
            print(f"  ✅ Keys: {keys}")
            for k in keys:
                print(f"    {k}: {item[k]}")
        else:
            print(f"  ❌ Empty response")
    else:
        print(f"  ❌ {resp.text[:100]}")

print(f"=== FUNDAMENTALS TEST ({TICKER}) ===")
print(f"Key: {KEY[:8]}...{KEY[-4:]}")

# 1. 決算EPS（CANSLIMのC）
test("earnings-history",
    f"{BASE}/earnings-historical-growth",
    {"symbol": TICKER})

# 2. 年次決算（CANSLIMのA）
test("income-statement",
    f"{BASE}/income-statement",
    {"symbol": TICKER, "period": "annual", "limit": 3})

# 3. 機関投資家（CANSLIMのI）
test("institutional-ownership",
    f"{BASE}/institutional-ownership",
    {"symbol": TICKER})

# 4. 現在確認済み（比較用）
test("key-metrics（確認済み）",
    f"{BASE}/key-metrics",
    {"symbol": TICKER, "period": "annual", "limit": 1})

# 5. income-statement-growth（確認済み）
test("income-statement-growth（確認済み）",
    f"{BASE}/income-statement-growth",
    {"symbol": TICKER, "period": "annual", "limit": 1})

print("\n[income-statement 全キー確認]")
resp = requests.get(
    f"{BASE}/income-statement",
    params={"symbol": TICKER, "period": "annual", "limit": 3, "apikey": KEY},
    timeout=15
)
data = resp.json()
if data and isinstance(data, list):
    print(f"  件数: {len(data)}")
    print(f"  全キー: {list(data[0].keys())}")
    
    # EPS・売上成長率を手動計算
    if len(data) >= 2:
        curr = data[0]
        prev = data[1]
        
        eps_curr = curr.get("eps", 0) or 0
        eps_prev = prev.get("eps", 0) or 0
        rev_curr = curr.get("revenue", 0) or 0
        rev_prev = prev.get("revenue", 0) or 0
        
        eps_growth = (eps_curr - eps_prev) / abs(eps_prev) * 100 if eps_prev else None
        rev_growth = (rev_curr - rev_prev) / abs(rev_prev) * 100 if rev_prev else None
        
        print(f"\n  EPS: {eps_prev} → {eps_curr} = {eps_growth:.1f}%" if eps_growth else "  EPS: 計算不可")
        print(f"  Rev: {rev_prev:,.0f} → {rev_curr:,.0f} = {rev_growth:.1f}%" if rev_growth else "  Rev: 計算不可")
print("\n=== END ===")