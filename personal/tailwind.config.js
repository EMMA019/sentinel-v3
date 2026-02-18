/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['"IBM Plex Sans"', 'sans-serif'],
      },
      colors: {
        ink:    '#060A0F',
        panel:  '#0C1117',
        border: '#182030',
        muted:  '#364858',
        dim:    '#6B8299',
        text:   '#C8DCF0',
        bright: '#E8F4FF',
        green:  { DEFAULT: '#00FF88', dim: '#003D20', glow: '#00FF8830' },
        amber:  { DEFAULT: '#FFB800', dim: '#3D2C00' },
        red:    { DEFAULT: '#FF4466', dim: '#3D0015' },
        blue:   { DEFAULT: '#4499FF', dim: '#0A1F3D' },
        purple: { DEFAULT: '#AA66FF', dim: '#1A0A3D' },
      },
    },
  },
  plugins: [],
};
