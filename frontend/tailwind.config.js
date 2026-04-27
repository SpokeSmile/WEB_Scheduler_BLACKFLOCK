/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bf: {
          bg: '#0B0F1A',
          bg2: '#0F172A',
          orange: '#F3701E',
          cream: '#E8D8C9',
          steel: '#4B607F',
        },
      },
      boxShadow: {
        glow: '0 0 16px rgba(243, 112, 30, 0.12)',
        panel: '0 12px 34px rgba(0, 0, 0, 0.24)',
      },
    },
  },
  plugins: [],
};
