/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Syne"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
        body:    ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        ink:    '#080C10',
        panel:  '#0E1318',
        border: '#1C2530',
        muted:  '#3D4F63',
        dim:    '#7A90A8',
        text:   '#D4E2F0',
        bright: '#EBF4FF',
        green:  { DEFAULT: '#22C55E', dim: '#16532A', glow: '#22C55E40' },
        amber:  { DEFAULT: '#F59E0B', dim: '#78350F' },
        red:    { DEFAULT: '#EF4444', dim: '#7F1D1D' },
        blue:   { DEFAULT: '#3B82F6', dim: '#1E3A5F' },
      },
      backgroundImage: {
        'grid-pattern': `
          linear-gradient(rgba(28,37,48,0.6) 1px, transparent 1px),
          linear-gradient(90deg, rgba(28,37,48,0.6) 1px, transparent 1px)
        `,
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'fade-up':   'fadeUp 0.5s ease forwards',
        'pulse-dot': 'pulseDot 2s ease-in-out infinite',
        'scan-line': 'scanLine 3s linear infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: 0, transform: 'translateY(16px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%,100%': { opacity: 1, transform: 'scale(1)' },
          '50%':     { opacity: 0.4, transform: 'scale(0.8)' },
        },
        scanLine: {
          from: { transform: 'translateY(-100%)' },
          to:   { transform: 'translateY(400%)' },
        },
      },
    },
  },
  plugins: [],
}
