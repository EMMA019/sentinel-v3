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
