/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          50: '#FFFEFA',
          100: '#FDFBF7',
          200: '#F7F3EA',
          300: '#EFE8D9',
          400: '#DDD2BA',
          500: '#C4B495',
          border: '#E8E1D3',
          line: '#E3DCce',
        },
        ink: {
          50: '#F8FAFC',
          100: '#F1F5F9',
          200: '#E2E8F0',
          300: '#CBD5E1',
          400: '#94A3B8',
          500: '#64748B',
          600: '#475569',
          700: '#334155',
          800: '#1E293B',
          900: '#0F172A',
          dark: '#1C1917',
        },
        vintage: {
          amber: '#D97706',
          gold: '#B45309',
          red: '#DC2626',
          green: '#16A34A',
          blue: '#2563EB',
          purple: '#7C3AED',
        }
      },
      fontFamily: {
        arabic: ['Cairo', 'Tajawal', 'sans-serif'],
        latin: ['Outfit', 'Montserrat', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'notebook': '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.04)',
        'tactile': '0 4px 0 0 rgba(180, 83, 9, 0.4)',
        'tactile-green': '0 4px 0 0 rgba(22, 163, 74, 0.4)',
        'tactile-red': '0 4px 0 0 rgba(220, 38, 38, 0.4)',
        'tactile-dark': '0 4px 0 0 rgba(15, 23, 42, 0.4)',
        'pop': '0 8px 20px -4px rgba(0,0,0,0.12)',
      },
      animation: {
        'bounce-short': 'bounce 0.5s ease-in-out 2',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-fast': 'spin 0.2s linear infinite',
      }
    },
  },
  plugins: [],
}
