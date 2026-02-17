#!/usr/bin/env python3
import os, requests

KEY = os.environ.get("FMP_API_KEY", "")
BASE = "https://financialmodelingprep.com/stable"

print(f"=== FMP TEST ===")
print(f"Key: {KEY[:8]}...{KEY[-4:]}")

url = f"{BASE}/historical-price-eod/full"
resp = requests.get(url, params={"symbol": "SPY", "apikey": KEY}, timeout=30)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    if "historical" in data and data["historical"]:
        latest = data["historical"][0]
        print(f"✅ SUCCESS: {latest['date']} close={latest['close']}")
    else:
        print(f"❌ No data: {data}")
else:
    print(f"❌ FAIL: {resp.text[:300]}")