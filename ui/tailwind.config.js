/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-main': 'var(--bg-main)',
        'bg-surface': 'var(--bg-surface)',
        'bg-card': 'var(--bg-card)',
        'bg-card-hover': 'var(--bg-card-hover)',
        'bg-dark': 'var(--bg-dark)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'accent': 'var(--accent)',
        'accent-soft': 'var(--accent-soft)',
        'accent-glow': 'var(--accent-glow)',
        'border-custom': 'var(--border)',
        'border-subtle': 'var(--border-subtle)',
      },
      borderRadius: {
        'xl-custom': 'var(--radius-xl)',
        'pill': 'var(--radius-pill)',
        'card': 'var(--radius-card)',
        'panel': 'var(--radius-panel)',
      },
      boxShadow: {
        'soft': 'var(--shadow)',
        'glow': 'var(--shadow-glow)',
        'float': '0 12px 36px rgba(0, 0, 0, 0.08)',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
