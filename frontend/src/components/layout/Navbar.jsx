import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, Menu, X } from 'lucide-react';

const NAV_LINKS = [
  { to: '/blog',       label: 'Research'   },
  { to: '/strategies', label: 'Strategies' },
  { to: '/market',     label: 'Market'     },
  { to: '/backtest',   label: 'Backtest'   },
  { to: '/tool',       label: 'Tool'       },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-ink/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-7 h-7 rounded-md bg-green/10 border border-green/30
                          flex items-center justify-center group-hover:bg-green/20 transition">
            <Shield size={14} className="text-green" />
          </div>
          <span className="font-display font-700 text-bright text-sm tracking-wide">SENTINEL</span>
          <span className="font-mono text-xs text-green px-1.5 py-0.5 bg-green/10 rounded border border-green/20">PRO</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(l => (
            <Link key={l.to} to={l.to}
              className={`px-3 py-1.5 text-sm rounded-md transition font-body ${
                loc.pathname.startsWith(l.to)
                  ? 'text-bright bg-border'
                  : 'text-dim hover:text-text hover:bg-border/50'
              }`}>{l.label}</Link>
          ))}
        </div>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-2">
          <Link to="/tool#contact"
            className="px-4 py-1.5 rounded-lg bg-green/10 border border-green/20
                       font-mono text-xs text-green hover:bg-green/20 transition">
            利用問い合わせ
          </Link>
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden text-dim" onClick={() => setOpen(!open)}>
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-border bg-panel px-4 py-4 space-y-1">
          {NAV_LINKS.map(l => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)}
              className="block px-3 py-2 text-sm text-dim hover:text-text rounded-md
                         hover:bg-border/50 transition">
              {l.label}
            </Link>
          ))}
          <div className="pt-2 border-t border-border mt-2">
            <Link to="/tool#contact" onClick={() => setOpen(false)}
              className="block text-center px-3 py-2 rounded-lg bg-green/10 border border-green/20
                         font-mono text-xs text-green">
              利用問い合わせ
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
