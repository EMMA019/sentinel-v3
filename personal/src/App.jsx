import React, { useState, useEffect } from 'react';
import { Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Star, Briefcase, ScanSearch, BarChart2, Award, Lock, LineChart, Brain } from 'lucide-react';
import Dashboard        from './pages/Dashboard';
import Watchlist        from './pages/Watchlist';
import Portfolio        from './pages/Portfolio';
import Scanner          from './pages/Scanner';
import Backtest         from './pages/Backtest';
import MethodComparison from './pages/MethodComparison';
import ChartPage        from './pages/ChartPage';
import AIJudgment       from './pages/AIJudgment';
import RealtimePage     from './pages/RealtimePage';

// ── パスワードゲート ──────────────────────────────────────
const PASS_KEY = 'sentinel_personal_auth';
const PASSWORD = import.meta.env.VITE_APP_PASSWORD || 'sentinel2026';

function PasswordGate({ children }) {
  const [auth, setAuth] = useState(() => sessionStorage.getItem(PASS_KEY) === 'ok');
  const [input, setInput] = useState('');
  const [err, setErr] = useState(false);

  if (auth) return children;

  const submit = (e) => {
    e.preventDefault();
    if (input === PASSWORD) {
      sessionStorage.setItem(PASS_KEY, 'ok');
      setAuth(true);
    } else {
      setErr(true);
      setInput('');
      setTimeout(() => setErr(false), 1500);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-ink">
      <div className="w-80">
        <div className="text-center mb-8">
          <div className="text-green font-mono text-2xl font-bold tracking-widest glow-green">SENTINEL</div>
          <div className="text-muted text-sm mt-1 font-mono">PERSONAL — RESTRICTED</div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div className={`flex items-center gap-3 bg-panel border rounded-lg px-4 py-3 transition-colors ${err ? 'border-red' : 'border-border focus-within:border-green/50'}`}>
            <Lock size={14} className="text-muted shrink-0" />
            <input
              type="password"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="パスワード"
              autoFocus
              className="bg-transparent flex-1 font-mono text-sm text-bright outline-none placeholder:text-muted"
            />
          </div>
          {err && <p className="text-red text-xs font-mono text-center">INVALID PASSWORD</p>}
          <button type="submit" className="w-full bg-green text-ink font-mono font-bold text-sm py-3 rounded-lg hover:bg-green/90 transition">
            ENTER
          </button>
        </form>
      </div>
    </div>
  );
}

// ── ナビゲーション ────────────────────────────────────────
const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/charts',    icon: LineChart,       label: 'Charts'    },
  { to: '/ai',        icon: Brain,           label: 'AI'        },
  { to: '/watchlist', icon: Star,            label: 'Watchlist' },
  { to: '/portfolio', icon: Briefcase,       label: 'Portfolio' },
  { to: '/scanner',   icon: ScanSearch,      label: 'Scanner'   },
  { to: '/methods',   icon: Award,           label: 'Methods'   },
  { to: '/backtest',  icon: BarChart2,       label: 'Backtest'  },
];

function Navbar() {
  const loc = useLocation();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-panel/95 backdrop-blur border-t border-border md:relative md:border-t-0 md:border-b">
      <div className="max-w-6xl mx-auto flex items-center justify-around md:justify-start md:gap-1 md:px-4 md:py-2">
        {/* ロゴ（デスクトップのみ） */}
        <div className="hidden md:block font-mono font-bold text-green text-sm tracking-widest mr-6 glow-green">
          SENTINEL
        </div>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-col md:flex-row items-center gap-1 md:gap-2 px-3 py-3 md:py-1.5 rounded-lg font-mono text-xs transition-colors ${
                isActive
                  ? 'text-green bg-green-dim'
                  : 'text-muted hover:text-text'
              }`
            }
          >
            <Icon size={16} strokeWidth={1.5} />
            <span className="hidden md:block">{label}</span>
            <span className="md:hidden text-[10px]">{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

// ── App ───────────────────────────────────────────────────
export default function App() {
  return (
    <PasswordGate>
      <div className="min-h-screen flex flex-col bg-ink">
        <Navbar />
        <main className="flex-1 pb-20 md:pb-0">
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/charts"    element={<ChartPage />} />
            <Route path="/ai"        element={<AIJudgment />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/scanner"   element={<Scanner />}   />
            <Route path="/methods"   element={<MethodComparison />} />
            <Route path="/backtest"  element={<Backtest />}  />
            <Route path="/realtime/:ticker" element={<RealtimePage />} />
          </Routes>
        </main>
      </div>
    </PasswordGate>
  );
}
