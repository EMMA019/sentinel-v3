import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Navbar        from './components/layout/Navbar';
import Landing       from './pages/Landing';
import Blog          from './pages/Blog';
import ArticleDetail from './pages/ArticleDetail';
import ToolPage      from './pages/ToolPage';
import Privacy       from './pages/Privacy';
import Backtest      from './pages/Backtest';
import Market       from './pages/Market';
import Strategies   from './pages/Strategies';

function Footer() {
  return (
    <footer className="border-t border-border bg-panel py-6 px-4 mt-auto">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="font-mono text-xs text-muted">
          © 2026 SENTINEL PRO — For educational purposes only. Not investment advice.
        </div>
        <div className="flex items-center gap-4">
          <Link to="/blog"      className="font-mono text-xs text-muted hover:text-dim transition">Blog</Link>
          <Link to="/backtest"  className="font-mono text-xs text-muted hover:text-dim transition">Backtest</Link>
          <Link to="/market"    className="font-mono text-xs text-muted hover:text-dim transition">Market</Link>
          <Link to="/tool"      className="font-mono text-xs text-muted hover:text-dim transition">Tool</Link>
          <Link to="/privacy"   className="font-mono text-xs text-muted hover:text-dim transition">Privacy</Link>
        </div>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/"           element={<Landing />} />
            <Route path="/blog"       element={<Blog />} />
            <Route path="/blog/:slug" element={<ArticleDetail />} />
            <Route path="/backtest"   element={<Backtest />} />
            <Route path="/market"     element={<Market />} />
            <Route path="/strategies" element={<Strategies />} />
            <Route path="/tool"       element={<ToolPage />} />
            <Route path="/privacy"    element={<Privacy />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
