import { useSEO } from '../hooks/useSEO';

export default function Privacy() {
  useSEO({
    title:       'プライバシーポリシー / Privacy Policy',
    description: 'SENTINEL PROのプライバシーポリシーおよびGoogle AdSense、Cookieの使用に関する説明。',
  });

  return (
    <div className="min-h-screen bg-ink pt-20 pb-16 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="font-display font-700 text-bright text-2xl mb-8">
          プライバシーポリシー / Privacy Policy
        </h1>

        {/* 日本語 */}
        <section className="mb-10 space-y-4">
          <h2 className="font-display font-700 text-bright text-lg border-b border-border pb-2">
            日本語
          </h2>

          <div className="space-y-3 font-body text-sm text-dim leading-relaxed">
            <p>
              本サイト（SENTINEL PRO）は、Google AdSenseを利用した広告を掲載しています。
              Googleはユーザーのウェブサイト閲覧情報を元に、関連性の高い広告を表示するためにCookieを使用することがあります。
            </p>
            <h3 className="font-700 text-text">Cookieについて</h3>
            <p>
              本サイトはCookieを使用しています。Cookieはブラウザの設定から無効にすることができますが、
              一部のサービスが正常に動作しなくなる場合があります。
            </p>
            <h3 className="font-700 text-text">Google AdSenseについて</h3>
            <p>
              本サイトはGoogle AdSenseを使用しています。Google AdSenseはユーザーの興味・関心に基づいた
              パーソナライズド広告を配信するためにDoubleClickのCookieを使用することがあります。
              詳細はGoogleの
              <a href="https://policies.google.com/technologies/ads"
                 className="text-green hover:underline mx-1" target="_blank" rel="noreferrer">
                広告ポリシー
              </a>
              をご参照ください。
            </p>
            <h3 className="font-700 text-text">アクセス解析について</h3>
            <p>
              本サイトは、サービス改善のためにGoogle Analytics等のアクセス解析ツールを使用する場合があります。
              収集されるデータは匿名化されており、個人を特定するものではありません。
            </p>
            <h3 className="font-700 text-text">免責事項</h3>
            <p>
              本サイトに掲載されているコンテンツは、教育目的で提供されるものであり、投資助言ではありません。
              投資に関する最終的な判断はご自身の責任において行ってください。
            </p>
            <p className="text-xs text-muted">最終更新: 2026年2月</p>
          </div>
        </section>

        {/* English */}
        <section className="space-y-4">
          <h2 className="font-display font-700 text-bright text-lg border-b border-border pb-2">
            English
          </h2>

          <div className="space-y-3 font-body text-sm text-dim leading-relaxed">
            <p>
              This website (SENTINEL PRO) displays advertisements through Google AdSense.
              Google may use cookies to show relevant ads based on your browsing history.
            </p>
            <h3 className="font-700 text-text">About Cookies</h3>
            <p>
              This site uses cookies. You can disable cookies through your browser settings,
              though some features may not function properly as a result.
            </p>
            <h3 className="font-700 text-text">Google AdSense</h3>
            <p>
              This site uses Google AdSense, which may use the DoubleClick cookie to serve
              personalized ads based on your interests. For details, please see Google's
              <a href="https://policies.google.com/technologies/ads"
                 className="text-green hover:underline mx-1" target="_blank" rel="noreferrer">
                Advertising Policies
              </a>.
            </p>
            <h3 className="font-700 text-text">Analytics</h3>
            <p>
              This site may use Google Analytics or similar tools for service improvement.
              All data collected is anonymized and cannot identify individuals.
            </p>
            <h3 className="font-700 text-text">Disclaimer</h3>
            <p>
              All content on this site is provided for educational purposes only and does
              not constitute investment advice. All investment decisions are made at your
              own risk and responsibility.
            </p>
            <p className="text-xs text-muted">Last updated: February 2026</p>
          </div>
        </section>
      </div>
    </div>
  );
}
