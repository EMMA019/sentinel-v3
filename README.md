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
