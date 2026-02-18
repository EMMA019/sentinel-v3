# SENTINEL PERSONAL — TradingViewスタイル完全版

**自分専用TradingView + AI判断エンジン**

公開しない。株価全表示。チャート埋め込み。AIが全ルール理解してBUY/WAIT判定。

---

## 📊 機能一覧

### ページ構成（8ページ）

```
1. Dashboard      本日のACTION（価格・Entry/Stop/Target全表示）
2. Charts         TradingViewフルチャート（マルチタブ・時間軸切替）
3. AI Judgment    OpenAI判定エンジン（VCP/CANSLIM/ECR全ルール投入）
4. Watchlist      ウォッチリスト（取得価格・損益・メモ）
5. Portfolio      保有銘柄P&Lトラッキング（円建て）
6. Scanner        全銘柄スキャン（フィルター・展開詳細）
7. Methods        手法別トップ30比較
8. Backtest       複利シミュレーション
```

### バックエンドスクリプト

```python
scripts/
├── ai_judge.py       OpenAI APIでBUY/WAIT/SELL判定
├── scrape_news.py    Seeking Alpha / Yahoo / Benzinga スクレイピング
├── notify_email.py   毎朝のHTMLメール送信
```

---

## 🚀 セットアップ

### 1. 依存関係インストール

```bash
# フロントエンド
cd personal
npm install

# バックエンド
pip install -r requirements.txt
pip install -r ../shared/requirements-shared.txt
pip install -r ../scripts/requirements-scripts.txt
```

### 2. 環境変数

```bash
# .env.local（フロントエンド）
VITE_APP_PASSWORD=your_secret_password

# GitHub Secrets（バックエンド）
FMP_API_KEY=xxx
OPENAI_API_KEY=xxx
OPENAI_BASE_URL=https://api.openai.com/v1  # optional
OPENAI_MODEL=gpt-4o  # optional
NOTIFY_EMAIL_TO=your@email.com
NOTIFY_EMAIL_FROM=your-gmail@gmail.com
NOTIFY_EMAIL_PASS=gmail-app-password
```

### 3. ローカル開発

```bash
# contentデータをコピー
cp -r ../frontend/public/content ./public/

# 開発サーバー起動
npm run dev  # → http://localhost:4000
```

### 4. Vercelデプロイ

```bash
# Vercel CLI
vercel --prod

# または Vercel Dashboard から
# - Root Directory: personal/
# - Build Command: npm run build
# - Output Directory: dist
# - Environment Variables: VITE_APP_PASSWORD
```

---

## 🤖 AI判断エンジンの使い方

### コマンドライン実行

```bash
# 環境変数設定
export OPENAI_API_KEY=sk-...

# 判定実行（例: NVDA）
cd personal
python scripts/ai_judge.py NVDA

# → frontend/public/content/nvda_judgment.json 生成
# → Webで /ai ページから確認
```

### AI判断の仕組み

**プロンプト構成:**

1. System Prompt（固定）: VCP/CANSLIM/ECRの全ルール + 判定基準
2. User Prompt（動的）: テクニカル + ファンダ + ニュース
3. Response: JSON形式で BUY/WAIT/SELL + 理由 + リスク + 材料

**OpenAI Response例:**
```json
{
  "judgment": "BUY",
  "confidence": 85,
  "reasoning": "VCP完成、RS高値、ニュース好材料",
  "entry_plan": "$450.00でピボットブレイク時エントリー",
  "risks": ["出来高不足", "FOMC待ち"],
  "catalysts": ["決算発表", "新製品発表"]
}
```

---

## 📰 ニュース収集

```bash
# 手動実行
python scripts/scrape_news.py NVDA
# → nvda_news.json 生成（センチメント分析付き）
```

**対応ソース:**
- FMP News API（既存）
- Seeking Alpha（BeautifulSoup）
- Yahoo Finance（BeautifulSoup）
- Benzinga（BeautifulSoup）

**センチメント分析:**
- Bullish/Neutral/Bearish判定
- ポジティブ/ネガティブキーワードカウント

---

## 📈 TradingViewチャート

### フルチャート（/charts）
- マルチタブ対応（複数銘柄同時監視）
- 時間軸切り替え（1分/5分/15分/1時間/日足/週足）
- 銘柄追加・削除
- Yahoo / Finviz / Seeking Alpha 直リンク

### カスタムVCPチャート
- Pivot Point表示
- MA20/50/200
- 出来高dry-up強調（色分け）
- タイトニング範囲視覚化

---

## 🔒 セキュリティ

**パスワード保護（2段階）**

1. アプリ内パスワード（App.jsx）
2. Vercel Password Protection（有料プラン）

**検索エンジン対策:**
- noindex/nofollow設定済み
- robots.txt全拒否

---

## 📂 ファイル構成

```
personal/
├── src/
│   ├── App.jsx
│   ├── components/
│   │   ├── TradingViewWidget.jsx
│   │   └── VCPChart.jsx
│   └── pages/ (8ページ)
├── scripts/
│   ├── ai_judge.py
│   ├── scrape_news.py
│   └── notify_email.py
├── requirements.txt
└── README.md
```

---

## 💡 自動化例

```bash
# cronで毎朝AI判定
0 8 * * 1-5 python ai_judge.py NVDA AAPL MSFT

# GitHub Actionsで毎朝メール送信
- name: Send morning email
  run: python scripts/notify_email.py
```

---

⚠️ **免責**: AI判定は参考情報。投資判断は自己責任で。

🛡️ **SENTINEL PERSONAL** — 完全個人用トレーディングシステム
