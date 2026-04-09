/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        onyx: {
          900: '#050505',
          800: '#0a0a0a',
          700: '#111111',
        },
        aurora: {
          500: '#6366f1',
          600: '#4f46e5',
        },
        silk: {
          400: '#a1a1aa',
          500: '#71717a',
        }
      },
      fontFamily: {
        display: ['Cabinet Grotesk', 'sans-serif'],
        body: ['Satoshi', 'sans-serif'],
      },
      backdropBlur: {
        '4xl': '80px',
      },
      boxShadow: {
        'premium': '0 20px 50px rgba(0, 0, 0, 0.5)',
        'glow': '0 0 15px rgba(99, 102, 241, 0.3)',
      }
    },
  },
  plugins: [],
  safelist: [
    'translate-x-0',
    '-translate-x-full',
  ],
}
